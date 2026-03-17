"""
main.py — Integración completa del sistema SCARA + YOLO.

Uso por día:
  python main.py --dia 1                    # verificar ambiente
  python main.py --dia 2                    # imprimir tabla D-H
  python main.py --dia 3                    # probar movimientos del robot
  python main.py --dia 4                    # demo de detección YOLO
  python main.py --dia 5                    # integración completa
  python main.py --dia 6                    # demo final con logging
  python main.py --dia 5 --skip-nxt         # sin NXT (solo visión)
  python main.py --dia 5 --calibrar         # recalibrar antes de correr
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import cv2


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _titulo(titulo: str) -> None:
    print("\n" + "═" * 52)
    print(f"  {titulo}")
    print("═" * 52)


def verificar_imports() -> None:
    errores = []
    for modulo, nombre in [("cv2", "opencv-python"),
                            ("ultralytics", "ultralytics"),
                            ("nxt.locator", "nxt-python"),
                            ("numpy", "numpy")]:
        try:
            __import__(modulo)
            version = ""
            try:
                import importlib
                m = importlib.import_module(modulo.split(".")[0])
                version = f" {m.__version__}"
            except AttributeError:
                pass
            print(f"  [OK] {nombre}{version}")
        except ImportError:
            print(f"  [--] {nombre}  ← FALTA")
            errores.append(nombre)

    if errores:
        print(f"\n[ERROR] Instala: uv pip install {' '.join(errores)}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════
# DÍA 1 — Verificación de ambiente
# ══════════════════════════════════════════════════════════════════

def dia_1(skip_nxt: bool, preview: bool, **_) -> None:
    _titulo("DÍA 1 — Verificación de ambiente")

    print("\n[1/4] Dependencias:")
    verificar_imports()

    from vision import verificar_webcam, cargar_modelo, preview_webcam
    print("\n[2/4] Webcam:")
    cam_ok = verificar_webcam(indice=0)

    print("\n[3/4] Modelo YOLO:")
    modelo = cargar_modelo("modelo/best.pt")

    if not skip_nxt:
        from robot import conectar_nxt, verificar_motores, verificar_sensores
        print("\n[4/4] NXT:")
        try:
            brick = conectar_nxt()
            verificar_motores(brick)
            verificar_sensores(brick)
            print("\n[OK] NXT verificado.")
        except Exception as e:
            print(f"[ERROR NXT] {e}")
    else:
        print("\n[4/4] NXT omitido (--skip-nxt).")

    if preview and cam_ok:
        print("\n[EXTRA] Preview con YOLO. Presiona 'q' para salir.")
        preview_webcam(modelo=modelo)


# ══════════════════════════════════════════════════════════════════
# DÍA 2 — Cinemática y tabla D-H
# ══════════════════════════════════════════════════════════════════

def dia_2(skip_nxt: bool, **_) -> None:
    _titulo("DÍA 2 — Modelado cinemático D-H")

    from cinematica import (
        imprimir_tabla_dh, imprimir_espacio_trabajo,
        cinematica_directa, cinematica_inversa,
        L1, L2, validar_limites,
    )

    imprimir_tabla_dh()
    imprimir_espacio_trabajo()

    if L1 == 0 or L2 == 0:
        print("\n[WARN] L1 y L2 son 0. Edita cinematica.py con las medidas reales.")
        return

    # Prueba de cinemática directa e inversa
    print("\n  Prueba de ida y vuelta (CD → CI):")
    casos = [(0, 0), (30, -30), (60, 45), (-45, 90)]
    for q1, q2 in casos:
        if not validar_limites(q1, q2):
            print(f"  ({q1}°, {q2}°) fuera de límites — omitido")
            continue
        x, y = cinematica_directa(q1, q2)
        ik   = cinematica_inversa(x, y)
        if ik:
            print(f"  CD({q1:+.0f}°,{q2:+.0f}°) → ({x:.4f},{y:.4f})m  "
                  f"CI → ({ik[0]:+.1f}°,{ik[1]:+.1f}°)")
        else:
            print(f"  ({x:.4f},{y:.4f})m fuera de alcance en CI")


# ══════════════════════════════════════════════════════════════════
# DÍA 3 — Robot y movimientos
# ══════════════════════════════════════════════════════════════════

def dia_3(skip_nxt: bool, **_) -> None:
    _titulo("DÍA 3 — Robot SCARA: movimientos y calibración mecánica")

    from cinematica import imprimir_tabla_dh, L1, L2
    imprimir_tabla_dh()

    if skip_nxt:
        print("[DÍA 3] NXT omitido. Conecta el brick para probar movimientos.")
        return

    from robot import (conectar_nxt, ir_a_home, ir_a_posicion,
                       mover_a_angulos, homing_con_tacto, POSICIONES)

    brick = conectar_nxt()

    print("\n  Posiciones definidas:")
    for nombre, (q1, q2, z) in POSICIONES.items():
        print(f"    {nombre:12s}: q1={q1:+.1f}° q2={q2:+.1f}° z={z}")

    print("\n  Iniciando secuencia de prueba de posiciones...")
    print("  Presiona ENTER para ir a cada posición. Ctrl+C para salir.")

    try:
        for nombre in ["HOME", "TOMA", "ZONA_ROJA", "ZONA_AZUL", "HOME"]:
            input(f"\n  → ENTER para ir a {nombre}: ")
            ir_a_posicion(brick, nombre)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  Interrumpido. Volviendo a HOME...")
        ir_a_posicion(brick, "HOME")

    print("\n[DÍA 3] Prueba completada. Ajusta POSICIONES en robot.py si es necesario.")


# ══════════════════════════════════════════════════════════════════
# DÍA 4 — Dataset y detección YOLO
# ══════════════════════════════════════════════════════════════════

def dia_4(skip_nxt: bool, preview: bool, **_) -> None:
    _titulo("DÍA 4 — Dataset y detección YOLO")

    from vision import cargar_modelo, abrir_camara, detectar, dibujar_hud

    print("  Opciones:")
    print("    1. Capturar imágenes para el dataset")
    print("    2. Demo de detección en tiempo real")
    print("    3. Entrenar modelo")
    print("    4. Validar modelo")

    try:
        opcion = input("\n  Selecciona (1-4): ").strip()
    except (EOFError, KeyboardInterrupt):
        opcion = "2"

    if opcion == "1":
        import capturar_dataset
        capturar_dataset.capturar()

    elif opcion == "2":
        modelo = cargar_modelo("modelo/best.pt")
        cap = abrir_camara(0)
        print("\n  Detección en tiempo real. 'q' para salir.")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            dets = detectar(frame, modelo)
            dibujar_hud(frame, dets, estado="DÍA 4 — DETECCIÓN")
            cv2.imshow("SCARA - Dia 4 Deteccion", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        cap.release()
        cv2.destroyAllWindows()

    elif opcion == "3":
        import entrenar
        entrenar.entrenar()

    elif opcion == "4":
        import entrenar
        entrenar.validar()


# ══════════════════════════════════════════════════════════════════
# DÍA 5 — Integración completa
# ══════════════════════════════════════════════════════════════════

def dia_5(skip_nxt: bool, calibrar: bool, **_) -> None:
    _titulo("DÍA 5 — Integración: visión + cinemática + robot")

    from vision import cargar_modelo, abrir_camara, detectar_mejor, dibujar_hud
    from calibracion import cargar_calibracion, calibrar_interactivo, pixel_a_robot
    from cinematica import cinematica_inversa, validar_limites

    # Calibración
    if calibrar:
        print("\n[CAL] Iniciando calibración...")
        H = calibrar_interactivo(indice_camara=0)
    else:
        H = cargar_calibracion()

    if H is None and not skip_nxt:
        print("[WARN] Sin calibración. Las coordenadas robot serán incorrectas.")

    # Modelo y cámara
    modelo = cargar_modelo("modelo/best.pt")
    cap    = abrir_camara(0)

    # NXT
    brick = None
    if not skip_nxt:
        try:
            from robot import conectar_nxt, ir_a_posicion, ejecutar_con_coordenadas
            brick = conectar_nxt()
            ir_a_posicion(brick, "HOME")
        except Exception as e:
            print(f"[ERROR NXT] {e}. Continuando solo con visión.")

    print("\n  Sistema activo. 'SPACE' = clasificar  'q' = salir")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        det = detectar_mejor(frame, modelo)
        coords_robot = None

        if det and H is not None:
            cx, cy = det["centroide"]
            coords_robot = pixel_a_robot(cx, cy, H)

        estado = f"{'DETECTADO: ' + det['clase'] if det else 'Sin pelota'}"
        dibujar_hud(frame, [det] if det else [], coords_robot, estado)
        cv2.imshow("SCARA - Dia 5 Integracion", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" ") and det and coords_robot and brick:
            xr, yr = coords_robot
            from robot import ejecutar_con_coordenadas
            ejecutar_con_coordenadas(brick, xr, yr, det["clase"])

    cap.release()
    cv2.destroyAllWindows()
    if brick:
        from robot import ir_a_posicion
        ir_a_posicion(brick, "HOME")


# ══════════════════════════════════════════════════════════════════
# DÍA 6 — Demo final con bitácora automática
# ══════════════════════════════════════════════════════════════════

def dia_6(skip_nxt: bool, calibrar: bool, **_) -> None:
    _titulo("DÍA 6 — Demo final y documentación")

    from vision import cargar_modelo, abrir_camara, detectar_mejor, dibujar_hud
    from calibracion import cargar_calibracion, pixel_a_robot

    H      = cargar_calibracion()
    modelo = cargar_modelo("modelo/best.pt")
    cap    = abrir_camara(0)

    # Bitácora
    os.makedirs("bitacora", exist_ok=True)
    ts_inicio = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_log = f"bitacora/sesion_{ts_inicio}.csv"
    log_file = open(archivo_log, "w", newline="")
    writer = csv.writer(log_file)
    writer.writerow(["timestamp", "clase", "confianza", "px", "py",
                     "xr_m", "yr_m", "resultado"])
    print(f"  Bitácora: {archivo_log}")

    brick = None
    if not skip_nxt:
        try:
            from robot import conectar_nxt, ir_a_posicion
            brick = conectar_nxt()
            ir_a_posicion(brick, "HOME")
        except Exception as e:
            print(f"[ERROR NXT] {e}. Continuando solo con visión.")

    aciertos = 0
    intentos = 0
    print("\n  MODO AUTOMÁTICO  'a' = activar/pausar  'q' = salir")
    activo = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        det = detectar_mejor(frame, modelo, confianza_min=0.6)
        coords_robot = None

        if det and H is not None:
            cx, cy = det["centroide"]
            coords_robot = pixel_a_robot(cx, cy, H)

        modo_txt = "AUTO: ON" if activo else "AUTO: OFF  (presiona 'a')"
        stats_txt = f"Aciertos: {aciertos}/{intentos}"
        estado    = f"{modo_txt}   {stats_txt}"
        dibujar_hud(frame, [det] if det else [], coords_robot, estado)

        # Indicador aciertos
        color_st = (0, 200, 0) if activo else (0, 100, 200)
        cv2.putText(frame, stats_txt, (10, frame.shape[0] - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_st, 2)

        cv2.imshow("SCARA - Dia 6 Demo Final", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("a"):
            activo = not activo
            print(f"  Modo automático: {'ON' if activo else 'OFF'}")

        # Clasificación automática
        if activo and det and coords_robot and brick:
            xr, yr = coords_robot
            intentos += 1
            from robot import ejecutar_con_coordenadas
            ok = ejecutar_con_coordenadas(brick, xr, yr, det["clase"])
            if ok:
                aciertos += 1

            # Loguear
            ts = datetime.now().isoformat()
            cx, cy = det["centroide"]
            writer.writerow([ts, det["clase"], f"{det['confianza']:.3f}",
                              cx, cy,
                              f"{xr:.4f}" if coords_robot else "",
                              f"{yr:.4f}" if coords_robot else "",
                              "OK" if ok else "ERROR"])
            log_file.flush()
            time.sleep(1.0)   # pausa entre clasificaciones

    cap.release()
    cv2.destroyAllWindows()
    log_file.close()

    if brick:
        from robot import ir_a_posicion
        ir_a_posicion(brick, "HOME")

    print(f"\n  ══ RESULTADO FINAL ══")
    print(f"  Aciertos : {aciertos} / {intentos}")
    pct = (aciertos / intentos * 100) if intentos > 0 else 0
    print(f"  Tasa     : {pct:.1f}%")
    print(f"  Bitácora : {archivo_log}")


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

DIAS = {
    1: dia_1,
    2: dia_2,
    3: dia_3,
    4: dia_4,
    5: dia_5,
    6: dia_6,
}

DESCRIPCIONES = {
    1: "Verificación de ambiente",
    2: "Modelado D-H y cinemática",
    3: "Robot SCARA: movimientos",
    4: "Dataset y detección YOLO",
    5: "Integración completa",
    6: "Demo final y bitácora",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SCARA YOLO NXT — Sistema de clasificación de pelotas"
    )
    parser.add_argument("--dia", type=int, default=1, choices=range(1, 7),
                        help="Día de trabajo (1-6)")
    parser.add_argument("--skip-nxt", action="store_true",
                        help="Omitir conexión con el NXT")
    parser.add_argument("--preview",  action="store_true",
                        help="Abrir preview de webcam (solo días 1 y 4)")
    parser.add_argument("--calibrar", action="store_true",
                        help="Recalibrar cámara-robot antes de correr (días 5-6)")
    args = parser.parse_args()

    desc = DESCRIPCIONES.get(args.dia, "")
    print(f"\n{'═'*52}")
    print(f"  SCARA ROBOT  —  Día {args.dia}: {desc}")
    print(f"{'═'*52}")

    DIAS[args.dia](
        skip_nxt=args.skip_nxt,
        preview=args.preview,
        calibrar=args.calibrar,
    )


if __name__ == "__main__":
    main()
