import cv2
import argparse
import torch
import numpy as np
import datetime
import json
import os

# --- CONSTANTES Y CONFIGURACIÓN ---
CONFIDENCE_THRESHOLD = 0.4  # Umbral de confianza para detecciones
SCALE_FACTOR = 0.5  # Factor de reducción de resolución
LINE_COLOR = (0, 255, 0)  # Verde para la línea virtual
LINE_THICKNESS = 2  # Grosor de la línea
BOX_COLOR_PERSON = (255, 0, 0)  # Azul para bounding boxes de personas
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.8
FONT_COLOR = (255, 255, 255)  # Blanco para texto
FONT_THICKNESS = 2
YOLO_MODEL_NAME = 'yolov5s'  # Modelo YOLO a usar
PIXELATE_BLOCK_SIZE = 20  # Tamaño de bloques para pixelado
MAX_TRACKING_DISTANCE = 0.1  # Distancia máxima para asociar detecciones (proporción del ancho)
CROSSING_RESET_DISTANCE = 50  # Distancia para resetear el flag de conteo (en píxeles)
LINE_ZONE_DISTANCE = 100  # Distancia para rastrear objetos cerca de la línea

# Coordenadas originales de la línea virtual (para resolución 1920x1080)
# Coordenadas originales de la línea virtual (para resolución 1920x1080)
# Estas serán cargadas desde un archivo JSON
# LINE_START_X_ORIGINAL = 568
# LINE_START_Y_ORIGINAL = 4
# LINE_END_X_ORIGINAL = 563
# LINE_END_Y_ORIGINAL = 765

def initialize_video_capture(video_source):
    """
    Inicializa la captura de video y obtiene las dimensiones escaladas.
    
    Args:
        video_source (str or int): Ruta del video o índice de la webcam.
    
    Returns:
        tuple: Objeto de captura, dimensiones originales (H, W), dimensiones escaladas (H, W).
    """
    cap = cv2.VideoCapture(video_source)
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
    
    return cap, H_original, W_original, H, W

