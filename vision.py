"""
vision.py — Carga de modelo YOLO, inferencia y extracción de clase/centroide.

Día 1 : verificar_webcam(), cargar_modelo(), preview_webcam()
Día 4 : detectar(), detectar_mejor(), dibujar_hud()
Día 5 : abrir_camara(), frame_con_detecciones()
"""

import os
import cv2
from ultralytics import YOLO


# ══════════════════════════════════════════════════════════════════
# MODELO
# ══════════════════════════════════════════════════════════════════

def cargar_modelo(ruta: str = "modelo/best.pt") -> YOLO:
    """
    Carga el modelo YOLO entrenado.
    Si no existe best.pt usa yolo11n.pt (modelo base de prueba).
    """
    if not os.path.exists(ruta):
        print(f"[VISION] '{ruta}' no encontrado. Usando yolo11n.pt para prueba.")
        ruta = "yolo11n.pt"
    modelo = YOLO(ruta)
    print(f"[VISION] Modelo cargado: {ruta}")
    return modelo


# ══════════════════════════════════════════════════════════════════
# DETECCIÓN
# ══════════════════════════════════════════════════════════════════

def detectar(frame, modelo: YOLO, confianza_min: float = 0.5) -> list[dict]:
    """
    Corre inferencia sobre un frame de OpenCV.
    Retorna lista de dicts:
      {clase, confianza, centroide: (cx, cy), bbox: (x1,y1,x2,y2)}
    """
    resultados = modelo(frame, verbose=False)
    detecciones = []
    for r in resultados:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < confianza_min:
                continue
            cls_id = int(box.cls[0])
            clase  = modelo.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            detecciones.append({
                "clase":     clase,
                "confianza": conf,
                "centroide": (cx, cy),
                "bbox":      (x1, y1, x2, y2),
            })
    # Ordenar por confianza descendente
    detecciones.sort(key=lambda d: d["confianza"], reverse=True)
    return detecciones


def detectar_mejor(frame, modelo: YOLO, confianza_min: float = 0.5) -> dict | None:
    """Retorna solo la detección con mayor confianza, o None."""
    dets = detectar(frame, modelo, confianza_min)
    return dets[0] if dets else None


# ══════════════════════════════════════════════════════════════════
# VISUALIZACIÓN
# ══════════════════════════════════════════════════════════════════

_COLORES = {
    "pelota_azul": (220, 100, 0),   # BGR naranja → azul en pantalla no confundir
    "pelota_roja": (0,   0,   220),
}
_COLOR_DEFAULT = (180, 180, 180)


def dibujar_detecciones(frame, detecciones: list[dict]) -> None:
    """Dibuja bboxes, etiquetas y centroides sobre el frame (in-place)."""
    for d in detecciones:
        x1, y1, x2, y2 = d["bbox"]
        cx, cy = d["centroide"]
        color = _COLORES.get(d["clase"], _COLOR_DEFAULT)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{d['clase']}  {d['confianza']:.2f}"
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)


def dibujar_hud(
    frame,
    detecciones: list[dict],
    coords_robot: tuple[float, float] | None = None,
    estado: str = "",
) -> None:
    """
    HUD completo: detecciones + coordenadas del robot + estado del sistema.
    """
    dibujar_detecciones(frame, detecciones)

    h, w = frame.shape[:2]

    # Panel inferior
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 50), (w, h), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Texto de estado
    if detecciones:
        d = detecciones[0]
        cx, cy = d["centroide"]
        txt = f"{d['clase']}  conf={d['confianza']:.2f}  px=({cx},{cy})"
        if coords_robot:
            xr, yr = coords_robot
            txt += f"  robot=({xr:.3f}m, {yr:.3f}m)"
    else:
        txt = "Sin deteccion"

    cv2.putText(frame, txt, (10, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    if estado:
        cv2.putText(frame, estado, (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


# ══════════════════════════════════════════════════════════════════
# CÁMARA
# ══════════════════════════════════════════════════════════════════

def verificar_webcam(indice: int = 0) -> bool:
    """Comprueba que la webcam se puede abrir y leer."""
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        print(f"[VISION] No se pudo abrir la webcam (índice {indice}).")
        return False
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[VISION] Webcam abierta pero no se pudo leer el frame.")
        return False
    h, w = frame.shape[:2]
    print(f"[VISION] Webcam OK — resolución: {w}x{h}")
    return True


def abrir_camara(indice: int = 0) -> cv2.VideoCapture:
    """Abre y retorna el objeto VideoCapture. Lanza excepción si falla."""
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la webcam (índice {indice}).")
    return cap


def preview_webcam(modelo: YOLO = None, indice: int = 0) -> None:
    """
    Preview en tiempo real. Si se pasa modelo, dibuja detecciones.
    Presiona 'q' para salir.
    """
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        print(f"[VISION] No se pudo abrir la webcam (índice {indice}).")
        return

    print("[VISION] Preview activo. Presiona 'q' para salir.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if modelo is not None:
            dets = detectar(frame, modelo)
            dibujar_hud(frame, dets, estado="PREVIEW")

        cv2.imshow("SCARA Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
