"""
cinematica.py — Parámetros D-H, cinemática directa/inversa, conversiones.

SCARA de 2 GDL rotacionales en plano XY + 1 eje Z (Motor C).
  Motor A → q1 (base)
  Motor B → q2 (codo)
  Motor C → Z (efector vertical)

Tabla D-H:
  i | a(i-1) | alpha(i-1) | d(i) | theta(i) | Tipo
  1 |   0    |     0      |  0   |    q1    |  R
  2 |   L1   |     0      |  0   |    q2    |  R
  E |   L2   |     0      |  dz  |    0     |  fijo

INSTRUCCIONES DÍA 2:
  1. Mide con regla los eslabones reales del robot.
  2. Actualiza L1, L2, DZ con esos valores en metros.
  3. Actualiza GEAR_RATIO_Q1 y GEAR_RATIO_Q2 según las ruedas dentadas usadas.
  4. Ajusta Q1_MIN/MAX y Q2_MIN/MAX con los límites mecánicos reales.
"""

import math
import numpy as np


# ══════════════════════════════════════════════════════════════════
# PARÁMETROS — EDITAR CON MEDIDAS REALES DEL ROBOT (DÍA 2)
# ══════════════════════════════════════════════════════════════════

L1 = 0.15        # longitud eslabón 1 [m]  ← MEDIR
L2 = 0.10        # longitud eslabón 2 [m]  ← MEDIR
DZ = 0.05        # descenso del efector    ← MEDIR

# Relación de transmisión: grados_motor / grados_articulación
# Ejemplo: si usas rueda 40 dientes + piñón 8 dientes → ratio = 5.0
GEAR_RATIO_Q1 = 1.0   # ← AJUSTAR con engranajes reales
GEAR_RATIO_Q2 = 1.0   # ← AJUSTAR con engranajes reales
GEAR_RATIO_Z  = 1.0   # pasos_motor / mm de desplazamiento Z

# Límites articulares [grados de articulación]
Q1_MIN, Q1_MAX = -90.0, 90.0
Q2_MIN, Q2_MAX = -135.0, 135.0
Z_MIN,  Z_MAX  =  0.0,   90.0   # en unidades de tacho del motor C


# ══════════════════════════════════════════════════════════════════
# MATRICES D-H
# ══════════════════════════════════════════════════════════════════

def _dh(a: float, alpha: float, d: float, theta: float) -> np.ndarray:
    """
    Matriz de transformación homogénea 4×4 usando convenio D-H estándar.
      a, d     : parámetros de distancia [metros]
      alpha, theta : parámetros de ángulo [radianes]
    """
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array([
        [ct,  -st * ca,   st * sa,  a * ct],
        [st,   ct * ca,  -ct * sa,  a * st],
        [0,    sa,         ca,       d     ],
        [0,    0,          0,        1     ],
    ])


def matriz_total(q1_deg: float, q2_deg: float) -> np.ndarray:
    """
    Retorna T_0E: transformación del marco base al efector.
    """
    q1 = math.radians(q1_deg)
    q2 = math.radians(q2_deg)
    T1 = _dh(a=0,  alpha=0, d=0,  theta=q1)
    T2 = _dh(a=L1, alpha=0, d=0,  theta=q2)
    Te = _dh(a=L2, alpha=0, d=DZ, theta=0)
    return T1 @ T2 @ Te


# ══════════════════════════════════════════════════════════════════
# CINEMÁTICA DIRECTA
# ══════════════════════════════════════════════════════════════════

def cinematica_directa(q1_deg: float, q2_deg: float) -> tuple[float, float]:
    """
    (q1_deg, q2_deg) → (x, y) en metros.
    x = L1·cos(q1) + L2·cos(q1+q2)
    y = L1·sin(q1) + L2·sin(q1+q2)
    """
    q1 = math.radians(q1_deg)
    q2 = math.radians(q2_deg)
    x = L1 * math.cos(q1) + L2 * math.cos(q1 + q2)
    y = L1 * math.sin(q1) + L2 * math.sin(q1 + q2)
    return round(x, 6), round(y, 6)


# ══════════════════════════════════════════════════════════════════
# CINEMÁTICA INVERSA
# ══════════════════════════════════════════════════════════════════

def cinematica_inversa(
    x: float, y: float, codo_arriba: bool = True
) -> tuple[float, float] | None:
    """
    (x, y) en metros → (q1_deg, q2_deg) | None si fuera de alcance.

    codo_arriba=True  → solución con q2 positivo (elbow up).
    codo_arriba=False → solución con q2 negativo (elbow down).
    """
    if L1 == 0 or L2 == 0:
        raise ValueError("Configura L1 y L2 en cinematica.py antes de usar IK.")

    d2 = x ** 2 + y ** 2
    d  = math.sqrt(d2)

    # Verificar alcance
    if d > L1 + L2 or d < abs(L1 - L2):
        return None

    cos_q2 = (d2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))   # clamp numérico

    q2 = math.acos(cos_q2)
    if not codo_arriba:
        q2 = -q2

    alpha = math.atan2(y, x)
    beta  = math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    q1    = alpha - beta

    return math.degrees(q1), math.degrees(q2)


# ══════════════════════════════════════════════════════════════════
# VALIDACIÓN
# ══════════════════════════════════════════════════════════════════

def validar_limites(q1_deg: float, q2_deg: float) -> bool:
    """Retorna True si los ángulos están dentro de los límites mecánicos."""
    return (Q1_MIN <= q1_deg <= Q1_MAX) and (Q2_MIN <= q2_deg <= Q2_MAX)


