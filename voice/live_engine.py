"""
Live Voice Engine — Gemini bidirectional audio streaming.
Real-time, human-quality voice conversation with tool execution.
Adapted from Mark-XXXV for macOS + Teni architecture.
"""

import asyncio
import threading
import json
import traceback
import numpy as np
from datetime import datetime

import sounddevice as sd
from google import genai
from google.genai import types

from config import Config


# ── Tool Declarations for Gemini Function Calling ────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens/activates any application on macOS. Always use this — never just say you opened it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "App name e.g. 'Safari', 'Notes', 'Terminal'"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "close_app",
        "description": "Closes an application.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "App name to close"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "search_web",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_note",
        "description": "Creates a new note in Apple Notes with a title and body.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Note title"},
                "body": {"type": "STRING", "description": "Note content"}
            },
            "required": ["title", "body"]
        }
    },
    {
        "name": "compose_email",
        "description": "Composes an email in Mail.app.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {"type": "STRING", "description": "Recipient email"},
                "subject": {"type": "STRING", "description": "Email subject"},
                "body": {"type": "STRING", "description": "Email body"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "split_windows",
        "description": "Splits two apps side by side on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app1": {"type": "STRING", "description": "Left app"},
                "app2": {"type": "STRING", "description": "Right app"}
            },
            "required": ["app1", "app2"]
        }
    },
    {
        "name": "screenshot",
        "description": "Takes a screenshot of the entire screen.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "volume_control",
        "description": "Controls system volume: up, down, mute.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "direction": {"type": "STRING", "description": "up, down, or mute"}
            },
            "required": ["direction"]
        }
    },
    {
        "name": "type_text",
        "description": "Types text into the currently focused application.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "Text to type"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "press_key",
        "description": "Presses a keyboard shortcut or key.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Key to press"},
                "modifiers": {"type": "STRING", "description": "Comma-separated: command, shift, option, control"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "run_shell_safe",
        "description": "Runs a safe shell command on macOS.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "Shell command to execute"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "git_push",
        "description": "Commits all changes and pushes to GitHub.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Repository path (default: current)"},
                "message": {"type": "STRING", "description": "Commit message"}
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam. "
            "Call when user asks what is on screen, analyze screen, look at camera etc. "
            "After calling, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' or 'camera'. Default: 'screen'"},
                "text": {"type": "STRING", "description": "Question about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call silently when the user reveals something worth remembering. "
            "Do NOT announce that you are saving."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "identity | preferences | projects | relationships | wishes | notes"},
                "key": {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food)"},
                "value": {"type": "STRING", "description": "Concise value in English"}
            },
            "required": ["category", "key", "value"]
        }
    },
]


