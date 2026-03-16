"""
robot.py — Conexión NXT, control de motores y rutinas de movimiento.
"""

import time
import nxt.locator
import nxt.motor
import nxt.sensor


# ──────────────────────────────────────────────
# Conexión
# ──────────────────────────────────────────────

def conectar_nxt():
    """Encuentra y retorna el primer ladrillo NXT disponible por USB."""
    print("[NXT] Buscando ladrillo...")
    brick = nxt.locator.find()
    info = brick.get_device_info()
    print(f"[NXT] Conectado: {info.name} | Bluetooth: {info.bt_address}")
    return brick


# ──────────────────────────────────────────────
# Motores
# ──────────────────────────────────────────────

PUERTOS_MOTOR = {
    "A": nxt.motor.Port.A,
    "B": nxt.motor.Port.B,
    "C": nxt.motor.Port.C,
}


def verificar_motores(brick, grados: int = 90, potencia: int = 30):
    """
    Gira cada motor (A, B, C) `grados` hacia adelante y luego regresa.
    Sirve como prueba visual de funcionamiento en el Día 1.
    """
    for nombre, puerto in PUERTOS_MOTOR.items():
        print(f"[MOTOR {nombre}] Girando {grados}° adelante...")
        motor = brick.get_motor(puerto)
        motor.turn(potencia, grados)
        time.sleep(0.5)
        print(f"[MOTOR {nombre}] Regresando {grados}°...")
        motor.turn(potencia, -grados)
        time.sleep(0.5)
        print(f"[MOTOR {nombre}] OK")


def mover_motor(brick, puerto_letra: str, grados: int, potencia: int = 30):
    """Mueve un motor específico. puerto_letra: 'A', 'B' o 'C'."""
    puerto = PUERTOS_MOTOR[puerto_letra.upper()]
    motor = brick.get_motor(puerto)
    motor.turn(potencia, grados)


# ──────────────────────────────────────────────
# Sensores — Día 1: solo verificación
# ──────────────────────────────────────────────

def verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1):
    """Lee el sensor de tacto y muestra su estado."""
    sensor = nxt.sensor.Touch(brick, puerto)
    estado = sensor.get_sample()
    print(f"[SENSOR TACTO S1] Presionado: {estado}")
    return estado


def verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4):
    """Lee el sensor ultrasónico y muestra la distancia en cm."""
    sensor = nxt.sensor.Ultrasonic(brick, puerto)
    distancia = sensor.get_sample()
    print(f"[SENSOR ULTRASONICO S4] Distancia: {distancia} cm")
    return distancia


def verificar_sensores(brick):
    """
    Verifica táctil (S1) y ultrasónico (S4).
    Ajusta los puertos si tu cableado es diferente.
    """
    print("\n--- Verificación de sensores ---")
    try:
        verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1)
    except Exception as e:
        print(f"[SENSOR TACTO S1] Error: {e}")

    try:
        verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4)
    except Exception as e:
        print(f"[SENSOR ULTRASONICO S4] Error: {e}")
