import cv2
import numpy as np
import torch
from ultralytics import YOLO
import datetime
import json
import os
import math
from collections import deque
import argparse

# Importar DeepSORT
try:
    from deep_sort_realtime import DeepSort
    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False

# --- CONSTANTES Y CONFIGURACIÓN ---
CONFIDENCE_THRESHOLD = 0.4  # Umbral de confianza para detecciones
SCALE_FACTOR = 0.9  # Factor de reducción de resolución
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.7
FONT_COLOR = (255, 255, 255)  # Blanco para texto
FONT_THICKNESS = 2
BOX_COLOR_PERSON = (0, 165, 255)  # Naranja para bounding boxes
BOX_THICKNESS = 1
CENTROID_SIZE = 4  # Tamaño del círculo del centroide
USE_WEBCAM = False  # Usar webcam en lugar de archivo de video
USE_GROUND_CIRCLE = True  # Dibujar elipse en el suelo
GROUND_CIRCLE_RADIUS = 20  # Radio de la elipse
GROUND_CIRCLE_COLOR = (0, 165, 255)  # Naranja para elipse
GROUND_CIRCLE_THICKNESS = 2
PIXELATE_BLOCK_SIZE = 20  # Tamaño de bloques para pixelado
HEATMAP_ALPHA = 0.6  # Transparencia del mapa de calor
HEATMAP_CIRCLE_RADIUS = 10  # Radio de los círculos en el mapa de calor
YOLO_MODEL_NAME = 'yolov8s'  # Modelo YOLO a usar
DEEPSORT_MAX_AGE = 150  # Máximo número de frames para mantener un track
DEEPSORT_NMS_MAX_OVERLAP = 0.5  # Umbral de solapamiento para NMS
DEEPSORT_MAX_COSINE_DISTANCE = 0.4  # Umbral de distancia para asociar detecciones
DEEPSORT_NN_BUDGET = 100  # Presupuesto para el embedder
OUTPUT_JSON_PREFIX = "tracking_datos"  # Prefijo para nombres de archivos JSON
OUTPUT_DIR = "datos_tracking"  # Directorio para guardar los archivos JSON de tracking
HEATMAP_OUTPUT_DIR = "heatmaps"  # Directorio para guardar los mapas de calor

# --- CLASES Y FUNCIONES AUXILIARES ---