class LiveEngine:
    """Gemini Live Audio — real-time bidirectional voice with tool execution."""

    def __init__(self, executor, ui=None, biometrics=None):
        self.executor = executor
        self.ui = ui
        self.biometrics = biometrics
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._muted = False
        self._running = False

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, val):
        self._muted = val
        if self.ui:
            self.ui.set_state("MUTED" if val else "LISTENING")

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if self.ui:
            if value:
                self.ui.set_state("SPEAKING")
            elif not self._muted:
                self.ui.set_state("LISTENING")

    def send_text(self, text: str):
        """Send a text command to the Gemini session (for typed input)."""
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def _build_config(self) -> types.LiveConnectConfig:
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")

        # Load long-term memory if available
        mem_str = ""
        try:
            from memory.long_term import load_memory, format_memory_for_prompt
            memory = load_memory()
            mem_str = format_memory_for_prompt(memory)
        except Exception:
            pass

        sys_prompt = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n\n"
            f"{mem_str}\n"
            f"You are TENI — Aansh's personal AI assistant on macOS. "
            f"You are sharp, calm, efficient, and slightly witty — like Jarvis. "
            f"Address the user as 'Aansh'. Be concise (1-2 sentences max). "
            f"Always use the correct tool. Never simulate results. "
            f"Keep responses SHORT. Speed is priority. "
            f"If you need to perform an action, call the tool FIRST, then report briefly."
        )

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=sys_prompt,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=Config.GEMINI_VOICE
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        """Execute a tool call from Gemini and return the result."""
        name = fc.name
        args = dict(fc.args or {})
        print(f"[TENI] 🔧 Tool: {name}  Args: {args}")

        if self.ui:
            self.ui.set_state("THINKING")

        # Handle save_memory silently
        if name == "save_memory":
            try:
                from memory.long_term import update_memory
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] 💾 {cat}/{key} = {val}")
            except Exception as e:
                print(f"[Memory] ⚠️ {e}")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        # Route to Teni's ExecutionEngine
        loop = asyncio.get_event_loop()
        result = "Done."

        try:
            # Build a normalized intent for the executor
            intent = {"action": name, "parameters": args}
            exec_result = await loop.run_in_executor(
                None, lambda: self.executor.execute(intent)
            )
            if isinstance(exec_result, dict):
                result = exec_result.get("message", exec_result.get("error", "Done."))
            else:
                result = str(exec_result)
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()

        if self.ui and not self._muted:
            self.ui.set_state("LISTENING")

        print(f"[TENI] 📤 {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        """Send mic audio chunks to Gemini."""
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        """Capture mic audio and queue for sending."""
        print("[TENI] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self._muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": data, "mime_type": "audio/pcm"}
                )

        try:
            with sd.InputStream(
                samplerate=Config.SEND_SAMPLE_RATE,
                channels=Config.AUDIO_CHANNELS,
                dtype="int16",
                blocksize=Config.AUDIO_CHUNK_SIZE,
                callback=callback,
            ):
                print("[TENI] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[TENI] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        """Receive audio and transcriptions from Gemini."""
        print("[TENI] 👂 Receiver started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self.set_speaking(False)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                if self.ui:
                                    self.ui.write_log(f"You: {full_in}")
                                print(f"[TENI] 🗣️ You: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                if self.ui:
                                    self.ui.write_log(f"Teni: {full_out}")
                                print(f"[TENI] 🤖 Teni: {full_out}")
                            out_buf = []

                            # Background memory extraction
                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=self._update_memory_bg,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[TENI] 📞 Calling: {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[TENI] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        """Play received audio from Gemini through speakers."""
        print("[TENI] 🔊 Audio player started")

        stream = sd.RawOutputStream(
            samplerate=Config.RECEIVE_SAMPLE_RATE,
            channels=Config.AUDIO_CHANNELS,
            dtype="int16",
            blocksize=Config.AUDIO_CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[TENI] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    def _update_memory_bg(self, user_text: str, ai_text: str):
        """Background thread to extract and save memory."""
        try:
            from memory.long_term import should_extract_memory, extract_memory, update_memory
            if not should_extract_memory(user_text, ai_text, Config.GEMINI_API_KEY):
                return
            data = extract_memory(user_text, ai_text, Config.GEMINI_API_KEY)
            if data:
                update_memory(data)
                print(f"[Memory] ✅ Auto-saved: {list(data.keys())}")
        except Exception as e:
            if "429" not in str(e):
                print(f"[Memory] ⚠️ {e}")

    async def _run(self):
        """Main async loop — connects to Gemini and runs all tasks."""
        client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
            http_options={"api_version": "v1beta"}
        )

        while self._running:
            try:
                print("[TENI] 🔌 Connecting to Gemini Live...")
                if self.ui:
                    self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(
                        model=Config.GEMINI_LIVE_MODEL, config=config
                    ) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    print("[TENI] ✅ Connected to Gemini Live.")
                    if self.ui:
                        self.ui.set_state("LISTENING")
                        self.ui.write_log("SYS: TENI online. Listening...")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[TENI] ⚠️ {e}")
                traceback.print_exc()

            self.set_speaking(False)
            if self.ui:
                self.ui.set_state("THINKING")
            print("[TENI] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

    def start(self):
        """Start the live engine in a background thread."""
        self._running = True
        thread = threading.Thread(target=self._thread_entry, daemon=True)
        thread.start()

    def _thread_entry(self):
        asyncio.run(self._run())

    def stop(self):
        self._running = False
