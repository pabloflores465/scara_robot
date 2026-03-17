"""
test_motor_microfono.py — Prueba interactiva de motor y sensor de sonido.

Conecta:
  Motor     → puerto A  (cambia PUERTO_MOTOR si usas B o C)
  Micrófono → puerto S2 (cambia PUERTO_MICRO si usas S1, S3 o S4)

Ejecutar:
  python test_motor_microfono.py
"""

import time
import nxt.locator
import nxt.motor
import nxt.sensor
from nxt.sensor.generic import Sound

PUERTO_MOTOR = nxt.motor.Port.A
PUERTO_MICRO = nxt.sensor.Port.S2   # ajusta si lo conectaste en otro puerto

# Umbral de sonido para activar el motor (0-1023)
UMBRAL_SONIDO = 300

# ══════════════════════════════════════════════════════════════════

def conectar():
    print("[NXT] Conectando...")
    brick = nxt.locator.find(backends=["usb"])
    name, _, _, _ = brick.get_device_info()
    print(f"[NXT] Conectado: {name}")
    brick.play_tone_and_wait(523, 100)
    return brick


def prueba_motor(brick):
    """Gira el motor adelante y atrás una vez."""
    motor = brick.get_motor(PUERTO_MOTOR)
    print("\n[MOTOR] → 360° adelante")
    motor.weak_turn(70, 360)
    time.sleep(2.0)
    print("[MOTOR] ← 360° atrás")
    motor.weak_turn(-70, 360)
    time.sleep(2.0)
    motor.idle()
    print("[MOTOR] OK")


def prueba_microfono(brick, segundos: int = 10):
    """
    Lee el nivel de sonido durante `segundos` segundos y lo muestra
    como barra en la terminal. Rango: 0-1023.
    """
    micro = Sound(brick, PUERTO_MICRO)
    print(f"\n[MICRO] Leyendo sonido {segundos}s  (Ctrl+C para salir antes)")
    print("        Habla, aplaude o silba cerca del sensor.\n")

    inicio = time.time()
    try:
        while time.time() - inicio < segundos:
            nivel = micro.get_loudness()
            barras = int(nivel / 1023 * 40)
            barra  = "█" * barras + "░" * (40 - barras)
            print(f"\r  {nivel:4d} [{barra}]", end="", flush=True)
            time.sleep(0.08)
    except KeyboardInterrupt:
        pass
    print("\n[MICRO] OK")


def modo_reactivo(brick, segundos: int = 30):
    """
    El motor gira cuando el sonido supera el umbral.
    Como una palma de mano que activa el robot.
    """
    micro = Sound(brick, PUERTO_MICRO)
    motor = brick.get_motor(PUERTO_MOTOR)
    print(f"\n[REACTIVO] Motor se activa si sonido > {UMBRAL_SONIDO}")
    print(f"           Duración: {segundos}s  (Ctrl+C para salir)\n")

    inicio = time.time()
    motor_corriendo = False

    try:
        while time.time() - inicio < segundos:
            nivel = micro.get_loudness()
            barras = int(nivel / 1023 * 30)
            barra  = "█" * barras + "░" * (30 - barras)
            estado = "MOTOR ON " if motor_corriendo else "motor off"
            print(f"\r  {nivel:4d} [{barra}] {estado}", end="", flush=True)

            if nivel > UMBRAL_SONIDO and not motor_corriendo:
                motor.run(60)
                motor_corriendo = True
            elif nivel <= UMBRAL_SONIDO and motor_corriendo:
                motor.idle()
                motor_corriendo = False

            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        motor.idle()

    print("\n[REACTIVO] OK")


# ══════════════════════════════════════════════════════════════════

def main():
    brick = conectar()

    while True:
        print("\n═══════════════════════════════")
        print("  1. Probar motor (giro 360°)")
        print("  2. Probar micrófono (10 s)")
        print("  3. Modo reactivo: sonido → motor")
        print("  4. Salir")
        print("═══════════════════════════════")

        try:
            op = input("  Opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if op == "1":
            prueba_motor(brick)
        elif op == "2":
            prueba_microfono(brick, segundos=10)
        elif op == "3":
            modo_reactivo(brick, segundos=30)
        elif op == "4":
            break
        else:
            print("  Opción inválida.")

    brick.play_tone_and_wait(440, 300)
    print("\n[NXT] Hasta luego.")


if __name__ == "__main__":
    main()
