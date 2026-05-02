"""
Teni AI — Jarvis-style Animated Overlay
A pure visual widget: no Dock icon, no focus stealing, fully click-through.
Uses native macOS AppKit to float above everything without acting like an app.
"""

import sys
import json
import os
import math

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QFont
)


def _make_invisible_to_macos(widget):
    """
    Use native Cocoa APIs to:
    1. Hide from Dock & Cmd-Tab (Accessory activation policy)
    2. Set window level above everything (like a screen overlay)
    3. Make it ignore ALL mouse events at the OS level
    """
    try:
        import objc  # type: ignore
        from AppKit import (  # type: ignore
            NSApp,
            NSApplication,
            NSApplicationActivationPolicyAccessory,
            NSFloatingWindowLevel,
        )

        # Hide from Dock and Cmd-Tab
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        # Get the native NSWindow backing this QWidget
        view = objc.objc_object(c_void_p=widget.winId().__int__())
        ns_window = view.window()

        # Float above all normal windows (level 3 = floating panel)
        # Using 25 = NSStatusWindowLevel which is above panels but below screen saver
        ns_window.setLevel_(25)

        # Completely ignore mouse — clicks fall through to apps below
        ns_window.setIgnoresMouseEvents_(True)

        # Don't let it become key or main window
        ns_window.setCanBecomeKeyWindow = lambda: False
        ns_window.setCanBecomeMainWindow = lambda: False

    except Exception:
        # If PyObjC fails, Qt flags alone are the fallback
        pass


