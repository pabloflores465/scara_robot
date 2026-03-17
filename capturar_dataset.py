"""
capturar_dataset.py — Herramienta de captura de imágenes para el dataset.

Día 4: Captura imágenes de pelotas rojas y azules con la webcam.

Controles:
  R / r  → guardar frame como  pelota_roja
  B / b  → guardar frame como  pelota_azul
  S / s  → guardar sin etiquetar (para revisión posterior)
  Q / q  → salir

Las imágenes se guardan en:
  dataset/images/train/   (80 %)
  dataset/images/val/     (20 %)

Ejecutar:
  python capturar_dataset.py
  python capturar_dataset.py --camara 1   (si hay más de una webcam)
"""

import argparse
import os
import random
import cv2


CLASES = {
    "r": "pelota_roja",
    "b": "pelota_azul",
}

DIRS = {
    "train": "dataset/images/train",
    "val":   "dataset/images/val",
}

VAL_PROB = 0.2   # 20% van a val, 80% a train


def _siguiente_indice(directorio: str, prefijo: str) -> int:
    """Retorna el siguiente índice disponible para nombrar imágenes."""
    existentes = [
        f for f in os.listdir(directorio)
        if f.startswith(prefijo) and f.endswith(".jpg")
    ]
    if not existentes:
        return 0
    indices = []
    for f in existentes:
        try:
            indices.append(int(f.replace(prefijo + "_", "").replace(".jpg", "")))
        except ValueError:
            pass
    return max(indices) + 1 if indices else 0


def _contar_imagenes() -> dict:
    """Cuenta imágenes por clase en train y val."""
    conteo = {}
    for clase in CLASES.values():
        conteo[clase] = {"train": 0, "val": 0}
    for split, directorio in DIRS.items():
        if not os.path.isdir(directorio):
            continue
        for f in os.listdir(directorio):
            for clase in CLASES.values():
                if f.startswith(clase):
                    conteo[clase][split] += 1
    return conteo


def capturar(indice_camara: int = 0) -> None:
    os.makedirs(DIRS["train"], exist_ok=True)
    os.makedirs(DIRS["val"],   exist_ok=True)

    cap = cv2.VideoCapture(indice_camara)
    if not cap.isOpened():
        print(f"[DS] No se pudo abrir la webcam (índice {indice_camara}).")
        return

    print("\n[DS] ══════════════════════════════════════════")
    print("[DS] CAPTURA DE DATASET")
    print("[DS]   R = pelota_roja   B = pelota_azul   Q = salir")
    print("[DS] ══════════════════════════════════════════\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        conteo = _contar_imagenes()
        display = frame.copy()

        # HUD
        y = 30
        for clase, splits in conteo.items():
            total = splits["train"] + splits["val"]
            txt = f"{clase}: {total}  (tr={splits['train']} vl={splits['val']})"
            color = (0, 0, 220) if "roja" in clase else (220, 100, 0)
            cv2.putText(display, txt, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            y += 28

        cv2.putText(display, "R=roja  B=azul  Q=salir", (10, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow("Captura Dataset - SCARA YOLO", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        clase_key = chr(key).lower() if key < 128 else ""
        if clase_key in CLASES:
            clase = CLASES[clase_key]
            split = "val" if random.random() < VAL_PROB else "train"
            directorio = DIRS[split]
            idx = _siguiente_indice(directorio, clase)
            nombre = f"{clase}_{idx:04d}.jpg"
            ruta = os.path.join(directorio, nombre)
            cv2.imwrite(ruta, frame)
            print(f"[DS] Guardado [{split}]: {ruta}")

    cap.release()
    cv2.destroyAllWindows()

    # Resumen final
    conteo = _contar_imagenes()
    print("\n[DS] ══════ Resumen del dataset ══════")
    total_global = 0
    for clase, splits in conteo.items():
        total = splits["train"] + splits["val"]
        total_global += total
        print(f"  {clase}: {total}  (train={splits['train']}, val={splits['val']})")
    print(f"  Total: {total_global} imágenes")
    print("[DS] Recuerda etiquetar las imágenes antes de entrenar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura de dataset YOLO")
    parser.add_argument("--camara", type=int, default=0, help="Índice de la webcam")
    args = parser.parse_args()
    capturar(indice_camara=args.camara)
