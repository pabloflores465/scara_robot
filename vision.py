"""
vision.py — Carga de modelo YOLO, inferencia y extracción de clase/centroide.
Día 1: solo verifica que YOLO y la webcam funcionen correctamente.
"""

import cv2
from ultralytics import YOLO


# ──────────────────────────────────────────────
# Carga del modelo
# ──────────────────────────────────────────────

def cargar_modelo(ruta: str = "modelo/best.pt") -> YOLO:
    """
    Carga el modelo YOLO entrenado.
    Si no existe 'best.pt', usa yolo11n.pt como modelo base para pruebas.
    """
    import os
    if not os.path.exists(ruta):
        print(f"[VISION] '{ruta}' no encontrado. Usando yolo11n.pt para prueba.")
        ruta = "yolo11n.pt"
    modelo = YOLO(ruta)
    print(f"[VISION] Modelo cargado: {ruta}")
    return modelo


# ──────────────────────────────────────────────
# Detección sobre un frame
# ──────────────────────────────────────────────

def detectar(frame, modelo: YOLO, confianza_min: float = 0.5):
    """
    Corre inferencia sobre un frame de OpenCV.
    Retorna lista de dicts: {clase, confianza, centroide: (cx, cy), bbox: (x1,y1,x2,y2)}
    """
    resultados = modelo(frame, verbose=False)
    detecciones = []
    for r in resultados:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < confianza_min:
                continue
            cls_id = int(box.cls[0])
            clase = modelo.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            detecciones.append({
                "clase": clase,
                "confianza": conf,
                "centroide": (cx, cy),
                "bbox": (x1, y1, x2, y2),
            })
    return detecciones


# ──────────────────────────────────────────────
# Prueba de webcam — solo Día 1
# ──────────────────────────────────────────────

def verificar_webcam(indice: int = 0):
    """
    Abre la webcam, muestra un frame y la cierra.
    Confirma que OpenCV puede acceder a la cámara.
    """
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


def preview_webcam(modelo: YOLO = None, indice: int = 0):
    """
    Muestra el feed de la webcam en tiempo real.
    Si se pasa un modelo, dibuja las detecciones.
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
            for d in dets:
                x1, y1, x2, y2 = d["bbox"]
                cx, cy = d["centroide"]
                color = (255, 0, 0) if "azul" in d["clase"] else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{d['clase']} {d['confianza']:.2f}"
                cv2.putText(frame, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        cv2.imshow("SCARA Vision - Dia 1", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