class JarvisOverlay(QWidget):
    SIZE = 120
    STATE_FILE = os.path.expanduser("~/Teni/state.json")

    PALETTES = {
        "happy":   {"ring": "#00FF88", "glow": "#00FFCC", "core": "#00FF66"},
        "neutral": {"ring": "#00D4FF", "glow": "#00AAFF", "core": "#0088CC"},
        "tired":   {"ring": "#8888AA", "glow": "#6666AA", "core": "#555577"},
        "angry":   {"ring": "#FF4444", "glow": "#FF6644", "core": "#CC2222"},
    }

    def __init__(self):
        super().__init__()

        self.mood = 7
        self.energy = 8
        self.confidence = 7
        self.angle = 0.0
        self.inner_angle = 0.0
        self.pulse = 0.0
        self.speaking_amp = 0.0
        self.activity = "idle"  # idle, thinking, speaking, acting
        self.particles = []

        self._init_particles(10)
        self._init_ui()

        # Animation at ~60fps
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(16)

        # Read personality state every 300ms
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._read_state)
        self.state_timer.start(300)

    # ────────────────────── setup ──────────────────────

    def _init_ui(self):
        # Qt-level flags: frameless, on-top, no taskbar, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setFixedSize(self.SIZE, self.SIZE)

        # Bottom-right corner
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.SIZE - 20, screen.height() - self.SIZE - 60)

    def showEvent(self, event):
        """After the window is shown, apply native macOS overrides."""
        super().showEvent(event)
        _make_invisible_to_macos(self)

    def _init_particles(self, n):
        import random
        self.particles = [
            {
                "angle": random.uniform(0, 360),
                "radius": random.uniform(30, 48),
                "speed": random.uniform(0.3, 1.2),
                "size": random.uniform(1.0, 2.5),
                "phase": random.uniform(0, math.pi * 2),
            }
            for _ in range(n)
        ]

    # ────────────────────── state I/O ──────────────────────

    def _read_state(self):
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, "r") as f:
                    data = json.load(f)
                self.mood = data.get("mood", 5)
                self.energy = data.get("energy", 5)
                self.confidence = data.get("confidence", 5)
                new_activity = data.get("activity", "idle")
                self.activity = new_activity
                
                # Live volume reactivity
                vol = data.get("volume", 0.0)
                if vol > 0.1:
                    # Apply smoothing to avoid jitter
                    self.speaking_amp = max(self.speaking_amp, vol)

        except Exception:
            pass

    def _palette(self):
        if self.energy < 3:
            return self.PALETTES["tired"]
        if self.mood > 7:
            return self.PALETTES["happy"]
        if self.mood < 3:
            return self.PALETTES["angry"]
        return self.PALETTES["neutral"]

    # ────────────────────── animation tick ──────────────────────

    def _tick(self):
        speed_mult = max(0.3, self.energy / 10.0)
        
        # Activity-driven speed boost
        if self.activity == "thinking":
            speed_mult *= 2.5
        elif self.activity in ("speaking", "acting"):
            speed_mult *= 1.8
            self.speaking_amp = max(self.speaking_amp, 0.6)  # Keep pulsing
        
        self.angle = (self.angle + 0.8 * speed_mult) % 360
        self.inner_angle = (self.inner_angle - 0.5 * speed_mult) % 360
        self.pulse += 0.04 * speed_mult

        for p in self.particles:
            p["angle"] = (p["angle"] + p["speed"] * speed_mult) % 360

        self.speaking_amp *= 0.94
        self.update()

    # ────────────────────── painting ──────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.SIZE / 2, self.SIZE / 2
        pal = self._palette()

        breath = 1.0 + 0.06 * math.sin(self.pulse)
        react = 1.0 + 0.12 * self.speaking_amp

        # 1. Background glow
        glow_r = 42 * breath * react
        grad = QRadialGradient(QPointF(cx, cy), glow_r)
        gc = QColor(pal["glow"])
        gc.setAlpha(50)
        grad.setColorAt(0.0, gc)
        gc2 = QColor(pal["glow"])
        gc2.setAlpha(0)
        grad.setColorAt(1.0, gc2)
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # 2. Outer rotating arcs
        ring_r = 46 * breath * react
        self._draw_arc_ring(painter, cx, cy, ring_r, self.angle, pal["ring"], 2.0, 3, 30)

        # 3. Inner counter-rotating arcs
        inner_r = 34 * breath * react
        self._draw_arc_ring(painter, cx, cy, inner_r, self.inner_angle, pal["ring"], 1.4, 4, 20)

        # 4. Dashed orbit
        mid_r = 40 * breath * react
        dash_pen = QPen(QColor(pal["ring"]))
        dash_pen.setWidthF(0.6)
        dash_pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(dash_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), mid_r, mid_r)

        # 5. Particles
        for p in self.particles:
            pa = math.radians(p["angle"])
            wobble = 1.0 + 0.15 * math.sin(self.pulse * 2 + p["phase"])
            pr = p["radius"] * breath * wobble * react
            px = cx + math.cos(pa) * pr
            py = cy + math.sin(pa) * pr
            pc = QColor(pal["glow"])
            pc.setAlpha(180)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(pc)
            painter.drawEllipse(QPointF(px, py), p["size"], p["size"])

        # 6. Core
        core_r = 14 * breath * react
        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        core_c = QColor(pal["core"])
        core_c.setAlpha(200)
        core_grad.setColorAt(0.0, core_c)
        core_c2 = QColor(pal["core"])
        core_c2.setAlpha(60)
        core_grad.setColorAt(1.0, core_c2)
        painter.setBrush(core_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # 7. Centre dot
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.drawEllipse(QPointF(cx, cy), 2 * breath, 2 * breath)

        # 8. Status text
        painter.setPen(QColor(pal["glow"]))
        painter.setFont(QFont("Menlo", 7))
        painter.drawText(
            QRectF(0, cy + 28, self.SIZE, 16),
            Qt.AlignmentFlag.AlignCenter,
            self._status_label(),
        )
        painter.end()

    def _draw_arc_ring(self, painter, cx, cy, radius, rotation, color_hex, width, segments, gap):
        span = (360 - segments * gap) / segments
        pen = QPen(QColor(color_hex))
        pen.setWidthF(width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        for i in range(segments):
            start = rotation + i * (span + gap)
            painter.drawArc(rect, int(start * 16), int(span * 16))

    def _status_label(self):
        if self.activity == "thinking":
            return "THINKING"
        if self.activity == "speaking":
            return "SPEAKING"
        if self.activity == "acting":
            return "ACTING"
        if self.energy < 3:
            return "STANDBY"
        if self.mood > 7:
            return "OPTIMAL"
        if self.mood < 3:
            return "ALERT"
        return "ONLINE"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = JarvisOverlay()
    overlay.show()
    sys.exit(app.exec())
