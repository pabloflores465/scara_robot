"""
robot.py — Conexión NXT, control de motores y rutinas de movimiento.

API usada: nxt-python 3.x
  - nxt.locator.find()            → busca el brick por USB (requiere libusb)
  - brick.get_motor(Port.X)       → retorna objeto Motor
  - motor.turn(power, tacho_units)→ gira `tacho_units` grados con `power` (-127..128)
  - motor.run(power)              → giro continuo sin límite
  - motor.idle()                  → detiene el motor
  - motor.brake()                 → frena y mantiene posición
  - nxt.sensor.generic.Touch      → sensor táctil
  - nxt.sensor.generic.Ultrasonic → sensor ultrasónico (I2C)
"""

import time

import nxt.locator
import nxt.motor
import nxt.sensor
from nxt.sensor.generic import Touch, Ultrasonic


# ──────────────────────────────────────────────
# Conexión
# ──────────────────────────────────────────────

def conectar_nxt():
    """
    Encuentra y retorna el primer ladrillo NXT disponible por USB.
    Requiere libusb instalado: brew install libusb
    get_device_info() → tuple(name, bt_address, bt_signal_strength, free_flash)
    """
    print("[NXT] Buscando ladrillo por USB...")
    brick = nxt.locator.find(backends=["usb"])
    name, bt_address, _, free_flash = brick.get_device_info()
    print(f"[NXT] Conectado  : {name}")
    print(f"[NXT] BT address : {bt_address}")
    print(f"[NXT] Flash libre: {free_flash} bytes")
    return brick


# ──────────────────────────────────────────────
# Motores
# ──────────────────────────────────────────────

PUERTOS_MOTOR = {
    "A": nxt.motor.Port.A,
    "B": nxt.motor.Port.B,
    "C": nxt.motor.Port.C,
}


def verificar_motores(brick, grados: int = 90, potencia: int = 75):
    """
    Gira cada motor (A, B, C) `grados` adelante y luego regresa.
    Prueba visual del Día 1.

    Usa weak_turn() en lugar de turn() para evitar BlockedException:
    weak_turn() envía el comando y retorna inmediatamente sin monitorear
    el tacómetro, lo que es ideal cuando el motor aún no tiene carga mecánica.
    """
    for nombre, puerto in PUERTOS_MOTOR.items():
        motor = brick.get_motor(puerto)
        print(f"[MOTOR {nombre}] → {grados}°")
        motor.weak_turn(potencia, grados)
        time.sleep(1.0)
        print(f"[MOTOR {nombre}] ← {grados}°")
        motor.weak_turn(-potencia, grados)
        time.sleep(1.0)
        motor.idle()
        print(f"[MOTOR {nombre}] OK")


def mover_motor(brick, puerto_letra: str, grados: int, potencia: int = 75):
    """
    Mueve un motor específico.
    - puerto_letra: 'A', 'B' o 'C'
    - grados: valor absoluto positivo
    - potencia: positivo = adelante, negativo = atrás (-127..128)
    """
    puerto = PUERTOS_MOTOR[puerto_letra.upper()]
    motor = brick.get_motor(puerto)
    motor.turn(potencia, abs(grados))


def ir_a_home(brick, potencia: int = 40):
    """Lleva todos los motores a posición 0 (reset de tacómetro)."""
    for nombre, puerto in PUERTOS_MOTOR.items():
        motor = brick.get_motor(puerto)
        motor.reset_position(relative=False)
        print(f"[MOTOR {nombre}] reset a home")


# ──────────────────────────────────────────────
# Sensores
# ──────────────────────────────────────────────

def verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1):
    """
    Lee el sensor de tacto.
    Clase correcta: nxt.sensor.generic.Touch
    Método: touch.is_pressed() → bool
    """
    sensor = Touch(brick, puerto)
    estado = sensor.is_pressed()
    print(f"[SENSOR TACTO  S{puerto.value + 1}] Presionado: {estado}")
    return estado


def verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4):
    """
    Lee el sensor ultrasónico (digital I2C).
    Clase correcta: nxt.sensor.generic.Ultrasonic
    Método: ultrasonic.get_distance() → int (cm)
    """
    sensor = Ultrasonic(brick, puerto)
    distancia = sensor.get_distance()
    print(f"[SENSOR ULTRASON S{puerto.value + 1}] Distancia: {distancia} cm")
    return distancia


def verificar_sensores(brick):
    """
    Verifica táctil (S1) y ultrasónico (S4).
    Ajusta los puertos según tu cableado real.
    """
    print("\n--- Verificación de sensores ---")
    try:
        verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1)
    except Exception as e:
        print(f"[SENSOR TACTO  S1] Error: {e}")

    try:
        verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4)
    except Exception as e:
        print(f"[SENSOR ULTRASON S4] Error: {e}")
