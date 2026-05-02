from __future__ import annotations
import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path
import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar,
)

# --- Configuration & Styling ---

_OS = platform.system()
_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 160
_RIGHT_W = 340

class C:
    """Teni Design System Colors"""
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff" # Teni Cyan
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00" # Warning/Proactive Orange
    ACC2      = "#ffcc00" # Thinking Yellow
    GREEN     = "#00ff88" # Success/Listening Green
    GREEN_D   = "#00aa55"
    RED       = "#ff3355" # Error/Muted Red
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"

def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class SysMetrics:
    """Real-time system monitoring for the left panel."""
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.net = 0.0
        self.gpu = -1.0
        self.tmp = -1.0
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                nc = psutil.net_io_counters()
                now = time.time()
                dt = now - self._last_net_t
                net = ((nc.bytes_sent - self._last_net.bytes_sent) + (nc.bytes_recv - self._last_net.bytes_recv)) / dt / (1024*1024) if dt > 0 else 0.0
                self._last_net, self._last_net_t = nc, now
                
                # Simple macOS temp/gpu fallback (Teni is macOS native)
                tmp = -1.0
                if _OS == "Darwin":
                    try:
                        # Heuristic for Apple Silicon
                        res = subprocess.run(["sysctl", "machdep.cpu.brand_string"], capture_output=True, text=True)
                        if "Apple" in res.stdout:
                            # Powermetrics is best but requires sudo. We'll use a placeholder or simpler check.
                            pass
                    except: pass

                with self._lock:
                    self.cpu, self.mem, self.net, self.tmp = cpu, mem, net, tmp
            except: pass
            time.sleep(2)

    def snapshot(self):
        with self._lock:
            return {"cpu": self.cpu, "mem": self.mem, "net": self.net, "gpu": self.gpu, "tmp": self.tmp}

_metrics = SysMetrics()

