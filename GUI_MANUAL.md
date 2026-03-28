# Manual de uso — GUI SCARA Robot

Interfaz gráfica de control integrado: motores, cámara, YOLO y clasificación automática.

---

## Iniciar la GUI

```bash
cd scara_robot
source .venv/bin/activate

# Con NXT conectado por USB
python gui_motores.py

# Con iPhone como cámara (índice 1)
python gui_motores.py --camara 1

# Sin hardware (modo simulación)
python gui_motores.py --skip-nxt
```

---

## Estructura de la pantalla

```
┌─────────────────────────────────────────────────────────────────┐
│  SCARA ROBOT · Control integrado   [NXT]   ● Desconectado  [Conectar NXT] │
├──────────────────────────┬──────────────────────────────────────┤
│  Motor 1 — Base  │ Motor 2 — Codo  │        Cámara              │
│  Motor 3 — Eje Z │ Motor 4 — Garra │  [video en tiempo real]    │
│                          │  CALIBRACIÓN  DETECCIÓN  IK  DESTINO │
│  [ HOME ]                │  [ CLASIFICAR ]  [ AUTO ]            │
│                          │  Consola                             │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 1. Conectar el NXT

1. Enciende el NXT y conéctalo por USB al Mac.
2. Haz clic en **Conectar NXT** (esquina superior derecha).
3. El indicador cambia a `● Conectado` en verde y los paneles de motor se habilitan.

> Si aparece `Error al conectar NXT: no brick found`:
> - Verifica que el NXT esté encendido.
> - Usa el cable USB original LEGO.
> - Comprueba con `system_profiler SPUSBDataType | grep -i LEGO`.

---

## 2. Controlar los motores

Cada motor tiene su propio panel con los mismos controles:

| Control | Función |
|---|---|
| Número grande (ej. `0°`) | Posición actual acumulada |
| Slider horizontal | Mover arrastrando; se ejecuta al soltar |
| **◀ −** / **+ ▶** | Mover el paso configurado en sentido − o + |
| **Paso** (spinner) | Cuántos grados/tachos mueve cada clic |
| **Velocidad** (slider) | Potencia del motor, 10–100 % |
| **Aceleración** (slider) | Suavidad del arranque: Directa → Muy lenta |
| **Resetear a 0** | Mueve de vuelta a la posición 0 |

### Motor 4 — Garra
Tiene además dos botones rápidos:
- **↔ ABRIR** — gira en sentido antihorario (abre la garra).
- **↕ CERRAR** — gira en sentido horario (cierra la garra).

### Botón HOME
Envía todos los motores a la posición de reposo definida en `robot.py → POSICIONES["HOME"]` y resetea los contadores de posición.

---

## 3. Usar la cámara

1. Ajusta el **Índice** de cámara:
   - `0` → cámara integrada del Mac
   - `1` → iPhone via Continuity Camera (conectar por cable primero)
2. Haz clic en **▶ Iniciar**.
3. El video aparece en tiempo real en el panel derecho.
4. Para detener: **■ Detener**.

---

## 4. Activar detección YOLO

1. Con la cámara activa, haz clic en **YOLO: OFF**.
2. Se carga el modelo `modelo/best.pt` (puede tardar unos segundos).
3. El botón cambia a **YOLO: ON** en verde.
4. El sistema detecta `pelota_roja` y `pelota_azul` en cada frame.
5. El panel pipeline muestra:
   - **DETECCIÓN** — clase y confianza de lo detectado.
   - **px** — posición en píxeles del centroide.
   - **DESTINO** — `→ ZONA_ROJA` o `→ ZONA_AZUL` según el color.
   - Las esquinas del video muestran los badges **ZONA ROJA** y **ZONA AZUL**; el destino activo se ilumina.

> Si no existe `modelo/best.pt`, usa el modelo genérico `yolo11n.pt` para pruebas (no reconocerá pelotas específicas).

---

## 5. Calibración cámara-robot

La calibración mapea píxeles del video a coordenadas reales del robot (metros). **Sin calibración, CLASIFICAR no funciona.**

### Opción A — ArUco AUTO (recomendado)

**Una sola vez: generar e imprimir marcadores**
```bash
python -c "from calibracion import generar_aruco; generar_aruco()"
```
Imprime los 4 archivos de `aruco_markers/` al mismo tamaño.

**Una sola vez: medir y configurar**
1. Coloca los 4 marcadores (ID 0, 1, 2, 3) sobre la mesa de trabajo.
2. Mide con regla la distancia X e Y desde el **centro de la base del robot** hasta cada marcador.
3. Edita `gui_motores.py`:
```python
ARUCO_ROBOT_COORDS = {
    0: ( 0.10,  0.15),   # X metros, Y metros — ajustar con medidas reales
    1: (-0.10,  0.15),
    2: (-0.10, -0.05),
    3: ( 0.10, -0.05),
}
```

**Cada sesión: calibrar**
1. Con la cámara activa y los 4 marcadores visibles en el video, haz clic en **▣ ArUco AUTO**.
2. La consola muestra `Detectados: [0, 1, 2, 3]` y calcula la homografía automáticamente.
3. El indicador cambia a `● Calibrado (ArUco)`.

> Si aparece `Faltan marcadores IDs: [x]` significa que ese marcador no está visible — ajusta la posición o iluminación.
> Si aparece un error de JSON, actualiza el código a la versión más reciente.

### Opción B — Manual

1. Coloca 4 marcas físicas en la mesa y mide su posición (X, Y) desde la base.
2. Haz clic en **Manual**.
3. Haz clic en cada una de las 4 marcas en el video (aparecen círculos numerados).
4. En el diálogo, ingresa las coordenadas reales de cada punto en metros.
5. Haz clic en **Confirmar**.

### Cargar calibración guardada
Si ya calibraste antes, haz clic en **Cargar** para recuperar `calibracion.json` sin repetir el proceso.

---

## 6. Clasificar una pelota

### Checklist antes de clasificar

Verifica que el panel pipeline muestre todo en orden:

| Indicador | Estado esperado |
|---|---|
| `CALIBRACIÓN` | `● Calibrado (ArUco)` en verde |
| `DETECCIÓN` | `pelota_roja` o `pelota_azul` con confianza > 0.5 |
| `px:` | coordenadas del centroide detectado |
| `robot:` | coordenadas en metros (ej. `0.123m, 0.087m`) |
| `IK` | `q1` y `q2` calculados + `ALCANZABLE` en verde |
| `DESTINO` | `→ ZONA_ROJA` o `→ ZONA_AZUL` |
| NXT | `● Conectado` en verde |

> **Antes de clasificar por primera vez**, prueba cada motor manualmente con los paneles para verificar que las posiciones son correctas. Si el robot va a un lugar incorrecto, ajusta `POSICIONES` en `robot.py`:
> ```python
> POSICIONES = {
>     "HOME":      (0.0,    0.0,   0),
>     "ZONA_ROJA": (90.0,  -45.0, 80),   # ajustar con medidas reales
>     "ZONA_AZUL": (-90.0, -45.0, 80),   # ajustar con medidas reales
> }
> ```

### Manual (un solo ciclo)
1. Con el checklist completo, haz clic en **CLASIFICAR**.
2. El robot ejecuta la secuencia completa:
   - HOME → posición sobre la pelota → bajar Z → cerrar garra → subir Z → zona destino → bajar Z → abrir garra → subir Z → HOME
3. La consola muestra el resultado (`✓ clasificada correctamente` o error).

### Automático (ciclo continuo)
1. Con todo listo, haz clic en **AUTO: OFF** para activarlo (`AUTO: ON` en verde).
2. El sistema clasifica automáticamente cada vez que detecta una pelota alcanzable.
3. Para detener: haz clic en **AUTO: ON**.

---

## 7. Sistema de coordenadas del robot

```
        Y+  (adelante)
        ↑
        │
