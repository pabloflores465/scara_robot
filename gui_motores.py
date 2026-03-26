"""
gui_motores.py — Interfaz gráfica para control manual de motores del robot SCARA.

Motores 1-3 (A, B, C) conectados al NXT.
Motores 4-5 reservados para expansión futura.

Uso:
    python gui_motores.py
    python gui_motores.py --skip-nxt    # modo simulación sin hardware
"""

import argparse
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ══════════════════════════════════════════════════════════════════
# CALIBRACIÓN ARUCO — editar con las posiciones físicas reales
# ══════════════════════════════════════════════════════════════════
# Imprime los marcadores con: python -c "import calibracion; calibracion.generar_aruco()"
# Colócalos en la mesa y mide su posición desde el centro de la base del robot.
# Unidades: metros. X = derecha, Y = adelante.
ARUCO_ROBOT_COORDS = {
    0: ( 0.10,  0.15),   # Marcador ID 0 — esquina ↗  (ajustar)
    1: (-0.10,  0.15),   # Marcador ID 1 — esquina ↖  (ajustar)
    2: (-0.10, -0.05),   # Marcador ID 2 — esquina ↙  (ajustar)
    3: ( 0.10, -0.05),   # Marcador ID 3 — esquina ↘  (ajustar)
}

try:
    _ARUCO_DICT   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    _ARUCO_PARAMS = cv2.aruco.DetectorParameters()
    _ARUCO_OK     = True
except AttributeError:
    _ARUCO_OK = False  # opencv sin módulo aruco (opencv-python básico)

# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE MOTORES
# ══════════════════════════════════════════════════════════════════

MOTORES = [
    {
        "id":        "A",
        "nombre":    "Motor 1 — Base (q1)",
        "unidad":    "°",
        "min":       -90,
        "max":       90,
        "paso":      5,
        "potencia":  60,
        "conectado": True,
    },
    {
        "id":        "B",
        "nombre":    "Motor 2 — Codo (q2)",
        "unidad":    "°",
        "min":       -135,
        "max":       135,
        "paso":      5,
        "potencia":  60,
        "conectado": True,
    },
    {
        "id":        "C",
        "nombre":    "Motor 3 — Eje Z",
        "unidad":    " tacho",
        "min":       -90,
        "max":       90,
        "paso":      5,
        "potencia":  70,
        "conectado": True,
    },
    {
        "id":        "D",
        "nombre":    "Motor 4 — Garra",
        "unidad":    "°",
        "min":       -90,
        "max":       90,
        "paso":      10,
        "potencia":  40,
        "conectado": True,
        "es_garra":  True,   # indica que tiene botones Abrir/Cerrar
    },
]

# Colores
COLOR_BG        = "#1e1e2e"
COLOR_PANEL     = "#2a2a3e"
COLOR_ACENTO    = "#89b4fa"
COLOR_VERDE     = "#a6e3a1"
COLOR_ROJO      = "#f38ba8"
COLOR_AMARILLO  = "#f9e2af"
COLOR_GRIS      = "#585b70"
COLOR_TEXTO     = "#cdd6f4"
COLOR_SUBTEXT   = "#6c7086"
COLOR_BTN       = "#313244"
COLOR_BTN_HVR   = "#45475a"


# ══════════════════════════════════════════════════════════════════
# LÓGICA NXT (puede correrse en modo simulación)
# ══════════════════════════════════════════════════════════════════

class ControladorNXT:
    def __init__(self, skip_nxt: bool = False):
        self.skip_nxt = skip_nxt
        self.brick = None

    def conectar(self) -> tuple[bool, str]:
        if self.skip_nxt:
            return True, "Modo simulación activo (--skip-nxt)"
        try:
            from robot import conectar_nxt
            self.brick = conectar_nxt()
            return True, "NXT conectado correctamente"
        except Exception as e:
            return False, f"Error al conectar NXT: {e}"

    def desconectar(self) -> None:
        self.brick = None

    def mover(self, puerto: str, pasos: int, potencia: int,
              aceleracion: int = 0) -> tuple[bool, str]:
        if self.skip_nxt or self.brick is None:
            return True, f"[SIM] Motor {puerto}: {pasos:+d} pasos  vel={potencia}%  acel={aceleracion}"
        try:
            from robot import mover_motor_suave
            mover_motor_suave(self.brick, puerto, pasos, potencia, aceleracion)
            return True, f"Motor {puerto}: {pasos:+d} pasos OK"
        except Exception as e:
            return False, f"Motor {puerto} error: {e}"

    def home(self) -> tuple[bool, str]:
        if self.skip_nxt or self.brick is None:
            return True, "[SIM] HOME ejecutado"
        try:
            from robot import ir_a_home
            ir_a_home(self.brick)
            return True, "HOME ejecutado"
        except Exception as e:
            return False, f"Error en HOME: {e}"

    def abrir_garra(self) -> tuple[bool, str]:
        if self.skip_nxt or self.brick is None:
            return True, "[SIM] Garra abierta"
        try:
            from robot import abrir_garra
            abrir_garra(self.brick)
            return True, "Garra abierta"
        except Exception as e:
            return False, f"Error abriendo garra: {e}"

    def cerrar_garra(self) -> tuple[bool, str]:
        if self.skip_nxt or self.brick is None:
            return True, "[SIM] Garra cerrada"
        try:
            from robot import cerrar_garra
            cerrar_garra(self.brick)
            return True, "Garra cerrada"
        except Exception as e:
            return False, f"Error cerrando garra: {e}"


# ══════════════════════════════════════════════════════════════════
# PANEL DE UN MOTOR
# ══════════════════════════════════════════════════════════════════

