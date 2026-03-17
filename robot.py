"""
robot.py — Conexión NXT, control de motores y rutinas de movimiento.

API: nxt-python 3.x  (requiere libusb: brew install libusb)
  Motor A → q1  (rotación base)
  Motor B → q2  (rotación codo)
  Motor C → Z   (eje vertical / gripper)
  Sensor S1 → táctil (homing)
  Sensor S4 → ultrasónico (detección presencia)

POSICIONES — editar con ángulos reales medidos en Día 3:
  Cada entrada es (q1_grados, q2_grados, z_tacho)
  q1, q2 en grados de articulación (cinematica.py los convierte a tacho)
"""

import time

import nxt.locator
import nxt.motor
import nxt.sensor
from nxt.motor import BlockedException
from nxt.sensor.generic import Touch, Ultrasonic


# ══════════════════════════════════════════════════════════════════
# POSICIONES CLAVE — EDITAR CON MEDIDAS REALES (DÍA 3)
# ══════════════════════════════════════════════════════════════════
#   (q1_deg, q2_deg, z_tacho)
#   z_tacho: pasos del motor C  (0 = arriba, positivo = bajar)

POSICIONES = {
    "HOME":       (0.0,    0.0,   0),    # posición de reposo
    "TOMA":       (45.0, -30.0,  80),    # sobre el punto de recogida
    "ZONA_ROJA":  (90.0, -45.0,  80),    # zona de depósito roja
    "ZONA_AZUL":  (-90.0,-45.0,  80),    # zona de depósito azul
}

# Potencias de movimiento (0–100)
POT_BASE   = 60   # motor A (q1)
POT_CODO   = 60   # motor B (q2)
POT_Z      = 50   # motor C (Z)
POT_HOMING = 30   # potencia para buscar home con sensor táctil

# Tiempo de espera entre movimientos [s]
PAUSA = 0.3


# ══════════════════════════════════════════════════════════════════
# CONEXIÓN
# ══════════════════════════════════════════════════════════════════

def conectar_nxt():
    """
    Encuentra y retorna el primer ladrillo NXT disponible por USB.
    Requiere: brew install libusb
    """
    print("[NXT] Buscando ladrillo por USB...")
    brick = nxt.locator.find(backends=["usb"])
    name, bt_address, _, free_flash = brick.get_device_info()
    print(f"[NXT] Conectado  : {name}")
    print(f"[NXT] BT address : {bt_address}")
    print(f"[NXT] Flash libre: {free_flash} bytes")
    for freq, dur in [(523, 150), (659, 150), (784, 300)]:
        brick.play_tone_and_wait(freq, dur)
    return brick


# ══════════════════════════════════════════════════════════════════
# MOVIMIENTO DE MOTORES
# ══════════════════════════════════════════════════════════════════

PUERTOS_MOTOR = {
    "A": nxt.motor.Port.A,
    "B": nxt.motor.Port.B,
    "C": nxt.motor.Port.C,
}


def _mover_motor_tacho(brick, puerto_letra: str, tacho: int, potencia: int) -> None:
    """
    Mueve un motor a una posición relativa en tacómetro.
    Usa turn() que bloquea hasta completar el movimiento.
    tacho positivo = dirección A, negativo = dirección B.
    """
    if tacho == 0:
        return
    puerto = PUERTOS_MOTOR[puerto_letra.upper()]
    motor  = brick.get_motor(puerto)
    pot    = potencia if tacho > 0 else -potencia
    try:
        motor.turn(pot, abs(tacho), timeout=5)
    except BlockedException:
        motor.brake()
        print(f"[MOTOR {puerto_letra}] BlockedException — verifica que no haya obstrucción.")


def mover_motor(brick, puerto_letra: str, grados: int, potencia: int = 75) -> None:
    """API pública: mueve un motor específico N grados relativos."""
    _mover_motor_tacho(brick, puerto_letra, grados, potencia)