def initialize_system(video_source, zones_file, model_name, output_dir, heatmap_output_dir):
    """
    Inicializa el modelo YOLO, la captura de video y las zonas escaladas.
    
    Args:
        video_source (str or int): Ruta del video o índice de la webcam.
        zones_file (str): Ruta del archivo de configuración de zonas.
        model_name (str): Nombre del modelo YOLO a usar.
        output_dir (str): Directorio para guardar los archivos JSON de tracking.
        heatmap_output_dir (str): Directorio para guardar los mapas de calor.
    
    Returns:
        tuple: Objetos de captura, modelo YOLO, dimensiones originales/escaladas, zonas escaladas, colores de zonas.
    """
    # Cargar modelo YOLO
    try:
        model = YOLO(model_name + '.pt')
        model.classes = [0]  # Solo detectar personas
        print(f"Modelo {model_name} cargado correctamente.")
    except Exception as e:
        print(f"Error al cargar el modelo YOLO: {e}")
        exit()

    # Inicializar captura de video
    cap = cv2.VideoCapture(video_source if not USE_WEBCAM else 0)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir la fuente de video: {video_source}")
        exit()

    ret, frame_test = cap.read()
    if not ret:
        print("Error: No se pudo leer el primer frame del video.")
        cap.release()
        exit()

    H_original, W_original, _ = frame_test.shape
    frame_test_resized = cv2.resize(frame_test, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR)
    H, W, _ = frame_test_resized.shape
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reiniciar al inicio si es un archivo

    # Cargar y escalar zonas
    zonas, colores_zonas = load_zones_from_json(zones_file)
    zonas_escaladas = {}
    for nombre, puntos in zonas.items():
        puntos_escalados = []
        for x, y in puntos:
            puntos_escalados.append((int(x * SCALE_FACTOR), int(y * SCALE_FACTOR)))
        zonas_escaladas[nombre] = puntos_escalados

    # Crear directorios de salida
    for directory in [output_dir, heatmap_output_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directorio creado: {directory}")

    return cap, model, H_original, W_original, H, W, zonas_escaladas, colores_zonas, output_dir, heatmap_output_dir

def load_zones_from_json(file_path):
    """
    Carga las zonas desde un archivo JSON o usa zonas por defecto si falla.
    
    Args:
        file_path (str): Ruta del archivo JSON.
    
    Returns:
        tuple: Diccionario de zonas (nombre: polígono o rectángulo) y colores de zonas.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        zonas = {}
        colores_zonas = {}
        if 'zones' in data:
            for zone in data['zones']:
                points = zone['points']
                # Guardar el polígono completo en lugar de convertirlo a rectángulo
                zonas[zone['name']] = points
                colores_zonas[zone['name']] = tuple(zone['color'])
                print(f"Cargada zona '{zone['name']}' con {len(points)} puntos")
        return zonas, colores_zonas
    except Exception as e:
        print(f"Error al cargar zonas desde {file_path}: {e}. Usando zonas por defecto.")
        return get_default_zones()

def get_default_zones():
    """
    Define zonas por defecto si no se encuentra el archivo JSON.
    
    Returns:
        tuple: Diccionario de zonas y colores de zonas.
    """
    # Definir zonas como polígonos (lista de puntos)
    zonas = {
        "entrada": [(50, 100), (300, 100), (300, 400), (50, 400)],
        "mostrador": [(400, 150), (700, 150), (700, 450), (400, 450)],
        "productos": [(200, 50), (600, 50), (600, 150), (200, 150)]
    }
    colores_zonas = {
        "entrada": (0, 255, 255),  # Amarillo
        "mostrador": (255, 0, 255),  # Magenta
        "productos": (0, 255, 0)  # Verde
    }
    print("Usando zonas por defecto (polígonos)")
    return zonas, colores_zonas

def point_in_polygon(point, polygon):
    """
    Determina si un punto está dentro de un polígono usando el algoritmo de ray casting.
    
    Args:
        point (tuple): Coordenadas (x, y) del punto.
        polygon (list): Lista de puntos (x, y) que forman el polígono.
    
    Returns:
        bool: True si el punto está dentro del polígono, False en caso contrario.
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def process_detections(frame, model):
    """
    Procesa las detecciones de YOLO en un frame.
    
    Args:
        frame (np.array): Frame de video redimensionado.
        model: Modelo YOLO cargado.
    
    Returns:
        list: Lista de detecciones con bounding boxes, centroides y confianza.
    """
    results = model(frame, classes=[0], conf=CONFIDENCE_THRESHOLD)
    detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf)
            centroid = (int((x1 + x2) / 2), int((y1 + y2) / 2))
            detections.append({
                'bbox': [x1, y1, x2, y2],
                'centroid': centroid,
                'confidence': confidence
            })
    return detections

