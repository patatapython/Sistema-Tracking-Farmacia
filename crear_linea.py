import cv2
import argparse
import json
import os

# Variables globales
line_points = []
drawing = False
output_file_path = None # Se inicializará con el argumento

def save_line_coordinates(points, output_path):
    """Guarda las coordenadas de la línea en un archivo JSON."""
    if not output_path:
        print("Advertencia: No se especificó un archivo de salida para las coordenadas de la línea.")
        return

    data = {
        "LINE_START_X": points[0][0],
        "LINE_START_Y": points[0][1],
        "LINE_END_X": points[1][0],
        "LINE_END_Y": points[1][1]
    }
    
    try:
        # Asegurarse de que el directorio de salida exista
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nCoordenadas de la línea guardadas en: {output_path}")
    except Exception as e:
        print(f"Error al guardar las coordenadas de la línea: {e}")

def mouse_callback(event, x, y, flags, param):
    """Función callback para capturar clics del mouse"""
    global line_points, drawing, output_file_path
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(line_points) == 0:
            line_points.append((x, y))
            print(f"Punto 1: ({x}, {y})")
        elif len(line_points) == 1:
            line_points.append((x, y))
            print(f"Punto 2: ({x}, {y})")
            print("\n" + "="*50)
            print("COORDENADAS DE TU LÍNEA:")
            print(f"LINE_START_X = {line_points[0][0]}")
            print(f"LINE_START_Y = {line_points[0][1]}")
            print(f"LINE_END_X = {line_points[1][0]}")
            print(f"LINE_END_Y = {line_points[1][1]}")
            print("="*50)
            print("Copia estas coordenadas y dámelas para aplicarlas al código original")
            print("Presiona 'r' para reiniciar o 'q' para salir")
            
            # Guardar en archivo JSON
            save_line_coordinates(line_points, output_file_path)

def main():
    global output_file_path, line_points

    parser = argparse.ArgumentParser(description="Herramienta para trazar una línea virtual en un video.")
    parser.add_argument("--video_source", type=str, default="0",
                        help="Ruta al archivo de video o '0' para usar la webcam.")
    parser.add_argument("--output_file", type=str, default="line_coordinates.json",
                        help="Ruta al archivo JSON donde se guardarán las coordenadas de la línea.")
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

    print("=== TRAZADOR DE LÍNEA ===")
    print("1. Haz clic en el PRIMER punto de la línea")
    print("2. Haz clic en el SEGUNDO punto de la línea")
    print("3. Las coordenadas aparecerán en la consola y se guardarán en el archivo de salida.")
    print("4. Presiona 'r' para reiniciar, 'q' para salir")
    print(f"Dimensiones del video: {frame.shape[1]}x{frame.shape[0]}")

    # Configurar ventana y mouse
    cv2.namedWindow("Trazador de Línea")
    cv2.setMouseCallback("Trazador de Línea", mouse_callback)

    while True:
        frame_copy = frame.copy()
        
        # Dibujar puntos ya marcados
        for i, point in enumerate(line_points):
            cv2.circle(frame_copy, point, 8, (0, 0, 255), -1)  # Círculo rojo
            cv2.putText(frame_copy, f"P{i+1}", (point[0]+15, point[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Dibujar línea si tenemos 2 puntos
        if len(line_points) == 2:
            cv2.line(frame_copy, line_points[0], line_points[1], (0, 255, 0), 3)
        
        # Instrucciones en pantalla
        if len(line_points) == 0:
            cv2.putText(frame_copy, "Haz clic en el PRIMER punto", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        elif len(line_points) == 1:
            cv2.putText(frame_copy, "Haz clic en el SEGUNDO punto", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        else:
            cv2.putText(frame_copy, "LINEA COMPLETA - Revisa la consola y el archivo de salida", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame_copy, "Presiona 'r' para reiniciar", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Trazador de Línea", frame_copy)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):  # Reiniciar
            line_points = []
            print("\nLínea reiniciada. Define nuevos puntos.")

    cap.release()
    cv2.destroyAllWindows()

    if len(line_points) == 2:
        print(f"\nCOORDENADAS FINALES:")
        print(f"Punto 1: {line_points[0]}")
        print(f"Punto 2: {line_points[1]}")
    else:
        print("No se completó la línea.")

if __name__ == "__main__":
    main()