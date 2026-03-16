"""
cinematica.py — Parámetros D-H, cinemática directa e inversa, conversiones.
Día 1: módulo en blanco listo para completar en el Día 2 con medidas reales.
"""

import math
import numpy as np


# ──────────────────────────────────────────────
# Parámetros D-H (llenar con medidas reales en Día 2)
# ──────────────────────────────────────────────
#
# Tabla D-H para SCARA de 2 GDL en plano XY:
#   i | a(i-1) | alpha(i-1) | d(i) | theta(i)
#   1 |   0    |     0      |  0   |   q1   ← articulación 1 (base)
#   2 |  L1    |     0      |  0   |   q2   ← articulación 2
#   3 |  L2    |     0      |  dz  |   0    ← eje Z (traslación)
#
# Reemplaza L1, L2 y DZ con los valores medidos en tu robot real.

L1 = 0.0   # longitud eslabón 1 [metros] — MEDIR EN DÍA 2
L2 = 0.0   # longitud eslabón 2 [metros] — MEDIR EN DÍA 2
DZ = 0.0   # desplazamiento vertical del efector [metros] — MEDIR EN DÍA 2


# ──────────────────────────────────────────────
# Cinemática directa
# ──────────────────────────────────────────────

def cinematica_directa(q1_deg: float, q2_deg: float) -> tuple[float, float]:
    """
    Calcula (x, y) del efector dado q1 y q2 en grados.
    Fórmula base SCARA plano XY:
        x = L1*cos(q1) + L2*cos(q1+q2)
        y = L1*sin(q1) + L2*sin(q1+q2)
    """
    q1 = math.radians(q1_deg)
    q2 = math.radians(q2_deg)
    x = L1 * math.cos(q1) + L2 * math.cos(q1 + q2)
    y = L1 * math.sin(q1) + L2 * math.sin(q1 + q2)
    return x, y


# ──────────────────────────────────────────────
# Cinemática inversa
# ──────────────────────────────────────────────

def cinematica_inversa(x: float, y: float) -> tuple[float, float] | None:
    """
    Calcula (q1, q2) en grados dado un punto objetivo (x, y).
    Retorna None si el punto está fuera del alcance.
    """
    if L1 == 0 or L2 == 0:
        raise ValueError("Define L1 y L2 antes de usar la cinemática inversa.")

    d = math.sqrt(x**2 + y**2)
    if d > (L1 + L2) or d < abs(L1 - L2):
        return None  # fuera de alcance

    cos_q2 = (d**2 - L1**2 - L2**2) / (2 * L1 * L2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))   # clamp numérico
    q2 = math.acos(cos_q2)                  # solución codo arriba

    alpha = math.atan2(y, x)
    beta = math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    q1 = alpha - beta

    return math.degrees(q1), math.degrees(q2)


# ──────────────────────────────────────────────
# Conversión píxeles → coordenadas robot
# ──────────────────────────────────────────────
#
# Estos parámetros se calibran en el Día 5.
# Por ahora son placeholders.

CALIBRACION = {
    "origen_px": (0, 0),    # píxel que corresponde al origen del robot
    "escala_x": 1.0,        # metros por píxel en X
    "escala_y": 1.0,        # metros por píxel en Y
}


def pixel_a_robot(px: int, py: int) -> tuple[float, float]:
    """Convierte coordenadas de imagen (px, py) a coordenadas del robot (x, y)."""
    ox, oy = CALIBRACION["origen_px"]
    x = (px - ox) * CALIBRACION["escala_x"]
    y = (py - oy) * CALIBRACION["escala_y"]
    return x, y