class PanelMotor(tk.Frame):
    def __init__(self, parent, cfg: dict, controlador: ControladorNXT,
                 log_fn, **kwargs):
        super().__init__(parent, bg=COLOR_PANEL, bd=0, **kwargs)
        self.cfg         = cfg
        self.controlador = controlador
        self.log         = log_fn
        self.conectado   = cfg["conectado"]
        self.posicion    = 0          # posición acumulada local
        self._ocupado    = False

        self._construir()
        self._actualizar_estado_widgets()

    def _construir(self):
        # ── Cabecera ──────────────────────────────────────────────
        color_titulo = COLOR_ACENTO if self.conectado else COLOR_GRIS
        tk.Label(
            self, text=self.cfg["nombre"],
            bg=COLOR_PANEL, fg=color_titulo,
            font=("Courier", 10, "bold"),
        ).pack(pady=(8, 2))

        # Badge de estado
        estado_txt = "CONECTADO" if self.conectado else "SIN CONECTAR"
        estado_col = COLOR_VERDE  if self.conectado else COLOR_GRIS
        tk.Label(
            self, text=estado_txt,
            bg=COLOR_PANEL, fg=estado_col,
            font=("Courier", 8),
        ).pack()

        # ── Posición actual ───────────────────────────────────────
        self.lbl_pos = tk.Label(
            self, text=f"0{self.cfg['unidad']}",
            bg=COLOR_PANEL, fg=COLOR_TEXTO,
            font=("Courier", 18, "bold"),
        )
        self.lbl_pos.pack(pady=(6, 2))

        # ── Slider ────────────────────────────────────────────────
        self.slider_var = tk.IntVar(value=0)
        self.slider = tk.Scale(
            self,
            variable=self.slider_var,
            from_=self.cfg["min"],
            to=self.cfg["max"],
            orient=tk.HORIZONTAL,
            length=150,
            showvalue=False,
            bg=COLOR_PANEL,
            fg=COLOR_TEXTO,
            troughcolor=COLOR_BTN,
            activebackground=COLOR_ACENTO,
            highlightthickness=0,
            bd=0,
        )
        self.slider.pack(padx=8)
        self.slider.bind("<ButtonRelease-1>", self._slider_soltado)

        # ── Etiquetas de rango ────────────────────────────────────
        f_rango = tk.Frame(self, bg=COLOR_PANEL)
        f_rango.pack(fill=tk.X, padx=18)
        tk.Label(f_rango, text=f"{self.cfg['min']}{self.cfg['unidad']}",
                 bg=COLOR_PANEL, fg=COLOR_SUBTEXT, font=("Courier", 8)
                 ).pack(side=tk.LEFT)
        tk.Label(f_rango, text=f"{self.cfg['max']}{self.cfg['unidad']}",
                 bg=COLOR_PANEL, fg=COLOR_SUBTEXT, font=("Courier", 8)
                 ).pack(side=tk.RIGHT)

        # ── Botones +/- ───────────────────────────────────────────
        f_btn = tk.Frame(self, bg=COLOR_PANEL)
        f_btn.pack(pady=10)

        # Paso personalizable
        tk.Label(f_btn, text="Paso:", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 9)).grid(row=0, column=0, padx=(0, 4))
        self.paso_var = tk.IntVar(value=self.cfg["paso"])
        sp = ttk.Spinbox(f_btn, from_=1, to=90, textvariable=self.paso_var,
                         width=4, font=("Courier", 10))
        sp.grid(row=0, column=1, padx=(0, 10))

        self.btn_menos = tk.Button(
            f_btn, text="◀  −", width=7,
            bg=COLOR_BTN, fg=COLOR_ROJO,
            activebackground=COLOR_BTN_HVR, activeforeground=COLOR_ROJO,
            font=("Courier", 10, "bold"), bd=0, cursor="hand2",
            command=self._click_menos,
        )
        self.btn_menos.grid(row=0, column=2, padx=4)

        self.btn_mas = tk.Button(
            f_btn, text="+ ▶", width=7,
            bg=COLOR_BTN, fg=COLOR_VERDE,
            activebackground=COLOR_BTN_HVR, activeforeground=COLOR_VERDE,
            font=("Courier", 10, "bold"), bd=0, cursor="hand2",
            command=self._click_mas,
        )
        self.btn_mas.grid(row=0, column=3, padx=4)

        # Botón de cero
        self.btn_cero = tk.Button(
            self, text="Resetear a 0",
            bg=COLOR_BTN, fg=COLOR_AMARILLO,
            activebackground=COLOR_BTN_HVR, activeforeground=COLOR_AMARILLO,
            font=("Courier", 9), bd=0, cursor="hand2",
            command=self._click_cero,
        )
        self.btn_cero.pack(pady=(0, 6))

        # ── Velocidad ─────────────────────────────────────────────
        f_vel = tk.Frame(self, bg=COLOR_PANEL)
        f_vel.pack(fill=tk.X, padx=14, pady=(4, 0))
        tk.Label(f_vel, text="Velocidad", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8)).pack(side=tk.LEFT)
        self.vel_var = tk.IntVar(value=self.cfg["potencia"])
        self.lbl_vel = tk.Label(f_vel, text=f"{self.cfg['potencia']}%",
                                bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                font=("Courier", 8, "bold"), width=5)
        self.lbl_vel.pack(side=tk.RIGHT)
        self.slider_vel = tk.Scale(
            self, variable=self.vel_var,
            from_=10, to=100, orient=tk.HORIZONTAL, length=150,
            showvalue=False, bg=COLOR_PANEL, fg=COLOR_TEXTO,
            troughcolor=COLOR_BTN, activebackground=COLOR_ACENTO,
            highlightthickness=0, bd=0,
            command=lambda v: self.lbl_vel.config(text=f"{v}%"),
        )
        self.slider_vel.pack(padx=8)

        # ── Aceleración ───────────────────────────────────────────
        f_acel = tk.Frame(self, bg=COLOR_PANEL)
        f_acel.pack(fill=tk.X, padx=14, pady=(4, 0))
        tk.Label(f_acel, text="Aceleración", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8)).pack(side=tk.LEFT)
        self.acel_var = tk.IntVar(value=0)
        self.lbl_acel = tk.Label(f_acel, text="Directa",
                                 bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                 font=("Courier", 8, "bold"), width=7)
        self.lbl_acel.pack(side=tk.RIGHT)
        self.slider_acel = tk.Scale(
            self, variable=self.acel_var,
            from_=0, to=9, orient=tk.HORIZONTAL, length=150,
            showvalue=False, bg=COLOR_PANEL, fg=COLOR_TEXTO,
            troughcolor=COLOR_BTN, activebackground=COLOR_AMARILLO,
            highlightthickness=0, bd=0,
            command=self._actualizar_lbl_acel,
        )
        self.slider_acel.pack(padx=8, pady=(0, 8))

        # Botones rápidos Abrir/Cerrar si es garra
        if self.cfg.get("es_garra"):
            f_garra = tk.Frame(self, bg=COLOR_PANEL)
            f_garra.pack(pady=(2, 0))
            self.btn_abrir = tk.Button(
                f_garra, text="↔ ABRIR",
                bg=COLOR_BTN, fg=COLOR_VERDE,
                activebackground=COLOR_BTN_HVR, activeforeground=COLOR_VERDE,
                font=("Courier", 9, "bold"), bd=0, cursor="hand2",
                padx=8, pady=4, command=self._click_abrir_garra,
            )
            self.btn_abrir.pack(side=tk.LEFT, padx=4)
            self.btn_cerrar = tk.Button(
                f_garra, text="↕ CERRAR",
                bg=COLOR_BTN, fg=COLOR_AMARILLO,
                activebackground=COLOR_BTN_HVR, activeforeground=COLOR_AMARILLO,
                font=("Courier", 9, "bold"), bd=0, cursor="hand2",
                padx=8, pady=4, command=self._click_cerrar_garra,
            )
            self.btn_cerrar.pack(side=tk.LEFT, padx=4)
        else:
            self.btn_abrir = self.btn_cerrar = None

        # Guardar referencias para habilitar/deshabilitar
        self._widgets_control = [
            self.slider, self.btn_menos, self.btn_mas,
            self.btn_cero, sp,
            self.slider_vel, self.slider_acel,
        ]
        if self.btn_abrir:
            self._widgets_control += [self.btn_abrir, self.btn_cerrar]

    def _actualizar_estado_widgets(self):
        state = tk.NORMAL if self.conectado else tk.DISABLED
        for w in self._widgets_control:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

    def habilitar(self, valor: bool):
        """Habilita o deshabilita todos los controles del panel."""
        self.conectado = valor
        self._actualizar_estado_widgets()

    def _click_abrir_garra(self):
        if not self.conectado or self._ocupado:
            return
        self._ocupado = True
        self._set_busy(True)
        self.update()
        ok, msg = self.controlador.abrir_garra()
        self.posicion = 0
        self.slider_var.set(0)
        self.lbl_pos.config(text=f"0{self.cfg['unidad']}", fg=COLOR_TEXTO)
        self.log(msg, "ok" if ok else "error")
        self._ocupado = False
        self._set_busy(False)

    def _click_cerrar_garra(self):
        if not self.conectado or self._ocupado:
            return
        self._ocupado = True
        self._set_busy(True)
        self.update()
        ok, msg = self.controlador.cerrar_garra()
        self.posicion = 0
        self.slider_var.set(0)
        self.lbl_pos.config(text=f"0{self.cfg['unidad']}", fg=COLOR_TEXTO)
        self.log(msg, "ok" if ok else "error")
        self._ocupado = False
        self._set_busy(False)

    _ACEL_LABELS = ["Directa", "Muy suave", "Suave", "Media-", "Media",
                    "Media+", "Gradual", "Gradual+", "Lenta", "Muy lenta"]

    def _actualizar_lbl_acel(self, valor):
        idx = int(valor)
        self.lbl_acel.config(text=self._ACEL_LABELS[idx])

    def _click_mas(self):
        self._mover(+self.paso_var.get())

    def _click_menos(self):
        self._mover(-self.paso_var.get())

    def _slider_soltado(self, _event):
        objetivo = self.slider_var.get()
        delta = objetivo - self.posicion
        if delta != 0:
            self._mover(delta, actualizar_slider=False)

    def _click_cero(self):
        delta = -self.posicion
        if delta != 0:
            self._mover(delta, actualizar_slider=True)

    def _mover(self, delta: int, actualizar_slider: bool = True):
        if self._ocupado or not self.conectado:
            return

        # Clamp a límites
        nueva_pos = max(self.cfg["min"],
                        min(self.cfg["max"], self.posicion + delta))
        delta_real = nueva_pos - self.posicion
        if delta_real == 0:
            return

        self._ocupado = True
        self._set_busy(True)
        self.update()  # refrescar UI antes de bloquear

        ok, msg = self.controlador.mover(
            self.cfg["id"], delta_real,
            self.vel_var.get(), self.acel_var.get(),
        )
        self._fin_movimiento(delta_real, ok, msg, actualizar_slider)

    def _fin_movimiento(self, delta: int, ok: bool, msg: str,
                        actualizar_slider: bool):
        if ok:
            self.posicion += delta
            self.lbl_pos.config(
                text=f"{self.posicion}{self.cfg['unidad']}",
                fg=COLOR_TEXTO,
            )
            if actualizar_slider:
                self.slider_var.set(self.posicion)
        else:
            self.lbl_pos.config(fg=COLOR_ROJO)

        self.log(msg, "ok" if ok else "error")
        self._ocupado = False
        self._set_busy(False)

    def _set_busy(self, ocupado: bool):
        state = tk.DISABLED if ocupado else (
            tk.NORMAL if self.conectado else tk.DISABLED
        )
        for w in self._widgets_control:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

    def reset_posicion(self):
        """Resetea el contador local de posición (después de HOME)."""
        self.posicion = 0
        self.slider_var.set(0)
        self.lbl_pos.config(
            text=f"0{self.cfg['unidad']}", fg=COLOR_TEXTO
        )


