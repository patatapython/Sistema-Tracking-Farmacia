import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import sys
import os
import threading
from datetime import datetime
from PIL import Image, ImageTk

class NuevaFarmaciaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Farmacia_Iren - Sistema de Gestión Farmacéutica")
        self.root.geometry("1200x800")
        
        # Variables para Herramientas
        self.line_video_source = ctk.StringVar(value="0")
        self.line_output_dir = ctk.StringVar(value="config")
        self.zones_video_source = ctk.StringVar(value="0")
        self.zones_output_dir = ctk.StringVar(value="config")
        
        # Variables para Procesamiento
        self.conteo_video_source = ctk.StringVar(value="0")
        self.conteo_line_file = ctk.StringVar(value="config/line_coordinates.json")
        self.conteo_output_dir = ctk.StringVar(value="datos_conteo")
        self.tracking_video_source = ctk.StringVar(value="0")
        self.tracking_zones_file = ctk.StringVar(value="config/zonas_config.json")
        self.tracking_output_dir = ctk.StringVar(value="datos_tracking")
        
        # Variables de estado de procesos
        self.conteo_process = None
        self.tracking_process = None
        self.conteo_activo = ctk.BooleanVar(value=False)
        self.tracking_activo = ctk.BooleanVar(value=False)
        
        # Configurar tema - Tema claro para farmacia
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz de usuario principal"""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Pestaña 1: Herramientas
        self.tab_tools = self.tabview.add("Herramientas")
        self.setup_tools_tab()
        
        # Pestaña 2: Procesamiento y Control (fusionadas)
        self.tab_processing = self.tabview.add("Procesamiento y Control")
        self.setup_processing_control_tab()
        
    def setup_tools_tab(self):
        """Configura la pestaña de herramientas con diseño farmacia"""
        # Frame principal de herramientas
        tools_main_frame = ctk.CTkFrame(self.tab_tools, fg_color="#F8FFFE")
        tools_main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Logo y título superior
        header_frame = ctk.CTkFrame(tools_main_frame, fg_color="#2E8B57", corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Logo de farmacia
        logo_frame = ctk.CTkFrame(header_frame, fg_color="white", corner_radius=10, width=100, height=70)
        logo_frame.pack(side="left", padx=20, pady=10)
        
        try:
            # Cargar imagen JPG usando PIL
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "Logo", "logo.jpg")
            
            if os.path.exists(logo_path):
                pil_image = Image.open(logo_path)
                # Redimensionar imagen manteniendo proporción
                pil_image = pil_image.resize((90, 60), Image.Resampling.LANCZOS)
                logo_image = ImageTk.PhotoImage(pil_image)
                
                logo_label = ctk.CTkLabel(
                    logo_frame,
                    image=logo_image,
                    text="",
                    width=90,
                    height=60
                )
                logo_label.image = logo_image  # Mantener referencia
                logo_label.pack(pady=5)
            else:
                raise FileNotFoundError(f"Logo no encontrado: {logo_path}")
                
        except Exception as e:
            # Si no se puede cargar el logo, usar el símbolo de respaldo
            print(f"Error cargando logo: {e}")
            logo_label = ctk.CTkLabel(
                logo_frame,
                text="🏥",
                font=("Arial", 36),
                text_color="#2E8B57"
            )
            logo_label.pack(pady=15)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Farmacia_Irene - Herramientas de Configuración",
            font=("Segoe UI", 22, "bold"),
            text_color="white"
        )
        title_label.pack(side="left", padx=20, pady=20)
        
        # Frame izquierdo para herramientas
        left_frame = ctk.CTkFrame(tools_main_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10))
        
        # Frame para Crear Línea Virtual
        line_frame = ctk.CTkFrame(
            left_frame,
            corner_radius=15,
            border_width=2,
            fg_color="white",
            border_color="#2E8B57"
        )
        line_frame.pack(fill="x", pady=(0, 20))
        
        line_title = ctk.CTkLabel(
            line_frame,
            text="Crear Línea Virtual",
            font=("Segoe UI", 16, "bold"),
            text_color="#2E8B57"
        )
        line_title.pack(pady=(15, 10))
        
        line_content = ctk.CTkFrame(line_frame, fg_color="transparent")
        line_content.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(line_content, text="Fuente de video:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkEntry(line_content, textvariable=self.line_video_source, width=280, height=35).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            line_content,
            text="Examinar",
            command=lambda: self.select_video_file(self.line_video_source),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(line_content, text="Carpeta de salida JSON:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkEntry(line_content, textvariable=self.line_output_dir, width=280, height=35).grid(row=1, column=1, padx=5)
        ctk.CTkButton(
            line_content,
            text="Examinar",
            command=lambda: self.select_directory(self.line_output_dir),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=1, column=2, padx=5)
        
        ctk.CTkButton(
            line_content,
            text="Crear Línea Virtual",
            command=self.create_line,
            fg_color="#2E8B57",
            hover_color="#228B22",
            height=40,
            font=("Segoe UI", 14, "bold"),
            text_color="white"
        ).grid(row=2, column=0, columnspan=3, pady=(15, 10), sticky="ew")
        
        # Frame para Crear Zonas Tracking
        zones_frame = ctk.CTkFrame(
            left_frame,
            corner_radius=15,
            border_width=2,
            fg_color="white",
            border_color="#2E8B57"
        )
        zones_frame.pack(fill="x", pady=(0, 20))
        
        zones_title = ctk.CTkLabel(
            zones_frame,
            text="Crear Zonas de Tracking",
            font=("Segoe UI", 16, "bold"),
            text_color="#2E8B57"
        )
        zones_title.pack(pady=(15, 10))
        
        zones_content = ctk.CTkFrame(zones_frame, fg_color="transparent")
        zones_content.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(zones_content, text="Fuente de video:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkEntry(zones_content, textvariable=self.zones_video_source, width=280, height=35).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            zones_content,
            text="Examinar",
            command=lambda: self.select_video_file(self.zones_video_source),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(zones_content, text="Carpeta de salida JSON:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkEntry(zones_content, textvariable=self.zones_output_dir, width=280, height=35).grid(row=1, column=1, padx=5)
        ctk.CTkButton(
            zones_content,
            text="Examinar",
            command=lambda: self.select_directory(self.zones_output_dir),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=1, column=2, padx=5)
        
        ctk.CTkButton(
            zones_content,
            text="Crear Zonas de Tracking",
            command=self.create_zones,
            fg_color="#2E8B57",
            hover_color="#228B22",
            height=40,
            font=("Segoe UI", 14, "bold"),
            text_color="white"
        ).grid(row=2, column=0, columnspan=3, pady=(15, 10), sticky="ew")
        
        # Frame derecho para logs e instrucciones
        right_frame = ctk.CTkFrame(tools_main_frame, fg_color="white", corner_radius=15)
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 20))
        
        # Título de logs
        logs_title = ctk.CTkLabel(
            right_frame,
            text="Logs e Instrucciones",
            font=("Segoe UI", 16, "bold"),
            text_color="#2E8B57"
        )
        logs_title.pack(pady=(15, 10))
        
        # Frame para logs
        logs_frame = ctk.CTkFrame(right_frame, fg_color="#F0FFF0", corner_radius=10)
        logs_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.tools_log_text = ctk.CTkTextbox(
            logs_frame,
            height=400,
            state='disabled',
            text_color="#2E8B57",
            fg_color="#F0FFF0",
            font=("Segoe UI", 11)
        )
        self.tools_log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
    def setup_processing_control_tab(self):
        """Configura la pestaña de procesamiento y control con diseño farmacia"""
        # Frame principal
        main_frame = ctk.CTkFrame(self.tab_processing, fg_color="#F8FFFE")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header con logo
        header_frame = ctk.CTkFrame(main_frame, fg_color="#2E8B57", corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Logo en el header de procesamiento
        logo_proc_frame = ctk.CTkFrame(header_frame, fg_color="white", corner_radius=10, width=100, height=70)
        logo_proc_frame.pack(side="left", padx=20, pady=10)
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "Logo", "logo.jpg")
            
            if os.path.exists(logo_path):
                pil_image = Image.open(logo_path)
                pil_image = pil_image.resize((90, 60), Image.Resampling.LANCZOS)
                logo_image = ImageTk.PhotoImage(pil_image)
                
                logo_proc_label = ctk.CTkLabel(
                    logo_proc_frame,
                    image=logo_image,
                    text="",
                    width=90,
                    height=60
                )
                logo_proc_label.image = logo_image
                logo_proc_label.pack(pady=5)
            else:
                raise FileNotFoundError(f"Logo no encontrado: {logo_path}")
                
        except Exception as e:
            print(f"Error cargando logo en procesamiento: {e}")
            logo_proc_label = ctk.CTkLabel(
                logo_proc_frame,
                text="🏥",
                font=("Arial", 36),
                text_color="#2E8B57"
            )
            logo_proc_label.pack(pady=15)
        
        header_title = ctk.CTkLabel(
            header_frame,
            text="Configuración de Procesamiento - Farmacia_Irene",
            font=("Segoe UI", 20, "bold"),
            text_color="white"
        )
        header_title.pack(side="left", padx=20, pady=15)
        
        # Frame superior - Configuración
        config_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        config_frame.pack(fill="x", padx=20, pady=5)
        
        # Frame para Conteo
        conteo_frame = ctk.CTkFrame(
            config_frame,
            corner_radius=15,
            border_width=2,
            fg_color="white",
            border_color="#2E8B57"
        )
        conteo_frame.pack(fill="x", pady=(0, 15))
        
        conteo_title = ctk.CTkLabel(
            conteo_frame,
            text="Configuración Conteo de Personas",
            font=("Segoe UI", 16, "bold"),
            text_color="#2E8B57"
        )
        conteo_title.pack(pady=(15, 10))
        
        conteo_content = ctk.CTkFrame(conteo_frame, fg_color="transparent")
        conteo_content.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(conteo_content, text=" Fuente de video:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkEntry(conteo_content, textvariable=self.conteo_video_source, width=250, height=35).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            conteo_content,
            text="Examinar",
            command=lambda: self.select_video_file(self.conteo_video_source),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(conteo_content, text=" Archivo JSON línea:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkEntry(conteo_content, textvariable=self.conteo_line_file, width=250, height=35).grid(row=1, column=1, padx=5)
        ctk.CTkButton(
            conteo_content,
            text="Examinar",
            command=lambda: self.select_json_file(self.conteo_line_file),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=1, column=2, padx=5)
        
        ctk.CTkLabel(conteo_content, text=" Carpeta de salida:", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="w", pady=5)
        ctk.CTkEntry(conteo_content, textvariable=self.conteo_output_dir, width=250, height=35).grid(row=2, column=1, padx=5)
        ctk.CTkButton(
            conteo_content,
            text="Examinar",
            command=lambda: self.select_directory(self.conteo_output_dir),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=2, column=2, padx=5)
        
        # Frame para Tracking
        tracking_frame = ctk.CTkFrame(
            config_frame,
            corner_radius=15,
            border_width=2,
            fg_color="white",
            border_color="#2E8B57"
        )
        tracking_frame.pack(fill="x", pady=(0, 15))
        
        tracking_title = ctk.CTkLabel(
            tracking_frame,
            text="Configuración Tracking de Zonas",
            font=("Segoe UI", 16, "bold"),
            text_color="#2E8B57"
        )
        tracking_title.pack(pady=(15, 10))
        
        tracking_content = ctk.CTkFrame(tracking_frame, fg_color="transparent")
        tracking_content.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(tracking_content, text=" Fuente de video:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkEntry(tracking_content, textvariable=self.tracking_video_source, width=250, height=35).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            tracking_content,
            text="Examinar",
            command=lambda: self.select_video_file(self.tracking_video_source),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(tracking_content, text=" Archivo JSON zonas:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkEntry(tracking_content, textvariable=self.tracking_zones_file, width=250, height=35).grid(row=1, column=1, padx=5)
        ctk.CTkButton(
            tracking_content,
            text="Examinar",
            command=lambda: self.select_json_file(self.tracking_zones_file),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=1, column=2, padx=5)
        
        ctk.CTkLabel(tracking_content, text=" Carpeta de salida:", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="w", pady=5)
        ctk.CTkEntry(tracking_content, textvariable=self.tracking_output_dir, width=250, height=35).grid(row=2, column=1, padx=5)
        ctk.CTkButton(
            tracking_content,
            text="Examinar",
            command=lambda: self.select_directory(self.tracking_output_dir),
            fg_color="#90EE90",
            text_color="#2E8B57",
            hover_color="#98FB98",
            width=80,
            height=35
        ).grid(row=2, column=2, padx=5)
        
        # Frame inferior - Control de procesos
        control_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        control_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        control_title = ctk.CTkLabel(
            control_frame,
            text="Control de Procesos",
            font=("Segoe UI", 18, "bold"),
            text_color="#2E8B57"
        )
        control_title.pack(pady=(10, 20))
        
        # Frame para controles individuales
        controls_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Controles para Conteo
        conteo_control_frame = ctk.CTkFrame(
            controls_frame,
            corner_radius=15,
            fg_color="white",
            border_width=2,
            border_color="#2E8B57"
        )
        conteo_control_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(
            conteo_control_frame,
            text="Conteo",
            font=("Segoe UI", 14, "bold"),
            text_color="#2E8B57"
        ).pack(pady=(10, 5))
        
        self.conteo_switch = ctk.CTkSwitch(
            conteo_control_frame,
            text="Activar Conteo",
            variable=self.conteo_activo,
            progress_color="#2E8B57",
            button_color="#90EE90",
            button_hover_color="#98FB98"
        )
        self.conteo_switch.pack(pady=5)
        
        self.conteo_status_label = ctk.CTkLabel(
            conteo_control_frame,
            text="Estado: Detenido",
            text_color="#DC3545",
            font=("Segoe UI", 12)
        )
        self.conteo_status_label.pack(pady=5)
        
        conteo_buttons = ctk.CTkFrame(conteo_control_frame, fg_color="transparent")
        conteo_buttons.pack(pady=10)
        
        ctk.CTkButton(
            conteo_buttons,
            text="Iniciar",
            command=self.start_conteo,
            fg_color="#2E8B57",
            hover_color="#228B22",
            width=90,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            conteo_buttons,
            text="Detener",
            command=self.stop_conteo,
            fg_color="#DC3545",
            hover_color="#B22222",
            width=90,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=5)
        
        # Controles para Tracking
        tracking_control_frame = ctk.CTkFrame(
            controls_frame,
            corner_radius=15,
            fg_color="white",
            border_width=2,
            border_color="#2E8B57"
        )
        tracking_control_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(
            tracking_control_frame,
            text="Tracking",
            font=("Segoe UI", 14, "bold"),
            text_color="#2E8B57"
        ).pack(pady=(10, 5))
        
        self.tracking_switch = ctk.CTkSwitch(
            tracking_control_frame,
            text="Activar Tracking",
            variable=self.tracking_activo,
            progress_color="#2E8B57",
            button_color="#90EE90",
            button_hover_color="#98FB98"
        )
        self.tracking_switch.pack(pady=5)
        
        self.tracking_status_label = ctk.CTkLabel(
            tracking_control_frame,
            text="Estado: Detenido",
            text_color="#DC3545",
            font=("Segoe UI", 12)
        )
        self.tracking_status_label.pack(pady=5)
        
        tracking_buttons = ctk.CTkFrame(tracking_control_frame, fg_color="transparent")
        tracking_buttons.pack(pady=10)
        
        ctk.CTkButton(
            tracking_buttons,
            text="Iniciar",
            command=self.start_tracking,
            fg_color="#2E8B57",
            hover_color="#228B22",
            width=90,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            tracking_buttons,
            text="Detener",
            command=self.stop_tracking,
            fg_color="#DC3545",
            hover_color="#B22222",
            width=90,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=5)
        
        # Controles globales
        global_frame = ctk.CTkFrame(
            controls_frame,
            corner_radius=15,
            fg_color="white",
            border_width=2,
            border_color="#2E8B57"
        )
        global_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(
            global_frame,
            text="Control Global",
            font=("Segoe UI", 14, "bold"),
            text_color="#2E8B57"
        ).pack(pady=(10, 5))
        
        global_buttons = ctk.CTkFrame(global_frame, fg_color="transparent")
        global_buttons.pack(pady=10)
        
        ctk.CTkButton(
            global_buttons,
            text="Iniciar Ambos",
            command=self.start_both,
            fg_color="#2E8B57",
            hover_color="#228B22",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=5)
        
        ctk.CTkButton(
            global_buttons,
            text="Detener Ambos",
            command=self.stop_both,
            fg_color="#DC3545",
            hover_color="#B22222",
            width=120,
            height=35,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=5)
        
        # Widget de información
        widget_frame = ctk.CTkFrame(control_frame, fg_color="white", corner_radius=15, border_width=2, border_color="#2E8B57")
        widget_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        widget_title = ctk.CTkLabel(
            widget_frame,
            text="Información del Sistema",
            font=("Segoe UI", 14, "bold"),
            text_color="#2E8B57"
        )
        widget_title.pack(pady=(10, 5))
        
        self.system_info = ctk.CTkLabel(
            widget_frame,
            text=" Sistema listo para procesar videos de farmacia",
            font=("Segoe UI", 12),
            text_color="#2E8B57"
        )
        self.system_info.pack(pady=(5, 10))
        
        # Logs de procesamiento
        logs_frame = ctk.CTkFrame(control_frame, fg_color="white", corner_radius=15, border_width=2, border_color="#2E8B57")
        logs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        logs_title = ctk.CTkLabel(
            logs_frame,
            text="Logs de Procesamiento",
            font=("Segoe UI", 14, "bold"),
            text_color="#2E8B57"
        )
        logs_title.pack(pady=(10, 5))
        
        self.processing_log_text = ctk.CTkTextbox(
            logs_frame,
            height=150,
            state='disabled',
            text_color="#2E8B57",
            fg_color="#F0FFF0",
            font=("Segoe UI", 11)
        )
        self.processing_log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
    def select_video_file(self, variable):
        """Selector de archivo de video"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de video",
            filetypes=[("Archivos de video", "*.mp4 *.avi *.mkv *.mov *.wmv"), ("Todos los archivos", "*.*")]
        )
        if filename:
            variable.set(filename)
            
    def select_directory(self, variable):
        """Selector de directorio"""
        directory = filedialog.askdirectory(title="Seleccionar carpeta")
        if directory:
            variable.set(directory)
            
    def select_json_file(self, variable):
        """Selector de archivo JSON"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if filename:
            variable.set(filename)
            
    def log_tools_message(self, message):
        """Añade mensaje al log de herramientas"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.tools_log_text.configure(state='normal')
        self.tools_log_text.insert("end", f"[{timestamp}] {message}\n")
        self.tools_log_text.see("end")
        self.tools_log_text.configure(state='disabled')
        
    def log_processing_message(self, message):
        """Añade mensaje al log de procesamiento"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.processing_log_text.configure(state='normal')
        self.processing_log_text.insert("end", f"[{timestamp}] {message}\n")
        self.processing_log_text.see("end")
        self.processing_log_text.configure(state='disabled')
        
    def create_line(self):
        """Ejecuta crear_linea.py con instrucciones"""
        video_source = self.line_video_source.get()
        output_file = os.path.join(self.line_output_dir.get(), "line_coordinates.json")
        
        # Crear directorio si no existe
        os.makedirs(self.line_output_dir.get(), exist_ok=True)
        
        script_path = os.path.join(os.path.dirname(__file__), "crear_linea.py")
        cmd = [sys.executable, script_path, "--video_source", video_source, "--output_file", output_file]
        
        self.log_tools_message(f"Iniciando creación de línea virtual...")
        self.log_tools_message(f"Fuente de video: {video_source}")
        self.log_tools_message(f"Archivo de salida: {output_file}")
        self.log_tools_message("\nINSTRUCCIONES PARA CREAR LÍNEA VIRTUAL:")
        self.log_tools_message("1. Selecciona el primer frame del video")
        self.log_tools_message("2. Haz clic en dos puntos para definir la línea de conteo")
        self.log_tools_message("3. Presiona 's' para guardar la línea")
        self.log_tools_message("4. Presiona 'q' para salir")
        
        threading.Thread(target=self.run_tool, args=(cmd, "crear_linea"), daemon=True).start()
        
    def create_zones(self):
        """Ejecuta crear_zonas.py con instrucciones"""
        video_source = self.zones_video_source.get()
        output_file = os.path.join(self.zones_output_dir.get(), "zonas_config.json")
        
        # Crear directorio si no existe
        os.makedirs(self.zones_output_dir.get(), exist_ok=True)
        
        script_path = os.path.join(os.path.dirname(__file__), "crear_zonas.py")
        cmd = [sys.executable, script_path, "--video_source", video_source, "--output_file", output_file]
        
        self.log_tools_message(f"Iniciando creación de zonas de tracking...")
        self.log_tools_message(f"Fuente de video: {video_source}")
        self.log_tools_message(f"Archivo de salida: {output_file}")
        self.log_tools_message("\nINSTRUCCIONES PARA CREAR ZONAS:")
        self.log_tools_message("1. Haz clic izquierdo para añadir puntos al polígono")
        self.log_tools_message("2. Clic derecho o presiona 'c' para completar el polígono actual")
        self.log_tools_message("3. Presiona 'n' para empezar una nueva zona")
        self.log_tools_message("4. Presiona 'r' para cancelar polígono actual")
        self.log_tools_message("5. Presiona 's' para guardar coordenadas")
        self.log_tools_message("6. Presiona 'g' para guardar en ubicación personalizada")
        self.log_tools_message("7. Presiona 'h' para ver coordenadas actuales")
        self.log_tools_message("8. Presiona 'q' para salir")
        
        threading.Thread(target=self.run_tool, args=(cmd, "crear_zonas"), daemon=True).start()
        
    def run_tool(self, cmd, tool_name):
        """Ejecuta una herramienta y captura la salida"""
        try:
            if tool_name == "crear_zonas":
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         encoding='utf-8', errors='replace', text=True, bufsize=1)
                def read_output():
                    for line in iter(process.stdout.readline, ''):
                        if line.strip():
                            self.log_tools_message(line.strip())
                    for line in iter(process.stderr.readline, ''):
                        if line.strip():
                            self.log_tools_message(f"ERROR: {line.strip()}")
                threading.Thread(target=read_output, daemon=True).start()
                process.wait()
                self.log_tools_message(f"{tool_name} finalizado")
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if result.stdout:
                    self.log_tools_message(result.stdout)
                if result.stderr:
                    self.log_tools_message(f"ERROR: {result.stderr}")
                if result.returncode == 0:
                    self.log_tools_message(f"{tool_name} completado exitosamente")
                else:
                    self.log_tools_message(f"Error en {tool_name}")
        except Exception as e:
            self.log_tools_message(f"Error ejecutando {tool_name}: {str(e)}")
            
    def start_conteo(self):
        """Inicia el proceso de conteo"""
        if self.conteo_process and self.conteo_process.poll() is None:
            self.log_processing_message("El proceso de conteo ya está en ejecución")
            return
            
        script_path = os.path.join(os.path.dirname(__file__), "conteo.py")
        cmd = [
            sys.executable, script_path,
            "--video_source", self.conteo_video_source.get(),
            "--output_dir", self.conteo_output_dir.get(),
            "--line_config_file", self.conteo_line_file.get()
        ]
        
        try:
            self.conteo_process = subprocess.Popen(cmd, cwd=os.path.dirname(__file__))
            self.conteo_status_label.configure(text="Estado: En ejecución", text_color="#28A745")
            self.conteo_activo.set(True)
            self.log_processing_message("Proceso de conteo iniciado")
            self.update_system_info("Conteo activo")
        except Exception as e:
            self.log_processing_message(f"Error al iniciar conteo: {str(e)}")
            
    def start_tracking(self):
        """Inicia el proceso de tracking"""
        if self.tracking_process and self.tracking_process.poll() is None:
            self.log_processing_message("El proceso de tracking ya está en ejecución")
            return
            
        script_path = os.path.join(os.path.dirname(__file__), "tracking.py")
        cmd = [
            sys.executable, script_path,
            "--video_source", self.tracking_video_source.get(),
            "--output_dir", self.tracking_output_dir.get(),
            "--zones_config_file", self.tracking_zones_file.get()
        ]
        
        try:
            self.tracking_process = subprocess.Popen(cmd, cwd=os.path.dirname(__file__))
            self.tracking_status_label.configure(text="Estado: En ejecución", text_color="#28A745")
            self.tracking_activo.set(True)
            self.log_processing_message("Proceso de tracking iniciado")
            self.update_system_info("Tracking activo")
        except Exception as e:
            self.log_processing_message(f"Error al iniciar tracking: {str(e)}")
            
    def start_both(self):
        """Inicia ambos procesos"""
        self.start_conteo()
        self.start_tracking()
        self.update_system_info("Ambos procesos activos")
        
    def stop_conteo(self):
        """Detiene el proceso de conteo"""
        if self.conteo_process and self.conteo_process.poll() is None:
            self.conteo_process.terminate()
            self.conteo_process.wait()
            self.conteo_status_label.configure(text="Estado: Detenido", text_color="#DC3545")
            self.conteo_activo.set(False)
            self.log_processing_message("Proceso de conteo detenido")
            self.update_system_info()
            
    def stop_tracking(self):
        """Detiene el proceso de tracking"""
        if self.tracking_process and self.tracking_process.poll() is None:
            self.tracking_process.terminate()
            self.tracking_process.wait()
            self.tracking_status_label.configure(text="Estado: Detenido", text_color="#DC3545")
            self.tracking_activo.set(False)
            self.log_processing_message("Proceso de tracking detenido")
            self.update_system_info()
            
    def stop_both(self):
        """Detiene ambos procesos"""
        self.stop_conteo()
        self.stop_tracking()
        self.update_system_info("Ambos procesos detenidos")
        
    def update_system_info(self, message=None):
        """Actualiza el widget de información del sistema"""
        if message:
            self.system_info.configure(text=message)
        else:
            conteo_status = "activo" if self.conteo_activo.get() else "detenido"
            tracking_status = "activo" if self.tracking_activo.get() else "detenido"
            self.system_info.configure(text=f"Conteo: {conteo_status} | Tracking: {tracking_status}")

def main():
    root = ctk.CTk()
    app = NuevaFarmaciaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()