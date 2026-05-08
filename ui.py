"""
J.A.R.V.I.S — IRON PROTOCOL · NEXUS EDITION
ui.py — Holographic Interface System

Visual paradigm: Iron Man-inspired arc reactor HUD with holographic
panels, plasma energy conduits, angular military-grade geometry,
hexagonal data matrices, and neon-outlined void architecture.

All public API preserved from previous editions.
"""
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
    QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent,
    QFont, QFontDatabase, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar, QGraphicsDropShadowEffect,
)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 1400, 860
_MIN_W,     _MIN_H     = 1000, 680
_LEFT_W  = 210
_RIGHT_W = 420

_OS = platform.system()


# ─────────────────────────────────────────────────────────────────
#  IRON PROTOCOL COLOUR PALETTE
#  Arc reactor plasma · military darkness · holographic light
# ─────────────────────────────────────────────────────────────────
class C:
    # ── Void substrates ─────────────────────────────────────────
    BG        = "#010408"       # deep void
    PANEL     = "#040b14"       # armour plate dark
    PANEL2    = "#060f1a"       # armour plate mid
    PANEL3    = "#08121f"       # armour plate lit
    VOID      = "#000204"       # singularity black

    # ── Structural borders ───────────────────────────────────────
    BORDER    = "#071525"
    BORDER_B  = "#0f2a42"
    BORDER_A  = "#152e4a"
    BORDER_G  = "#0a1e10"

    # ── ARC REACTOR BLUE — primary energy signal ─────────────────
    PRI       = "#00c8ff"       # arc plasma blue
    PRI_DIM   = "#005a7a"
    PRI_GHO   = "#001520"
    PRI_GLOW  = "#80e8ff"
    PRI_ULTRA = "#ffffff"
    PRI_DEEP  = "#002535"

    # ── PLASMA GOLD — secondary energy / power ───────────────────
    ACC       = "#ffaa00"       # plasma gold
    ACC2      = "#ffd060"
    ACC_DIM   = "#7a4800"
    ACC_GLOW  = "#ffe8a0"
    ACC_DEEP  = "#1e0f00"

    # ── TACTICAL GREEN — system health ───────────────────────────
    GREEN     = "#00ff88"
    GREEN_D   = "#009952"
    GREEN_G   = "#001a10"
    GREEN_ULT = "#80ffcc"

    # ── ALERT RED — danger / muted ───────────────────────────────
    RED       = "#ff2244"
    RED_G     = "#1a0010"
    RED_D     = "#7a0025"
    MUTED_C   = "#ff2244"

    # ── VIOLET — processing ──────────────────────────────────────
    VIOLET    = "#aa44ff"
    VIOLET_D  = "#4a1a80"
    VIOLET_G  = "#130028"

    # ── Text hierarchy ───────────────────────────────────────────
    TEXT      = "#5ab8d8"
    TEXT_DIM  = "#1e4a60"
    TEXT_MED  = "#3888a8"
    TEXT_BRIGHT = "#a0ddf0"
    WHITE     = "#e8f8ff"

    # ── Misc system ──────────────────────────────────────────────
    BAR_BG    = "#020b12"
    TEAL      = "#00bbee"
    TEAL_D    = "#004460"
    CYAN      = "#00ffff"
    ORANGE    = "#ff6600"
    GOLD      = "#ffcc00"
    AMBER     = "#ff9900"
    AMBER2    = "#ffcc66"
    AMBER_D   = "#7a4400"
    AMBER_G   = "#150800"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(max(0, min(255, int(a)))); return c


# ─────────────────────────────────────────────────────────────────
#  SYSTEM METRICS
# ─────────────────────────────────────────────────────────────────
class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0

        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now
        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
            }


_metrics = _SysMetrics()


