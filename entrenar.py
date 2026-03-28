"""
entrenar.py — Entrenamiento del modelo YOLO para detección de pelotas.

Día 4:
  1. Etiqueta las imágenes capturadas con capturar_dataset.py usando
     una herramienta como LabelImg o Roboflow.
  2. Ejecuta este script para crear data.yaml y entrenar el modelo.
  3. El mejor modelo se copia automáticamente a modelo/best.pt.

Ejecutar:
  python entrenar.py                         # configuración por defecto
  python entrenar.py --epochs 100 --img 416  # personalizado
  python entrenar.py --validar               # solo valida sin entrenar

Herramienta de etiquetado recomendada:
  pip install labelImg
  labelImg dataset/images/train dataset/labels/train
"""

import argparse
import os
import shutil
import yaml
from pathlib import Path
from ultralytics import YOLO


# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════

CLASES = ["pelota_azul", "pelota_roja"]   # orden importa: 0=azul, 1=roja
MODELO_BASE = "yolo11m.pt"               # modelo preentrenado de partida
MODELO_DESTINO = "modelo/best.pt"
DATA_YAML = "dataset/data.yaml"


# ══════════════════════════════════════════════════════════════════
# DATA.YAML
# ══════════════════════════════════════════════════════════════════

def crear_data_yaml() -> None:
    """
    Genera dataset/data.yaml con rutas absolutas.
    YOLO requiere rutas absolutas o relativas al directorio de ejecución.
    """
    ruta_base = str(Path("dataset").resolve())
    datos = {
        "path":  ruta_base,
        "train": "images/train",
        "val":   "images/val",
        "nc":    len(CLASES),
        "names": CLASES,
    }
    os.makedirs("dataset", exist_ok=True)
    with open(DATA_YAML, "w") as f:
        yaml.dump(datos, f, allow_unicode=True, default_flow_style=False)
    print(f"[TRAIN] data.yaml creado: {DATA_YAML}")
    print(f"  Clases: {CLASES}")


# ══════════════════════════════════════════════════════════════════
# VERIFICAR DATASET
# ══════════════════════════════════════════════════════════════════

def verificar_dataset() -> bool:
    """
    Verifica que existan imágenes y etiquetas en train y val.
    Las etiquetas deben estar en dataset/labels/train y dataset/labels/val
    en formato YOLO (.txt con clase cx cy w h normalizados).
    """
    ok = True
    for split in ["train", "val"]:
        imgs   = list(Path(f"dataset/images/{split}").glob("*.jpg")) + \
                 list(Path(f"dataset/images/{split}").glob("*.png"))
        labels = list(Path(f"dataset/labels/{split}").glob("*.txt"))

        print(f"[TRAIN] {split}: {len(imgs)} imágenes, {len(labels)} etiquetas")

        if len(imgs) == 0:
            print(f"  [WARN] Sin imágenes en dataset/images/{split}/")
            ok = False
        if len(labels) == 0:
            print(f"  [WARN] Sin etiquetas en dataset/labels/{split}/")
            print(f"  Usa LabelImg para etiquetar en formato YOLO.")
            ok = False
        if len(imgs) > 0 and len(labels) == 0:
            print(f"  [WARN] Hay imágenes pero no etiquetas — no se puede entrenar.")
            ok = False

    return ok


# ══════════════════════════════════════════════════════════════════
# ENTRENAMIENTO
# ══════════════════════════════════════════════════════════════════

def entrenar(epochs: int = 50, imgsz: int = 640, batch: int = 8) -> None:
    """
    Entrena el modelo YOLO con el dataset capturado.

    epochs : número de épocas de entrenamiento
    imgsz  : tamaño de imagen (cuadrado)
    batch  : tamaño de lote (reducir si hay problemas de memoria)
    """
    crear_data_yaml()

    if not verificar_dataset():
        print("\n[TRAIN] Dataset incompleto. Etiqueta las imágenes primero.")
        return

    os.makedirs("modelo", exist_ok=True)

    print(f"\n[TRAIN] Iniciando entrenamiento...")
    print(f"  Modelo base : {MODELO_BASE}")
    print(f"  Épocas      : {epochs}")
    print(f"  Imagen      : {imgsz}×{imgsz}")
    print(f"  Batch       : {batch}")

    modelo = YOLO(MODELO_BASE)
    resultado = modelo.train(
        data=DATA_YAML,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        name="scara_yolo",
        project="runs/detect",
        exist_ok=True,
        verbose=True,
    )

    # Copiar el mejor modelo
    mejor = Path("runs/detect/scara_yolo/weights/best.pt")
    if mejor.exists():
        shutil.copy(mejor, MODELO_DESTINO)
        print(f"\n[TRAIN] Mejor modelo guardado en: {MODELO_DESTINO}")
    else:
        print("\n[TRAIN] No se encontró best.pt. Revisa los logs de entrenamiento.")


# ══════════════════════════════════════════════════════════════════
# VALIDACIÓN
# ══════════════════════════════════════════════════════════════════

def validar() -> None:
    """Valida el modelo entrenado sobre el conjunto de validación."""
    if not os.path.exists(MODELO_DESTINO):
        print(f"[TRAIN] {MODELO_DESTINO} no encontrado. Entrena primero.")
        return

    if not os.path.exists(DATA_YAML):
        crear_data_yaml()

    print(f"\n[TRAIN] Validando {MODELO_DESTINO} ...")
    modelo = YOLO(MODELO_DESTINO)
    metrics = modelo.val(data=DATA_YAML)
    print(f"\n  mAP50    : {metrics.box.map50:.4f}")
    print(f"  mAP50-95 : {metrics.box.map:.4f}")
    print(f"  Precisión : {metrics.box.mp:.4f}")
    print(f"  Recall    : {metrics.box.mr:.4f}")


# ══════════════════════════════════════════════════════════════════
# EXPORTAR (opcional, para dispositivos sin GPU)
# ══════════════════════════════════════════════════════════════════

def exportar_onnx() -> None:
    """Exporta el modelo a ONNX para inferencia sin PyTorch."""
    if not os.path.exists(MODELO_DESTINO):
        print(f"[TRAIN] {MODELO_DESTINO} no encontrado.")
        return
    modelo = YOLO(MODELO_DESTINO)
    modelo.export(format="onnx")
    print("[TRAIN] Modelo exportado a ONNX.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenamiento YOLO — SCARA")
    parser.add_argument("--epochs",  type=int,  default=50,  help="Épocas de entrenamiento")
    parser.add_argument("--img",     type=int,  default=640, help="Tamaño de imagen")
    parser.add_argument("--batch",   type=int,  default=8,   help="Tamaño de lote")
    parser.add_argument("--validar", action="store_true",    help="Solo validar modelo existente")
    parser.add_argument("--exportar",action="store_true",    help="Exportar a ONNX")
    args = parser.parse_args()

    if args.validar:
        validar()
    elif args.exportar:
        exportar_onnx()
    else:
        entrenar(epochs=args.epochs, imgsz=args.img, batch=args.batch)
