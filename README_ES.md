<div align="center">

<img src="Logo/logo.jpg" width="140" alt="Logo del Sistema">

# Sistema de Conteo y Seguimiento de Personas en Farmacias

**Analisis avanzado de comportamiento de clientes mediante vision por ordenador**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![YOLOv5](https://img.shields.io/badge/YOLOv5-Deteccion-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://github.com/ultralytics/yolov5)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Tracking-FF6F00?style=for-the-badge&logo=yolo&logoColor=white)](https://github.com/ultralytics/ultralytics)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![License](https://img.shields.io/badge/Licencia-MIT-green?style=for-the-badge)](LICENSE)

<br>

[**Read in English**](README.md)

</div>

---

## Resumen

Trabajo Fin de Master (TFM): sistema en tiempo real para **conteo y seguimiento de personas** en farmacias usando deep learning. Detecta clientes con YOLO, los rastrea con DeepSORT, analiza tiempo de permanencia por zona y genera mapas de calor — todo con **privacidad RGPD** integrada (pixelado en tiempo real, procesamiento 100% local).

---

## Caracteristicas

<table>
<tr>
<td width="50%">

**Deteccion y Conteo**
- Deteccion de personas con YOLOv5 y lineas virtuales de conteo
- Seguimiento de entradas/salidas en tiempo real
- Umbrales de confianza configurables
- Exportacion JSON de todos los datos

</td>
<td width="50%">

**Tracking y Analitica**
- YOLOv8 + DeepSORT para seguimiento persistente
- Definicion de zonas poligonales con tiempo de permanencia
- Generacion automatica de mapas de calor
- Historial de trayectorias y zonas por persona

</td>
</tr>
<tr>
<td width="50%">

**Privacidad y Cumplimiento**
- Pixelado en tiempo real (activar con tecla `P`)
- Procesamiento 100% local — sin transmision externa
- Cumplimiento RGPD por diseno

</td>
<td width="50%">

**Interfaz Grafica**
- GUI de escritorio con CustomTkinter
- Herramientas interactivas de configuracion
- Vista previa de video integrada
- Inicio/parada con un clic

</td>
</tr>
</table>

---

## Galeria

### Interfaz Principal

| ![Interfaz principal](extras/Imagenes/frontal1.jpg) | ![Panel de procesamiento](extras/Imagenes/frontal2.jpg) |
| :---: | :---: |
| *Panel de control* | *Procesamiento y controles en tiempo real* |

### Herramientas de Configuracion

| ![Crear linea](extras/Imagenes/crear_linea.jpg) | ![Crear zonas](extras/Imagenes/Crear_zonas.jpg) |
| :---: | :---: |
| *Lineas virtuales de conteo* | *Definicion de zonas poligonales* |

### Conteo y Seguimiento

| ![Conteo](extras/Imagenes/conteo_sinpixelado.jpg) | ![Privacidad](extras/Imagenes/conteo_pixelado.jpg) |
| :---: | :---: |
| *Conteo de personas en tiempo real* | *Pixelado de privacidad activado* |

| ![Tracking](extras/Imagenes/tra2.jpg) | ![Mapa de calor](extras/Imagenes/mapas_calor.jpg) |
| :---: | :---: |
| *Seguimiento de trayectorias DeepSORT* | *Mapa de calor generado* |

---

## Arquitectura

```mermaid
graph TD
    A[GUI - CustomTkinter] -->|Pestana Herramientas| B[Configuracion]
    B --> B1[Definir Lineas Virtuales]
    B --> B2[Definir Zonas Poligonales]
    A -->|Pestana Procesamiento| C[Deteccion y Analisis]
    C --> C1[Conteo YOLOv5]
    C --> C2[Tracking YOLOv8+DeepSORT]
    C1 --> D[Exportacion]
    C2 --> D
    D --> D1[datos_conteo/ JSON]
    D --> D2[datos_tracking/ JSON]
    D --> D3[heatmaps/ PNG]
```

---

## Inicio Rapido

### Requisitos

- Python 3.8+
- pip

### Instalacion

```bash
git clone https://github.com/patatapython/Sistema-Tracking-Farmacia.git
cd Sistema-Tracking-Farmacia
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Descargar Modelos YOLO

```bash
# YOLOv5s (~15MB)
wget https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt
# YOLOv8s (~22MB)
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt
```

### Ejecutar

```bash
python uiFarmacia_logo.py
```

---

## Uso

1. **Configurar** (pestana Herramientas): definir lineas de conteo y zonas poligonales interactivamente
2. **Procesar** (pestana Procesamiento): seleccionar fuente de video, iniciar conteo o tracking
3. **Analizar**: los resultados se exportan automaticamente a `datos_conteo/`, `datos_tracking/` y `heatmaps/`

<details>
<summary><b>Formatos de datos de salida</b></summary>

**Conteo** (`datos_conteo/*.json`):
```json
{
  "entradas": 15,
  "salidas": 12,
  "total_personas": 27,
  "personas_dentro": 3,
  "timestamp": "2025-09-05T14:42:45.598Z"
}
```

**Tracking** (`datos_tracking/*.json`):
```json
{
  "timestamp": "20250905_144534",
  "total_personas": 5,
  "sistema_tracking": "DeepSORT",
  "personas": [
    {
      "id": 1,
      "zona_actual": "mostrador",
      "tiempo_en_zona_actual": 45.2,
      "historial_zonas": [
        {
          "zona": "entrada",
          "tiempo_entrada": "2025-09-05T14:40:00",
          "tiempo_salida": "2025-09-05T14:40:30",
          "duracion": 30.0
        }
      ]
    }
  ]
}
```

</details>

---

## Estructura del Proyecto

```
Sistema-Tracking-Farmacia/
├── uiFarmacia_logo.py      Aplicacion GUI principal
├── conteo.py               Modulo de conteo con YOLOv5
├── tracking.py             Modulo de tracking YOLOv8 + DeepSORT
├── crear_linea.py          Creador interactivo de lineas de conteo
├── crear_zonas.py          Creador interactivo de zonas poligonales
├── config/                 Archivos de configuracion (lineas y zonas)
├── datos_conteo/           Resultados de conteo (JSON)
├── datos_tracking/         Resultados de tracking (JSON)
├── heatmaps/               Mapas de calor generados (PNG)
├── extras/Imagenes/        Capturas de pantalla
├── Logo/                   Logo de la aplicacion
└── requirements.txt        Dependencias Python
```

---

## Creditos

Desarrollado como **Trabajo Fin de Master (TFM)** por **Guillermo** — [patatapython](https://github.com/patatapython/)

Agradecimientos:
- [Ultralytics](https://ultralytics.com/) por los modelos YOLO
- [OpenCV](https://opencv.org/) por las herramientas de vision por computadora

---

## Licencia

Distribuido bajo la Licencia MIT. Consulta [LICENSE](LICENSE) para mas informacion.

---

<div align="center">
<sub>Hecho con Python y vision por computadora open source</sub>
</div>