class HudCanvas(QWidget):
    """The central animated core of Teni."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.muted = False
        self.speaking = False
        self.state = "IDLE" # IDLE, THINKING, LISTENING, WATCHFUL, DORMANT
        self.has_notification = False
        
        self._tick = 0
        self._scale = 1.0
        self._tgt_scale = 1.0
        self._halo = 55.0
        self._tgt_halo = 55.0
        self._last_t = time.time()
        self._rings = [0.0, 120.0, 240.0]
        self._pulses = [0.0, 50.0, 100.0]
        self._scan = 0.0
        
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _step(self):
        self._tick += 1
        now = time.time()
        
        # Adjust dynamics based on state
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._tgt_scale, self._tgt_halo = random.uniform(1.05, 1.12), random.uniform(140, 180)
            elif self.state == "WATCHFUL":
                self._tgt_scale, self._tgt_halo = random.uniform(0.99, 1.01), random.uniform(20, 40)
            elif self.muted:
                self._tgt_scale, self._tgt_halo = 1.0, 15
            else:
                self._tgt_scale, self._tgt_halo = random.uniform(1.0, 1.02), random.uniform(45, 65)
            self._last_t = now

        sp = 0.3 if self.speaking else 0.1
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        rot_speed = [1.2, -0.8, 1.8] if self.speaking else [0.4, -0.2, 0.6]
        for i, s in enumerate(rot_speed):
            self._rings[i] = (self._rings[i] + s) % 360
        self._scan = (self._scan + (2.5 if self.speaking else 1.0)) % 360

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG))
        
        W, H = self.width(), self.height()
        cx, cy = W/2, H/2
        fw = min(W, H)
        
        # Halo
        col = qcol(C.MUTED_C if self.muted else (C.ACC2 if self.state == "THINKING" else C.PRI))
        for i in range(8):
            r = fw * 0.3 * (1.5 - i*0.1)
            a = max(0, int(self._halo * 0.1 * (1 - i/8)))
            p.setPen(QPen(qcol(col.name(), a), 1.5))
            p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))

        # Rings
        for i, r_frac in enumerate([0.45, 0.38, 0.3]):
            r = fw * r_frac
            p.setPen(QPen(qcol(col.name(), 180 - i*40), 2 - i*0.5))
            p.drawArc(QRectF(cx-r, cy-r, r*2, r*2), int(self._rings[i]*16), 120*16)
            
        # Teni Core Label
        p.setPen(QPen(qcol(C.PRI, 200)))
        p.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "T.E.N.I")
        
        # Notification Badge
        if self.has_notification:
            p.setBrush(QBrush(qcol(C.ACC)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(W-20, 20), 5, 5)

class MetricBar(QWidget):
    def __init__(self, label, color=C.PRI, parent=None):
        super().__init__(parent)
        self._label, self._color, self._value, self._text = label, color, 0.0, "--"
        self.setFixedHeight(35)
    def set_value(self, v, t):
        self._value, self._text = v, t
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.setBrush(QBrush(qcol(C.PANEL2))); p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W-2, H-2), 4, 4)
        p.setFont(QFont("Courier New", 8)); p.setPen(QPen(qcol(C.TEXT_DIM)))
        p.drawText(QRectF(5, 5, 50, 15), Qt.AlignmentFlag.AlignLeft, self._label)
        p.setPen(QPen(qcol(self._color))); p.drawText(QRectF(W-65, 5, 60, 15), Qt.AlignmentFlag.AlignRight, self._text)
        # Bar
        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.drawRect(QRectF(5, 25, W-10, 4))
        p.setBrush(QBrush(qcol(self._color)))
        p.drawRect(QRectF(5, 25, (W-10)*self._value/100, 4))

class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setStyleSheet(f"background: {C.PANEL}; color: {C.TEXT}; border: 1px solid {C.BORDER}; padding: 5px;")
        self._sig.connect(self._append)
    def _append(self, txt):
        self.append(txt)
        self.ensureCursorVisible()
    def append_log(self, txt):
        self._sig.emit(txt)

class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(80)
        self.current_file = None
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.current_file = path
            self.file_selected.emit(path)
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(qcol(C.PANEL2))); p.setPen(QPen(qcol(C.BORDER), 1, Qt.PenStyle.DashLine))
        p.drawRoundedRect(QRectF(2, 2, self.width()-4, self.height()-4), 5, 5)
        p.setPen(QPen(qcol(C.PRI_DIM)))
        txt = os.path.basename(self.current_file) if self.current_file else "Drop File Here"
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, txt)

class MainWindow(QMainWindow):
    _state_sig = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("T.E.N.I — JARVIS EDITION")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        self.setStyleSheet(f"background: {C.BG};")
        self.on_text_command = None
        self._is_compact = False
        
        # Main Container
        self.root = QWidget()
        self.setCentralWidget(self.root)
        self.layout = QHBoxLayout(self.root)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel (Metrics)
        self.left_widget = QWidget()
        self.left_panel = QVBoxLayout(self.left_widget)
        self.bar_cpu = MetricBar("CPU", C.PRI)
        self.bar_mem = MetricBar("MEM", C.ACC2)
        self.bar_net = MetricBar("NET", C.GREEN)
        self.left_panel.addWidget(QLabel("◈ MONITOR"))
        self.left_panel.addWidget(self.bar_cpu)
        self.left_panel.addWidget(self.bar_mem)
        self.left_panel.addWidget(self.bar_net)
        self.left_panel.addStretch()
        self.layout.addWidget(self.left_widget, 1)
        
        # Center (Core)
        self.hud = HudCanvas()
        self.layout.addWidget(self.hud, 3)
        
        # Right Panel (Log & Input)
        self.right_widget = QWidget()
        self.right_panel = QVBoxLayout(self.right_widget)
        self.log = LogWidget()
        self.drop_zone = FileDropZone()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Command...")
        self.input.returnPressed.connect(self._send)
        
        self.right_panel.addWidget(QLabel("◈ ACTIVITY"))
        self.right_panel.addWidget(self.log)
        self.right_panel.addWidget(self.drop_zone)
        self.right_panel.addWidget(self.input)
        
        self.mute_btn = QPushButton("🎙 ACTIVE")
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.right_panel.addWidget(self.mute_btn)
        self.layout.addWidget(self.right_widget, 2)
        
        # Shortcuts
        self.sc_compact = QShortcut(QKeySequence("Ctrl+M"), self)
        self.sc_compact.activated.connect(self.toggle_compact)
        
        # Timers
        self._metrics_tmr = QTimer(self)
        self._metrics_tmr.timeout.connect(self._update_metrics)
        self._metrics_tmr.start(2000)
        
        self._state_sig.connect(self._apply_state)

    def _update_metrics(self):
        s = _metrics.snapshot()
        self.bar_cpu.set_value(s["cpu"], f"{s['cpu']:.0f}%")
        self.bar_mem.set_value(s["mem"], f"{s['mem']:.0f}%")
        self.bar_net.set_value(min(100, s["net"]*10), f"{s['net']:.1f}MB/s")

    def _send(self):
        txt = self.input.text().strip()
        if txt and self.on_text_command:
            self.log.append_log(f"You: {txt}")
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()
            self.input.clear()

    def _toggle_mute(self):
        self.hud.muted = not self.hud.muted
        self.mute_btn.setText("🔇 MUTED" if self.hud.muted else "🎙 ACTIVE")

    def _apply_state(self, s):
        self.hud.state = s
        self.hud.speaking = (s == "SPEAKING")

    def toggle_compact(self):
        self._is_compact = not self._is_compact
        if self._is_compact:
            self.left_widget.hide()
            self.right_widget.hide()
            self.setMinimumSize(250, 250)
            self.resize(300, 300)
            # Stay on top for compact mode
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.left_widget.show()
            self.right_widget.show()
            self.setMinimumSize(_MIN_W, _MIN_H)
            self.resize(_DEFAULT_W, _DEFAULT_H)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

class TeniHUD:
    """Teni UI Interface Wrapper"""
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._win = MainWindow()
        self.on_text_command = None
    
    @property
    def muted(self): return self._win.hud.muted
    
    def set_state(self, s): self._win._state_sig.emit(s)
    def write_log(self, t): self._win.log.append_log(t)
    
    def run(self):
        self._win.on_text_command = self.on_text_command
        self._win.show()
        self._app.exec()
