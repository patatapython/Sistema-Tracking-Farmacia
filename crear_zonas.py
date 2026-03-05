import cv2
import numpy as np
import json
import os
from datetime import datetime
import argparse

# --- CONFIGURACIÓN ---
VIDEO_SOURCE = r"I:\tfm_tracking\videos\webcam\cajas2.mkv" # Mantener VIDEO_SOURCE aquí, se sobrescribirá con argparse

# Variables globales
current_polygon = []
completed_polygons = []
current_zone_name = ""
drawing_mode = False
zone_colors = [
    (0, 255, 255),    # Amarillo
    (255, 0, 255),    # Magenta
    (0, 255, 0),      # Verde
    (255, 255, 0),    # Cian
    (255, 0, 0),      # Azul
    (0, 165, 255),    # Naranja
    (128, 0, 128),    # Púrpura
    (255, 192, 203)   # Rosa
]
output_file_path = None # Se inicializará con el argumento

def get_zone_name():
    """Solicita el nombre de la zona al usuario mediante una ventana de OpenCV"""
    print("\n" + "="*50)
    print("CREAR NUEVA ZONA")
    print("="*50)
    
    # Crear una imagen en blanco para la ventana de diálogo
    dialog_img = np.zeros((200, 400, 3), np.uint8)
    dialog_img[:] = (240, 240, 240)  # Fondo gris claro
    
    # Nombre predeterminado
    default_name = f"zona_{len(completed_polygons) + 1}"
    zone_name = default_name
    input_text = default_name
    
    # Función para manejar eventos de teclado
    def on_key(key):
        nonlocal input_text
        key = chr(key & 0xFF)
        
        # Verificar si es una tecla válida (letras, números, guiones, etc.)
        if key.isalnum() or key in "_-":
            input_text += key
        elif key == '\b':  # Backspace
            input_text = input_text[:-1]
    
    # Mostrar la ventana de diálogo
    cv2.namedWindow("Nombre de Zona")
    
    # Bucle para capturar la entrada del usuario
    while True:
        # Crear una copia de la imagen para dibujar
        img_copy = dialog_img.copy()
        
        # Dibujar título
        cv2.putText(img_copy, "Ingresa el nombre de la zona:",
                   (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # Dibujar campo de texto
        cv2.rectangle(img_copy, (20, 60), (380, 100), (255, 255, 255), -1)
        cv2.rectangle(img_copy, (20, 60), (380, 100), (0, 0, 0), 1)
        cv2.putText(img_copy, input_text,
                   (30, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        # Dibujar instrucciones
        cv2.putText(img_copy, "Presiona ENTER para confirmar",
                   (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.putText(img_copy, "ESC para usar nombre predeterminado",
                   (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Mostrar la imagen
        cv2.imshow("Nombre de Zona", img_copy)
        
        # Capturar tecla
        key = cv2.waitKey(1) & 0xFF
        
        # Verificar si es ENTER (confirmar) o ESC (cancelar)
        if key == 13:  # ENTER
            if input_text:
                zone_name = input_text
            break
        elif key == 27:  # ESC
            zone_name = default_name
            break
        # Backspace
        elif key == 8:
            if input_text:
                input_text = input_text[:-1]
        # Caracteres normales
        elif 32 <= key <= 126:  # ASCII imprimible
            char = chr(key)
            if char.isalnum() or char in "_-":
                input_text += char
    
    # Cerrar la ventana
    cv2.destroyWindow("Nombre de Zona")
    
    print(f"Nombre de zona seleccionado: {zone_name}")
    return zone_name

def mouse_callback(event, x, y, flags, param):
    """Función callback para capturar clics del mouse"""
    global current_polygon, drawing_mode, current_zone_name
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if not drawing_mode:
            # Iniciar nueva zona
            current_zone_name = get_zone_name()
            drawing_mode = True
            current_polygon = []
            print(f"\n--- CREANDO ZONA: {current_zone_name.upper()} ---")
            print("Haz clic para añadir puntos al polígono")
            print("Presiona 'c' para completar el polígono")
            print("Presiona 'r' para cancelar y reiniciar")
        
        # Añadir punto al polígono actual
        current_polygon.append((x, y))
        print(f"Punto {len(current_polygon)}: ({x}, {y})")
    
    elif event == cv2.EVENT_RBUTTONDOWN:
        # Clic derecho para completar polígono
        if len(current_polygon) >= 3:
            complete_polygon()

def complete_polygon():
    """Completa el polígono actual y lo añade a la lista"""
    global current_polygon, completed_polygons, drawing_mode, current_zone_name
    
    try:
        if len(current_polygon) >= 3:
            color = zone_colors[len(completed_polygons) % len(zone_colors)]
            polygon_data = {
                'name': current_zone_name,
                'points': current_polygon.copy(),
                'color': color
            }
            completed_polygons.append(polygon_data)
            
            print(f"\n[OK] ZONA '{current_zone_name}' COMPLETADA")
            print(f"Puntos: {current_polygon}")
            print(f"Total de zonas creadas: {len(completed_polygons)}")
            
            # Resetear para la siguiente zona
            current_polygon = []
            drawing_mode = False
            current_zone_name = ""
            
            # Mostrar coordenadas
            show_current_coordinates()
        else:
            print("[ERROR] Error: Se necesitan al menos 3 puntos para crear un polígono")
    except Exception as e:
        print(f"[ERROR] Excepción en complete_polygon(): {e}")
        # Asegurar que las variables se reseteen incluso si hay error
        current_polygon = []
        drawing_mode = False
        current_zone_name = ""

def show_current_coordinates():
    """Muestra las coordenadas actuales en formato código"""
    try:
        print("\n" + "="*60)
        print("COORDENADAS ACTUALES PARA TU CÓDIGO:")
        print("="*60)
        
        # Formato para el diccionario ZONAS
        print("# Para usar en tu código hola.py:")
        print("ZONAS = {")
        for i, zone in enumerate(completed_polygons):
            points_str = str(zone['points'])
            print(f'    "{zone["name"]}": {points_str}{"," if i < len(completed_polygons)-1 else ""}')
        print("}")
        
        # Formato para los colores
        print("\n# Colores para cada zona:")
        print("COLORES_ZONAS = {")
        for i, zone in enumerate(completed_polygons):
            color_str = str(zone['color'])
            print(f'    "{zone["name"]}": {color_str}{"," if i < len(completed_polygons)-1 else ""}')
        print("}")
        print("="*60)
    except Exception as e:
        print(f"[ERROR] Excepción en show_current_coordinates(): {e}")

def choose_save_location():
    """Permite al usuario elegir dónde guardar el archivo"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Crear ventana temporal para el diálogo
        root = tk.Tk()
        root.withdraw()  # Ocultar la ventana principal
        
        # Mostrar diálogo para guardar archivo
        filename = filedialog.asksaveasfilename(
            title="Guardar archivo de zonas como",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfilename="zonas_config.json"
        )
        
        root.destroy()
        return filename if filename else None
        
    except ImportError:
        print("[ERROR] No se puede abrir el diálogo de guardado (tkinter no disponible)")
        return None
    except Exception as e:
        print(f"[ERROR] Error al abrir diálogo de guardado: {e}")
        return None

def save_coordinates(custom_path=None):
    """Guarda las coordenadas en un archivo JSON"""
    global output_file_path
    if not completed_polygons:
        print("No hay zonas para guardar")
        return
    
    # Usar ruta personalizada si se proporciona, sino usar la ruta por defecto
    save_path = custom_path if custom_path else output_file_path
    
    if not save_path:
        print("Advertencia: No se especificó un archivo de salida para las zonas.")
        return

    # Asegurarse de que el directorio de salida exista
    output_dir = os.path.dirname(save_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    data = {
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'total_zones': len(completed_polygons),
        'zones': completed_polygons
    }
    
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVED] Coordenadas guardadas en: {save_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error al guardar: {e}")
        return False

def draw_polygon(frame, points, color, thickness=2, closed=True):
    """Dibuja un polígono en el frame"""
    if len(points) < 2:
        return
    
    # Convertir puntos a numpy array
    pts = np.array(points, np.int32)
    
    if closed and len(points) >= 3:
        # Dibujar polígono cerrado
        cv2.fillPoly(frame, [pts], color + (50,))  # Relleno semi-transparente
        cv2.polylines(frame, [pts], True, color, thickness)
    else:
        # Dibujar líneas conectando los puntos
        cv2.polylines(frame, [pts], False, color, thickness)

def draw_points(frame, points, color):
    """Dibuja los puntos individuales"""
    for i, point in enumerate(points):
        cv2.circle(frame, point, 5, color, -1)
        cv2.putText(frame, f"P{i+1}", (point[0]+10, point[1]-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def main():
    global output_file_path, current_polygon, completed_polygons, drawing_mode, current_zone_name

    parser = argparse.ArgumentParser(description="Herramienta para crear áreas/polígonos para tracking.")
    parser.add_argument("--video_source", type=str, default="0",
                        help="Ruta al archivo de video o '0' para usar la webcam.")
    parser.add_argument("--output_file", type=str, default="zonas_config.json",
                        help="Ruta al archivo JSON donde se guardarán las coordenadas de las zonas.")
    args = parser.parse_args()

    output_file_path = args.output_file

    # --- CAPTURA DE VIDEO ---
    cap = cv2.VideoCapture(args.video_source)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir el video: {args.video_source}")
        exit()

    # Obtener primer frame
    ret, frame = cap.read()
    if not ret:
        print("Error: No se pudo leer el frame del video.")
        exit()

    print("=== CREADOR DE ÁREAS/POLÍGONOS PARA TRACKING ===")
    print(f"Dimensiones del video: {frame.shape[1]}x{frame.shape[0]}")
    print("\nINSTRUCCIONES:")
    print("1. Haz clic izquierdo para añadir puntos al polígono")
    print("2. Clic derecho o presiona 'c' para completar el polígono actual")
    print("3. Presiona 'n' para empezar una nueva zona")
    print("4. Presiona 'r' para cancelar polígono actual")
    print("5. Presiona 's' para guardar coordenadas")
    print("6. Presiona 'g' para guardar en ubicación personalizada")
    print("7. Presiona 'h' para ver coordenadas actuales")
    print("8. Presiona 'q' para salir")

    # Configurar ventana y mouse
    cv2.namedWindow("Creador de Zonas")
    cv2.setMouseCallback("Creador de Zonas", mouse_callback)

    while True:
        frame_copy = frame.copy()
        
        # Dibujar polígonos completados
        for zone in completed_polygons:
            draw_polygon(frame_copy, zone['points'], zone['color'])
            draw_points(frame_copy, zone['points'], zone['color'])
            
            # Etiqueta de la zona
            if zone['points']:
                label_pos = zone['points'][0]
                cv2.putText(frame_copy, zone['name'].upper(),
                           (label_pos[0], label_pos[1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, zone['color'], 2)
        
        # Dibujar polígono actual (en construcción)
        if current_polygon:
            color = zone_colors[len(completed_polygons) % len(zone_colors)]
            draw_polygon(frame_copy, current_polygon, color, closed=False)
            draw_points(frame_copy, current_polygon, color)
            
            # Mostrar nombre de la zona actual
            if current_zone_name:
                cv2.putText(frame_copy, f"Creando: {current_zone_name.upper()}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Instrucciones en pantalla
        status_y = frame.shape[0] - 60
        if drawing_mode:
            cv2.putText(frame_copy, f"Puntos: {len(current_polygon)} | Clic derecho o 'c' para completar",
                       (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            cv2.putText(frame_copy, f"Zonas creadas: {len(completed_polygons)} | Clic izquierdo para nueva zona",
                       (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(frame_copy, "Presiona 'h' coordenadas | 's' guardar | 'g' guardar como | 'q' salir",
                   (10, status_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        cv2.imshow("Creador de Zonas", frame_copy)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):  # Completar polígono
            if len(current_polygon) >= 3:
                complete_polygon()
            else:
                print("[ERROR] Se necesitan al menos 3 puntos para completar el polígono")
        elif key == ord('r'):  # Reiniciar polígono actual
            if drawing_mode:
                current_polygon = []
                drawing_mode = False
                current_zone_name = ""
                print("[RESET] Polígono actual cancelado")
        elif key == ord('n'):  # Nueva zona
            if not drawing_mode:
                current_zone_name = get_zone_name()
                drawing_mode = True
                current_polygon = []
                print(f"\n--- CREANDO ZONA: {current_zone_name.upper()} ---")
        elif key == ord('s'):  # Guardar coordenadas
            save_coordinates()
        elif key == ord('g'):  # Guardar con ubicación personalizada
            custom_path = choose_save_location()
            if custom_path:
                save_coordinates(custom_path)
            else:
                print("[INFO] Guardado cancelado por el usuario")
        elif key == ord('h'):  # Mostrar coordenadas
            show_current_coordinates()
        elif key == ord('d'):  # Eliminar última zona
            if completed_polygons:
                removed = completed_polygons.pop()
                print(f"[DELETE] Zona '{removed['name']}' eliminada")
            else:
                print("[ERROR] No hay zonas para eliminar")

    cap.release()
    cv2.destroyAllWindows()

    # Mostrar resumen final
    print("\n" + "="*60)
    print("RESUMEN FINAL")
    print("="*60)
    print(f"Total de zonas creadas: {len(completed_polygons)}")
    for i, zone in enumerate(completed_polygons, 1):
        print(f"{i}. {zone['name']}: {len(zone['points'])} puntos")

    if completed_polygons:
        save_coordinates()
        show_current_coordinates()
        print("\n[OK] ¡Listo! Copia las coordenadas y úsalas en tu código de tracking.")
    else:
        print("[ERROR] No se crearon zonas.")

if __name__ == "__main__":
    main()