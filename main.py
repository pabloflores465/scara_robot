"""
main.py — Lógica de integración completa del sistema SCARA + YOLO.

DÍA 1: script de verificación de ambiente.
  - Verifica instalación de ultralytics y OpenCV.
  - Conecta al NXT y prueba motores A, B, C.
  - Verifica sensores táctil y ultrasónico.
  - Abre la webcam y confirma resolución.

Ejecutar:
    python main.py
    python main.py --preview   (abre ventana de cámara)
    python main.py --skip-nxt  (omite NXT si no está conectado)
"""

import argparse
import sys


def verificar_imports():
    """Confirma que todas las dependencias están instaladas."""
    errores = []
    try:
        import cv2
        print(f"[OK] opencv-python {cv2.__version__}")
    except ImportError:
        errores.append("opencv-python")

    try:
        import ultralytics
        print(f"[OK] ultralytics {ultralytics.__version__}")
    except ImportError:
        errores.append("ultralytics")

    try:
        import nxt.locator  # noqa: F401
        print("[OK] nxt-python")
    except ImportError:
        errores.append("nxt-python")

    if errores:
        print(f"\n[ERROR] Falta instalar: {', '.join(errores)}")
        print("  Ejecuta: uv pip install ultralytics opencv-python nxt-python")
        sys.exit(1)
    else:
        print("\n[OK] Todas las dependencias están instaladas.\n")


def main():
    parser = argparse.ArgumentParser(description="SCARA YOLO NXT — Día 1")
    parser.add_argument("--skip-nxt", action="store_true",
                        help="Omite las pruebas de NXT (útil si el brick no está conectado)")
    parser.add_argument("--preview", action="store_true",
                        help="Abre ventana de preview de la webcam al final")
    args = parser.parse_args()

    print("=" * 50)
    print("  SCARA ROBOT — Día 1: Verificación de ambiente")
    print("=" * 50)

    # 1. Verificar dependencias
    print("\n[1/4] Verificando dependencias...")
    verificar_imports()

    # 2. Webcam
    from vision import verificar_webcam, cargar_modelo, preview_webcam
    print("[2/4] Verificando webcam...")
    cam_ok = verificar_webcam(indice=0)
    if not cam_ok:
        print("  Prueba con otro índice (1, 2...) si tienes varias cámaras.")

    # 3. Modelo YOLO base
    print("\n[3/4] Cargando modelo YOLO de prueba...")
    modelo = cargar_modelo("modelo/best.pt")   # usará yolo11n.pt si best.pt no existe

    # 4. NXT
    if args.skip_nxt:
        print("\n[4/4] NXT omitido (--skip-nxt).")
    else:
        from robot import conectar_nxt, verificar_motores, verificar_sensores
        print("\n[4/4] Conectando al NXT...")
        try:
            brick = conectar_nxt()
            print("\n--- Verificación de motores (A, B, C) ---")
            verificar_motores(brick)
            verificar_sensores(brick)
            print("\n[OK] NXT verificado correctamente.")
        except Exception as e:
            print(f"[ERROR NXT] {e}")
            print("  Verifica que el NXT esté encendido y conectado por USB.")
            print("  Puedes re-ejecutar con --skip-nxt para omitir esta prueba.")

    # 5. Preview opcional
    if args.preview and cam_ok:
        print("\n[EXTRA] Abriendo preview de webcam con YOLO. Presiona 'q' para salir.")
        preview_webcam(modelo=modelo, indice=0)

    print("\n" + "=" * 50)
    print("  Día 1 completado. Revisa los resultados arriba.")
    print("=" * 50)


if __name__ == "__main__":
    main()