# ══════════════════════════════════════════════════════════════════
# HELPERS DE VISUALIZACIÓN
# ══════════════════════════════════════════════════════════════════

def _draw_zone_badges(frame, det):
    """
    Dibuja en las esquinas del frame los indicadores de zona roja/azul.
    La zona destino de la detección actual se resalta en color vivo.
    """
    h, w = frame.shape[:2]
    es_roja = det is not None and "roja" in det["clase"]
    es_azul = det is not None and "azul" in det["clase"]

    # Zona Roja — esquina superior izquierda
    col_r = (0, 0, 220) if es_roja else (60, 60, 80)
    cv2.rectangle(frame, (8, 8), (130, 36), col_r, -1)
    cv2.putText(frame, "ZONA ROJA", (14, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255) if es_roja else (120, 120, 120), 1)

    # Zona Azul — esquina superior derecha
    col_b = (220, 80, 0) if es_azul else (60, 60, 80)
    cv2.rectangle(frame, (w - 132, 8), (w - 8, 36), col_b, -1)
    cv2.putText(frame, "ZONA AZUL", (w - 126, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255) if es_azul else (120, 120, 120), 1)

    # Flecha indicando destino sobre el objeto detectado
    if det is not None:
        cx, cy = det["centroide"]
        arrow_col = (0, 0, 220) if es_roja else (220, 80, 0)
        cv2.putText(frame, "↓", (cx - 8, cy - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, arrow_col, 2)


# ══════════════════════════════════════════════════════════════════
# VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class AppSCARA(tk.Tk):
    def __init__(self, skip_nxt: bool = False, camara_idx: int = 0):
        super().__init__()
        self.skip_nxt    = skip_nxt
        self.controlador = ControladorNXT(skip_nxt)
        self.nxt_ok      = False
        self.paneles: list[PanelMotor] = []

        # Estado de cámara
        self.camara_idx    = camara_idx
        self.cap           = None
        self.camara_activa = False
        self.yolo_activo   = False
        self.modelo_yolo   = None
        self._photo        = None   # referencia para evitar GC

        # Pipeline YOLO → IK → NXT
        self.H_cal         = None   # homografía calibración
        self.ultima_det    = None   # última detección YOLO
        self.modo_auto     = False  # clasificación automática
        self.clasificando  = False  # bloquea re-entrada en secuencia
        self.cal_mode      = False  # modo captura de puntos
        self.cal_clicks    = []     # clics durante calibración
        self._frame_size   = (640, 360)  # tamaño display actual

        self.title("SCARA Robot — Control integrado")
        self.configure(bg=COLOR_BG)
        self.resizable(False, False)

        self._construir_ui()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ── Construcción de la UI ──────────────────────────────────────

    def _construir_ui(self):
        # Pantalla completa
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")

        # ── Cabecera ───────────────────────────────────────────────
        f_header = tk.Frame(self, bg=COLOR_BG)
        f_header.pack(fill=tk.X, padx=12, pady=(12, 0))

        tk.Label(
            f_header, text="SCARA ROBOT  ·  Control integrado",
            bg=COLOR_BG, fg=COLOR_ACENTO, font=("Courier", 14, "bold"),
        ).pack(side=tk.LEFT)

        modo_txt = "[ SIMULACIÓN ]" if self.skip_nxt else "[ NXT ]"
        modo_col = COLOR_AMARILLO if self.skip_nxt else COLOR_VERDE
        tk.Label(f_header, text=modo_txt, bg=COLOR_BG, fg=modo_col,
                 font=("Courier", 9)).pack(side=tk.LEFT, padx=12)

        # Conexión en la cabecera (lado derecho)
        self.btn_conectar = tk.Button(
            f_header, text="Conectar NXT",
            bg=COLOR_VERDE, fg=COLOR_BG,
            activebackground="#7ec77a", activeforeground=COLOR_BG,
            font=("Courier", 9, "bold"), bd=0, cursor="hand2",
            padx=10, pady=4, command=self._toggle_conexion,
        )
        self.btn_conectar.pack(side=tk.RIGHT, padx=(8, 0))

        self.lbl_conn = tk.Label(
            f_header, text="● Desconectado",
            bg=COLOR_BG, fg=COLOR_ROJO, font=("Courier", 9),
        )
        self.lbl_conn.pack(side=tk.RIGHT)

        # Separador bajo cabecera
        tk.Frame(self, bg=COLOR_GRIS, height=1).pack(fill=tk.X, padx=12, pady=6)

        # ── Cuerpo principal (2 columnas) ──────────────────────────
        f_main = tk.Frame(self, bg=COLOR_BG)
        f_main.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # ── Columna izquierda: motores ─────────────────────────────
        f_izq = tk.Frame(f_main, bg=COLOR_BG)
        f_izq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(f_izq, text="Motores", bg=COLOR_BG, fg=COLOR_SUBTEXT,
                 font=("Courier", 8)).pack(anchor="w", pady=(2, 4))

        f_motores = tk.Frame(f_izq, bg=COLOR_BG)
        f_motores.pack()

        for i, cfg in enumerate(MOTORES):
            panel = PanelMotor(f_motores, cfg, self.controlador, log_fn=self._log)
            panel.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="n")
            panel.habilitar(self.skip_nxt and cfg["conectado"])
            self.paneles.append(panel)

        # HOME bajo los motores
        self.btn_home = tk.Button(
            f_izq, text="  ⌂  HOME  ",
            bg=COLOR_BTN, fg=COLOR_AMARILLO,
            activebackground=COLOR_BTN_HVR, activeforeground=COLOR_AMARILLO,
            font=("Courier", 11, "bold"), bd=0, cursor="hand2",
            padx=14, pady=7, command=self._ir_home,
        )
        self.btn_home.pack(fill=tk.X, pady=(8, 0))
        self.btn_home.configure(state=tk.DISABLED)

        # Separador vertical
        tk.Frame(f_main, bg=COLOR_GRIS, width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=(0, 10)
        )

        # ── Columna derecha: cámara + log ──────────────────────────
        f_der = tk.Frame(f_main, bg=COLOR_BG)
        f_der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Cámara
        f_cam = tk.Frame(f_der, bg=COLOR_PANEL)
        f_cam.pack(fill=tk.X)

        tk.Label(f_cam, text="Cámara", bg=COLOR_PANEL, fg=COLOR_ACENTO,
                 font=("Courier", 10, "bold")).pack(side=tk.LEFT, padx=10, pady=6)

        # Controles de cámara (en la misma fila que el título)
        f_cam_ctrl = tk.Frame(f_cam, bg=COLOR_PANEL)
        f_cam_ctrl.pack(side=tk.RIGHT, padx=8)

        tk.Label(f_cam_ctrl, text="Índice:", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 9)).pack(side=tk.LEFT)
        self.cam_idx_var = tk.IntVar(value=self.camara_idx)
        ttk.Spinbox(f_cam_ctrl, from_=0, to=9, textvariable=self.cam_idx_var,
                    width=3, font=("Courier", 9)).pack(side=tk.LEFT, padx=(4, 10))

        self.btn_camara = tk.Button(
            f_cam_ctrl, text="▶  Iniciar",
            bg=COLOR_BTN, fg=COLOR_VERDE,
            activebackground=COLOR_BTN_HVR, activeforeground=COLOR_VERDE,
            font=("Courier", 9, "bold"), bd=0, cursor="hand2",
            padx=8, pady=3, command=self._toggle_camara,
        )
        self.btn_camara.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_yolo = tk.Button(
            f_cam_ctrl, text="YOLO: OFF",
            bg=COLOR_BTN, fg=COLOR_SUBTEXT,
            activebackground=COLOR_BTN_HVR,
            font=("Courier", 9), bd=0, cursor="hand2",
            padx=8, pady=3, command=self._toggle_yolo,
            state=tk.DISABLED,
        )
        self.btn_yolo.pack(side=tk.LEFT)

        # Video frame (se expande horizontal y verticalmente)
        f_video = tk.Frame(f_der, bg="black")
        f_video.pack(fill=tk.BOTH, expand=True)
        f_video.pack_propagate(False)
        self.lbl_video = tk.Label(f_video, bg="black")
        self.lbl_video.pack(fill=tk.BOTH, expand=True)

        # ── Panel pipeline ────────────────────────────────────────
        f_pipe = tk.Frame(f_der, bg=COLOR_PANEL)
        f_pipe.pack(fill=tk.X, pady=(4, 0))

        # Fila 1: Calibración
        f_cal = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_cal.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(f_cal, text="CALIBRACIÓN", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_cal_status = tk.Label(f_cal, text="● Sin calibrar",
                                       bg=COLOR_PANEL, fg=COLOR_ROJO,
                                       font=("Courier", 8))
        self.lbl_cal_status.pack(side=tk.LEFT, padx=8)
        tk.Button(f_cal, text="Cargar", bg=COLOR_BTN, fg=COLOR_TEXTO,
                  font=("Courier", 8), bd=0, padx=6, pady=2,
                  cursor="hand2", command=self._cargar_calibracion
                  ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(f_cal, text="Manual", bg=COLOR_BTN, fg=COLOR_AMARILLO,
                  font=("Courier", 8), bd=0, padx=6, pady=2,
                  cursor="hand2", command=self._iniciar_calibracion
                  ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(f_cal, text="▣ ArUco AUTO", bg=COLOR_BTN, fg=COLOR_VERDE,
                  font=("Courier", 8, "bold"), bd=0, padx=6, pady=2,
                  cursor="hand2", command=self._calibrar_aruco
                  ).pack(side=tk.RIGHT)

        tk.Frame(f_pipe, bg=COLOR_GRIS, height=1).pack(fill=tk.X, padx=8, pady=2)

        # Fila 2: Detección
        f_det = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_det.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(f_det, text="DETECCIÓN", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_det = tk.Label(f_det, text="—", bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                font=("Courier", 8))
        self.lbl_det.pack(side=tk.LEFT, padx=8)

        f_coords = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_coords.pack(fill=tk.X, padx=8, pady=(0, 2))
        self.lbl_px = tk.Label(f_coords, text="px: —", bg=COLOR_PANEL,
                               fg=COLOR_SUBTEXT, font=("Courier", 8))
        self.lbl_px.pack(side=tk.LEFT)
        self.lbl_robot_xy = tk.Label(f_coords, text="  robot: —", bg=COLOR_PANEL,
                                     fg=COLOR_TEXTO, font=("Courier", 8))
        self.lbl_robot_xy.pack(side=tk.LEFT)

        tk.Frame(f_pipe, bg=COLOR_GRIS, height=1).pack(fill=tk.X, padx=8, pady=2)

        # Fila 3: IK
        f_ik = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_ik.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(f_ik, text="IK", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_ik = tk.Label(f_ik, text="q1: —  q2: —", bg=COLOR_PANEL,
                               fg=COLOR_TEXTO, font=("Courier", 8))
        self.lbl_ik.pack(side=tk.LEFT, padx=8)
        self.lbl_ik_estado = tk.Label(f_ik, text="", bg=COLOR_PANEL,
                                      fg=COLOR_GRIS, font=("Courier", 8, "bold"))
        self.lbl_ik_estado.pack(side=tk.RIGHT, padx=4)

        tk.Frame(f_pipe, bg=COLOR_GRIS, height=1).pack(fill=tk.X, padx=8, pady=2)

        # Fila 4: Destino
        f_dest = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_dest.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(f_dest, text="DESTINO", bg=COLOR_PANEL, fg=COLOR_SUBTEXT,
                 font=("Courier", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_destino = tk.Label(f_dest, text="—", bg=COLOR_PANEL,
                                    fg=COLOR_GRIS, font=("Courier", 9, "bold"))
        self.lbl_destino.pack(side=tk.LEFT, padx=8)

        # Indicadores fijos de zonas
        f_zonas = tk.Frame(f_dest, bg=COLOR_PANEL)
        f_zonas.pack(side=tk.RIGHT, padx=4)
        self.lbl_zona_roja = tk.Label(f_zonas, text="● ZONA ROJA",
                                      bg=COLOR_PANEL, fg=COLOR_GRIS,
                                      font=("Courier", 8, "bold"))
        self.lbl_zona_roja.pack(side=tk.LEFT, padx=6)
        self.lbl_zona_azul = tk.Label(f_zonas, text="● ZONA AZUL",
                                      bg=COLOR_PANEL, fg=COLOR_GRIS,
                                      font=("Courier", 8, "bold"))
        self.lbl_zona_azul.pack(side=tk.LEFT, padx=6)

        tk.Frame(f_pipe, bg=COLOR_GRIS, height=1).pack(fill=tk.X, padx=8, pady=2)

        # Fila 5: Acciones
        f_acc = tk.Frame(f_pipe, bg=COLOR_PANEL)
        f_acc.pack(fill=tk.X, padx=8, pady=(4, 8))
        self.btn_clasificar = tk.Button(
            f_acc, text="  ⚙  CLASIFICAR  ",
            bg=COLOR_ACENTO, fg=COLOR_BG,
            activebackground="#6ba3f5", activeforeground=COLOR_BG,
            font=("Courier", 10, "bold"), bd=0, cursor="hand2",
            padx=10, pady=5, command=self._clasificar,
            state=tk.DISABLED,
        )
        self.btn_clasificar.pack(side=tk.LEFT)
        self.btn_auto = tk.Button(
            f_acc, text="AUTO: OFF",
            bg=COLOR_BTN, fg=COLOR_SUBTEXT,
            activebackground=COLOR_BTN_HVR,
            font=("Courier", 9), bd=0, cursor="hand2",
            padx=10, pady=5, command=self._toggle_auto,
            state=tk.DISABLED,
        )
        self.btn_auto.pack(side=tk.LEFT, padx=8)

        # Bind clics en el video para calibración
        self.lbl_video.bind("<Button-1>", self._video_click)

        # Log
        tk.Label(f_der, text="Consola", bg=COLOR_BG, fg=COLOR_SUBTEXT,
                 font=("Courier", 8)).pack(anchor="w", pady=(6, 2))

        f_log = tk.Frame(f_der, bg=COLOR_BG, height=140)
        f_log.pack(fill=tk.X)
        f_log.pack_propagate(False)

        self.txt_log = tk.Text(
            f_log, bg=COLOR_PANEL, fg=COLOR_TEXTO,
            font=("Courier", 9), bd=0, state=tk.DISABLED,
            insertbackground=COLOR_TEXTO, wrap=tk.WORD,
        )
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(f_log, command=self.txt_log.yview,
                          bg=COLOR_PANEL, troughcolor=COLOR_BG)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.configure(yscrollcommand=sb.set)

        self.txt_log.tag_configure("ok",    foreground=COLOR_VERDE)
        self.txt_log.tag_configure("error", foreground=COLOR_ROJO)
        self.txt_log.tag_configure("info",  foreground=COLOR_ACENTO)

        self._log("Interfaz lista. Conecta el NXT para empezar.", "info")
        if self.skip_nxt:
            self._log("Modo simulación: los movimientos son solo visuales.", "info")
        if not _PIL_OK:
            self._log("WARN: instala Pillow para mejor rendimiento de cámara.", "error")
        self._log("Cámara: ajusta el índice y presiona ▶ Iniciar.", "info")

        # Intentar cargar calibración automáticamente al inicio
        self._cargar_calibracion_silencioso()

    # ── Conexión NXT ───────────────────────────────────────────────

    def _toggle_conexion(self):
        if self.nxt_ok:
            self.controlador.desconectar()
            self.nxt_ok = False
            self.lbl_conn.config(text="● Desconectado", fg=COLOR_ROJO)
            self.btn_conectar.config(text="  Conectar NXT  ",
                                     bg=COLOR_VERDE, fg=COLOR_BG)
            self.btn_home.configure(state=tk.DISABLED)
            for p in self.paneles:
                p.habilitar(False)
            self._log("NXT desconectado.", "info")
        else:
            self._log("Conectando NXT...", "info")
            self.btn_conectar.configure(state=tk.DISABLED)
            self.update()  # forzar redibujado antes de bloquear

            ok, msg = self.controlador.conectar()
            self._fin_conexion(ok, msg)

    def _fin_conexion(self, ok: bool, msg: str):
        self.btn_conectar.configure(state=tk.NORMAL)
        if ok:
            self.nxt_ok = True
            self.lbl_conn.config(text="● Conectado", fg=COLOR_VERDE)
            self.btn_conectar.config(text="  Desconectar  ",
                                     bg=COLOR_ROJO, fg=COLOR_BG)
            self.btn_home.configure(state=tk.NORMAL)
            for p in self.paneles:
                if p.cfg["conectado"]:
                    p.habilitar(True)
        else:
            messagebox.showerror("Error de conexión", msg)

        self._log(msg, "ok" if ok else "error")

    # ── HOME ───────────────────────────────────────────────────────

    def _ir_home(self):
        self.btn_home.configure(state=tk.DISABLED)
        self._log("Ejecutando HOME...", "info")
        self.update()  # refrescar UI antes de bloquear

        ok, msg = self.controlador.home()
        self._fin_home(ok, msg)

    def _fin_home(self, ok: bool, msg: str):
        if ok:
            for p in self.paneles:
                p.reset_posicion()
        self._log(msg, "ok" if ok else "error")
        self.btn_home.configure(state=tk.NORMAL)

    # ── Cámara ─────────────────────────────────────────────────────

    def _toggle_camara(self):
        if self.camara_activa:
            self._detener_camara()
        else:
            self._iniciar_camara()

    def _iniciar_camara(self):
        idx = self.cam_idx_var.get()
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            self._log(f"No se pudo abrir cámara {idx}", "error")
            return
        self.cap = cap
        self.camara_activa = True
        self.btn_camara.config(text="■  Detener", fg=COLOR_ROJO,
                               activeforeground=COLOR_ROJO)
        self.btn_yolo.config(state=tk.NORMAL)
        self._log(f"Cámara {idx} iniciada.", "ok")
        self._actualizar_frame()

    def _detener_camara(self):
        self.camara_activa = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.lbl_video.config(image="", bg="black")
        self._photo = None
        self.btn_camara.config(text="▶  Iniciar", fg=COLOR_VERDE,
                               activeforeground=COLOR_VERDE)
        self.btn_yolo.config(state=tk.DISABLED)
        self._log("Cámara detenida.", "info")

    def _actualizar_frame(self):
        if not self.camara_activa or self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            # Redimensionar manteniendo 16:9 según el ancho disponible
            fw = max(self.lbl_video.winfo_width(), 400)
            fh = fw * 9 // 16
            frame = cv2.resize(frame, (fw, fh))
            self._frame_size = (fw, fh)

            coords_robot = None
            det = None

            # YOLO sobre el frame ya redimensionado (coords == coords display)
            if self.yolo_activo and self.modelo_yolo:
                try:
                    from vision import detectar, dibujar_hud
                    dets = detectar(frame, self.modelo_yolo)
                    det = dets[0] if dets else None

                    if det and self.H_cal is not None:
                        cx, cy = det["centroide"]
                        from calibracion import pixel_a_robot
                        coords_robot = pixel_a_robot(cx, cy, self.H_cal)

                    dibujar_hud(frame, dets, coords_robot, estado="DETECCIÓN")
                except Exception:
                    pass

            self.ultima_det = (det, coords_robot)
            self.after(0, lambda d=det, r=coords_robot: self._actualizar_pipeline_ui(d, r))

            # Overlay de zonas (esquinas del video)
            _draw_zone_badges(frame, det)

            # Overlay modo calibración
            if self.cal_mode:
                txt = f"CAL [{len(self.cal_clicks)}/4]: haz clic en punto {len(self.cal_clicks)+1}"
                cv2.putText(frame, txt, (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                for i, (px, py) in enumerate(self.cal_clicks):
                    cv2.circle(frame, (px, py), 8, (0, 255, 0), -1)
                    cv2.putText(frame, str(i + 1), (px + 10, py - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Auto-clasificación
            if (self.modo_auto and det and coords_robot
                    and self.nxt_ok and not self.clasificando):
                self.after(0, self._clasificar)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if _PIL_OK:
                photo = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
            else:
                import base64
                _, buf = cv2.imencode('.jpg', frame)
                photo = tk.PhotoImage(data=base64.b64encode(buf.tobytes()))

            self.lbl_video.config(image=photo)
            self._photo = photo

        self.after(33, self._actualizar_frame)  # ~30 fps

    def _toggle_yolo(self):
        if self.yolo_activo:
            self.yolo_activo = False
            self.btn_yolo.config(text="YOLO: OFF", fg=COLOR_SUBTEXT)
            self._log("YOLO desactivado.", "info")
        else:
            if self.modelo_yolo is None:
                self._log("Cargando modelo YOLO...", "info")
                self.update()
                try:
                    from vision import cargar_modelo
                    self.modelo_yolo = cargar_modelo("modelo/best.pt")
                    self._log("Modelo YOLO cargado.", "ok")
                except Exception as e:
                    self._log(f"Error cargando YOLO: {e}", "error")
                    return
            self.yolo_activo = True
            self.btn_yolo.config(text="YOLO: ON", fg=COLOR_VERDE)
            self._log("YOLO activado.", "ok")

    # ── Pipeline UI ────────────────────────────────────────────────

    def _actualizar_pipeline_ui(self, det, coords_robot):
        """Actualiza los labels del panel pipeline con la detección actual."""
        if det is None:
            self.lbl_det.config(text="—", fg=COLOR_GRIS)
            self.lbl_px.config(text="px: —")
            self.lbl_robot_xy.config(text="  robot: —")
            self.lbl_ik.config(text="q1: —  q2: —")
            self.lbl_ik_estado.config(text="")
            self.lbl_destino.config(text="—", fg=COLOR_GRIS)
            self.lbl_zona_roja.config(fg=COLOR_GRIS)
            self.lbl_zona_azul.config(fg=COLOR_GRIS)
            self.btn_clasificar.config(state=tk.DISABLED)
            self.btn_auto.config(state=tk.DISABLED)
            return

        es_roja = "roja" in det["clase"]
        color_det = COLOR_ROJO if es_roja else COLOR_ACENTO
        zona_nombre = "ZONA_ROJA" if es_roja else "ZONA_AZUL"

        self.lbl_det.config(
            text=f"{det['clase']}  conf: {det['confianza']:.2f}",
            fg=color_det,
        )

        # Destino e indicadores de zona
        self.lbl_destino.config(
            text=f"→ {zona_nombre}",
            fg=COLOR_ROJO if es_roja else COLOR_ACENTO,
        )
        self.lbl_zona_roja.config(fg=COLOR_ROJO if es_roja else COLOR_GRIS)
        self.lbl_zona_azul.config(fg=COLOR_ACENTO if not es_roja else COLOR_GRIS)
        cx, cy = det["centroide"]
        self.lbl_px.config(text=f"px: ({cx}, {cy})")

        if coords_robot:
            xr, yr = coords_robot
            self.lbl_robot_xy.config(text=f"  robot: ({xr:.3f}m, {yr:.3f}m)")

            # Calcular IK
            try:
                from cinematica import cinematica_inversa, validar_limites
                ik = cinematica_inversa(xr, yr)
                if ik:
                    q1, q2 = ik
                    alcanzable = validar_limites(q1, q2)
                    self.lbl_ik.config(
                        text=f"q1: {q1:+.1f}°   q2: {q2:+.1f}°"
                    )
                    if alcanzable:
                        self.lbl_ik_estado.config(text="ALCANZABLE", fg=COLOR_VERDE)
                        self.btn_clasificar.config(
                            state=tk.NORMAL if self.nxt_ok else tk.DISABLED
                        )
                        self.btn_auto.config(
                            state=tk.NORMAL if self.nxt_ok else tk.DISABLED
                        )
                    else:
                        self.lbl_ik_estado.config(text="FUERA DE LÍMITES", fg=COLOR_ROJO)
                        self.btn_clasificar.config(state=tk.DISABLED)
                else:
                    self.lbl_ik.config(text="q1: —  q2: —")
                    self.lbl_ik_estado.config(text="FUERA DE ALCANCE", fg=COLOR_ROJO)
                    self.btn_clasificar.config(state=tk.DISABLED)
            except Exception as e:
                self.lbl_ik_estado.config(text=str(e)[:30], fg=COLOR_ROJO)
        else:
            self.lbl_robot_xy.config(text="  robot: sin calibración")
            self.lbl_ik.config(text="q1: —  q2: —")
            self.lbl_ik_estado.config(text="SIN CAL", fg=COLOR_GRIS)
            self.btn_clasificar.config(state=tk.DISABLED)

    # ── Calibración ────────────────────────────────────────────────

    def _calibrar_aruco(self):
        """Detecta automáticamente 4 marcadores ArUco y calcula la homografía."""
        if not _ARUCO_OK:
            self._log("ArUco no disponible. Instala: pip install opencv-contrib-python", "error")
            return
        if not self.camara_activa or self.cap is None:
            self._log("Inicia la cámara antes de calibrar.", "error")
            return

        self._log("Buscando marcadores ArUco...", "info")
        self.update()

        # Captura varios frames para dar tiempo a enfocar
        frame = None
        for _ in range(5):
            ret, frame = self.cap.read()

        if frame is None:
            self._log("No se pudo capturar frame.", "error")
            return

        detector = cv2.aruco.ArucoDetector(_ARUCO_DICT, _ARUCO_PARAMS)
        corners, ids, _ = detector.detectMarkers(frame)

        if ids is None or len(ids) == 0:
            self._log("No se detectaron marcadores ArUco en el frame.", "error")
            return

        ids_flat = [int(i[0]) for i in ids]
        faltantes = [k for k in ARUCO_ROBOT_COORDS if k not in ids_flat]
        if faltantes:
            self._log(f"Faltan marcadores: {faltantes}. Detectados: {ids_flat}", "error")
            return

        import numpy as np
        puntos_px    = []
        puntos_robot = []
        for corner, id_arr in zip(corners, ids):
            mid = ARUCO_ROBOT_COORDS.get(int(id_arr[0]))
            if mid is None:
                continue
            cx = float(corner[0][:, 0].mean())
            cy = float(corner[0][:, 1].mean())

            # Escalar a coordenadas del display
            fh_orig, fw_orig = frame.shape[:2]
            fw_disp, fh_disp = self._frame_size
            cx = cx * fw_disp / fw_orig
            cy = cy * fh_disp / fh_orig

            puntos_px.append([cx, cy])
            puntos_robot.append(list(mid))

        src = np.array(puntos_px,    dtype=np.float32)
        dst = np.array(puntos_robot, dtype=np.float32)
        H, _ = cv2.findHomography(src, dst)

        from calibracion import guardar_calibracion
        guardar_calibracion(H, [list(p) for p in src], [list(p) for p in dst])

        self.H_cal = H
        self.lbl_cal_status.config(text="● Calibrado (ArUco)", fg=COLOR_VERDE)
        self._log(f"Calibración ArUco OK — {len(puntos_px)} marcadores detectados.", "ok")

    def _cargar_calibracion_silencioso(self):
        """Carga calibración al inicio sin mostrar error si no existe."""
        try:
            import os, json
            import numpy as np
            if os.path.exists("calibracion.json"):
                with open("calibracion.json") as f:
                    datos = json.load(f)
                self.H_cal = np.array(datos["homografia"], dtype=np.float64)
                self.lbl_cal_status.config(text="● Calibrado", fg=COLOR_VERDE)
                self._log("Calibración cargada automáticamente.", "ok")
        except Exception:
            pass

    def _cargar_calibracion(self):
        try:
            from calibracion import cargar_calibracion
            H = cargar_calibracion()
            if H is not None:
                self.H_cal = H
                self.lbl_cal_status.config(text="● Calibrado", fg=COLOR_VERDE)
                self._log("Calibración cargada desde calibracion.json", "ok")
            else:
                self._log("calibracion.json no encontrado. Usa 'Calibrar'.", "error")
        except Exception as e:
            self._log(f"Error cargando calibración: {e}", "error")

    def _iniciar_calibracion(self):
        if not self.camara_activa:
            self._log("Inicia la cámara antes de calibrar.", "error")
            return
        self.cal_mode = True
        self.cal_clicks = []
        self.lbl_cal_status.config(text="● Capturando...", fg=COLOR_AMARILLO)
        self._log("Calibración: haz clic en 4 puntos de referencia en el video.", "info")

    def _video_click(self, event):
        if not self.cal_mode:
            return
        self.cal_clicks.append((event.x, event.y))
        self._log(f"  Punto {len(self.cal_clicks)}: pixel ({event.x}, {event.y})", "info")

        if len(self.cal_clicks) == 4:
            self.cal_mode = False
            self._pedir_coords_robot()

    def _pedir_coords_robot(self):
        """Ventana para ingresar las coordenadas robot de los 4 puntos."""
        win = tk.Toplevel(self)
        win.title("Coordenadas del robot [m]")
        win.configure(bg=COLOR_BG)
        win.resizable(False, False)

        tk.Label(win, text="Ingresa las coordenadas del robot para cada punto",
                 bg=COLOR_BG, fg=COLOR_TEXTO, font=("Courier", 10)).pack(pady=(12, 8))

        entradas = []
        for i, (px, py) in enumerate(self.cal_clicks):
            f = tk.Frame(win, bg=COLOR_BG)
            f.pack(padx=20, pady=4, fill=tk.X)
            tk.Label(f, text=f"Punto {i+1} (px={px},{py})",
                     bg=COLOR_BG, fg=COLOR_ACENTO,
                     font=("Courier", 9, "bold"), width=22).pack(side=tk.LEFT)
            ex = tk.Entry(f, width=8, bg=COLOR_BTN, fg=COLOR_TEXTO,
                          insertbackground=COLOR_TEXTO, font=("Courier", 9))
            ex.insert(0, "0.000")
            ex.pack(side=tk.LEFT, padx=(8, 2))
            tk.Label(f, text="x[m]", bg=COLOR_BG, fg=COLOR_SUBTEXT,
                     font=("Courier", 8)).pack(side=tk.LEFT)
            ey = tk.Entry(f, width=8, bg=COLOR_BTN, fg=COLOR_TEXTO,
                          insertbackground=COLOR_TEXTO, font=("Courier", 9))
            ey.insert(0, "0.000")
            ey.pack(side=tk.LEFT, padx=(8, 2))
            tk.Label(f, text="y[m]", bg=COLOR_BG, fg=COLOR_SUBTEXT,
                     font=("Courier", 8)).pack(side=tk.LEFT)
            entradas.append((ex, ey))

        def _confirmar():
            try:
                puntos_robot = [(float(ex.get()), float(ey.get()))
                                for ex, ey in entradas]
            except ValueError:
                self._log("Valores inválidos en calibración.", "error")
                return

            src = __import__("numpy").array(self.cal_clicks, dtype="float32")
            dst = __import__("numpy").array(puntos_robot, dtype="float32")
            H = cv2.getPerspectiveTransform(src, dst)

            from calibracion import guardar_calibracion
            guardar_calibracion(H, self.cal_clicks, puntos_robot)

            self.H_cal = H
            self.lbl_cal_status.config(text="● Calibrado", fg=COLOR_VERDE)
            self._log("Calibración calculada y guardada.", "ok")
            win.destroy()

        tk.Button(win, text="Confirmar", bg=COLOR_VERDE, fg=COLOR_BG,
                  font=("Courier", 10, "bold"), bd=0, padx=12, pady=6,
                  command=_confirmar).pack(pady=12)

    # ── Clasificación ──────────────────────────────────────────────

    def _clasificar(self):
        if self.clasificando or not self.nxt_ok:
            return
        if self.ultima_det is None:
            self._log("Sin detección activa.", "error")
            return

        det, coords_robot = self.ultima_det
        if det is None or coords_robot is None:
            self._log("Necesita detección + calibración para clasificar.", "error")
            return

        self.clasificando = True
        self.btn_clasificar.config(state=tk.DISABLED)
        xr, yr = coords_robot
        self._log(f"Clasificando {det['clase']} en ({xr:.3f}m, {yr:.3f}m)...", "info")
        self.update()

        try:
            from robot import ejecutar_con_coordenadas
            ok = ejecutar_con_coordenadas(self.controlador.brick, xr, yr, det["clase"])
            if ok:
                self._log(f"✓ {det['clase']} clasificada correctamente.", "ok")
            else:
                self._log("✗ Clasificación fallida (fuera de alcance o error).", "error")
        except Exception as e:
            self._log(f"Error en clasificación: {e}", "error")
        finally:
            self.clasificando = False
            self.btn_clasificar.config(state=tk.NORMAL)

    def _toggle_auto(self):
        self.modo_auto = not self.modo_auto
        if self.modo_auto:
            self.btn_auto.config(text="AUTO: ON", fg=COLOR_VERDE,
                                 bg=COLOR_BTN_HVR)
            self._log("Modo AUTO activado — clasificará automáticamente.", "info")
        else:
            self.btn_auto.config(text="AUTO: OFF", fg=COLOR_SUBTEXT,
                                 bg=COLOR_BTN)
            self._log("Modo AUTO desactivado.", "info")

    def _cerrar(self):
        self._detener_camara()
        self.destroy()

    # ── Log ────────────────────────────────────────────────────────

    def _log(self, mensaje: str, nivel: str = "info"):
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.insert(tk.END, f"▸ {mensaje}\n", nivel)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Interfaz gráfica de control de motores SCARA"
    )
    parser.add_argument(
        "--skip-nxt", action="store_true",
        help="Modo simulación: sin hardware NXT"
    )
    parser.add_argument(
        "--camara", type=int, default=0,
        help="Índice de cámara inicial (0=integrada, 1=iPhone, etc.)"
    )
    args = parser.parse_args()

    app = AppSCARA(skip_nxt=args.skip_nxt, camara_idx=args.camara)
    app.mainloop()


if __name__ == "__main__":
    main()