def alcance_maximo() -> float:
    return L1 + L2


def alcance_minimo() -> float:
    return abs(L1 - L2)


# ══════════════════════════════════════════════════════════════════
# CONVERSIÓN ARTICULACIÓN ↔ MOTOR
# ══════════════════════════════════════════════════════════════════

def articulacion_a_tacho(q_deg: float, gear_ratio: float) -> int:
    """
    Convierte grados de articulación a unidades de tacómetro del motor.
    tacho = q_deg × gear_ratio
    """
    return round(q_deg * gear_ratio)


def tacho_a_articulacion(tacho: int, gear_ratio: float) -> float:
    """Convierte unidades de tacómetro a grados de articulación."""
    return tacho / gear_ratio


# ══════════════════════════════════════════════════════════════════
# CONVERSIÓN PÍXELES → COORDENADAS ROBOT
# (parámetros se calibran en calibracion.py, Día 5)
# ══════════════════════════════════════════════════════════════════

_H_CALIBRACION: np.ndarray | None = None   # Matriz de homografía


def cargar_homografia(H: np.ndarray) -> None:
    """Carga la matriz de homografía calculada en calibracion.py."""
    global _H_CALIBRACION
    _H_CALIBRACION = H


def pixel_a_robot(px: int, py: int) -> tuple[float, float]:
    """
    Convierte coordenadas de imagen (px, py) a coordenadas del robot (x, y) [m].
    Requiere que la calibración haya sido cargada con cargar_homografia().
    """
    if _H_CALIBRACION is None:
        raise RuntimeError("Calibración no cargada. Ejecuta calibracion.py primero.")

    pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
    resultado = cv2.perspectiveTransform(pt, _H_CALIBRACION)
    xr, yr = resultado[0][0]
    return float(xr), float(yr)


# ══════════════════════════════════════════════════════════════════
# RESOLUCIÓN COMPLETA: píxel → IK → tachos
# ══════════════════════════════════════════════════════════════════

def resolver_para_pixel(
    px: int, py: int, codo_arriba: bool = True
) -> dict | None:
    """
    Pipeline completo: píxel → robot coords → IK → tachos de motor.

    Retorna dict con:
      x, y          : coordenadas del robot [m]
      q1, q2        : ángulos articulares [grados]
      tacho_A       : tacómetro motor A (base)
      tacho_B       : tacómetro motor B (codo)
    O None si fuera de alcance o sin calibración.
    """
    try:
        x, y = pixel_a_robot(px, py)
    except RuntimeError:
        return None

    ik = cinematica_inversa(x, y, codo_arriba)
    if ik is None:
        return None

    q1, q2 = ik
    if not validar_limites(q1, q2):
        return None

    return {
        "x":       x,
        "y":       y,
        "q1":      q1,
        "q2":      q2,
        "tacho_A": articulacion_a_tacho(q1, GEAR_RATIO_Q1),
        "tacho_B": articulacion_a_tacho(q2, GEAR_RATIO_Q2),
    }


# ══════════════════════════════════════════════════════════════════
# UTILIDADES DE DIAGNÓSTICO
# ══════════════════════════════════════════════════════════════════

def imprimir_tabla_dh() -> None:
    """Imprime la tabla D-H con los parámetros actuales."""
    print("\n╔══════ Tabla Denavit-Hartenberg ══════════════════════╗")
    print(f"  L1 = {L1*100:.1f} cm  |  L2 = {L2*100:.1f} cm  |  DZ = {DZ*100:.1f} cm")
    print(f"  GR_q1 = {GEAR_RATIO_Q1}  |  GR_q2 = {GEAR_RATIO_Q2}")
    print("╠══ i ══╦══ a(i-1) ══╦══ α(i-1) ══╦══ d(i) ══╦══ θ(i) ══╣")
    print(f"║  1    ║    0       ║    0        ║   0      ║   q1     ║")
    print(f"║  2    ║  {L1:.4f}  ║    0        ║   0      ║   q2     ║")
    print(f"║  E    ║  {L2:.4f}  ║    0        ║  {DZ:.4f} ║   0      ║")
    print("╚═══════╩════════════╩═════════════╩══════════╩══════════╝\n")


def imprimir_espacio_trabajo() -> None:
    """Muestra alcance mínimo y máximo del SCARA."""
    print(f"  Alcance máximo : {alcance_maximo()*100:.1f} cm")
    print(f"  Alcance mínimo : {alcance_minimo()*100:.1f} cm")
    print(f"  Límites q1     : [{Q1_MIN}°, {Q1_MAX}°]")
    print(f"  Límites q2     : [{Q2_MIN}°, {Q2_MAX}°]")


# Import tardío para evitar circular (solo lo usa pixel_a_robot)
try:
    import cv2
except ImportError:
    pass


if __name__ == "__main__":
    imprimir_tabla_dh()
    imprimir_espacio_trabajo()

    # Prueba rápida de ida y vuelta
    q1_test, q2_test = 30.0, -45.0
    x, y = cinematica_directa(q1_test, q2_test)
    ik   = cinematica_inversa(x, y)
    print(f"\n  CD: ({q1_test}°, {q2_test}°) → ({x:.4f} m, {y:.4f} m)")
    if ik:
        print(f"  CI: ({x:.4f}, {y:.4f}) → ({ik[0]:.2f}°, {ik[1]:.2f}°)")
    else:
        print("  CI: fuera de alcance")