def verificar_motores(brick, grados: int = 90, potencia: int = 75) -> None:
    """
    Día 1: gira cada motor adelante y atrás para comprobar funcionamiento.
    Usa weak_turn (sin monitoreo de bloqueo) porque el robot aún no está armado.
    """
    for nombre in ["A", "B", "C"]:
        motor = brick.get_motor(PUERTOS_MOTOR[nombre])
        print(f"[MOTOR {nombre}] → {grados}°")
        motor.weak_turn(potencia, grados)
        time.sleep(1.0)
        print(f"[MOTOR {nombre}] ← {grados}°")
        motor.weak_turn(-potencia, grados)
        time.sleep(1.0)
        motor.idle()
        print(f"[MOTOR {nombre}] OK")


# ══════════════════════════════════════════════════════════════════
# HOMING
# ══════════════════════════════════════════════════════════════════

def homing_con_tacto(brick, puerto_tacto=nxt.sensor.Port.S1) -> None:
    """
    Lleva el eje de la base (Motor A) a home usando el sensor táctil.
    El robot gira lentamente hasta presionar el sensor; ese punto es home.
    Después resetea el tacómetro.
    """
    sensor = Touch(brick, puerto_tacto)
    motor  = brick.get_motor(nxt.motor.Port.A)

    print("[HOME] Buscando home con sensor táctil...")
    motor.run(-POT_HOMING)   # girar hacia home

    while not sensor.is_pressed():
        time.sleep(0.05)

    motor.brake()
    time.sleep(0.1)
    motor.reset_position(relative=False)
    print("[HOME] Home encontrado. Tacómetro reseteado.")
    brick.play_tone_and_wait(880, 200)


def ir_a_home(brick) -> None:
    """
    Versión sin sensor: resetea tacómetros y lleva los motores a 0.
    Para usarse solo si los motores ya están en la posición home física.
    """
    for nombre, puerto in PUERTOS_MOTOR.items():
        brick.get_motor(puerto).reset_position(relative=False)
    print("[HOME] Tacómetros reseteados a 0.")


# ══════════════════════════════════════════════════════════════════
# MOVIMIENTO A POSICIÓN ARTICULAR
# ══════════════════════════════════════════════════════════════════

def mover_a_angulos(brick, q1_deg: float, q2_deg: float, z_tacho: int = 0) -> None:
    """
    Mueve el robot a los ángulos articulares dados.
    Convierte grados → tachos usando los gear ratios de cinematica.py.
    Secuencia: primero Z arriba → q1/q2 → Z a posición final.
    """
    from cinematica import (
        articulacion_a_tacho, GEAR_RATIO_Q1, GEAR_RATIO_Q2,
        validar_limites,
    )

    if not validar_limites(q1_deg, q2_deg):
        print(f"[ROBOT] Ángulos fuera de límites: q1={q1_deg:.1f}° q2={q2_deg:.1f}°")
        return

    tacho_a = articulacion_a_tacho(q1_deg, GEAR_RATIO_Q1)
    tacho_b = articulacion_a_tacho(q2_deg, GEAR_RATIO_Q2)

    # Subir eje Z antes de girar (seguridad)
    if z_tacho > 0:
        _mover_motor_tacho(brick, "C", -z_tacho, POT_Z)   # subir primero
        time.sleep(PAUSA)

    # Mover base y codo
    _mover_motor_tacho(brick, "A", tacho_a, POT_BASE)
    time.sleep(PAUSA)
    _mover_motor_tacho(brick, "B", tacho_b, POT_CODO)
    time.sleep(PAUSA)

    # Bajar a posición Z final
    if z_tacho > 0:
        _mover_motor_tacho(brick, "C", z_tacho, POT_Z)
        time.sleep(PAUSA)


def ir_a_posicion(brick, nombre: str) -> None:
    """Mueve el robot a una posición predefinida en POSICIONES."""
    if nombre not in POSICIONES:
        print(f"[ROBOT] Posición '{nombre}' no definida. Opciones: {list(POSICIONES)}")
        return
    q1, q2, z = POSICIONES[nombre]
    print(f"[ROBOT] → {nombre}  (q1={q1}°, q2={q2}°, z={z})")
    mover_a_angulos(brick, q1, q2, z)