def draw_ground_ellipse(frame, center_x, bottom_y, width=40, height=15, color=GROUND_CIRCLE_COLOR, thickness=GROUND_CIRCLE_THICKNESS):
    """
    Dibuja una elipse en el suelo para representar la posición de una persona.
    
    Args:
        frame (np.array): Frame de video.
        center_x, bottom_y (int): Coordenadas del centro de la elipse.
        width, height (int): Dimensiones de la elipse.
        color (tuple): Color de la elipse en formato BGR.
        thickness (int): Grosor de la elipse.
    
    Returns:
        np.array: Frame con la elipse dibujada.
    """
    ellipse_center = (center_x, bottom_y + 5)
    cv2.ellipse(frame, ellipse_center, (width//2, height//2), 0, 0, 360, color, thickness)
    shadow_color = (color[0]//3, color[1]//3, color[2]//3)
    cv2.ellipse(frame, (ellipse_center[0] + 2, ellipse_center[1] + 2), 
                (width//2, height//2), 0, 0, 360, shadow_color, thickness//2)
    return frame

def pixelate_region(frame, x1, y1, x2, y2, block_size=PIXELATE_BLOCK_SIZE):
    """
    Aplica un efecto de pixelado a una región del frame.
    
    Args:
        frame (np.array): Frame de video.
        x1, y1, x2, y2 (int): Coordenadas de la región a pixelar.
        block_size (int): Tamaño de los bloques para el efecto.
    
    Returns:
        np.array: Frame con la región pixelada.
    """
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return frame
    h, w = region.shape[:2]
    h_blocks = max(1, h // block_size)
    w_blocks = max(1, w // block_size)
    small = cv2.resize(region, (w_blocks, h_blocks), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    frame[y1:y2, x1:x2] = pixelated
    return frame

def draw_zones_and_objects(frame, tracked_objects, zonas_escaladas, colores_zonas, pixelate_enabled, show_heatmap, heatmap_generator):
    """
    Dibuja las zonas, objetos rastreados y el mapa de calor en el frame.
    
    Args:
        frame (np.array): Frame de video.
        tracked_objects (list): Lista de objetos rastreados.
        zonas_escaladas (dict): Zonas escaladas (nombre: lista de puntos del polígono).
        colores_zonas (dict): Colores de las zonas (nombre: color).
        pixelate_enabled (bool): Si se debe aplicar pixelado.
        show_heatmap (bool): Si se debe mostrar el mapa de calor.
        heatmap_generator (HeatmapGenerator): Generador de mapas de calor.
    
    Returns:
        np.array: Frame con los elementos dibujados.
    """
    # Dibujar zonas
    for nombre, puntos in zonas_escaladas.items():
        color = colores_zonas.get(nombre, FONT_COLOR)
        # Convertir lista de puntos a formato numpy para polylines
        puntos_np = np.array(puntos, np.int32)
        puntos_np = puntos_np.reshape((-1, 1, 2))
        cv2.polylines(frame, [puntos_np], True, color, 2)
        
        # Calcular posición para el texto (usar el primer punto del polígono)
        if len(puntos) > 0:
            x1, y1 = puntos[0]
            cv2.putText(frame, nombre.upper(), (x1, y1 - 10), FONT, 0.6, color, 2)

    # Dibujar personas rastreadas
    for obj in tracked_objects:
        x1, y1, x2, y2 = obj.bbox
        cx, cy = obj.centroid

        # Dibujar elipse en el suelo o bounding box
        if USE_GROUND_CIRCLE:
            frame = draw_ground_ellipse(frame, cx, y2, width=50, height=20)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR_PERSON, BOX_THICKNESS)

        # Dibujar centroide
        cv2.circle(frame, (cx, cy), CENTROID_SIZE, BOX_COLOR_PERSON, -1)

        # Mostrar ID encima de la cabeza
        label = f"ID:{obj.track_id}"
        (label_width, label_height), baseline = cv2.getTextSize(label, FONT, 0.5, 2)
        cv2.rectangle(frame, (x1, y1 - label_height - 10), (x1 + label_width, y1 - 10 + baseline), (0, 0, 0), -1)
        cv2.putText(frame, label, (x1, y1 - 10), FONT, 0.5, FONT_COLOR, 2)

        # Mostrar tiempo en zona si está en una
        if obj.zona_actual:
            tiempo_zona = obj.get_tiempo_en_zona_actual()
            tiempo_text = f"{obj.zona_actual}: {int(tiempo_zona)}s"
            (text_width, text_height), baseline = cv2.getTextSize(tiempo_text, FONT, 0.4, 1)
            cv2.rectangle(frame, (x1, y1 - text_height - 30), (x1 + text_width, y1 - 30 + baseline), (0, 0, 0), -1)
            cv2.putText(frame, tiempo_text, (x1, y1 - 30), FONT, 0.4, (255, 255, 0), 1)

        # Aplicar pixelado si está activado
        if pixelate_enabled:
            frame = pixelate_region(frame, x1, y1, x2, y2)

    # Mostrar mapa de calor
    if show_heatmap:
        heatmap_overlay = heatmap_generator.get_heatmap_overlay()
        if heatmap_overlay is not None:
            frame = cv2.addWeighted(frame, 0.7, heatmap_overlay, HEATMAP_ALPHA, 0)

    # Mostrar información general
    info_text = f"Personas: {len(tracked_objects)} | Tracker: {'DeepSORT' if DEEPSORT_AVAILABLE else 'Básico'}"
    cv2.putText(frame, info_text, (10, 30), FONT, 0.6, FONT_COLOR, 2)
    if show_heatmap:
        cv2.putText(frame, "HEATMAP ACTIVO", (10, 60), FONT, 0.6, (0, 255, 255), 2)

    return frame

def handle_controls(key, pixelate_enabled, show_heatmap, tracked_objects, heatmap_generator, output_dir, heatmap_output_dir):
    """
    Maneja los controles de teclado y actualiza el estado.
    
    Args:
        key (int): Código de la tecla presionada.
        pixelate_enabled (bool): Estado actual del pixelado.
        show_heatmap (bool): Estado actual del mapa de calor.
        tracked_objects (list): Lista de objetos rastreados.
        heatmap_generator (HeatmapGenerator): Generador de mapas de calor.
    
    Returns:
        tuple: Nuevos estados de pixelado, mapa de calor y bandera de continuación.
    """
    if key == ord('q'):
        # Usar todos los objetos rastreados para la exportación
        if hasattr(tracked_objects, 'get_all_tracked_objects'):
            all_objects = tracked_objects.get_all_tracked_objects()
            export_to_json(all_objects, heatmap_generator, output_dir, heatmap_output_dir)
        else:
            export_to_json(tracked_objects, heatmap_generator, output_dir, heatmap_output_dir)
        return pixelate_enabled, show_heatmap, False
    elif key == ord('p'):
        pixelate_enabled = not pixelate_enabled
        print(f"Pixelado {'activado' if pixelate_enabled else 'desactivado'}")
    elif key == ord('e'):
        # Usar todos los objetos rastreados para la exportación
        if hasattr(tracked_objects, 'get_all_tracked_objects'):
            all_objects = tracked_objects.get_all_tracked_objects()
            export_to_json(all_objects, heatmap_generator, output_dir, heatmap_output_dir)
        else:
            export_to_json(tracked_objects, heatmap_generator, output_dir, heatmap_output_dir)
        print("Datos exportados manualmente.")
    elif key == ord('h'):
        show_heatmap = not show_heatmap
        print(f"Mapa de calor {'activado' if show_heatmap else 'desactivado'}")
    elif key == ord('r'):
        heatmap_generator.__init__(heatmap_generator.width, heatmap_generator.height)
        print("Mapa de calor reiniciado.")
    return pixelate_enabled, show_heatmap, True

def export_to_json(tracked_objects, heatmap_generator, output_dir, heatmap_output_dir, prefix=OUTPUT_JSON_PREFIX):
    """
    Exporta datos de tracking y mapa de calor a un archivo JSON.
    
    Args:
        tracked_objects (list): Lista de objetos rastreados.
        heatmap_generator (HeatmapGenerator): Generador de mapas de calor.
        output_dir (str): Directorio de salida para archivos JSON.
        heatmap_output_dir (str): Directorio de salida para mapas de calor.
        prefix (str): Prefijo para el nombre del archivo JSON.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    personas_data = [
        {
            'id': obj.track_id,
            'zona_actual': obj.zona_actual,
            'tiempo_en_zona_actual': obj.get_tiempo_en_zona_actual(),
            'historial_zonas': obj.historial_zonas,
            'centroid': obj.centroid,
            'ultima_actualizacion': obj.last_seen.isoformat()
        } for obj in tracked_objects
    ]
    datos_export = {
        'timestamp': timestamp,
        'total_personas': len(personas_data),
        'sistema_tracking': 'DeepSORT' if DEEPSORT_AVAILABLE else 'Básico',
        'directorio_salida': output_dir,
        'directorio_heatmap': heatmap_output_dir,
        'personas': personas_data
    }
    archivo_datos = os.path.join(output_dir, f"{prefix}_{timestamp}.json")
    with open(archivo_datos, 'w', encoding='utf-8') as f:
        json.dump(datos_export, f, indent=2, ensure_ascii=False)
    print(f"Datos exportados a: {archivo_datos}")
    print(f"Directorio de salida configurado: {output_dir}")
    print(f"Directorio de heatmap configurado: {heatmap_output_dir}")

    heatmap_file = os.path.join(heatmap_output_dir, f"heatmap_{timestamp}.png")
    heatmap_generator.save_heatmap(heatmap_file)
    print(f"Mapa de calor guardado en: {heatmap_file}")

class IDManager:
    """
    Gestiona IDs secuenciales para objetos rastreados.
    """
    def __init__(self):
        self.current_id = 1
        self.id_mapping = {}  # Mapea IDs originales a IDs secuenciales
        self.reverse_mapping = {}  # Mapea IDs secuenciales a originales
        self.active_ids = set()  # IDs actualmente activos

    def get_sequential_id(self, original_id):
        """
        Obtiene un ID secuencial estable para un ID original.
        
        Args:
            original_id: ID original proporcionado por el tracker.
        
        Returns:
            int: ID secuencial asignado.
        """
        if original_id not in self.id_mapping:
            self.id_mapping[original_id] = self.current_id
            self.reverse_mapping[self.current_id] = original_id
            self.current_id += 1
        sequential_id = self.id_mapping[original_id]
        self.active_ids.add(sequential_id)
        return sequential_id

    def cleanup_inactive_ids(self, active_original_ids):
        """
        Limpia IDs inactivos para liberar memoria.
        
        Args:
            active_original_ids (list): Lista de IDs originales activos.
        """
        active_sequential = set()
        for oid in active_original_ids:
            if oid in self.id_mapping:
                active_sequential.add(self.id_mapping[oid])
        inactive_sequential = self.active_ids - active_sequential
        for seq_id in inactive_sequential:
            self.active_ids.remove(seq_id)
            if len(self.id_mapping) > 200:
                original_id = self.reverse_mapping.get(seq_id)
                if original_id and original_id not in active_original_ids:
                    del self.id_mapping[original_id]
                    del self.reverse_mapping[seq_id]

class HeatmapGenerator:
    """
    Genera y gestiona mapas de calor basados en posiciones de personas.
    """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.heatmap_data = np.zeros((height, width), dtype=np.float32)

    def add_person(self, x, y, radius=HEATMAP_CIRCLE_RADIUS):
        """
        Añade una persona al mapa de calor.
        
        Args:
            x, y (int): Coordenadas del centroide.
            radius (int): Radio de influencia.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            y_min = max(0, y - radius)
            y_max = min(self.height, y + radius)
            x_min = max(0, x - radius)
            x_max = min(self.width, x + radius)
            for py in range(y_min, y_max):
                for px in range(x_min, x_max):
                    distance = math.sqrt((px - x)**2 + (py - y)**2)
                    if distance <= radius:
                        weight = 1.0 - (distance / radius)
                        self.heatmap_data[py, px] += weight

    def get_heatmap_overlay(self, alpha=HEATMAP_ALPHA):
        """
        Genera una superposición del mapa de calor.
        
        Args:
            alpha (float): Transparencia del mapa de calor.
        
        Returns:
            np.array: Imagen del mapa de calor coloreada.
        """
        if self.heatmap_data.max() == 0:
            return None
        normalized = cv2.normalize(self.heatmap_data, None, 0, 255, cv2.NORM_MINMAX)
        normalized = normalized.astype(np.uint8)
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        mask = normalized > 10
        overlay = np.zeros_like(colored)
        overlay[mask] = colored[mask]
        return overlay

    def save_heatmap(self, filename):
        """
        Guarda el mapa de calor como imagen.
        
        Args:
            filename (str): Ruta del archivo de salida.
        """
        overlay = self.get_heatmap_overlay()
        if overlay is not None:
            cv2.imwrite(filename, overlay)

class PersonTracker:
    """
    Rastrea una persona y registra su historial de zonas.
    """
    def __init__(self, track_id, bbox, confidence):
        self.original_id = track_id
        self.track_id = track_id  # Se asignará ID secuencial
        self.bbox = bbox
        self.confidence = confidence
        self.centroid = self.get_centroid(bbox)
        self.last_seen = datetime.datetime.now()
        self.zona_actual = None
        self.tiempo_entrada_zona = None
        self.historial_zonas = []

    def get_centroid(self, bbox):
        """
        Calcula el centroide de un bounding box.
        
        Args:
            bbox (list): Coordenadas [x1, y1, x2, y2].
        
        Returns:
            tuple: Coordenadas (x, y) del centroide.
        """
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    def update(self, bbox):
        """
        Actualiza la posición y centroide.
        
        Args:
            bbox (list): Nuevas coordenadas [x1, y1, x2, y2].
        """
        self.bbox = bbox
        self.centroid = self.get_centroid(bbox)
        self.last_seen = datetime.datetime.now()

    def update_zone(self, zonas_escaladas):
        """
        Actualiza la zona actual y registra tiempos.
        
        Args:
            zonas_escaladas (dict): Zonas escaladas (nombre: lista de puntos del polígono).
        """
        cx, cy = self.centroid
        ahora = datetime.datetime.now()
        nueva_zona = None
        for nombre, puntos in zonas_escaladas.items():
            if point_in_polygon((cx, cy), puntos):
                nueva_zona = nombre
                break
        if nueva_zona != self.zona_actual:
            if self.zona_actual is not None and self.tiempo_entrada_zona is not None:
                tiempo_en_zona = (ahora - self.tiempo_entrada_zona).total_seconds()
                self.historial_zonas.append({
                    'zona': self.zona_actual,
                    'tiempo_entrada': self.tiempo_entrada_zona.isoformat(),
                    'tiempo_salida': ahora.isoformat(),
                    'duracion': tiempo_en_zona
                })
            self.zona_actual = nueva_zona
            self.tiempo_entrada_zona = ahora if nueva_zona else None

    def get_tiempo_en_zona_actual(self):
        """
        Obtiene el tiempo en la zona actual en segundos.
        
        Returns:
            float: Tiempo en segundos.
        """
        if self.zona_actual is None or self.tiempo_entrada_zona is None:
            return 0
        return (datetime.datetime.now() - self.tiempo_entrada_zona).total_seconds()

class DeepSORTTracker:
    """
    Wrapper para el tracker DeepSORT o sistema básico.
    """
    def __init__(self, zonas_escaladas):
        self.zonas_escaladas = zonas_escaladas
        self.id_manager = IDManager()
        self.tracked_objects = {}  # Objetos actualmente rastreados
        self.all_tracked_objects = {}  # Historial de todos los objetos rastreados
        if DEEPSORT_AVAILABLE:
            print(f"Inicializando DeepSORT con max_age={DEEPSORT_MAX_AGE} y max_cosine_distance={DEEPSORT_MAX_COSINE_DISTANCE}")
            self.tracker = DeepSort(
                max_age=DEEPSORT_MAX_AGE,
                n_init=5,
                nms_max_overlap=DEEPSORT_NMS_MAX_OVERLAP,
                max_cosine_distance=DEEPSORT_MAX_COSINE_DISTANCE,
                nn_budget=DEEPSORT_NN_BUDGET,
                embedder="mobilenet",
                half=True,
                bgr=True,
                embedder_gpu=False
            )
            self.use_deepsort = True
        else:
            self.use_deepsort = False

    def update(self, detections):
        """
        Actualiza el tracker con nuevas detecciones.
        
        Args:
            detections (list): Lista de detecciones con bbox, centroid y confianza.
        
        Returns:
            list: Lista de objetos rastreados actualizados.
        """
        if self.use_deepsort:
            active_objects = self._update_deepsort(detections)
        else:
            active_objects = self._update_basic(detections)
        
        # Devolver solo los objetos activos para visualización
        return active_objects
    
    def get_all_tracked_objects(self):
        """
        Obtiene todos los objetos rastreados, incluso los que ya no están activos.
        
        Returns:
            list: Lista de todos los objetos rastreados.
        """
        return list(self.all_tracked_objects.values())

    def _update_deepsort(self, detections):
        """
        Actualización usando DeepSORT.
        
        Args:
            detections (list): Lista de detecciones.
        
        Returns:
            list: Objetos rastreados actualizados.
        """
        active_original_ids = []
        result_objects = []

        if not detections:
            current_time = datetime.datetime.now()
            inactive_ids = [seq_id for seq_id, obj in self.tracked_objects.items()
                           if (current_time - obj.last_seen).total_seconds() > 5.0]
            for seq_id in inactive_ids:
                del self.tracked_objects[seq_id]
            self.id_manager.cleanup_inactive_ids(active_original_ids)
            return list(self.tracked_objects.values())

        dets = [(det['bbox'], det['confidence'], 'person') for det in detections]
        tracks = self.tracker.update_tracks(dets, frame=None)

        for track in tracks:
            if not track.is_confirmed():
                continue
            original_id = track.track_id
            active_original_ids.append(original_id)
            sequential_id = self.id_manager.get_sequential_id(original_id)
            bbox = track.to_ltrb()
            x1, y1, x2, y2 = map(int, bbox)

            if sequential_id not in self.tracked_objects:
                self.tracked_objects[sequential_id] = PersonTracker(original_id, [x1, y1, x2, y2], 0.8)
                self.tracked_objects[sequential_id].track_id = sequential_id
                # Añadir al historial de todos los objetos rastreados
                self.all_tracked_objects[sequential_id] = self.tracked_objects[sequential_id]
            else:
                self.tracked_objects[sequential_id].update([x1, y1, x2, y2])

            self.tracked_objects[sequential_id].update_zone(self.zonas_escaladas)
            result_objects.append(self.tracked_objects[sequential_id])

        self.id_manager.cleanup_inactive_ids(active_original_ids)
        current_sequential_ids = {obj.track_id for obj in result_objects}
        for seq_id in set(self.tracked_objects.keys()) - current_sequential_ids:
            if (datetime.datetime.now() - self.tracked_objects[seq_id].last_seen).total_seconds() > 5.0:
                del self.tracked_objects[seq_id]

        return result_objects

    def _update_basic(self, detections):
        """
        Actualización usando sistema básico de seguimiento.
        
        Args:
            detections (list): Lista de detecciones.
        
        Returns:
            list: Objetos rastreados actualizados.
        """
        result_objects = []
        active_original_ids = []
        current_positions = [(det['centroid'], det['bbox'], det['confidence']) for det in detections]
        tracked_ids = set(self.tracked_objects.keys())

        for centroid, bbox, confidence in current_positions:
            cx, cy = centroid
            matched_id = None
            min_dist = float('inf')

            for seq_id, obj in self.tracked_objects.items():
                dist = math.sqrt((cx - obj.centroid[0])**2 + (cy - obj.centroid[1])**2)
                if dist < 100 * SCALE_FACTOR and dist < min_dist:
                    min_dist = dist
                    matched_id = seq_id

            if matched_id is not None:
                self.tracked_objects[matched_id].update(bbox)
                self.tracked_objects[matched_id].update_zone(self.zonas_escaladas)
                result_objects.append(self.tracked_objects[matched_id])
                active_original_ids.append(self.tracked_objects[matched_id].original_id)
            else:
                original_id = f"basic_{len(self.id_manager.id_mapping) + 1}"
                sequential_id = self.id_manager.get_sequential_id(original_id)
                new_tracker = PersonTracker(original_id, bbox, confidence)
                new_tracker.track_id = sequential_id
                new_tracker.update_zone(self.zonas_escaladas)
                self.tracked_objects[sequential_id] = new_tracker
                # Añadir al historial de todos los objetos rastreados
                self.all_tracked_objects[sequential_id] = new_tracker
                result_objects.append(new_tracker)
                active_original_ids.append(original_id)

        for seq_id in tracked_ids - {obj.track_id for obj in result_objects}:
            if (datetime.datetime.now() - self.tracked_objects[seq_id].last_seen).total_seconds() > 5.0:
                del self.tracked_objects[seq_id]

        self.id_manager.cleanup_inactive_ids(active_original_ids)
        return result_objects

def main():
    """
    Procesa el video, rastrea personas, genera mapas de calor y exporta datos.
    """
    parser = argparse.ArgumentParser(description="Sistema de tracking de personas en farmacias.")
    parser.add_argument("--video_source", type=str, default="0",
                        help="Ruta al archivo de video o '0' para usar la webcam.")
    parser.add_argument("--zones_config_file", type=str, default="zonas_config.json",
                        help="Ruta al archivo JSON con la configuración de las zonas.")
    parser.add_argument("--output_dir", type=str, default="datos_tracking",
                        help="Directorio para guardar los archivos JSON de tracking.")
    parser.add_argument("--heatmap_output_dir", type=str, default="heatmaps",
                        help="Directorio para guardar los mapas de calor.")
    args = parser.parse_args()

    # Inicializar sistema
    cap, model, H_original, W_original, H, W, zonas_escaladas, colores_zonas, output_dir, heatmap_output_dir = initialize_system(
        args.video_source, args.zones_config_file, YOLO_MODEL_NAME, args.output_dir, args.heatmap_output_dir
    )
    
    # Inicializar sistemas de tracking y heatmap
    tracking_system = DeepSORTTracker(zonas_escaladas)
    heatmap_generator = HeatmapGenerator(W, H)
    
    # Variables de control
    pixelate_enabled = False
    show_heatmap = False
    
    # Imprimir información inicial
    print(f"Dimensiones originales: Ancho={W_original}, Alto={H_original}")
    print(f"Dimensiones escaladas: Ancho={W}, Alto={H} (Factor: {SCALE_FACTOR})")
    print(f"Directorio de salida configurado: {output_dir}")
    print(f"Directorio de heatmap configurado: {heatmap_output_dir}")
    print("Controles: 'q' para salir, 'p' para pixelado, 'e' para exportar, 'h' para heatmap, 'r' para reiniciar heatmap")
    
    # Bucle principal
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Fin del video o error al leer frame.")
            break
        
        # Redimensionar frame
        frame = cv2.resize(frame, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR)
        
        # Procesar detecciones
        detections = process_detections(frame, model)
        
        # Actualizar tracking
        tracked_objects = tracking_system.update(detections)
        
        # Actualizar heatmap
        for obj in tracked_objects:
            heatmap_generator.add_person(obj.centroid[0], obj.centroid[1])
        
        # Dibujar zonas, objetos y heatmap
        frame = draw_zones_and_objects(
            frame, tracked_objects, zonas_escaladas, colores_zonas, pixelate_enabled, show_heatmap, heatmap_generator
        )
        
        # Mostrar frame
        cv2.imshow("Sistema de Tracking Mejorado", frame)
        
        # Manejar controles
        key = cv2.waitKey(1) & 0xFF
        print(f"Key pressed: {key}")  # Add this line for debugging
        pixelate_enabled, show_heatmap, continue_loop = handle_controls(
            key, pixelate_enabled, show_heatmap, tracked_objects, heatmap_generator, OUTPUT_DIR, HEATMAP_OUTPUT_DIR
        )
        if not continue_loop:
            break
    
    # Exportar datos finales
    if hasattr(tracking_system, 'get_all_tracked_objects'):
        all_objects = tracking_system.get_all_tracked_objects()
        export_to_json(all_objects, heatmap_generator, output_dir, heatmap_output_dir)
    else:
        export_to_json(tracked_objects, heatmap_generator, output_dir, heatmap_output_dir)
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    
    # Imprimir resumen
    print("Proceso finalizado.")
    print(f"Total personas rastreadas: {len(tracked_objects)}")
    print(f"Archivos guardados en:")
    print(f"  - JSON: {output_dir}")
    print(f"  - Heatmap: {heatmap_output_dir}")

if __name__ == "__main__":
    main()