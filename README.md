# SCARA Robot — YOLO + LEGO Mindstorms NXT 9797

Proyecto integrador de clasificación automática de pelotas rojas y azules con visión artificial (YOLO) y brazo robot tipo SCARA construido con LEGO Mindstorms NXT (kit 9797).

## Requisitos

- Python 3.11
- [uv](https://docs.astral.sh/uv/)
- LEGO Mindstorms NXT (kit 9797) conectado por USB
- Webcam USB

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/pabloflores465/scara_robot.git
cd scara_robot

# Crear entorno virtual e instalar dependencias
uv venv .venv --python 3.11
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

uv pip install ultralytics opencv-python nxt-python
```

## Estructura del proyecto

```
scara_robot/
├── dataset/          # Imágenes y etiquetas para entrenamiento YOLO
├── modelo/           # Pesos entrenados (best.pt)
├── vision.py         # Carga de modelo, inferencia y extracción de clase/centroide
├── robot.py          # Conexión NXT, control de motores y rutinas de movimiento
├── cinematica.py     # Parámetros D-H, cinemática directa/inversa y conversiones
├── main.py           # Lógica de integración completa
└── README.md
```

## Comandos

### Día 1 — Verificación de ambiente

```bash
# Verificar dependencias + webcam + YOLO (sin NXT)
python main.py --skip-nxt

# Verificar todo incluyendo NXT por USB
python main.py

# Verificar todo y abrir preview de cámara con detección YOLO
python main.py --preview

# Solo NXT: girar motores A, B, C y leer sensores
python -c "from robot import conectar_nxt, verificar_motores, verificar_sensores; b = conectar_nxt(); verificar_motores(b); verificar_sensores(b)"

# Solo webcam
python -c "from vision import verificar_webcam; verificar_webcam()"
```

### Días 2–3 — Robot y cinemática

```bash
# Probar movimiento de un motor específico (puerto, grados, potencia)
python -c "from robot import conectar_nxt, mover_motor; b = conectar_nxt(); mover_motor(b, 'A', 90)"

# Calcular cinemática directa (editar L1/L2 en cinematica.py primero)
python -c "from cinematica import cinematica_directa; print(cinematica_directa(45, 30))"

# Calcular cinemática inversa
python -c "from cinematica import cinematica_inversa; print(cinematica_inversa(0.15, 0.10))"
```

### Día 4 — Dataset y entrenamiento YOLO

```bash
# Entrenar modelo con dataset propio (archivo data.yaml en dataset/)
python -c "from ultralytics import YOLO; m = YOLO('yolo11n.pt'); m.train(data='dataset/data.yaml', epochs=50, imgsz=640)"

# Validar modelo entrenado
python -c "from ultralytics import YOLO; m = YOLO('modelo/best.pt'); m.val()"
```

### Días 5–6 — Integración completa

```bash
# Ejecutar el sistema completo de clasificación
python main.py --preview
```

## Parámetros Denavit-Hartenberg

Completar con medidas reales del robot en el Día 2. Editar `cinematica.py`:

```python
L1 = 0.0   # longitud eslabón 1 [metros]
L2 = 0.0   # longitud eslabón 2 [metros]
DZ = 0.0   # desplazamiento vertical del efector [metros]
```

| i | a(i-1) | α(i-1) | d(i) | θ(i) | Tipo |
|---|--------|--------|------|------|------|
| 1 | 0      | 0      | 0    | q1   | R    |
| 2 | L1     | 0      | 0    | q2   | R    |
| 3 | L2     | 0      | dz   | 0    | P    |

## Referencias

- [NXT-Python — Instalación](https://ni.srht.site/nxt-python/latest/installation.html)
- [NXT-Python — Tutorial](https://ni.srht.site/nxt-python/latest/handbook/tutorial.html)
- [Ultralytics YOLO — Quickstart](https://docs.ultralytics.com/quickstart/)
- [LEGO 9797 — Building Instructions](https://www.lego.com/en-us/service/building-instructions/9797)