# ══════════════════════════════════════════════════════════════════
# SECUENCIAS DE CLASIFICACIÓN (Día 5-6)
# ══════════════════════════════════════════════════════════════════

def secuencia_clasificar(brick, color: str) -> bool:
    """
    Secuencia completa de clasificación para una pelota.
    color: "pelota_roja" o "pelota_azul"

    Etapas:
      1. HOME
      2. TOMA (posición sobre la pelota)
      3. Bajar efector
      4. Tomar pelota (activar gripper si hay motor para ello)
      5. Subir efector
      6. ZONA_ROJA o ZONA_AZUL
      7. Bajar efector
      8. Soltar pelota
      9. Subir efector
     10. HOME
    """
    zona = "ZONA_ROJA" if "roja" in color else "ZONA_AZUL"
    print(f"\n[SEQ] Clasificando: {color} → {zona}")

    try:
        # 1. Home
        ir_a_posicion(brick, "HOME")

        # 2-5. Tomar pelota
        ir_a_posicion(brick, "TOMA")
        print("[SEQ] Tomando pelota...")
        # Si Motor C es el gripper: añadir lógica aquí
        time.sleep(0.5)

        # 6-9. Depositar en zona
        ir_a_posicion(brick, zona)
        print("[SEQ] Depositando pelota...")
        time.sleep(0.5)

        # 10. Volver a home
        ir_a_posicion(brick, "HOME")

        brick.play_tone_and_wait(1047, 200)   # do agudo = éxito
        print(f"[SEQ] OK — {color} depositada en {zona}")
        return True

    except Exception as e:
        print(f"[SEQ] Error durante clasificación: {e}")
        ir_a_posicion(brick, "HOME")   # intentar volver a home
        return False


def ejecutar_con_coordenadas(brick, x: float, y: float, color: str) -> bool:
    """
    Versión de clasificación usando coordenadas del robot (de la cámara).
    Calcula la cinemática inversa y mueve directamente al punto de toma.
    """
    from cinematica import cinematica_inversa, validar_limites

    ik = cinematica_inversa(x, y)
    if ik is None:
        print(f"[ROBOT] ({x:.3f}, {y:.3f}) fuera de alcance del robot.")
        return False

    q1, q2 = ik
    if not validar_limites(q1, q2):
        print(f"[ROBOT] Ángulos fuera de límites: q1={q1:.1f}° q2={q2:.1f}°")
        return False

    zona = "ZONA_ROJA" if "roja" in color else "ZONA_AZUL"
    _, _, z_toma = POSICIONES["TOMA"]
    _, _, z_zona = POSICIONES[zona]

    print(f"[ROBOT] IK: ({x:.3f},{y:.3f}) → q1={q1:.1f}° q2={q2:.1f}°")

    ir_a_posicion(brick, "HOME")
    mover_a_angulos(brick, q1, q2, z_toma)
    time.sleep(0.5)
    ir_a_posicion(brick, zona)
    time.sleep(0.5)
    ir_a_posicion(brick, "HOME")

    brick.play_tone_and_wait(1047, 200)
    return True


# ══════════════════════════════════════════════════════════════════
# SENSORES
# ══════════════════════════════════════════════════════════════════

def verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1) -> bool:
    sensor = Touch(brick, puerto)
    estado = sensor.is_pressed()
    print(f"[SENSOR TACTO  S{puerto.value + 1}] Presionado: {estado}")
    return estado


def verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4) -> int:
    sensor = Ultrasonic(brick, puerto)
    distancia = sensor.get_distance()
    print(f"[SENSOR ULTRASON S{puerto.value + 1}] Distancia: {distancia} cm")
    return distancia


def verificar_sensores(brick) -> None:
    print("\n--- Verificación de sensores ---")
    try:
        verificar_sensor_tacto(brick, puerto=nxt.sensor.Port.S1)
    except Exception as e:
        print(f"[SENSOR TACTO  S1] Error: {e}")
    try:
        verificar_sensor_ultrasonico(brick, puerto=nxt.sensor.Port.S4)
    except Exception as e:
        print(f"[SENSOR ULTRASON S4] Error: {e}")
