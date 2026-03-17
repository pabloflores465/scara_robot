"""
calibracion.py — Calibración cámara-robot mediante homografía.

Flujo del Día 5:
  1. Ejecutar:  python calibracion.py
  2. La webcam se abre y muestra el área de trabajo.
  3. Hacer clic en 4 puntos de referencia CONOCIDOS en el área del robot.
  4. Ingresar las coordenadas (x, y) del robot en metros para cada punto.
  5. El script calcula la homografía y la guarda en calibracion.json.
  6. cinematica.py la carga automáticamente en pixel_a_robot().

Uso posterior:
  from calibracion import cargar_calibracion, pixel_a_robot
  H = cargar_calibracion()
  x, y = pixel_a_robot(cx, cy, H)
"""

import json
import os
import cv2
import numpy as np

ARCHIVO = "calibracion.json"
N_PUNTOS = 4


# ══════════════════════════════════════════════════════════════════
# GUARDAR / CARGAR
# ══════════════════════════════════════════════════════════════════

def guardar_calibracion(H: np.ndarray, puntos_px: list, puntos_robot: list) -> None:
    datos = {
        "homografia": H.tolist(),
        "puntos_px":    puntos_px,
        "puntos_robot": puntos_robot,
    }
    with open(ARCHIVO, "w") as f:
        json.dump(datos, f, indent=2)
    print(f"[CAL] Calibración guardada en {ARCHIVO}")


def cargar_calibracion() -> np.ndarray | None:
    """Retorna la matriz de homografía 3×3 o None si no existe archivo."""
    if not os.path.exists(ARCHIVO):
        print(f"[CAL] {ARCHIVO} no encontrado. Ejecuta: python calibracion.py")
        return None
    with open(ARCHIVO) as f:
        datos = json.load(f)
    H = np.array(datos["homografia"], dtype=np.float64)
    print(f"[CAL] Homografía cargada desde {ARCHIVO}")
    return H


# ══════════════════════════════════════════════════════════════════
# CONVERSIÓN
# ══════════════════════════════════════════════════════════════════

def pixel_a_robot(px: int, py: int, H: np.ndarray) -> tuple[float, float]:
    """
    Convierte un punto en píxeles a coordenadas del robot [m] usando
    la homografía H calculada en la calibración.
    """
    pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
    res = cv2.perspectiveTransform(pt, H)
    return float(res[0][0][0]), float(res[0][0][1])


# ══════════════════════════════════════════════════════════════════
# CALIBRACIÓN INTERACTIVA
# ══════════════════════════════════════════════════════════════════

_clicks: list[tuple[int, int]] = []


def _on_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(_clicks) < N_PUNTOS:
        _clicks.append((x, y))
        print(f"  [Clic {len(_clicks)}/{N_PUNTOS}] pixel=({x}, {y})")


def calibrar_interactivo(indice_camara: int = 0) -> np.ndarray | None:
    """
    Proceso interactivo:
      - Abre la webcam.
      - El usuario hace clic en N_PUNTOS puntos de referencia.
      - Ingresa coordenadas robot (x, y) en metros para cada punto.
      - Calcula y guarda la homografía.
    Retorna la homografía H o None si fue cancelado.
    """
    global _clicks
    _clicks = []

    cap = cv2.VideoCapture(indice_camara)
    if not cap.isOpened():
        print("[CAL] No se pudo abrir la webcam.")
        return None

    cv2.namedWindow("Calibracion - Haz clic en 4 puntos")
    cv2.setMouseCallback("Calibracion - Haz clic en 4 puntos", _on_click)

    print("\n[CAL] ══════════════════════════════════════════")
    print("[CAL] INSTRUCCIONES DE CALIBRACIÓN")
    print("[CAL] 1. Coloca 4 marcas físicas en el área de trabajo.")
    print("[CAL] 2. Mide sus posiciones en el sistema del robot (metros).")
    print("[CAL] 3. Haz clic en cada marca en el orden que las mediste.")
    print("[CAL] Presiona 'q' para cancelar.")
    print("[CAL] ══════════════════════════════════════════\n")

    ret, frame_ref = cap.read()
    if not ret:
        cap.release()
        return None

    # Esperar 4 clics
    while len(_clicks) < N_PUNTOS:
        ret, frame = cap.read()
        if not ret:
            break
        display = frame.copy()

        # Dibujar clics ya registrados
        for i, (px, py) in enumerate(_clicks):
            cv2.circle(display, (px, py), 8, (0, 255, 0), -1)
            cv2.putText(display, str(i + 1), (px + 10, py - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        restantes = N_PUNTOS - len(_clicks)
        cv2.putText(display, f"Haz clic en {restantes} punto(s) mas",
                    (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        cv2.imshow("Calibracion - Haz clic en 4 puntos", display)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return None

    cap.release()
    cv2.destroyAllWindows()

    # Pedir coordenadas robot para cada clic
    puntos_robot = []
    print("\n[CAL] Ingresa las coordenadas del robot para cada punto (en metros):")
    for i, (px, py) in enumerate(_clicks):
        print(f"  Punto {i+1} (pixel {px},{py}):")
        try:
            xr = float(input("    x [m]: "))
            yr = float(input("    y [m]: "))
        except ValueError:
            print("[CAL] Valor inválido. Cancelando.")
            return None
        puntos_robot.append((xr, yr))

    # Calcular homografía
    src = np.array(_clicks, dtype=np.float32)
    dst = np.array(puntos_robot, dtype=np.float32)

    # Para 4 puntos usamos getPerspectiveTransform (exacto, sin RANSAC)
    H = cv2.getPerspectiveTransform(src, dst)

    # Verificar reproyección
    print("\n[CAL] Verificación de reproyección:")
    for i, ((px, py), (xr, yr)) in enumerate(zip(_clicks, puntos_robot)):
        xc, yc = pixel_a_robot(px, py, H)
        err = math.sqrt((xc - xr) ** 2 + (yc - yr) ** 2)
        print(f"  Punto {i+1}: robot=({xr:.4f},{yr:.4f})  calc=({xc:.4f},{yc:.4f})  err={err*1000:.2f} mm")

    guardar_calibracion(H, _clicks, puntos_robot)
    return H


def verificar_calibracion(H: np.ndarray, indice_camara: int = 0) -> None:
    """
    Muestra el feed de la cámara con coordenadas del robot superpuestas.
    Útil para verificar que la calibración es correcta antes del Día 5.
    """
    cap = cv2.VideoCapture(indice_camara)
    if not cap.isOpened():
        return

    print("[CAL] Preview de calibración activo. Mueve el mouse. 'q' para salir.")
    coords_mouse = [0, 0]

    def _mouse_move(event, x, y, flags, param):
        coords_mouse[0], coords_mouse[1] = x, y

    cv2.namedWindow("Verificar Calibracion")
    cv2.setMouseCallback("Verificar Calibracion", _mouse_move)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        px, py = coords_mouse
        xr, yr = pixel_a_robot(px, py, H)
        txt = f"px=({px},{py})  robot=({xr:.3f}m, {yr:.3f}m)"
        cv2.putText(frame, txt, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.circle(frame, (px, py), 5, (0, 255, 255), -1)
        cv2.imshow("Verificar Calibracion", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


import math

if __name__ == "__main__":
    H = calibrar_interactivo(indice_camara=0)
    if H is not None:
        resp = input("\n¿Verificar calibración con preview? (s/n): ").strip().lower()
        if resp == "s":
            verificar_calibracion(H, indice_camara=0)