─── ────●──────── X+  (derecha)
      base
   del robot
```

- Origen `(0, 0)`: centro del eje de rotación de la base.
- Los motores A y B mueven el brazo en el plano horizontal (XY).
- El motor C mueve el efector verticalmente (arriba/abajo).
- El motor D abre y cierra la garra.

---

## 8. Parámetros a ajustar en el código

| Archivo | Variable | Qué ajustar |
|---|---|---|
| `cinematica.py` | `L1`, `L2`, `DZ` | Longitudes reales del brazo (metros) |
| `robot.py` | `POSICIONES` | HOME, ZONA_ROJA, ZONA_AZUL en grados |
| `robot.py` | `PUERTO_GRIPPER` | Puerto del motor de la garra (`"A"`, `"B"`, `"C"`) |
| `robot.py` | `TACHO_CERRAR` | Cuántos grados cierra la garra |
| `gui_motores.py` | `ARUCO_ROBOT_COORDS` | Posición física de los marcadores ArUco |

---

## 9. Solución de problemas

| Problema | Solución |
|---|---|
| `no brick found` | NXT apagado, cable incorrecto o sin libusb (`brew install libusb`) |
| Cámara negra | Hacer clic en **▶ Iniciar**; verificar índice correcto |
| iPhone no aparece | Conectar por cable, activar Continuity Camera en Ajustes |
| YOLO no detecta | Verificar que `modelo/best.pt` existe y fue entrenado con `pelota_roja`/`pelota_azul` |
| ArUco no detecta | Instalar `pip install opencv-contrib-python`; mejorar iluminación; acercar cámara |
| `Faltan marcadores IDs: [x]` | El marcador x no es visible — moverlo o mejorar iluminación |
| CLASIFICAR deshabilitado | Falta calibración, YOLO apagado, NXT desconectado o pelota fuera de alcance |
| Robot va a posición incorrecta | Ajustar `POSICIONES` en `robot.py` con ángulos reales medidos |
| Motor no responde | Verificar que el puerto (A/B/C/D) coincide con la conexión física |
| `robot:` muestra valores incorrectos | Recalibrar — los marcadores ArUco se movieron o la cámara cambió de posición |