# ─────────────────────────────────────────────────────────────────
#  ARC REACTOR HUD CANVAS — IRON PROTOCOL
#  Hexagonal matrices, plasma arcs, energy conduits, orbital rings
# ─────────────────────────────────────────────────────────────────
class HudCanvas(QWidget):
    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(340, 340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 50.0
        self._tgt_halo   = 50.0
        self._last_t     = time.time()
        self._blink      = True
        self._blink_tick = 0

        # Hexagonal grid points
        self._hex_grid: list[tuple] = []
        self._regen_hex_grid()

        # Arc reactor rings
        self._rings = [i * (360 / 8) for i in range(8)]
        self._ring_speeds = [0.8, -0.5, 1.2, -0.3, 0.6, -0.9, 0.4, -0.7]

        # Energy conduit lines (angular, Iron Man style)
        self._conduits: list[dict] = []
        self._regen_conduits()

        # Data stream particles along conduits
        self._particles: list[dict] = []
        self._particle_timer = 0

        # Plasma burst rings
        self._pulses: list[dict] = []

        # Scanner sweep
        self._scan_angle = 0.0

        # Waveform
        self._wave_data = [0.0] * 80
        self._wave_phase = 0.0

        # Targeting brackets
        self._bracket_rot = 0.0

        # Holographic data nodes
        self._data_nodes: list[dict] = []
        self._regen_data_nodes()

        # Triangular corner accents
        self._tri_rot = 0.0

        # Arc reactor animation accumulator
        self._arc_t = 0.0

        # Face image
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        # Chromatic aberration
        self._chrom_t = 0.0

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(14)   # ~70fps

    # ── DATA GENERATION ──────────────────────────────────────────

    def _regen_hex_grid(self):
        """Generate hexagonal grid for the HUD background."""
        self._hex_grid = []
        for q in range(-6, 7):
            for r in range(-6, 7):
                x = q + r * 0.5
                y = r * 0.866
                dist = math.hypot(x, y)
                if 1.5 < dist < 5.8:
                    self._hex_grid.append((x, y, random.uniform(0, math.pi * 2),
                                           random.uniform(0.008, 0.025)))

    def _regen_conduits(self):
        """Angular energy conduit lines — Iron Man style."""
        self._conduits = []
        angles = [0, 30, 60, 90, 120, 150, 210, 240, 270, 300, 330]
        for ang in angles:
            rad = math.radians(ang)
            self._conduits.append({
                "angle": rad,
                "r_start": 0.22,
                "r_end": random.uniform(0.55, 0.72),
                "color": random.choice([C.PRI, C.PRI, C.ACC, C.GREEN]),
                "width": random.uniform(0.5, 1.8),
                "phase": random.uniform(0, math.pi * 2),
            })

    def _regen_data_nodes(self):
        """Floating holographic data nodes."""
        self._data_nodes = []
        labels = ["SYS", "NET", "AI", "MEM", "PWR", "SEC", "QTM", "SYN"]
        colors = [C.PRI, C.ACC, C.GREEN, C.VIOLET, C.PRI, C.GREEN, C.ACC, C.PRI]
        for i, (lbl, col) in enumerate(zip(labels, colors)):
            ang = math.radians(i * 45 + 22.5)
            self._data_nodes.append({
                "label": lbl,
                "color": col,
                "angle": ang,
                "r_frac": random.uniform(0.60, 0.72),
                "phase": random.uniform(0, math.pi * 2),
                "val": random.randint(20, 95),
            })

    # ── STEP ─────────────────────────────────────────────────────

    def _step(self):
        self._tick += 1
        now = time.time()
        speak = self.speaking
        muted = self.muted

        # Scale / halo
        if now - self._last_t > (0.07 if speak else 0.40):
            if speak:
                self._tgt_scale = random.uniform(1.04, 1.10)
                self._tgt_halo  = random.uniform(160, 220)
            elif muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo  = random.uniform(6, 18)
            else:
                self._tgt_scale = random.uniform(1.0, 1.015)
                self._tgt_halo  = random.uniform(55, 85)
            self._last_t = now

        self._scale = self._scale + (self._tgt_scale - self._scale) * 0.12
        self._halo  = self._halo  + (self._tgt_halo  - self._halo)  * 0.10

        # Rings
        for i, spd in enumerate(self._ring_speeds):
            self._rings[i] = (self._rings[i] + spd * (2.2 if speak else 1.0)) % 360

        # Scan angle
        self._scan_angle = (self._scan_angle + (3.5 if speak else 1.8)) % 360

        # Bracket rotation
        self._bracket_rot = (self._bracket_rot + (0.4 if speak else 0.15)) % 360

        # Tri rotation
        self._tri_rot = (self._tri_rot + (0.6 if speak else 0.2)) % 360

        # Chromatic aberration
        self._chrom_t += 0.045

        # Arc reactor time advance
        self._arc_t += 0.012

        # Blink
        self._blink_tick += 1
        if self._blink_tick >= (8 if speak else 24):
            self._blink = not self._blink
            self._blink_tick = 0

        # Hex grid phase
        self._hex_grid = [
            (x, y, ph + spd, spd)
            for x, y, ph, spd in self._hex_grid
        ]

        # Data nodes value drift
        if self._tick % 45 == 0:
            for nd in self._data_nodes:
                nd["val"] = max(5, min(99, nd["val"] + random.randint(-8, 8)))
                nd["r_frac"] = 0.60 + 0.12 * math.sin(nd["phase"] + self._tick * 0.008)

        # Particles
        self._particle_timer += 1
        if self._particle_timer >= (3 if speak else 8):
            self._particle_timer = 0
            cond = random.choice(self._conduits)
            self._particles.append({
                "angle": cond["angle"],
                "r": cond["r_start"],
                "r_end": cond["r_end"],
                "color": cond["color"],
                "speed": random.uniform(0.008, 0.022),
                "size": random.uniform(1.8, 4.0),
                "life": 1.0,
            })

        self._particles = [p for p in self._particles if p["r"] < p["r_end"]]
        for p2 in self._particles:
            p2["r"] += p2["speed"]
            p2["life"] = 1.0 - (p2["r"] - p2["r_end"] * 0.5) / (p2["r_end"] * 0.5)

        # Pulse rings
        if self._tick % (12 if speak else 40) == 0:
            self._pulses.append({"r": 0.0, "life": 1.0, "color": C.PRI if not muted else C.RED})
        self._pulses = [p3 for p3 in self._pulses if p3["life"] > 0]
        for p3 in self._pulses:
            p3["r"] += 0.012
            p3["life"] -= 0.025

        # Waveform
        self._wave_phase += 0.08 if speak else 0.03
        target_amp = random.uniform(0.5, 1.0) if speak else random.uniform(0.05, 0.25)
        for i in range(80):
            t_val = target_amp * abs(math.sin(i * 0.22 + self._wave_phase))
            self._wave_data[i] = self._wave_data[i] * 0.7 + t_val * 0.3

        self.update()

    # ── PAINT ─────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        W, H = self.width(), self.height()
        cx, cy = W / 2.0, H / 2.0
        fw = min(W, H) * 0.5

        # Background
        bg_g = QRadialGradient(QPointF(cx, cy), fw * 1.4)
        bg_g.setColorAt(0.0, qcol(C.PANEL, 255))
        bg_g.setColorAt(0.5, qcol(C.PANEL2, 255))
        bg_g.setColorAt(1.0, qcol(C.VOID, 255))
        p.fillRect(self.rect(), QBrush(bg_g))

        # Draw layers
        self._draw_hex_grid(p, cx, cy, fw)
        self._draw_conduits(p, cx, cy, fw)
        self._draw_outer_rings(p, cx, cy, fw)
        self._draw_pulse_rings(p, cx, cy, fw)
        self._draw_scanner(p, cx, cy, fw)
        self._draw_arc_corona(p, cx, cy, fw)
        self._draw_bracket_ring(p, cx, cy, fw)
        self._draw_inner_hex(p, cx, cy, fw)
        self._draw_face(p, cx, cy, fw)
        self._draw_particles(p, cx, cy, fw)
        self._draw_data_nodes(p, cx, cy, fw)
        self._draw_corner_triangles(p, cx, cy, fw, W, H)
        self._draw_crosshair(p, cx, cy, fw)
        self._draw_state_label(p, cx, cy, fw, W, H)
        self._draw_wave(p, cx, cy, fw, W, H)

    def _draw_hex_grid(self, p: QPainter, cx: float, cy: float, fw: float):
        """Hexagonal background grid — military HUD aesthetic."""
        p.setPen(Qt.PenStyle.NoPen)
        hex_scale = fw * 0.088
        for x, y, phase, _ in self._hex_grid:
            sx = cx + x * hex_scale
            sy = cy + y * hex_scale
            dist = math.hypot(x, y) / 5.8
            alpha = max(0, int(22 * (1.0 - dist) * (0.5 + 0.5 * math.sin(phase))))
            if alpha < 2:
                continue
            col = qcol(C.PRI, alpha)
            p.setPen(QPen(col, 0.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Draw hexagon
            path = QPainterPath()
            r_hex = hex_scale * 0.48
            for k in range(6):
                hang = math.radians(k * 60 + 30)
                hx = sx + math.cos(hang) * r_hex
                hy = sy + math.sin(hang) * r_hex
                if k == 0:
                    path.moveTo(hx, hy)
                else:
                    path.lineTo(hx, hy)
            path.closeSubpath()
            p.drawPath(path)

    def _draw_conduits(self, p: QPainter, cx: float, cy: float, fw: float):
        """Angular energy conduit lines radiating from center."""
        for cond in self._conduits:
            ang = cond["angle"] + self._rings[0] * 0.002
            r1 = cond["r_start"] * fw
            r2 = cond["r_end"] * fw
            x1 = cx + math.cos(ang) * r1
            y1 = cy + math.sin(ang) * r1
            x2 = cx + math.cos(ang) * r2
            y2 = cy + math.sin(ang) * r2
            alpha = int(35 + 25 * math.sin(cond["phase"] + self._tick * 0.04))
            p.setPen(QPen(qcol(cond["color"], alpha), cond["width"]))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_outer_rings(self, p: QPainter, cx: float, cy: float, fw: float):
        """Concentric arc rings — Iron Man HUD style."""
        ring_configs = [
            (0.85, 1.4, 80, 55, C.PRI, 40),
            (0.78, 2.0, 72, 42, C.PRI, 30),
            (0.71, 1.2, 110, 28, C.ACC, 22),
            (0.64, 1.8, 88, 35, C.PRI, 28),
        ]
        for r_frac, ww, arc_l, gap, col_h, base_a in ring_configs:
            ring_r = fw * r_frac
            base   = self._rings[0]
            a_val  = max(0, min(220, int(self._halo * 0.9 * base_a / 60)))
            col    = qcol(C.MUTED_C if self.muted else col_h, a_val)
            p.setPen(QPen(col, ww))
            p.setBrush(Qt.BrushStyle.NoBrush)
            rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            angle = base
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        # Tick ring
        tick_r = fw * 0.68
        for deg in range(0, 360, 3):
            rad   = math.radians(deg + self._rings[1] * 0.02)
            major = deg % 30 == 0
            mid_t = deg % 10 == 0
            r_out = tick_r
            r_in  = tick_r - (8 if major else (4 if mid_t else 2))
            alpha = 200 if major else (100 if mid_t else 40)
            col = qcol(C.PRI if major else (C.ACC if mid_t else C.TEAL), alpha)
            p.setPen(QPen(col, 2.0 if major else (1.0 if mid_t else 0.5)))
            p.drawLine(
                QPointF(cx + r_out * math.cos(rad), cy + r_out * math.sin(rad)),
                QPointF(cx + r_in  * math.cos(rad), cy + r_in  * math.sin(rad)),
            )

    def _draw_pulse_rings(self, p: QPainter, cx: float, cy: float, fw: float):
        """Expanding plasma pulse rings."""
        for pulse in self._pulses:
            r_p = pulse["r"] * fw * 1.2
            a_p = int(pulse["life"] * 140)
            p.setPen(QPen(qcol(pulse["color"], a_p), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r_p, cy - r_p, r_p * 2, r_p * 2))

    def _draw_scanner(self, p: QPainter, cx: float, cy: float, fw: float):
        """Rotating plasma scanner sweep with decay trail."""
        sr = fw * 0.65
        arc_span = 90 if self.speaking else 55
        col_h = C.MUTED_C if self.muted else C.PRI
        ang = self._scan_angle

        for ti in range(8):
            t_ang = ang - ti * (arc_span * 0.11)
            t_a   = max(0, int(self._halo * 0.9 * (1.0 - ti * 0.13)))
            srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
            p.setPen(QPen(qcol(col_h, t_a // (4 if ti > 0 else 1)), 1.8 if ti == 0 else 0.8))
            p.drawArc(srect, int(t_ang * 16), int(arc_span * 0.55 * 16))

    def _draw_arc_corona(self, p: QPainter, cx: float, cy: float, fw: float):
        """Arc reactor corona glow — the heart of the system."""
        base_r = fw * 0.30

        # Outer multi-ring glow
        for i in range(20):
            r4 = base_r * (1.0 - i * 0.048) * self._scale
            frc = 1.0 - i / 20
            a   = max(0, int(self._halo * 0.075 * frc))
            if self.muted:
                col = qcol(C.MUTED_C, a)
            else:
                col = qcol(C.PRI if i < 10 else C.ACC, a)
            pw = max(0.3, 2.8 - i * 0.12)
            p.setPen(QPen(col, pw))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r4, cy - r4, r4 * 2, r4 * 2))

        # Radial gradient fill
        grad = QRadialGradient(QPointF(cx, cy), base_r * self._scale)
        if self.muted:
            grad.setColorAt(0.0, qcol(C.RED, int(self._halo * 0.9)))
            grad.setColorAt(0.5, qcol(C.RED_D, int(self._halo * 0.4)))
            grad.setColorAt(1.0, qcol(C.VOID, 0))
        else:
            grad.setColorAt(0.0, qcol(C.PRI, int(self._halo * 1.1)))
            grad.setColorAt(0.3, qcol(C.PRI_DIM, int(self._halo * 0.35)))
            grad.setColorAt(0.7, qcol(C.ACC, int(self._halo * 0.06)))
            grad.setColorAt(1.0, qcol(C.VOID, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        r_fill = base_r * self._scale
        p.drawEllipse(QRectF(cx - r_fill, cy - r_fill, r_fill * 2, r_fill * 2))

    def _draw_bracket_ring(self, p: QPainter, cx: float, cy: float, fw: float):
        """Rotating targeting bracket ring with corner marks."""
        half = fw * 0.515
        rot  = math.radians(self._bracket_rot)
        col  = qcol(C.MUTED_C if self.muted else C.PRI, 200)
        p.setPen(QPen(col, 2.0))

        for base_ang in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
            ang   = base_ang + rot
            hx    = cx + math.cos(ang) * half
            hy    = cy + math.sin(ang) * half
            tang  = ang + math.pi / 2
            arm_len = fw * 0.052

            # Angular bracket arms
            p.drawLine(QPointF(hx + math.cos(tang) * arm_len, hy + math.sin(tang) * arm_len),
                       QPointF(hx - math.cos(tang) * arm_len, hy - math.sin(tang) * arm_len))
            # Radial arm
            p.setPen(QPen(qcol(C.ACC, 160), 1.2))
            inner = fw * 0.030
            p.drawLine(QPointF(hx, hy),
                       QPointF(cx + math.cos(ang) * (half - inner),
                               cy + math.sin(ang) * (half - inner)))
            p.setPen(QPen(col, 2.0))

            # Vertex diamond
            dm = fw * 0.012
            diamond = QPainterPath()
            diamond.moveTo(hx,      hy - dm)
            diamond.lineTo(hx + dm, hy)
            diamond.lineTo(hx,      hy + dm)
            diamond.lineTo(hx - dm, hy)
            diamond.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI_GLOW, 220)))
            p.drawPath(diamond)
            p.setPen(QPen(col, 2.0))

        # Counter-rotating inner bracket ring
        rot2 = math.radians(-self._bracket_rot * 0.6 + 45)
        half2 = fw * 0.42
        p.setPen(QPen(qcol(C.ACC, 130), 1.0))
        for base_ang2 in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
            ang2 = base_ang2 + rot2
            hx2  = cx + math.cos(ang2) * half2
            hy2  = cy + math.sin(ang2) * half2
            tang2 = ang2 + math.pi / 2
            arm2 = fw * 0.038
            p.drawLine(QPointF(hx2 + math.cos(tang2) * arm2, hy2 + math.sin(tang2) * arm2),
                       QPointF(hx2 - math.cos(tang2) * arm2, hy2 - math.sin(tang2) * arm2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.ACC, 200)))
            p.drawEllipse(QPointF(hx2, hy2), 2.5, 2.5)
            p.setPen(QPen(qcol(C.ACC, 130), 1.0))

    def _draw_inner_hex(self, p: QPainter, cx: float, cy: float, fw: float):
        """Inner hexagonal frame — arc reactor containment ring."""
        hex_r = fw * 0.245
        col  = qcol(C.MUTED_C if self.muted else C.PRI, int(self._halo * 2.2))
        p.setPen(QPen(col, 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        rot = math.radians(self._rings[3] * 0.15)
        path = QPainterPath()
        for k in range(6):
            hang = math.radians(k * 60) + rot
            hx = cx + math.cos(hang) * hex_r
            hy = cy + math.sin(hang) * hex_r
            if k == 0:
                path.moveTo(hx, hy)
            else:
                path.lineTo(hx, hy)
        path.closeSubpath()
        p.drawPath(path)

        # Inner hex fill glow
        grad2 = QRadialGradient(QPointF(cx, cy), hex_r)
        if self.muted:
            grad2.setColorAt(0.0, qcol(C.RED, int(self._halo * 0.4)))
        else:
            grad2.setColorAt(0.0, qcol(C.PRI, int(self._halo * 0.5)))
        grad2.setColorAt(1.0, qcol(C.VOID, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad2))
        p.drawPath(path)

    def _draw_face(self, p: QPainter, cx: float, cy: float, fw: float):
        """Face render with arc-light chromatic effect."""
        chrom = 2.8 * math.sin(self._chrom_t)
        if self._face_px:
            fsz    = int(fw * 0.54 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.setOpacity(0.10)
            p.drawPixmap(int(cx - fsz / 2 + chrom), int(cy - fsz / 2), scaled)
            p.setOpacity(0.07)
            p.drawPixmap(int(cx - fsz / 2 - chrom), int(cy - fsz / 2 + 1), scaled)
            p.setOpacity(1.0)
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            self._draw_arc_reactor(p, cx, cy, fw)

    def _draw_arc_reactor(self, p: QPainter, cx: float, cy: float, fw: float):
        """Full rotating arc reactor — Iron Man JARVIS style.
        Translated from arc-reactor.html canvas animation.
        All radii are scaled by fw/210 so it fills any window size.
        """
        t     = self._arc_t
        scale = fw / 210.0

        pulse  = 0.5 + 0.5 * math.sin(t * 2)
        pulse2 = 0.5 + 0.5 * math.sin(t * 3 + 1)

        def _a(frac: float) -> int:
            return max(0, min(255, int(frac * 255)))

        def _ring(radius, width, r, g, b, af):
            rad = radius * scale
            p.setPen(QPen(QColor(r, g, b, _a(af)), width * scale))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))

        def _glow_ring(radius, r, g, b, blur, af):
            for bw, ba in [(blur, af * 0.55), (blur * 0.5, af * 0.75), (2, af)]:
                _ring(radius, bw, r, g, b, ba)

        def _polygon(n, radius, angle_off):
            path = QPainterPath()
            for i in range(n):
                a = angle_off + (i / n) * math.pi * 2
                x = cx + math.cos(a) * radius * scale
                y = cy + math.sin(a) * radius * scale
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            return path

        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── outer aura ────────────────────────────────────────────
        ar = 210 * scale
        ag = QRadialGradient(QPointF(cx, cy), ar)
        ag.setColorAt(0.0, QColor(0, 255, 234, _a(0.06 + pulse  * 0.04)))
        ag.setColorAt(0.5, QColor(0, 180, 255, _a(0.03 + pulse  * 0.02)))
        ag.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ag))
        p.drawEllipse(QRectF(cx - ar, cy - ar, ar * 2, ar * 2))

        # ── static outer rings ────────────────────────────────────
        _ring(195, 1,   0, 255, 234, 0.15)
        _ring(190, 0.5, 0, 191, 255, 0.08)

        # ── forward segment ring (24 segs, r=188) ─────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 0.3)); p.translate(-cx, -cy)
        sr = 188 * scale
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        span = (1 / 24) * 360 * 0.6
        for i in range(24):
            p.setPen(QPen(QColor(0, 255, 234, _a(0.20 + pulse * 0.15)), 2.5 * scale))
            p.drawArc(srect, int((i / 24) * 360 * 16), int(span * 16))
        p.restore()

        # ── reverse segment ring (16 segs, r=175) ─────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 0.18)); p.translate(-cx, -cy)
        sr2 = 175 * scale
        srect2 = QRectF(cx - sr2, cy - sr2, sr2 * 2, sr2 * 2)
        span2 = (1 / 16) * 360 * 0.5
        for i in range(16):
            p.setPen(QPen(QColor(123, 0, 255, _a(0.15 + pulse2 * 0.10)), 1.5 * scale))
            p.drawArc(srect2, int((i / 16) * 360 * 16), int(span2 * 16))
        p.restore()

        # ── outer tick marks (48 ticks, r=162) ────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 0.1)); p.translate(-cx, -cy)
        for i in range(48):
            a  = (i / 48) * math.pi * 2
            ro = 162 * scale
            ri = (155 if i % 4 == 0 else 158) * scale
            p.setPen(QPen(QColor(0, 255, 234, _a(0.5 if i % 4 == 0 else 0.2)),
                          (1.5 if i % 4 == 0 else 0.8) * scale))
            p.drawLine(QPointF(cx + math.cos(a) * ro, cy + math.sin(a) * ro),
                       QPointF(cx + math.cos(a) * ri, cy + math.sin(a) * ri))
        p.restore()

        _ring(155, 1, 0, 255, 234, 0.12)

        # ── mid rotating hexagons ──────────────────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 0.5)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 255, 234, _a(0.20 + pulse  * 0.12)), 1.2 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(6, 130, 0))
        p.restore()

        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 0.35)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 191, 255, _a(0.15 + pulse2 * 0.10)), 1.0 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(6, 130, math.pi / 6))
        p.restore()

        # ── mid glow ring (r=120) ──────────────────────────────────
        _glow_ring(120, 0, 255, 234, 14, 0.25 + pulse * 0.15)
        _ring(120, 1.5, 0, 255, 234, 0.40)

        # ── petal triangles (r=105) ────────────────────────────────
        for base_a, dr, dg, db, daf in [
            (t * 0.4,              0, 255, 234, 0.30),
            (-t * 0.3 + math.pi/6, 0, 191, 255, 0.20),
        ]:
            for i in range(6):
                a  = base_a + (i / 6) * math.pi * 2
                a1 = a - math.pi / 6 * 0.4
                a2 = a + math.pi / 6 * 0.4
                r  = 105 * scale
                pt = QPainterPath()
                pt.moveTo(cx + math.cos(a)  * r,       cy + math.sin(a)  * r)
                pt.lineTo(cx + math.cos(a1) * r * 0.7, cy + math.sin(a1) * r * 0.7)
                pt.lineTo(cx + math.cos(a2) * r * 0.7, cy + math.sin(a2) * r * 0.7)
                pt.closeSubpath()
                p.setPen(QPen(QColor(dr, dg, db, _a(daf)), 1.0 * scale))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(pt)

        # ── 6-point star + spokes (r=90) ──────────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 0.6)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 255, 234, _a(0.25 + pulse * 0.15)), 1.0 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(6, 90, 0))
        for i in range(6):
            a = (i / 6) * math.pi * 2 + t * 0.6
            p.setPen(QPen(QColor(0, 255, 234, _a(0.08 + pulse * 0.04)), 0.8 * scale))
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + math.cos(a) * 88 * scale,
                               cy + math.sin(a) * 88 * scale))
        p.restore()

        # ── inner tick marks (36 ticks, r=78) ────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 0.25)); p.translate(-cx, -cy)
        for i in range(36):
            a  = (i / 36) * math.pi * 2
            ro = 78 * scale
            ri = (66 if i % 6 == 0 else 72) * scale
            p.setPen(QPen(QColor(0, 255, 234, _a(0.5 if i % 6 == 0 else 0.15)),
                          (1.5 if i % 6 == 0 else 0.7) * scale))
            p.drawLine(QPointF(cx + math.cos(a) * ro, cy + math.sin(a) * ro),
                       QPointF(cx + math.cos(a) * ri, cy + math.sin(a) * ri))
        p.restore()

        # ── inner glow ring (r=65) ────────────────────────────────
        _ring(65, 1, 0, 255, 234, 0.25)
        _glow_ring(65, 0, 255, 234, 18, 0.30 + pulse * 0.20)

        # ── inner spinning arcs (8 segs, r=56) ────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 1.2)); p.translate(-cx, -cy)
        r56 = 56 * scale
        rect56 = QRectF(cx - r56, cy - r56, r56 * 2, r56 * 2)
        for i in range(8):
            p.setPen(QPen(QColor(0, 255, 234, _a(0.35 + pulse * 0.20)), 3.0 * scale))
            p.drawArc(rect56, int((i / 8) * 360 * 16), int((1/8) * 360 * 0.55 * 16))
        p.restore()

        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 0.9)); p.translate(-cx, -cy)
        r46 = 46 * scale
        rect46 = QRectF(cx - r46, cy - r46, r46 * 2, r46 * 2)
        for i in range(6):
            p.setPen(QPen(QColor(123, 0, 255, _a(0.25 + pulse2 * 0.15)), 2.0 * scale))
            p.drawArc(rect46, int((i / 6) * 360 * 16), int((1/6) * 360 * 0.45 * 16))
        p.restore()

        # ── inner hexagon (r=36) ──────────────────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 0.7)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 255, 234, _a(0.30 + pulse * 0.20)), 1.5 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(6, 36, 0))
        p.restore()

        # ── core triangles ────────────────────────────────────────
        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(t * 1.5)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 255, 234, _a(0.50 + pulse * 0.30)), 2.0 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(3, 22, 0))
        p.restore()

        p.save()
        p.translate(cx, cy); p.rotate(math.degrees(-t * 1.2 + math.pi)); p.translate(-cx, -cy)
        p.setPen(QPen(QColor(0, 191, 255, _a(0.40 + pulse2 * 0.25)), 1.5 * scale))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_polygon(3, 22, 0))
        p.restore()

        # ── core radial glow ──────────────────────────────────────
        cr = 18 * scale
        cg = QRadialGradient(QPointF(cx, cy), cr)
        cg.setColorAt(0.0, QColor(180, 255, 255, _a(0.90 + pulse  * 0.10)))
        cg.setColorAt(0.4, QColor(  0, 255, 234, _a(0.70 + pulse  * 0.15)))
        cg.setColorAt(0.8, QColor(  0, 180, 255, _a(0.30 + pulse  * 0.10)))
        cg.setColorAt(1.0, QColor(  0,   0,   0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(cg))
        p.drawEllipse(QRectF(cx - cr, cy - cr, cr * 2, cr * 2))

        # ── bright centre dot ─────────────────────────────────────
        dr = 5 * scale
        dg = QRadialGradient(QPointF(cx, cy), dr * 4)
        dg.setColorAt(0.0, QColor(220, 255, 255, 255))
        dg.setColorAt(0.5, QColor(  0, 255, 234, _a(0.60 + pulse * 0.30)))
        dg.setColorAt(1.0, QColor(  0,   0,   0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(dg))
        p.drawEllipse(QRectF(cx - dr * 4, cy - dr * 4, dr * 8, dr * 8))
        p.setBrush(QBrush(QColor(220, 255, 255, 255)))
        p.drawEllipse(QRectF(cx - dr, cy - dr, dr * 2, dr * 2))

        # ── energy sparks on outer ring ───────────────────────────
        for i in range(6):
            a   = t * 0.5 + (i / 6) * math.pi * 2
            rs  = (188 + math.sin(t * 3 + i) * 4) * scale
            sx  = cx + math.cos(a) * rs
            sy  = cy + math.sin(a) * rs
            sg  = QRadialGradient(QPointF(sx, sy), 6 * scale)
            sg.setColorAt(0.0, QColor(0, 255, 234, _a(0.70 + pulse * 0.30)))
            sg.setColorAt(1.0, QColor(0,   0,   0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(sg))
            p.drawEllipse(QRectF(sx - 6 * scale, sy - 6 * scale, 12 * scale, 12 * scale))
            p.setBrush(QBrush(QColor(0, 255, 234, _a(0.70 + pulse * 0.30))))
            p.drawEllipse(QRectF(sx - 2 * scale, sy - 2 * scale, 4 * scale, 4 * scale))

    def _draw_arc_orb(self, p: QPainter, cx: float, cy: float, fw: float):
        """Arc reactor orb — glowing energy core."""
        orb_r = int(fw * 0.22 * self._scale)

        # Radial fill
        grad = QRadialGradient(QPointF(cx, cy), orb_r)
        if self.muted:
            grad.setColorAt(0.0, QColor(255, 20, 60, min(255, int(self._halo * 2.0))))
            grad.setColorAt(0.5, QColor(180, 0, 40, min(255, int(self._halo * 0.9))))
            grad.setColorAt(1.0, QColor(30, 0, 10, 0))
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255, min(255, int(self._halo * 1.6))))
            grad.setColorAt(0.15, QColor(0, 200, 255, min(255, int(self._halo * 1.4))))
            grad.setColorAt(0.5, QColor(0, 80, 160, min(255, int(self._halo * 0.6))))
            grad.setColorAt(1.0, QColor(0, 0, 30, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(cx - orb_r, cy - orb_r, orb_r * 2, orb_r * 2))

        # Inner triangular arc reactor pattern
        tri_rot = math.radians(self._rings[0] * 0.5)
        tri_r   = orb_r * 0.55
        p.setPen(QPen(qcol(C.PRI, min(255, int(self._halo * 1.8))), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path_tri = QPainterPath()
        for k in range(3):
            hang = math.radians(k * 120) + tri_rot
            tx = cx + math.cos(hang) * tri_r
            ty = cy + math.sin(hang) * tri_r
            if k == 0:
                path_tri.moveTo(tx, ty)
            else:
                path_tri.lineTo(tx, ty)
        path_tri.closeSubpath()
        p.drawPath(path_tri)

        # Counter-rotating triangle
        p.setPen(QPen(qcol(C.ACC, min(200, int(self._halo * 1.2))), 1.2))
        path_tri2 = QPainterPath()
        tri_r2 = orb_r * 0.38
        for k in range(3):
            hang = math.radians(k * 120) - tri_rot + math.pi / 3
            tx = cx + math.cos(hang) * tri_r2
            ty = cy + math.sin(hang) * tri_r2
            if k == 0:
                path_tri2.moveTo(tx, ty)
            else:
                path_tri2.lineTo(tx, ty)
        path_tri2.closeSubpath()
        p.drawPath(path_tri2)

        # Label
        p.setPen(QPen(qcol(C.PRI_GLOW, min(255, int(self._halo * 2.2))), 1))
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 80, cy - 12, 160, 24),
                   Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")

    def _draw_particles(self, p: QPainter, cx: float, cy: float, fw: float):
        """Energy particles streaming along conduits."""
        p.setPen(Qt.PenStyle.NoPen)
        for part in self._particles:
            r_p = part["r"] * fw
            px  = cx + math.cos(part["angle"]) * r_p
            py  = cy + math.sin(part["angle"]) * r_p
            a_p = max(0, int(part["life"] * 220))
            p.setBrush(QBrush(qcol(part["color"], a_p)))
            p.drawEllipse(QPointF(px, py), part["size"], part["size"])
            # Glow trail
            p.setBrush(QBrush(qcol(part["color"], a_p // 4)))
            p.drawEllipse(QPointF(px, py), part["size"] * 2, part["size"] * 2)

    def _draw_data_nodes(self, p: QPainter, cx: float, cy: float, fw: float):
        """Holographic hexagonal data nodes orbiting the HUD."""
        p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))

        for nd in self._data_nodes:
            ang  = nd["angle"] + self._rings[0] * 0.005
            dist = nd["r_frac"] * fw
            nx   = cx + math.cos(ang) * dist
            ny   = cy + math.sin(ang) * dist
            col  = qcol(nd["color"], 170)

            # Hexagonal node
            hex_r = 13
            p.setPen(QPen(col, 0.9))
            p.setBrush(QBrush(qcol(C.PANEL, 160)))
            hex_path = QPainterPath()
            for k in range(6):
                hang = math.radians(k * 60 + 30)
                hx2  = nx + math.cos(hang) * hex_r
                hy2  = ny + math.sin(hang) * hex_r
                if k == 0:
                    hex_path.moveTo(hx2, hy2)
                else:
                    hex_path.lineTo(hx2, hy2)
            hex_path.closeSubpath()
            p.drawPath(hex_path)

            # Label + value
            p.setPen(QPen(col, 1))
            p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))
            p.drawText(QRectF(nx - 18, ny - 9, 36, 10), Qt.AlignmentFlag.AlignCenter, nd["label"])
            p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            p.drawText(QRectF(nx - 18, ny + 1, 36, 10), Qt.AlignmentFlag.AlignCenter, f"{nd['val']:02d}")
            p.setFont(QFont("Courier New", 6, QFont.Weight.Bold))

            # Connector line to main ring
            inner_r = fw * 0.52
            ix = cx + math.cos(ang) * inner_r
            iy = cy + math.sin(ang) * inner_r
            p.setPen(QPen(qcol(nd["color"], 40), 0.6))
            p.drawLine(QPointF(ix, iy), QPointF(nx - math.cos(ang) * hex_r, ny - math.sin(ang) * hex_r))

    def _draw_corner_triangles(self, p: QPainter, cx: float, cy: float,
                                fw: float, W: int, H: int):
        """Angular corner accent triangles — military HUD style."""
        size  = fw * 0.14
        col   = qcol(C.PRI, int(self._halo * 0.9))
        col2  = qcol(C.ACC, int(self._halo * 0.6))
        rot   = math.radians(self._tri_rot)

        for bx, by, sx, sy in [
            (cx - fw * 0.58, cy - fw * 0.58, 1,  1),
            (cx + fw * 0.58, cy - fw * 0.58, -1,  1),
            (cx - fw * 0.58, cy + fw * 0.58, 1, -1),
            (cx + fw * 0.58, cy + fw * 0.58, -1, -1),
        ]:
            p.setPen(QPen(col, 1.5))
            arm = size * 0.4
            p.drawLine(QPointF(bx, by), QPointF(bx + sx * arm, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + sy * arm))
            # Small diagonal
            p.setPen(QPen(col2, 0.8))
            p.drawLine(QPointF(bx + sx * 6, by + sy * 6),
                       QPointF(bx + sx * arm * 0.6, by + sy * arm * 0.6))

    def _draw_crosshair(self, p: QPainter, cx: float, cy: float, fw: float):
        """Military targeting crosshair."""
        ch_r  = fw * 0.545
        gap_h = fw * 0.12
        ra    = int(self._halo * 0.72)

        for off, am in [(0, 1.0), (2.0, 0.2), (-2.0, 0.2)]:
            p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, int(ra * am)), 1.2))
            p.drawLine(QPointF(cx - ch_r + off, cy), QPointF(cx - gap_h + off, cy))
            p.drawLine(QPointF(cx + gap_h + off, cy), QPointF(cx + ch_r + off, cy))
            p.drawLine(QPointF(cx, cy - ch_r + off), QPointF(cx, cy - gap_h + off))
            p.drawLine(QPointF(cx, cy + gap_h + off), QPointF(cx, cy + ch_r + off))

        # 45-degree diagonal markers
        for ang_off in [45, 135, 225, 315]:
            rad = math.radians(ang_off)
            r_in  = fw * 0.22
            r_out = fw * 0.30
            p.setPen(QPen(qcol(C.ACC, ra // 2), 0.9))
            p.drawLine(
                QPointF(cx + r_in * math.cos(rad), cy + r_in * math.sin(rad)),
                QPointF(cx + r_out * math.cos(rad), cy + r_out * math.sin(rad)),
            )

    def _draw_state_label(self, p: QPainter, cx: float, cy: float, fw: float,
                          W: int, H: int):
        """State label with glow."""
        sy = cy + fw * 0.42
        if self.muted:
            txt, col_h = "⊘  SIGNAL OFFLINE",          C.MUTED_C
        elif self.speaking:
            txt, col_h = "◈  TRANSMITTING",             C.PRI_GLOW
        elif self.state == "THINKING":
            sym = "⬡" if self._blink else "⬢"
            txt, col_h = f"{sym}  PROCESSING",          C.VIOLET
        elif self.state == "PROCESSING":
            sym = "▷" if self._blink else "▶"
            txt, col_h = f"{sym}  COMPUTING",           C.ACC
        elif self.state == "LISTENING":
            sym = "◉" if self._blink else "◎"
            txt, col_h = f"{sym}  ONLINE · READY",      C.GREEN
        else:
            sym = "◉" if self._blink else "○"
            txt, col_h = f"{sym}  {self.state}",        C.PRI

        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        for dx2, dy2 in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -2), (0, 2)]:
            p.setPen(QPen(qcol(col_h, 28), 1))
            p.drawText(QRectF(dx2, sy + dy2, W, 26), Qt.AlignmentFlag.AlignCenter, txt)
        p.setPen(QPen(qcol(col_h), 1))
        p.drawText(QRectF(0, sy, W, 26), Qt.AlignmentFlag.AlignCenter, txt)

    def _draw_wave(self, p: QPainter, cx: float, cy: float, fw: float, W: int, H: int):
        """Plasma waveform visualizer."""
        wy = cy + fw * 0.49
        N, bw = 80, 4
        wx0 = (W - N * bw) / 2

        for i in range(N):
            h_val = self._wave_data[i]
            max_h = 26
            hgt   = max(1, int(h_val * max_h))

            if self.muted:
                col = qcol(C.RED_D, 110)
            else:
                brightness = h_val
                if brightness > 0.8:
                    col = qcol(C.PRI_ULTRA, 240)
                elif brightness > 0.55:
                    col = qcol(C.PRI_GLOW, 210)
                elif brightness > 0.3:
                    col = qcol(C.PRI, 175)
                else:
                    col = qcol(C.PRI_DIM, 95)

            mid  = N // 2
            dist = abs(i - mid) / mid
            h_sc = max(1, int(hgt * (1.0 - dist * 0.20)))

            # Glow
            glow_col = qcol(col.name(), col.alpha() // 3)
            p.fillRect(QRectF(wx0 + i * bw - 1, wy + max_h - h_sc - 1, bw + 1, h_sc + 2), glow_col)
            p.fillRect(QRectF(wx0 + i * bw, wy + max_h - h_sc, bw - 1, h_sc), col)

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None


# ─────────────────────────────────────────────────────────────────
#  METRIC BAR — Plasma arc meter
# ─────────────────────────────────────────────────────────────────
class MetricBar(QWidget):
    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._text  = "--"
        self._anim_val = 0.0
        self._tick_mb  = 0
        self.setFixedHeight(50)
        self.setMinimumWidth(80)
        t = QTimer(self)
        t.timeout.connect(self._anim_step)
        t.start(30)

    def _anim_step(self):
        self._anim_val += (self._value - self._anim_val) * 0.16
        self._tick_mb  += 1
        self.update()

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # Background card with angular cut corners
        bg_g = QLinearGradient(0, 0, W, H)
        bg_g.setColorAt(0.0, qcol(C.PANEL2))
        bg_g.setColorAt(1.0, qcol(C.VOID))

        # Angular card shape
        cut = 6
        path = QPainterPath()
        path.moveTo(cut, 1)
        path.lineTo(W - 1, 1)
        path.lineTo(W - 1, H - cut)
        path.lineTo(W - cut, H - 1)
        path.lineTo(1, H - 1)
        path.lineTo(1, cut)
        path.closeSubpath()
        p.fillPath(path, QBrush(bg_g))

        # Colour logic
        if self._anim_val > 88:
            bar_col  = qcol(C.RED)
            glow_col = qcol(C.RED, 70)
        elif self._anim_val > 68:
            bar_col  = qcol(C.AMBER)
            glow_col = qcol(C.AMBER, 55)
        else:
            bar_col  = qcol(self._color)
            glow_col = qcol(self._color, 45)

        # Left accent stripe
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(self._color, 90)))
        p.drawRect(QRectF(2, 4, 2, H - 8))

        # Label
        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(9, 3, W - 70, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   self._label)

        # Value
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 3, W - 7, 16),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self._text)

        # Segmented arc bar
        bar_h  = 6
        bar_y  = H - bar_h - 5
        bar_w  = W - 16
        bar_x  = 8
        n_segs = 28
        seg_w  = (bar_w - (n_segs - 1)) / n_segs
        fill_segs = int(self._anim_val / 100 * n_segs)

        for s in range(n_segs):
            sx = bar_x + s * (seg_w + 1)
            if s < fill_segs:
                bright = 1.0 if s == fill_segs - 1 else (0.6 + 0.4 * (s / max(1, fill_segs)))
                p.setBrush(QBrush(qcol(glow_col.name(), int(glow_col.alpha() * bright))))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(QRectF(sx - 1, bar_y - 1, seg_w + 2, bar_h + 2))
                bc2 = QColor(bar_col)
                bc2.setAlphaF(bright)
                p.setBrush(QBrush(bc2))
                p.drawRect(QRectF(sx, bar_y, seg_w, bar_h))
            else:
                p.setBrush(QBrush(qcol(C.BAR_BG)))
                p.setPen(QPen(qcol(C.BORDER, 50), 0.3))
                p.drawRect(QRectF(sx, bar_y, seg_w, bar_h))

        # Border
        p.strokePath(path, QPen(qcol(self._color, 40), 1.0))
        # Cut corner accent
        p.setPen(QPen(qcol(self._color, 100), 1.0))
        p.drawLine(QPointF(cut, 1), QPointF(1, cut))
        p.drawLine(QPointF(W - cut, H - 1), QPointF(W - 1, H - cut))


