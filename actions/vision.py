"""
Vision Module — Screen capture and webcam analysis via Gemini multimodal.
Adapted from Mark-XXXV's screen_processor.py for macOS.
"""

import asyncio
import base64
import io
import json
import re
import threading
import time
import traceback

import sounddevice as sd
import numpy as np

try:
    import mss
    import mss.tools
    _MSS_OK = True
except ImportError:
    _MSS_OK = False

try:
    import cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

try:
    import PIL.Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from google import genai
from google.genai import types
from config import Config

IMG_MAX_W = 640
IMG_MAX_H = 360
JPEG_Q = 55

VISION_PROMPT = (
    "You are TENI, Aansh's personal AI assistant. "
    "Analyze images with precision and intelligence. "
    "Be concise, smart, and helpful. "
    "Respond in 2 short sentences. Speed is priority. "
    "Address the user as 'Aansh'."
)


def _to_jpeg(img_bytes: bytes) -> bytes:
    if not _PIL_OK:
        return img_bytes
    img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail([IMG_MAX_W, IMG_MAX_H], PIL.Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q, optimize=False)
    return buf.getvalue()


def _capture_screenshot() -> bytes:
    if not _MSS_OK:
        raise RuntimeError("mss not installed — cannot capture screen")
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        png_bytes = mss.tools.to_png(shot.rgb, shot.size)
    return _to_jpeg(png_bytes)


def _capture_camera() -> bytes:
    if not _CV2_OK:
        raise RuntimeError("opencv not installed — cannot capture camera")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Camera could not be opened")
    for _ in range(10):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError("Could not capture camera frame")
    if _PIL_OK:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail([IMG_MAX_W, IMG_MAX_H], PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_Q, optimize=False)
        return buf.getvalue()
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    return buf.tobytes()


class _VisionSession:
    """Separate Gemini Live session for vision analysis."""

    def __init__(self):
        self._loop = None
        self._thread = None
        self._session = None
        self._out_queue = None
        self._audio_in = None
        self._ready = threading.Event()
        self._player = None

    def start(self, player=None):
        if self._thread and self._thread.is_alive():
            return
        self._player = player
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="VisionThread"
        )
        self._thread.start()
        ok = self._ready.wait(timeout=20)
        if not ok:
            raise RuntimeError("Vision session did not start")
        print("[Vision] ✅ Ready")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        self._out_queue = asyncio.Queue(maxsize=30)
        self._audio_in = asyncio.Queue()

        client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
            http_options={"api_version": "v1beta"}
        )

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            system_instruction=VISION_PROMPT,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=Config.GEMINI_VOICE
                    )
                )
            ),
        )

        while True:
            try:
                print("[Vision] 🔌 Connecting...")
                async with client.aio.live.connect(
                    model=Config.GEMINI_LIVE_MODEL, config=config
                ) as session:
                    self._session = session
                    self._ready.set()
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._send_loop())
                        tg.create_task(self._recv_loop())
                        tg.create_task(self._play_loop())
            except Exception as e:
                print(f"[Vision] ⚠️ {e}")
                self._session = None
                self._ready.clear()
                await asyncio.sleep(2)
                self._ready.set()

    async def _send_loop(self):
        while True:
            item = await self._out_queue.get()
            if self._session:
                image_bytes, mime_type, user_text = item
                try:
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    await self._session.send_client_content(
                        turns={
                            "parts": [
                                {"inline_data": {"mime_type": mime_type, "data": b64}},
                                {"text": user_text}
                            ]
                        },
                        turn_complete=True
                    )
                    print("[Vision] ✅ Image sent")
                except Exception as e:
                    print(f"[Vision] ⚠️ Send error: {e}")

    async def _recv_loop(self):
        transcript_buf = []
        try:
            async for response in self._session.receive():
                if response.data:
                    await self._audio_in.put(response.data)
                sc = response.server_content
                if not sc:
                    continue
                if sc.output_transcription and sc.output_transcription.text:
                    chunk = sc.output_transcription.text.strip()
                    if chunk:
                        transcript_buf.append(chunk)
                if sc.turn_complete:
                    if transcript_buf and self._player:
                        full = re.sub(r'\s+', ' ', " ".join(transcript_buf)).strip()
                        if full:
                            self._player.write_log(f"Teni: {full}")
                            print(f"[Vision] 💬 {full}")
                    transcript_buf = []
        except Exception as e:
            print(f"[Vision] ⚠️ Recv error: {e}")
            transcript_buf = []

    async def _play_loop(self):
        stream = sd.RawOutputStream(
            samplerate=Config.RECEIVE_SAMPLE_RATE,
            channels=Config.AUDIO_CHANNELS,
            dtype="int16",
            blocksize=Config.AUDIO_CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self._audio_in.get()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[Vision] ❌ Play error: {e}")
            raise
        finally:
            stream.stop()
            stream.close()

    def analyze(self, image_bytes, mime_type, user_text):
        if not self._loop:
            return
        asyncio.run_coroutine_threadsafe(
            self._out_queue.put((image_bytes, mime_type, user_text)),
            self._loop
        )


_live = _VisionSession()
_started = False
_start_lock = threading.Lock()


def _ensure_started(player=None):
    global _started
    with _start_lock:
        if not _started:
            _live.start(player=player)
            _started = True
        elif player is not None:
            _live._player = player


def screen_process(parameters: dict, player=None) -> str:
    """Capture screen/camera and analyze with Gemini vision."""
    user_text = (parameters or {}).get("text", "").strip()
    if not user_text:
        return "No question provided."

    angle = (parameters or {}).get("angle", "screen").lower().strip()
    print(f"[Vision] angle={angle}  text={user_text}")

    _ensure_started(player=player)

    try:
        if angle == "camera":
            image_bytes = _capture_camera()
            mime_type = "image/jpeg"
            print("[Vision] 📷 Camera captured")
        else:
            image_bytes = _capture_screenshot()
            mime_type = "image/jpeg"
            print("[Vision] 🖥️ Screen captured")
    except Exception as e:
        traceback.print_exc()
        return f"Capture error: {e}"

    _live.analyze(image_bytes, mime_type, user_text)
    return "Vision module activated — analyzing now."