def load_line_coordinates_from_json(file_path):
    """
    Carga las coordenadas de la línea desde un archivo JSON.
    
    Args:
        file_path (str): Ruta al archivo JSON con las coordenadas.
        
    Returns:
        tuple: Coordenadas (LINE_START_X, LINE_START_Y, LINE_END_X, LINE_END_Y).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        start_x = data.get("LINE_START_X")
        start_y = data.get("LINE_START_Y")
        end_x = data.get("LINE_END_X")
        end_y = data.get("LINE_END_Y")
        
        if all(v is not None for v in [start_x, start_y, end_x, end_y]):
            print(f"Coordenadas de línea cargadas desde {file_path}")
            return start_x, start_y, end_x, end_y
        else:
            raise ValueError("El archivo JSON de configuración de línea no contiene todas las coordenadas necesarias.")
    except FileNotFoundError:
        print(f"Error: Archivo de configuración de línea no encontrado en {file_path}. Usando valores por defecto.")
        # Valores por defecto si el archivo no se encuentra
        return 568, 4, 563, 765
    except json.JSONDecodeError:
        print(f"Error: El archivo {file_path} no es un JSON válido. Usando valores por defecto.")
        return 568, 4, 563, 765
    except Exception as e:
        print(f"Error al cargar las coordenadas de línea desde {file_path}: {e}. Usando valores por defecto.")
        return 568, 4, 563, 765

def calculate_line_parameters(line_coords_original):
    """
    Calcula las coordenadas escaladas y parámetros de la línea virtual.
    
    Args:
        line_coords_original (tuple): Coordenadas originales (start_x, start_y, end_x, end_y).
        
    Returns:
        tuple: Coordenadas escaladas (start_x, start_y, end_x, end_y) y parámetros (a, b, c).
    """
    LINE_START_X_ORIGINAL, LINE_START_Y_ORIGINAL, LINE_END_X_ORIGINAL, LINE_END_Y_ORIGINAL = line_coords_original

    start_x = int(LINE_START_X_ORIGINAL * SCALE_FACTOR)
    start_y = int(LINE_START_Y_ORIGINAL * SCALE_FACTOR)
    end_x = int(LINE_END_X_ORIGINAL * SCALE_FACTOR)
    end_y = int(LINE_END_Y_ORIGINAL * SCALE_FACTOR)
    
    # Parámetros de la línea (ax + by + c = 0)
    a = end_y - start_y
    b = start_x - end_x
    c = end_x * start_y - start_x * end_y
    
    return start_x, start_y, end_x, end_y, a, b, c

def point_line_side(x, y, a, b, c):
    """
    Determina de qué lado de la línea virtual está un punto.
    
    Args:
        x (int): Coordenada x del punto.
        y (int): Coordenada y del punto.
        a, b, c (int): Parámetros de la línea (ax + by + c = 0).
    
    Returns:
        int: >0 si está a un lado, <0 al otro, 0 si está sobre la línea.
    """
    return a * x + b * y + c

def distance_point_to_line(x, y, a, b, c):
    """
    Calcula la distancia perpendicular de un punto a la línea.
    
    Args:
        x, y (int): Coordenadas del punto.
        a, b, c (int): Parámetros de la línea (ax + by + c = 0).
    
    Returns:
        float: Distancia perpendicular.
    """
    return abs(a * x + b * y + c) / np.sqrt(a**2 + b**2)

def get_centroid(x1, y1, x2, y2):
    """
    Calcula el centroide de un bounding box.
    
    Args:
        x1, y1, x2, y2 (int): Coordenadas del bounding box.
    
    Returns:
        tuple: Coordenadas (x, y) del centroide.
    """
    return int((x1 + x2) / 2), int((y1 + y2) / 2)

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

def draw_frame(frame, detections, line_coords, counts):
    """
    Dibuja la línea virtual, bounding boxes y contadores en el frame.
    
    Args:
        frame (np.array): Frame de video.
        detections (list): Lista de detecciones con bounding boxes y centroides.
        line_coords (tuple): Coordenadas de la línea (start_x, start_y, end_x, end_y).
        counts (dict): Contadores de entradas, salidas, total y personas dentro.
    """
    start_x, start_y, end_x, end_y = line_coords
    H = frame.shape[0]
    
    # Dibujar línea virtual y puntos de referencia
    cv2.line(frame, (start_x, start_y), (end_x, end_y), LINE_COLOR, LINE_THICKNESS)
    cv2.circle(frame, (start_x, start_y), 6, (0, 0, 255), -1)  # Punto inicial rojo
    cv2.circle(frame, (end_x, end_y), 6, (0, 0, 255), -1)      # Punto final rojo
    
    # Dibujar detecciones
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        centroid_x, centroid_y = det['centroid']
        confidence = det['confidence']
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR_PERSON, 2)
        cv2.putText(frame, f"Persona {confidence:.2f}", (x1, y1 - 10), FONT, 0.5, BOX_COLOR_PERSON, 2)
        cv2.circle(frame, (centroid_x, centroid_y), 5, (0, 0, 255), -1)
    
    # Mostrar contadores
    cv2.putText(frame, f"Entradas: {counts['entry']}", (10, H - 120), FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
    cv2.putText(frame, f"Salidas: {counts['exit']}", (10, H - 90), FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
    cv2.putText(frame, f"Total personas: {counts['total']}", (10, H - 60), FONT, FONT_SCALE, (0, 255, 255), FONT_THICKNESS, cv2.LINE_AA)
    cv2.putText(frame, f"Personas dentro: {counts['inside']}", (10, H - 30), FONT, FONT_SCALE, (255, 0, 255), FONT_THICKNESS, cv2.LINE_AA)

def process_detections(frame, model, pixelate_enabled=False):
    """
    Procesa las detecciones de YOLO en un frame.
    
    Args:
        frame (np.array): Frame de video redimensionado.
        model: Modelo YOLO cargado.
        pixelate_enabled (bool): Si se debe aplicar pixelado.
    
    Returns:
        list: Lista de detecciones con bounding boxes y centroides.
    """
    results = model(frame)
    detections = results.pandas().xyxy[0]
    processed_detections = []
    
    for _, row in detections.iterrows():
        if row['name'] == 'person' and row['confidence'] > CONFIDENCE_THRESHOLD:
            x1, y1, x2, y2 = map(int, [row['xmin'], row['ymin'], row['xmax'], row['ymax']])
            centroid = get_centroid(x1, y1, x2, y2)
            if pixelate_enabled:
                frame = pixelate_region(frame, x1, y1, x2, y2)
            processed_detections.append({
                'bbox': (x1, y1, x2, y2),
                'centroid': centroid,
                'confidence': row['confidence']
            })
    
    return processed_detections

def track_and_count_objects(detections, tracked_objects, line_params, counts, frame_width):
    """
    Realiza el seguimiento de objetos y cuenta cruces de la línea virtual.
    
    Args:
        detections (list): Lista de detecciones actuales.
        tracked_objects (dict): Objetos rastreados con sus datos.
        line_params (tuple): Parámetros de la línea (a, b, c).
        counts (dict): Contadores de entradas, salidas, total y personas dentro.
        frame_width (int): Ancho del frame escalado.
    
    Returns:
        dict: Objetos rastreados actualizados.
    """
    a, b, c = line_params
    new_tracked_objects = {}
    global object_id_counter
    object_id_counter = len(tracked_objects)  # Mantener IDs únicos
    
    for centroid_x, centroid_y in [det['centroid'] for det in detections]:
        matched_id = None
        min_dist = float('inf')
        
        # Buscar el objeto rastreado más cercano
        for obj_id, data in tracked_objects.items():
            dist = np.sqrt((centroid_x - data['last_x'])**2 + (centroid_y - data['last_y'])**2)
            if dist < frame_width * MAX_TRACKING_DISTANCE and dist < min_dist:
                min_dist = dist
                matched_id = obj_id
        
        current_side = point_line_side(centroid_x, centroid_y, a, b, c)
        
        if matched_id is not None:
            prev_side = tracked_objects[matched_id]['last_side']
            counted_flag = tracked_objects[matched_id]['counted_this_crossing']
            
            # Detectar cruce de línea
            if prev_side > 0 and current_side <= 0 and not counted_flag:
                counts['entry'] += 1
                counts['inside'] += 1
                counts['total'] += 1
                new_tracked_objects[matched_id] = {
                    'last_side': current_side,
                    'last_x': centroid_x,
                    'last_y': centroid_y,
                    'counted_this_crossing': True
                }
                print(f"Entrada detectada a las {datetime.datetime.now()}. Total entradas: {counts['entry']}")
            elif prev_side <= 0 and current_side > 0 and not counted_flag:
                counts['exit'] += 1
                counts['inside'] = max(0, counts['inside'] - 1)  # Evitar negativos
                new_tracked_objects[matched_id] = {
                    'last_side': current_side,
                    'last_x': centroid_x,
                    'last_y': centroid_y,
                    'counted_this_crossing': True
                }
                print(f"Salida detectada a las {datetime.datetime.now()}. Total salidas: {counts['exit']}")
            else:
                new_tracked_objects[matched_id] = {
                    'last_side': current_side,
                    'last_x': centroid_x,
                    'last_y': centroid_y,
                    'counted_this_crossing': counted_flag
                }
            
            # Resetear flag de conteo si está lejos de la línea
            if distance_point_to_line(centroid_x, centroid_y, a, b, c) > CROSSING_RESET_DISTANCE * SCALE_FACTOR:
                new_tracked_objects[matched_id]['counted_this_crossing'] = False
        else:
            # Nuevo objeto cerca de la línea
            if distance_point_to_line(centroid_x, centroid_y, a, b, c) < LINE_ZONE_DISTANCE * SCALE_FACTOR:
                object_id_counter += 1
                new_tracked_objects[object_id_counter] = {
                    'last_side': current_side,
                    'last_x': centroid_x,
                    'last_y': centroid_y,
                    'counted_this_crossing': False
                }
    
    return new_tracked_objects

def export_to_json(counts, output_dir):
    """
    Exporta los datos de conteo a un archivo JSON.
    
    Args:
        counts (dict): Contadores de entradas, salidas, total y personas dentro.
        output_dir (str): Directorio donde guardar el archivo JSON.
    """
    # Crear directorio de salida si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"conteo_resultados_{timestamp}.json")
    
    # Estructura de datos para exportar
    datos_conteo = {
        "entradas": counts['entry'],
        "salidas": counts['exit'],
        "total_personas": counts['total'],
        "personas_dentro": counts['inside'],
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Guardar en archivo JSON
    with open(output_file, "w") as f:
        json.dump(datos_conteo, f, indent=2)
    print(f"Datos exportados a {output_file}")

def main():
    """
    Procesa el video, detecta personas y cuenta entradas/salidas.
    """
    parser = argparse.ArgumentParser(description="Contador de personas en farmacias.")
    parser.add_argument("--video_source", type=str, default="0",
                        help="Ruta al archivo de video o '0' para usar la webcam.")
    parser.add_argument("--output_dir", type=str, default="datos_conteo",
                        help="Directorio para guardar los archivos JSON de conteo.")
    parser.add_argument("--line_config_file", type=str, default="line_coordinates.json",
                        help="Ruta al archivo JSON con las coordenadas de la línea virtual.")
    args = parser.parse_args()

    # Inicializar modelo YOLO
    try:
        model = torch.hub.load('ultralytics/yolov5', YOLO_MODEL_NAME, pretrained=True)
        model.classes = [0]  # Solo detectar personas
        print(f"Modelo {YOLO_MODEL_NAME} cargado correctamente.")
    except Exception as e:
        print(f"Error al cargar el modelo YOLO: {e}")
        print("Asegúrate de tener conexión a internet la primera vez que ejecutas.")
        exit()
    
    # Inicializar captura de video
    cap, H_original, W_original, H, W = initialize_video_capture(args.video_source)
    
    # Cargar coordenadas de la línea
    line_coords_original = load_line_coordinates_from_json(args.line_config_file)

    # Inicializar línea virtual
    line_start_x, line_start_y, line_end_x, line_end_y, line_a, line_b, line_c = calculate_line_parameters(line_coords_original)
    line_coords = (line_start_x, line_start_y, line_end_x, line_end_y)
    line_params = (line_a, line_b, line_c)
    
    # Inicializar variables de conteo
    counts = {'entry': 0, 'exit': 0, 'total': 0, 'inside': 0}
    tracked_objects = {}
    pixelate_enabled = False
    
    # Imprimir información inicial
    print(f"Dimensiones originales: Ancho={W_original}, Alto={H_original}")
    print(f"Dimensiones escaladas: Ancho={W}, Alto={H} (Factor: {SCALE_FACTOR})")
    print(f"Línea escalada desde ({line_start_x}, {line_start_y}) hasta ({line_end_x}, {line_end_y})")
    print("Controles: 'q' para salir, 'p' para activar/desactivar pixelado")
    
    # Bucle principal
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Fin del video o error al leer frame.")
            break
        
        # Redimensionar frame
        frame = cv2.resize(frame, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR)
        
        # Procesar detecciones
        detections = process_detections(frame, model, pixelate_enabled)
        
        # Seguimiento y conteo
        tracked_objects = track_and_count_objects(detections, tracked_objects, line_params, counts, W)
        
        # Dibujar en el frame
        draw_frame(frame, detections, line_coords, counts)
        
        # Mostrar frame
        cv2.imshow("Contador de Personas YOLOv5", frame)
        
        # Manejar teclas
        key = cv2.waitKey(1) & 0xFF
        print(f"Key pressed: {key}")  # Add this line for debugging
        if key == ord('q'):
            break
        elif key == ord('p'):
            pixelate_enabled = not pixelate_enabled
            print(f"Pixelado {'activado' if pixelate_enabled else 'desactivado'}")
    
    # Exportar datos a JSON
    export_to_json(counts, args.output_dir)
    
    # Liberar recursos
    cap.release()
    cv2.destroyAllWindows()
    
    # Imprimir resumen
    print("Proceso finalizado.")
    print(f"Resumen: Entradas={counts['entry']}, Salidas={counts['exit']}, "
          f"Total personas={counts['total']}, Personas dentro={counts['inside']}")

if __name__ == "__main__":
    object_id_counter = 0  # Contador global para IDs de objetos
    main()