# ─────────────────────────────────────────────────────────────────
#  LOG WIDGET — Holographic typewriter output
# ─────────────────────────────────────────────────────────────────
class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER_A};
                border-radius: 0px;
                padding: 10px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.VOID};
                width: 4px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.PRI_DIM};
                border-radius: 2px;
                min-height: 16px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("jarvis:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        self._tmr.start(4)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI_GLOW),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.AMBER2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)


# ─────────────────────────────────────────────────────────────────
#  FILE DROP ZONE — Data injection portal
# ─────────────────────────────────────────────────────────────────
_FILE_ICONS = {
    "image":   ("🖼", C.PRI),     "video":   ("🎬", C.AMBER),
    "audio":   ("🎵", C.VIOLET),  "pdf":     ("📄", C.RED),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", C.GREEN),
    "code":    ("💻", C.AMBER2),  "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", C.TEXT),    "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],          "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],         "audio"),
    **dict.fromkeys(["pdf"],                                                       "pdf"),
    **dict.fromkeys(["doc","docx"],                                                "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                          "excel"),
    **dict.fromkeys(["ppt","pptx"],                                                "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],    "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                    "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                      "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                    "data"),
}


def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")


def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._pulse = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(28)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 28
        self._pulse = (self._pulse + 0.055) % (math.pi * 2)
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Data Injection — Select File",
            str(Path.home()),
            "All Formats (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 4
        cut  = 8

        # Angular background shape
        path = QPainterPath()
        path.moveTo(pad + cut, pad)
        path.lineTo(W - pad, pad)
        path.lineTo(W - pad, H - pad - cut)
        path.lineTo(W - pad - cut, H - pad)
        path.lineTo(pad, H - pad)
        path.lineTo(pad, pad + cut)
        path.closeSubpath()

        if z._drag_over:
            grad = QLinearGradient(0, 0, 0, H)
            grad.setColorAt(0, qcol(C.PRI_DEEP))
            grad.setColorAt(1, qcol(C.PRI_GHO))
        elif z._hovering:
            grad = QLinearGradient(0, 0, 0, H)
            grad.setColorAt(0, qcol(C.PANEL3))
            grad.setColorAt(1, qcol(C.PANEL))
        else:
            grad = QLinearGradient(0, 0, 0, H)
            grad.setColorAt(0, qcol(C.PANEL))
            grad.setColorAt(1, qcol(C.VOID))

        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        # Border
        if z._current_file:
            pen = QPen(qcol(C.GREEN, 200), 1.5)
        elif z._drag_over:
            pulse_a = int(200 + 55 * math.sin(z._pulse))
            pen = QPen(qcol(C.PRI_GLOW, pulse_a), 2.0)
        elif z._hovering:
            pulse_a = int(150 + 80 * math.sin(z._pulse))
            pen = QPen(qcol(C.PRI, pulse_a), 1.5, Qt.PenStyle.DashLine)
            pen.setDashOffset(z._dash_offset)
        else:
            pen = QPen(qcol(C.BORDER_A, 100), 1.0, Qt.PenStyle.DashLine)
            pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Cut corner indicators
        bc2 = qcol(C.PRI if not z._current_file else C.GREEN, 180)
        p.setPen(QPen(bc2, 1.5))
        p.drawLine(QPointF(pad + cut, pad), QPointF(pad, pad + cut))
        p.drawLine(QPointF(W - pad - cut, H - pad), QPointF(W - pad, H - pad - cut))

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col  = qcol(C.PRI if hover else C.PRI_DIM)
        p.setPen(QPen(col, 1.8)); p.setBrush(Qt.BrushStyle.NoBrush)
        # Upload arrow
        p.drawLine(QPointF(cx, cy - 18), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 9, cy - 10), QPointF(cx, cy - 18))
        p.drawLine(QPointF(cx + 9, cy - 10), QPointF(cx, cy - 18))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        # Pulsing ring
        pulse_r = 13 + 2 * math.sin(self._z._pulse * 2)
        p.setPen(QPen(qcol(C.PRI, 60 if not hover else 100), 0.8))
        p.drawEllipse(QPointF(cx, cy - 7), pulse_r, pulse_r)
        p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_BRIGHT if hover else C.TEXT_DIM), 1))
        p.drawText(QRectF(0, cy + 10, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "INJECT DATA  ·  CLICK TO BROWSE")
        p.setFont(QFont("Courier New", 6))
        p.setPen(QPen(qcol(C.BORDER_B, 150), 1))
        p.drawText(QRectF(0, cy + 26, W, 12), Qt.AlignmentFlag.AlignCenter,
                   "IMG  ·  VIDEO  ·  AUDIO  ·  PDF  ·  CODE  ·  DATA")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Courier New", 18))
        p.setPen(QPen(qcol(C.PRI_GLOW), 1))
        p.drawText(QRectF(0, cy - 28, W, 34), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI_GLOW), 1))
        p.drawText(QRectF(0, cy + 10, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "RELEASE TO INJECT")

    def _paint_file(self, p, W, H):
        path     = Path(self._z._current_file)
        cat      = _file_category(path)
        icon, ic = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 55
        p.setFont(QFont("Segoe UI Emoji", 20) if _OS == "Windows" else QFont("Arial", 20))
        p.setPen(QPen(qcol(ic), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 8
        tw = W - tx - 40
        p.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 38 else path.name[:35] + "..."
        p.drawText(QRectF(tx, H * 0.15, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        p.setFont(QFont("Courier New", 7))
        p.setPen(QPen(qcol(C.TEXT_MED), 1))
        p.drawText(QRectF(tx, H * 0.15 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")
        p.setFont(QFont("Courier New", 6))
        p.setPen(QPen(qcol(C.BORDER_B), 1))
        par = str(path.parent)
        if len(par) > 50:
            par = "…" + par[-48:]
        p.drawText(QRectF(tx, H * 0.15 + 32, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)
        p.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.GREEN, 200), 1))
        p.drawText(QRectF(W - 36, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✓")


# ─────────────────────────────────────────────────────────────────
#  STATUS INDICATOR — Pulsing plasma node
# ─────────────────────────────────────────────────────────────────
class NodeIndicator(QWidget):
    def __init__(self, color: str = C.GREEN, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._color = color
        self._phase = random.uniform(0, math.pi * 2)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(35)

    def _step(self):
        self._phase += 0.09
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(self._color, int(40 * pulse))))
        p.drawEllipse(QPointF(cx, cy), 6.5, 6.5)
        p.setBrush(QBrush(qcol(self._color, 230)))
        p.drawEllipse(QPointF(cx, cy), 3.0, 3.0)
        p.setBrush(QBrush(qcol(C.WHITE, 140)))
        p.drawEllipse(QPointF(cx - 0.8, cy - 0.8), 1.0, 1.0)


# ─────────────────────────────────────────────────────────────────
#  SETUP OVERLAY — Iron Protocol Init Interface
# ─────────────────────────────────────────────────────────────────
class SetupOverlay(QWidget):
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(1, 4, 8, 252);
                border: 1px solid {C.PRI_DIM};
                border-radius: 0px;
            }}
        """)
        detected = {"darwin": "mac", "windows": "windows"}.get(_OS.lower(), "linux")
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(10)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Courier New", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        # Header
        header_row = QHBoxLayout(); header_row.setSpacing(10)
        header_row.addStretch()
        nd = NodeIndicator(C.PRI_GLOW)
        header_row.addWidget(nd)
        header_lbl = QLabel("IRON PROTOCOL · INIT SEQUENCE")
        header_lbl.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"""
            color: {C.PRI_GLOW};
            background: transparent;
            padding: 6px 0;
            letter-spacing: 4px;
        """)
        header_row.addWidget(header_lbl)
        nd2 = NodeIndicator(C.PRI_GLOW)
        header_row.addWidget(nd2)
        header_row.addStretch()
        layout.addLayout(header_row)

        layout.addWidget(_lbl("Configure J.A.R.V.I.S before activation.", 8, color=C.TEXT_DIM))
        layout.addSpacing(4)

        def _sep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.HLine)
            s.setStyleSheet(f"color: {C.BORDER_B};")
            return s

        layout.addWidget(_sep())
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, True, C.TEXT_MED,
                               Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Courier New", 10))
        self._key_input.setFixedHeight(40)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.PANEL2};
                color: {C.TEXT};
                border: 1px solid {C.BORDER_A};
                border-radius: 0px;
                padding: 4px 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
                background: {C.PRI_GHO};
            }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(10)
        layout.addWidget(_sep())
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, True, C.TEXT_MED,
                               Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"AUTO-DETECTED: {det_name}", 7, color=C.AMBER2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(8)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows", "⊞  WINDOWS"), ("mac", "  macOS"), ("linux", "🐧  LINUX")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("◈  ACTIVATE J.A.R.V.I.S  ◈")
        init_btn.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        init_btn.setFixedHeight(46)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI_GHO}, stop:0.5 {C.PRI_DEEP}, stop:1 {C.PRI_GHO});
                color: {C.PRI_GLOW};
                border: 1px solid {C.PRI};
                border-radius: 0px;
                letter-spacing: 5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PRI_DIM}, stop:0.5 {C.BORDER_B}, stop:1 {C.PRI_DIM});
                color: {C.WHITE};
                border: 1px solid {C.PRI_GLOW};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {
            "windows": (C.PRI,   C.PRI_GHO,   C.PRI),
            "mac":     (C.AMBER2, C.AMBER_G,   C.AMBER),
            "linux":   (C.GREEN,  C.GREEN_G,   C.GREEN_D),
        }
        for k, btn in self._os_btns.items():
            fg, bg, border = pal[k]
            if k == key:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {bg}; color: {fg};
                        border: 1px solid {border};
                        border-radius: 0px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PANEL2}; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 0px;
                    }}
                    QPushButton:hover {{
                        color: {C.TEXT}; border: 1px solid {C.BORDER_B};
                    }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, self._sel_os)


# ─────────────────────────────────────────────────────────────────
#  PLASMA SCAN BAR — Top edge sweep
# ─────────────────────────────────────────────────────────────────
class HeaderScanBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self._pos  = 0.0
        self._pos2 = 500.0
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(14)

    def _step(self):
        self._pos  = (self._pos  + 3.5) % (self.width() + 300)
        self._pos2 = (self._pos2 + 2.1) % (self.width() + 300)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        W = self.width()
        p.fillRect(self.rect(), qcol(C.BORDER_A, 60))
        # Primary sweep
        cx_s = self._pos - 120
        g = QLinearGradient(cx_s - 100, 0, cx_s + 100, 0)
        g.setColorAt(0.0, qcol(C.PRI, 0))
        g.setColorAt(0.5, qcol(C.PRI_GLOW, 240))
        g.setColorAt(1.0, qcol(C.PRI, 0))
        p.fillRect(QRectF(max(0, cx_s - 100), 0, 200, 2), QBrush(g))
        # Secondary sweep (gold)
        cx_s2 = self._pos2 - 120
        g2 = QLinearGradient(cx_s2 - 70, 0, cx_s2 + 70, 0)
        g2.setColorAt(0.0, qcol(C.ACC, 0))
        g2.setColorAt(0.5, qcol(C.ACC2, 130))
        g2.setColorAt(1.0, qcol(C.ACC, 0))
        p.fillRect(QRectF(max(0, cx_s2 - 70), 0, 140, 2), QBrush(g2))


# ─────────────────────────────────────────────────────────────────
#  MAIN WINDOW — IRON PROTOCOL LAYOUT
# ─────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    _log_sig   = pyqtSignal(str)
    _state_sig = pyqtSignal(str)

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S — IRON PROTOCOL · NEXUS EDITION")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command  = None
        self._muted           = False
        self._current_file: str | None = None

        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(HeaderScanBar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)

        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(self.hud, stretch=5)

        self._right_panel = self._build_right_panel()
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 520, 460
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _metrics.snapshot()
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")
        net = snap["net"]
        net_str = f"{net*1024:.0f}KB/s" if net < 1.0 else f"{net:.1f}MB/s"
        self._bar_net.set_value(min(100, net * 10), net_str)


        try:
            elapsed = time.time() - psutil.boot_time()
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UPTIME  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UPTIME  --:--")
        try:
            self._proc_lbl.setText(f"PROC  {len(psutil.pids())}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

    # ── HEADER ──────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(72)
        w.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.VOID},
                stop:0.12 {C.PANEL2},
                stop:0.5  #050d18,
                stop:0.88 {C.PANEL2},
                stop:1 {C.VOID});
            border-bottom: 1px solid {C.BORDER_B};
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(0)

        def _badge(txt, color=C.TEXT_DIM, size=8):
            l = QLabel(txt)
            l.setFont(QFont("Courier New", size))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        # Left — version + status nodes
        left = QVBoxLayout(); left.setSpacing(3)
        left.addWidget(_badge("IRON PROTOCOL", C.PRI_DIM, 7))
        left.addWidget(_badge("NEXUS EDITION", C.BORDER_B, 6))
        lay.addLayout(left)

        node_row = QHBoxLayout(); node_row.setSpacing(6)
        node_row.setContentsMargins(16, 0, 16, 0)
        for col_n, lbl_n in [(C.GREEN, "AI"), (C.PRI, "NET"), (C.ACC, "SYS")]:
            nd = NodeIndicator(col_n)
            lbl_w = QLabel(lbl_n)
            lbl_w.setFont(QFont("Courier New", 6))
            lbl_w.setStyleSheet(f"color: {col_n}; background: transparent;")
            node_row.addWidget(nd)
            node_row.addWidget(lbl_w)
            node_row.addSpacing(4)
        lay.addLayout(node_row)

        lay.addStretch()

        # Centre — title with angular accents
        mid = QVBoxLayout(); mid.setSpacing(3)
        title = QLabel("J.A.R.V.I.S")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"""
            color: {C.PRI_GLOW};
            background: transparent;
            letter-spacing: 12px;
        """)
        mid.addWidget(title)
        sub = QLabel("IRON PROTOCOL  ·  NEXUS INTELLIGENCE SYSTEM  ·  ONLINE")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Courier New", 6))
        sub.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 3px;")
        mid.addWidget(sub)
        lay.addLayout(mid)

        lay.addStretch()

        # Right — clock
        right_col = QVBoxLayout(); right_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Courier New", 7))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)
        return w

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    # ── LEFT PANEL ───────────────────────────────────────────────
    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.VOID}, stop:1 {C.PANEL2});
            border-right: 1px solid {C.BORDER_A};
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 16, 10, 16)
        lay.setSpacing(8)

        # Header
        hdr_row = QHBoxLayout(); hdr_row.setSpacing(6)
        hdr_nd = NodeIndicator(C.PRI)
        hdr_nd.setFixedSize(10, 10)
        hdr_row.addWidget(hdr_nd)
        hdr = QLabel("SYSTEM TELEMETRY")
        hdr.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"""
            color: {C.PRI};
            background: transparent;
            letter-spacing: 2px;
        """)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        lay.addLayout(hdr_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER_B}; margin-bottom: 4px;")
        lay.addWidget(sep)

        self._bar_cpu = MetricBar("CPU",      C.PRI)
        self._bar_mem = MetricBar("MEMORY",   C.VIOLET)
        self._bar_net = MetricBar("NETWORK",  C.GREEN)

        for bar in [self._bar_cpu, self._bar_mem, self._bar_net]:
            lay.addWidget(bar)

        lay.addSpacing(6)

        # Info card — angular style
        info_panel = QWidget()
        info_panel.setStyleSheet(f"""
            background: {C.PANEL2};
            border: 1px solid {C.BORDER_A};
            border-radius: 0px;
        """)
        ip_lay = QVBoxLayout(info_panel)
        ip_lay.setContentsMargins(10, 8, 10, 8)
        ip_lay.setSpacing(5)

        self._uptime_lbl = QLabel("UPTIME  --:--")
        self._uptime_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Courier New", 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN-64", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        os_lbl = QLabel(f"OS  {os_name}")
        os_lbl.setFont(QFont("Courier New", 8))
        os_lbl.setStyleSheet(f"color: {C.AMBER2}; background: transparent; border: none;")
        ip_lay.addWidget(os_lbl)

        lay.addWidget(info_panel)
        lay.addStretch()

        # Status indicators — angular cards
        for txt, col, bg_col, border_c in [
            ("AI CORE  ONLINE",    C.GREEN,    C.GREEN_G,   C.GREEN_D),
            ("NETWORK  SECURE",    C.PRI,      C.PRI_GHO,   C.PRI_DIM),
            ("PROTOCOL  ACTIVE",   C.TEXT_DIM, C.PANEL2,    C.BORDER_A),
        ]:
            ind_row = QHBoxLayout(); ind_row.setSpacing(6)
            nd2 = NodeIndicator(col); nd2.setFixedSize(10, 10)
            ind_row.addWidget(nd2)
            lbl2 = QLabel(txt)
            lbl2.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            lbl2.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            lbl2.setStyleSheet(f"""
                color: {col};
                background: {bg_col};
                border: 1px solid {border_c};
                border-radius: 0px;
                padding: 5px 8px;
                letter-spacing: 1px;
            """)
            ind_row.addWidget(lbl2, stretch=1)
            lay.addLayout(ind_row)

        return w

    # ── RIGHT PANEL ──────────────────────────────────────────────
    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"""
            background: qlineargradient(x1:1, y1:0, x2:0, y2:0,
                stop:0 {C.VOID}, stop:1 {C.PANEL2});
            border-left: 1px solid {C.BORDER_A};
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(7)

        def _sec(txt, color=C.TEXT_MED, node_col=C.PRI):
            row = QHBoxLayout(); row.setSpacing(6)
            nd3 = NodeIndicator(node_col); nd3.setFixedSize(10, 10)
            row.addWidget(nd3)
            l = QLabel(txt)
            l.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"""
                color: {color};
                background: transparent;
                letter-spacing: 2px;
            """)
            row.addWidget(l)
            row.addStretch()
            c2 = QWidget()
            c2.setStyleSheet(f"""
                border-bottom: 1px solid {C.BORDER};
                padding-bottom: 3px;
                background: transparent;
            """)
            c2.setLayout(row)
            return c2

        lay.addWidget(_sec("ACTIVITY LOG", C.TEXT_MED, C.GREEN))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        lay.addSpacing(2)
        lay.addWidget(_sec("DATA INJECTION", C.TEXT_MED, C.ACC))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded  ·  Drop or click above")
        self._file_hint.setFont(QFont("Courier New", 7))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        lay.addSpacing(2)
        lay.addWidget(_sec("COMMAND INPUT", C.TEXT_MED, C.PRI))
        lay.addLayout(self._build_input_row())

        self._mute_btn = QPushButton("◉  ONLINE · LISTENING")
        self._mute_btn.setFixedHeight(36)
        self._mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        lay.addWidget(self._mute_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(28)
        fs_btn.setFont(QFont("Courier New", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER};
                border-radius: 0px;
            }}
            QPushButton:hover {{
                color: {C.PRI};
                border: 1px solid {C.PRI_DIM};
            }}
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(fs_btn)
        return w

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter command…")
        self._input.setFont(QFont("Courier New", 9))
        self._input.setFixedHeight(38)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C.PANEL2}, stop:1 {C.VOID});
                color: {C.TEXT_BRIGHT};
                border: 1px solid {C.BORDER_A};
                border-radius: 0px;
                padding: 4px 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
                background: {C.PRI_GHO};
            }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▶")
        send.setFixedSize(38, 38)
        send.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO};
                color: {C.PRI_GLOW};
                border: 1px solid {C.PRI_DIM};
                border-radius: 0px;
            }}
            QPushButton:hover {{
                background: {C.PRI_DEEP};
                color: {C.WHITE};
                border: 1px solid {C.PRI_GLOW};
            }}
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    # ── FOOTER ──────────────────────────────────────────────────
    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(24)
        w.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C.VOID},
                stop:0.5 #030a12,
                stop:1 {C.VOID});
            border-top: 1px solid {C.BORDER_B};
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 0, 18, 0)

        def _fl(txt, color=C.TEXT_DIM):
            l = QLabel(txt)
            l.setFont(QFont("Courier New", 7))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_fl("[F4] TOGGLE MIC  ·  [F11] FULLSCREEN"))
        lay.addStretch()
        lay.addWidget(_fl("J.A.R.V.I.S  ·  IRON PROTOCOL  ·  NEXUS EDITION  ·  CLASSIFIED", C.BORDER_B))
        lay.addStretch()
        lay.addWidget(_fl("ONLINE", C.PRI_DIM))
        return w

    # ── INTERNAL METHODS ─────────────────────────────────────────
    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Ready")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone disabled.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("⊘  OFFLINE · MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.RED_G};
                    color: {C.MUTED_C};
                    border: 1px solid {C.RED_D};
                    border-radius: 0px;
                }}
            """)
        else:
            self._mute_btn.setText("◉  ONLINE · LISTENING")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.GREEN_G};
                    color: {C.GREEN};
                    border: 1px solid {C.GREEN_D};
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    background: #001e12;
                    border: 1px solid {C.GREEN};
                }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 520, 460
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def _on_setup_done(self, key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(
            f"SYS: J.A.R.V.I.S online. OS={os_name.upper()}. IRON PROTOCOL ACTIVE."
        )


# ─────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")