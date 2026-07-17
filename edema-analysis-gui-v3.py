import sys
import os
import glob
import csv
import random
from datetime import datetime
from pathlib import Path
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QSlider, QTabWidget,
                             QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
                             QSpinBox, QGroupBox, QMessageBox, QComboBox, QCheckBox,
                             QScrollArea, QTextBrowser)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Importar tus funciones
from filters_functions import gray_clustering, remove_spots, area_ratio
from fit_functions import apply_kmeans_clustering, fit_contours, compute_acf_metrics
from acf_method_optimized import calcule_2D_ACF, select_best_cluster, preprocessing_file
from PyQt5.QtGui import QIcon


class CalibrationThread(QThread):
    """Thread para procesar filtros de calibración sin bloquear la GUI"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, img_path, filter_params):
        super().__init__()
        self.img_path = img_path
        self.filter_params = filter_params

    def run(self):
        try:
            n = 1024
            # Cargar imagen original
            image = cv2.imread(self.img_path)

            if image.shape != (1024, 1024, 3):
                if image.shape == (2048, 2448, 3):
                    image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
                cx, cy = image.shape[0] // 2, image.shape[1] // 2
                image = image[cx - n // 2: cx + n // 2, cy - n // 2: cy + n // 2]

            # Preprocesamiento con parámetros del usuario
            n_clusters = 3  # Fijo en 3
            sigma = self.filter_params['blur_sigma']
            kernel_size = self.filter_params['kernel_size']

            # Aplicar filtrado personalizado
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size),
                                       sigmaX=sigma, sigmaY=sigma)

            # Clustering
            img_reshaped = blurred.reshape(-1, 1)
            from sklearn.mixture import GaussianMixture as GMM
            gmm = GMM(n_components=n_clusters, covariance_type='tied', random_state=1).fit(img_reshaped)
            labels = gmm.predict(img_reshaped)
            centers = np.uint8(gmm.means_)
            clustered = centers[labels].reshape(gray.shape)

            # Remover spots
            img_filtered = remove_spots(clustered, min_size=self.filter_params['min_spot_size'])

            # Calcular ratio
            ratio = area_ratio(img_filtered)

            # Emitir resultados
            self.finished.emit({
                'original': image,
                'blurred': blurred,
                'preprocessed_0': clustered,
                'preprocessed': img_filtered,
                'ratio': ratio
            })

        except Exception as e:
            self.error.emit(str(e))


class ImageProcessingThread(QThread):
    """Thread para procesar imágenes sin bloquear la GUI"""
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, images, filter_params):
        super().__init__()
        self.images = images
        self.filter_params = filter_params
        self.results = []

    def run(self):
        n = 1024
        total = len(self.images)

        for idx, img_path in enumerate(self.images):
            try:
                # Preprocesamiento
                img_filtered, filename, tissue_air_ratio = preprocessing_file(img_path, idx)

                # Calcular ACF
                apply_window = tissue_air_ratio > 5.0
                ACFm, levels = calcule_2D_ACF(img_filtered, apply_window)

                # Métricas
                fwhm_val = compute_acf_metrics(ACFm)
                cluster = select_best_cluster(fwhm_val, tissue_air_ratio)
                level = levels[cluster]

                # Ajuste de contornos
                sx_i, sy_i, angle = fit_contours(ACFm, n, filename, level)

                # Correcciones
                if sy_i / sx_i > 2 and (sy_i >= n or sx_i > n // 4) or sy_i / sx_i > 3.9 and sy_i > n // 4:
                    sy_i = sx_i
                if sy_i / sx_i > 3.0 and sy_i < n // 4:
                    sx_i = sy_i

                sxy = (sx_i + sy_i) / 2
                notes = ["Highly Instilled", "Instilled", "Medium", "Control"]
                note = notes[cluster - 1]

                result = {
                    'filename': filename,
                    'sxy': round(sxy, 2),
                    'tissue_air_ratio': round(tissue_air_ratio, 2),
                    'fwhm': round(fwhm_val, 2),
                    'cluster': cluster,
                    'note': note,
                    'has_edema': cluster <= 2  # Highly Instilled o Instilled
                }

                self.results.append(result)
                self.result.emit(result)

            except Exception as e:
                print(f"Error procesando {img_path}: {e}")

            self.progress.emit(int((idx + 1) / total * 100))

        self.finished.emit()


class FilterWidget(QWidget):
    """Widget para controlar filtros con sliders"""
    filterChanged = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.emit_filter_params)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Instrucciones
        instructions = QLabel(
            "<b>Instrucciones de Calibración:</b><br>"
            "Ajuste los parámetros observando las 10 imágenes de calibración.<br>"
            "El sistema guardará el valor promedio óptimo de cada parámetro."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(instructions)

        # Parámetros de filtrado (SIN k-means clusters)
        self.sliders = {}
        filters = [
            ('Desenfoque Gaussiano (sigma)', 'blur_sigma', 1, 30, 9),
            ('Tamaño kernel Gaussian (impar)', 'kernel_size', 3, 31, 9),
            ('Tamaño mínimo spots (px²)', 'min_spot_size', 100, 2000, 900),
        ]

        for label, key, min_val, max_val, default in filters:
            group = QGroupBox(label)
            group_layout = QHBoxLayout()

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(default)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval((max_val - min_val) // 10)

            # Ajuste especial para kernel_size (debe ser impar)
            if key == 'kernel_size':
                slider.valueChanged.connect(self.ensure_odd_kernel)

            value_label = QLabel(str(default))
            value_label.setMinimumWidth(60)
            value_label.setStyleSheet("font-size: 14px; font-weight: bold;")

            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
            slider.valueChanged.connect(self.schedule_update)

            group_layout.addWidget(slider)
            group_layout.addWidget(value_label)
            group.setLayout(group_layout)

            layout.addWidget(group)
            self.sliders[key] = slider

        # Info sobre k-means fijo
        kmeans_info = QLabel("🔒 K-means clusters: <b>3</b> (valor fijo óptimo)")
        kmeans_info.setStyleSheet("background-color: #fff3cd; padding: 8px; border-radius: 5px;")
        layout.addWidget(kmeans_info)

        layout.addStretch()
        self.setLayout(layout)

    def ensure_odd_kernel(self, value):
        """Asegurar que kernel_size sea impar"""
        if value % 2 == 0:
            self.sliders['kernel_size'].setValue(value + 1)

    def schedule_update(self):
        """Programar actualización con delay para evitar múltiples calls"""
        self.update_timer.start(300)  # 300ms delay

    def emit_filter_params(self):
        params = {key: slider.value() for key, slider in self.sliders.items()}
        params['n_clusters'] = 3  # Siempre fijo en 3
        self.filterChanged.emit(params)

    def get_params(self):
        params = {key: slider.value() for key, slider in self.sliders.items()}
        params['n_clusters'] = 3  # Siempre fijo en 3
        return params


class ImageViewer(QWidget):
    """Widget para mostrar imágenes con matplotlib - TAMAÑO AUMENTADO"""

    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Figura más grande: de (4,4) a (6,6)
        self.figure = Figure(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def show_image(self, img, title=None, cmap='gray'):
        self.ax.clear()
        if img is not None:
            if len(img.shape) == 3 and img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.ax.imshow(img, cmap=cmap, interpolation='none')
            if title:
                self.ax.set_title(title, fontsize=11)
            self.ax.axis('off')
        self.figure.tight_layout()
        self.canvas.draw()


class EdemaAnalysisGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.calibration_images = []
        self.current_calibration_idx = 0
        self.filter_params = {}
        self.processing_results = []
        self.calibration_thread = None
        self.is_processing_calibration = False

        # NUEVO: Almacenar parámetros óptimos de cada imagen de calibración
        self.calibration_params_history = []

        # NUEVO: Cache de datos procesados para análisis de elipse (evita reprocesar)
        self.cached_ellipse_data = None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sistema de Análisis de Edema Pulmonar - Método ACF")
        self.setGeometry(50, 50, 1800, 1000)

        icon_path = os.path.join(os.path.dirname(__file__), "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Carga de imágenes
        self.tab_load = self.create_load_tab()
        self.tabs.addTab(self.tab_load, "1. Carga de Imágenes")

        # Tab 2: Calibración y filtros
        self.tab_calibration = self.create_calibration_tab()
        self.tabs.addTab(self.tab_calibration, "2. Calibración de Filtros")

        # Tab 3: Procesamiento
        self.tab_processing = self.create_processing_tab()
        self.tabs.addTab(self.tab_processing, "3. Procesamiento Dataset")

        # Tab 4: Resultados
        self.tab_results = self.create_results_tab()
        self.tabs.addTab(self.tab_results, "4. Resultados")

        # Botón de ayuda en la parte inferior
        help_layout = QHBoxLayout()
        help_layout.addStretch()

        self.btn_help = QPushButton("📖 Guía de Usuario")
        self.btn_help.setMinimumHeight(40)
        self.btn_help.setMinimumWidth(200)
        self.btn_help.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_help.clicked.connect(self.show_user_guide)
        help_layout.addWidget(self.btn_help)

        help_layout.addStretch()
        main_layout.addLayout(help_layout)
        self.tabs.addTab(self.tab_results, "4. Resultados y Exportación")

        self.show()

    def create_load_tab(self):
        """Tab para cargar imágenes"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Instrucciones
        instructions = QLabel(
            "<h2>Bienvenido al Sistema de Análisis de Edema Pulmonar</h2>"
            "<p>Este sistema analiza imágenes histológicas pulmonares usando el método ACF (Autocorrelation Function).</p>"
            "<p><b>Instrucciones:</b></p>"
            "<ul>"
            "<li>Seleccione las imágenes TIFF RGB de su estudio (1024x1024 píxeles recomendado)</li>"
            "<li>El sistema seleccionará <b>10 imágenes aleatorias</b> para calibración</li>"
            "<li>Ajuste los parámetros en cada imagen y el sistema <b>promediará los valores óptimos</b></li>"
            "<li>Procese todo el dataset con los parámetros calibrados</li>"
            "</ul>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Botones de carga
        btn_layout = QHBoxLayout()

        self.btn_load_folder = QPushButton("📁 Cargar Carpeta de Imágenes")
        self.btn_load_folder.setMinimumHeight(50)
        self.btn_load_folder.clicked.connect(self.load_folder)

        self.btn_load_files = QPushButton("📄 Seleccionar Archivos Individuales")
        self.btn_load_files.setMinimumHeight(50)
        self.btn_load_files.clicked.connect(self.load_files)

        btn_layout.addWidget(self.btn_load_folder)
        btn_layout.addWidget(self.btn_load_files)
        layout.addLayout(btn_layout)

        # Info de imágenes cargadas
        self.label_images_info = QLabel("No hay imágenes cargadas")
        self.label_images_info.setStyleSheet("font-size: 14px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.label_images_info)

        # Lista de imágenes
        self.image_list_widget = QTableWidget()
        self.image_list_widget.setColumnCount(3)
        self.image_list_widget.setHorizontalHeaderLabels(["Archivo", "Ruta", "Calibración"])
        self.image_list_widget.setColumnWidth(0, 300)
        self.image_list_widget.setColumnWidth(1, 500)
        layout.addWidget(self.image_list_widget)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_calibration_tab(self):
        """Tab para calibración con visualización de filtros - IMÁGENES MÁS GRANDES"""
        tab = QWidget()
        main_layout = QHBoxLayout()

        # Panel izquierdo: controles (más estrecho)
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Selector de imagen de calibración
        calib_group = QGroupBox("Navegación de Calibración")
        calib_control = QVBoxLayout()

        nav_layout = QHBoxLayout()
        self.btn_prev_calib = QPushButton("◀ Anterior")
        self.btn_prev_calib.clicked.connect(self.prev_calibration_image)

        self.label_calib_idx = QLabel("0 / 0")
        self.label_calib_idx.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.label_calib_idx.setAlignment(Qt.AlignCenter)

        self.btn_next_calib = QPushButton("Siguiente ▶")
        self.btn_next_calib.clicked.connect(self.next_calibration_image)

        nav_layout.addWidget(self.btn_prev_calib)
        nav_layout.addWidget(self.label_calib_idx)
        nav_layout.addWidget(self.btn_next_calib)
        calib_control.addLayout(nav_layout)

        # Estado de procesamiento
        self.label_calib_status = QLabel("Listo")
        self.label_calib_status.setStyleSheet("padding: 8px; background-color: #e0ffe0; font-size: 12px;")
        self.label_calib_status.setAlignment(Qt.AlignCenter)
        calib_control.addWidget(self.label_calib_status)

        # NUEVO: Mostrar ratio actual
        self.label_current_ratio = QLabel("Ratio tejido/aire: -")
        self.label_current_ratio.setStyleSheet("padding: 5px; background-color: #f0f0f0; font-size: 11px;")
        self.label_current_ratio.setAlignment(Qt.AlignCenter)
        calib_control.addWidget(self.label_current_ratio)

        calib_group.setLayout(calib_control)
        left_layout.addWidget(calib_group)

        # Filtros
        self.filter_widget = FilterWidget()
        self.filter_widget.filterChanged.connect(self.on_filter_changed)
        left_layout.addWidget(self.filter_widget)

        # NUEVO: Botón para guardar parámetros de esta imagen
        self.btn_save_params = QPushButton("✓ Guardar Parámetros de Esta Imagen")
        self.btn_save_params.setMinimumHeight(45)
        self.btn_save_params.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_save_params.clicked.connect(self.save_current_calibration_params)
        left_layout.addWidget(self.btn_save_params)

        # NUEVO: Mostrar parámetros promedio
        self.label_avg_params = QLabel("<b>Parámetros Promedio:</b><br>Ajuste al menos 1 imagen")
        self.label_avg_params.setWordWrap(True)
        self.label_avg_params.setStyleSheet("background-color: #fff9c4; padding: 10px; border-radius: 5px;")
        left_layout.addWidget(self.label_avg_params)

        # Botón aplicar manual
        self.btn_apply_filters = QPushButton("🔄 Refrescar Vista")
        self.btn_apply_filters.setMinimumHeight(35)
        self.btn_apply_filters.clicked.connect(self.apply_calibration_filters)
        left_layout.addWidget(self.btn_apply_filters)

        # NUEVO: Botón para ver elipse (opción avanzada)
        self.btn_show_ellipse = QPushButton("🔬 Ver Análisis de Elipse (avanzado)")
        self.btn_show_ellipse.setMinimumHeight(40)
        self.btn_show_ellipse.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold;")
        self.btn_show_ellipse.setToolTip(
            "Muestra ventana con análisis completo: ACF, elipse ajustada, imagen con escala e información")
        self.btn_show_ellipse.clicked.connect(self.show_ellipse_analysis)
        left_layout.addWidget(self.btn_show_ellipse)

        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(420)
        main_layout.addWidget(left_panel)

        # Panel derecho: visualización 2x2 (MÁS GRANDE)
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Grid 2x2 de imágenes
        grid_top = QHBoxLayout()
        self.viewer_original = ImageViewer("Original")
        self.viewer_blurred = ImageViewer("Gaussian Blur")
        grid_top.addWidget(self.viewer_original)
        grid_top.addWidget(self.viewer_blurred)

        grid_bottom = QHBoxLayout()
        self.viewer_preprocessed = ImageViewer("K-means Clustering")
        self.viewer_final = ImageViewer("Spots Removed")
        grid_bottom.addWidget(self.viewer_preprocessed)
        grid_bottom.addWidget(self.viewer_final)

        right_layout.addLayout(grid_top)
        right_layout.addLayout(grid_bottom)
        right_panel.setLayout(right_layout)

        main_layout.addWidget(right_panel)

        tab.setLayout(main_layout)
        return tab

    def create_processing_tab(self):
        """Tab para procesar todo el dataset"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Información
        info = QLabel(
            "<h3>Procesamiento del Dataset Completo</h3>"
            "<p>Una vez calibrados los parámetros, procese todas las imágenes del dataset.</p>"
            "<p>El sistema aplicará el método ACF con los <b>parámetros promedio calibrados</b> y clasificará cada imagen.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Opciones de procesamiento
        options_group = QGroupBox("Opciones de Procesamiento")
        options_layout = QVBoxLayout()

        self.checkbox_save_results = QCheckBox("Guardar resultados en archivo CSV")
        self.checkbox_save_results.setChecked(True)

        self.checkbox_parallel = QCheckBox("Procesamiento paralelo (más rápido)")
        self.checkbox_parallel.setChecked(True)

        options_layout.addWidget(self.checkbox_save_results)
        options_layout.addWidget(self.checkbox_parallel)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Botón de procesamiento
        self.btn_process = QPushButton("▶ Iniciar Procesamiento")
        self.btn_process.setMinimumHeight(60)
        self.btn_process.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.btn_process.clicked.connect(self.process_dataset)
        layout.addWidget(self.btn_process)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; }")
        layout.addWidget(self.progress_bar)

        self.label_progress = QLabel("Esperando inicio...")
        self.label_progress.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_progress)

        # Resumen en tiempo real
        self.processing_summary = QLabel("")
        self.processing_summary.setStyleSheet("font-size: 12px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(self.processing_summary)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_results_tab(self):
        """Tab para visualización y exportación de resultados"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Resumen estadístico
        self.label_summary = QLabel("<h3>Resumen de Resultados</h3><p>Procese las imágenes primero</p>")
        layout.addWidget(self.label_summary)

        # Tabla de resultados
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Archivo", "sXY", "Ratio Tejido/Aire", "FWHM", "Clasificación", "Edema Detectado"
        ])
        self.results_table.setColumnWidth(0, 300)
        layout.addWidget(self.results_table)

        # Botones de exportación
        export_layout = QHBoxLayout()

        self.btn_export_csv = QPushButton("📊 Exportar CSV Completo")
        self.btn_export_csv.setMinimumHeight(40)
        self.btn_export_csv.clicked.connect(self.export_csv)

        self.btn_export_summary = QPushButton("📈 Exportar Resumen Estadístico")
        self.btn_export_summary.setMinimumHeight(40)
        self.btn_export_summary.clicked.connect(self.export_summary)

        export_layout.addWidget(self.btn_export_csv)
        export_layout.addWidget(self.btn_export_summary)
        layout.addLayout(export_layout)

        tab.setLayout(layout)
        return tab

    # Métodos de funcionalidad

    def load_folder(self):
        """Cargar todas las imágenes de una carpeta"""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder:
            tif_files = glob.glob(os.path.join(folder, "*.tif")) + glob.glob(os.path.join(folder, "*.tiff"))
            if tif_files:
                self.image_paths = sorted(tif_files)
                self.update_image_list()
                self.setup_calibration()
            else:
                QMessageBox.warning(self, "Advertencia", "No se encontraron archivos TIFF en la carpeta seleccionada")

    def load_files(self):
        """Cargar archivos individuales"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Imágenes", "", "Imágenes TIFF (*.tif *.tiff)"
        )
        if files:
            self.image_paths = sorted(files)
            self.update_image_list()
            self.setup_calibration()

    def update_image_list(self):
        """Actualizar la lista de imágenes en la UI"""
        self.image_list_widget.setRowCount(len(self.image_paths))
        for idx, path in enumerate(self.image_paths):
            self.image_list_widget.setItem(idx, 0, QTableWidgetItem(os.path.basename(path)))
            self.image_list_widget.setItem(idx, 1, QTableWidgetItem(path))
            calib = "Sí" if idx < 10 else "No"
            self.image_list_widget.setItem(idx, 2, QTableWidgetItem(calib))

        self.label_images_info.setText(
            f"✅ {len(self.image_paths)} imágenes cargadas | "
            f"{min(10, len(self.image_paths))} seleccionadas para calibración"
        )

    def setup_calibration(self):
        """Configurar imágenes de calibración - ALEATORIAS"""
        num_calib = min(10, len(self.image_paths))

        # Seleccionar 10 imágenes ALEATORIAS
        self.calibration_images = random.sample(self.image_paths, num_calib)

        self.current_calibration_idx = 0
        self.calibration_params_history = []  # Resetear historial

        self.label_calib_idx.setText(f"{self.current_calibration_idx + 1} / {len(self.calibration_images)}")
        self.update_avg_params_display()

        self.tabs.setCurrentIndex(1)  # Cambiar a tab de calibración

        QMessageBox.information(
            self,
            "Calibración",
            f"Se seleccionaron {num_calib} imágenes ALEATORIAS para calibración.\n\n"
            "Ajuste los parámetros para cada imagen y presione 'Guardar Parámetros'.\n"
            "El sistema promediará los valores para usar en todo el dataset."
        )

        self.apply_calibration_filters()

    def prev_calibration_image(self):
        if self.current_calibration_idx > 0:
            self.current_calibration_idx -= 1
            self.label_calib_idx.setText(f"{self.current_calibration_idx + 1} / {len(self.calibration_images)}")
            self.cached_ellipse_data = None  # Invalidar cache
            self.apply_calibration_filters()

    def next_calibration_image(self):
        if self.current_calibration_idx < len(self.calibration_images) - 1:
            self.current_calibration_idx += 1
            self.label_calib_idx.setText(f"{self.current_calibration_idx + 1} / {len(self.calibration_images)}")
            self.cached_ellipse_data = None  # Invalidar cache
            self.apply_calibration_filters()

    def on_filter_changed(self, params):
        """Callback cuando cambian los filtros (con debounce)"""
        self.filter_params = params
        self.cached_ellipse_data = None  # Invalidar cache cuando cambian filtros
        self.apply_calibration_filters()

    def save_current_calibration_params(self):
        """NUEVO: Guardar los parámetros actuales para esta imagen"""
        current_params = self.filter_widget.get_params().copy()
        img_name = os.path.basename(self.calibration_images[self.current_calibration_idx])

        # Agregar al historial
        self.calibration_params_history.append({
            'image': img_name,
            'params': current_params
        })

        QMessageBox.information(
            self,
            "Parámetros Guardados",
            f"Parámetros guardados para: {img_name}\n\n"
            f"Total de imágenes calibradas: {len(self.calibration_params_history)}/10"
        )

        # Actualizar display de parámetros promedio
        self.update_avg_params_display()

        # Avanzar a siguiente imagen automáticamente si no es la última
        if self.current_calibration_idx < len(self.calibration_images) - 1:
            self.next_calibration_image()

    def update_avg_params_display(self):
        """NUEVO: Actualizar display de parámetros promedio"""
        if not self.calibration_params_history:
            self.label_avg_params.setText(
                "<b>Parámetros Promedio:</b><br>"
                "Ajuste y guarde al menos 1 imagen"
            )
            return

        # Calcular promedios
        avg_sigma = np.mean([p['params']['blur_sigma'] for p in self.calibration_params_history])
        avg_kernel = int(np.mean([p['params']['kernel_size'] for p in self.calibration_params_history]))
        # Asegurar que sea impar
        if avg_kernel % 2 == 0:
            avg_kernel += 1
        avg_spot_size = int(np.mean([p['params']['min_spot_size'] for p in self.calibration_params_history]))

        self.label_avg_params.setText(
            f"<b>Parámetros Promedio ({len(self.calibration_params_history)} imágenes):</b><br>"
            f"• Sigma Gaussiano: <b>{avg_sigma:.1f}</b><br>"
            f"• Kernel Size: <b>{avg_kernel}</b><br>"
            f"• Tamaño min spots: <b>{avg_spot_size}</b><br>"
            f"• K-means clusters: <b>3</b> (fijo)"
        )

    def get_averaged_calibration_params(self):
        """NUEVO: Obtener parámetros promediados de todas las calibraciones"""
        if not self.calibration_params_history:
            QMessageBox.warning(
                self,
                "Advertencia",
                "No hay parámetros de calibración guardados.\n"
                "Por favor calibre al menos una imagen."
            )
            return None

        avg_sigma = np.mean([p['params']['blur_sigma'] for p in self.calibration_params_history])
        avg_kernel = int(np.mean([p['params']['kernel_size'] for p in self.calibration_params_history]))
        if avg_kernel % 2 == 0:
            avg_kernel += 1
        avg_spot_size = int(np.mean([p['params']['min_spot_size'] for p in self.calibration_params_history]))

        return {
            'blur_sigma': avg_sigma,
            'kernel_size': avg_kernel,
            'min_spot_size': avg_spot_size,
            'n_clusters': 3,
            'apply_hann': False
        }

    def apply_calibration_filters(self):
        """Aplicar filtros en thread separado"""
        if not self.calibration_images or self.is_processing_calibration:
            return

        # Cancelar thread anterior si existe
        if self.calibration_thread and self.calibration_thread.isRunning():
            self.calibration_thread.terminate()
            self.calibration_thread.wait()

        img_path = self.calibration_images[self.current_calibration_idx]
        self.filter_params = self.filter_widget.get_params()

        self.is_processing_calibration = True
        self.label_calib_status.setText("Procesando...")
        self.label_calib_status.setStyleSheet("padding: 8px; background-color: #ffffcc; font-size: 12px;")

        # Crear y ejecutar thread
        self.calibration_thread = CalibrationThread(img_path, self.filter_params)
        self.calibration_thread.finished.connect(self.on_calibration_finished)
        self.calibration_thread.error.connect(self.on_calibration_error)
        self.calibration_thread.start()

    def on_calibration_finished(self, results):
        """Actualizar UI con resultados de calibración"""
        self.is_processing_calibration = False
        self.label_calib_status.setText("Listo ✓")
        self.label_calib_status.setStyleSheet("padding: 8px; background-color: #e0ffe0; font-size: 12px;")

        # Actualizar ratio
        self.label_current_ratio.setText(f"Ratio tejido/aire: {results['ratio']}")

        # Mostrar resultados
        self.viewer_original.show_image(results['original'], "Original", cmap=None)
        self.viewer_blurred.show_image(results['blurred'], "Gaussian Filtered")
        self.viewer_preprocessed.show_image(results['preprocessed_0'], "K-means Clustering")
        self.viewer_final.show_image(results['preprocessed'], "Spots Removed")

        # NUEVO: Calcular y cachear datos de ACF en segundo plano para análisis rápido de elipse
        self.calculate_ellipse_data_async()

    def on_calibration_error(self, error_msg):
        """Manejar errores de calibración"""
        self.is_processing_calibration = False
        self.label_calib_status.setText(f"Error: {error_msg}")
        self.label_calib_status.setStyleSheet("padding: 8px; background-color: #ffcccc; font-size: 12px;")
        QMessageBox.critical(self, "Error", f"Error al procesar imagen:\n{error_msg}")

    def calculate_ellipse_data_async(self):
        """Calcular datos de ACF en segundo plano para análisis rápido"""
        try:
            img_path = self.calibration_images[self.current_calibration_idx]
            n = 1024

            # Cargar imagen
            image = cv2.imread(img_path)
            if image.shape != (1024, 1024, 3):
                if image.shape == (2048, 2448, 3):
                    image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
                cx, cy = image.shape[0] // 2, image.shape[1] // 2
                image = image[cx - n // 2: cx + n // 2, cy - n // 2: cy + n // 2]

            # Preprocesamiento
            img_filtered, filename, tissue_air_ratio = preprocessing_file(img_path, 0)

            # Calcular ACF
            apply_window = tissue_air_ratio > 5.0
            ACFm, levels = calcule_2D_ACF(img_filtered, apply_window)

            # Métricas
            fwhm_val = compute_acf_metrics(ACFm)
            cluster = select_best_cluster(fwhm_val, tissue_air_ratio)

            if cluster < 1 or cluster > len(levels):
                cluster = min(max(1, cluster), len(levels))

            level = levels[cluster]

            # Ajuste de contornos
            sx_i, sy_i, angle = fit_contours(ACFm, n, filename, level)

            if sx_i <= 0 or sy_i <= 0:
                return

            # Correcciones
            if sy_i / sx_i > 2 and (sy_i >= n or sx_i > n // 4) or sy_i / sx_i > 3.9 and sy_i > n // 4:
                sy_i = sx_i
            if sy_i / sx_i > 3.0 and sy_i < n // 4:
                sx_i = sy_i

            # Cachear datos
            self.cached_ellipse_data = {
                'image': image,
                'img_filtered': img_filtered,
                'filename': filename,
                'tissue_air_ratio': tissue_air_ratio,
                'ACFm': ACFm,
                'levels': levels,
                'fwhm_val': fwhm_val,
                'cluster': cluster,
                'level': level,
                'sx_i': sx_i,
                'sy_i': sy_i,
                'angle': angle,
                'n': n
            }
        except:
            self.cached_ellipse_data = None

    def show_ellipse_analysis(self):
        """Mostrar análisis avanzado con elipse del método ACF en ventana emergente"""
        if not self.calibration_images:
            return

        # Si no hay cache, calcular ahora
        if self.cached_ellipse_data is None:
            self.label_calib_status.setText("Calculando datos...")
            self.label_calib_status.setStyleSheet("padding: 8px; background-color: #ffffcc; font-size: 12px;")
            self.calculate_ellipse_data_async()

            if self.cached_ellipse_data is None:
                QMessageBox.warning(self, "Error", "No se pudo calcular el análisis de elipse")
                return

        try:
            from matplotlib.patches import Ellipse

            # Usar datos cacheados
            data = self.cached_ellipse_data
            image = data['image']
            img_filtered = data['img_filtered']
            filename = data['filename']
            tissue_air_ratio = data['tissue_air_ratio']
            ACFm = data['ACFm']
            levels = data['levels']
            fwhm_val = data['fwhm_val']
            cluster = data['cluster']
            level = data['level']
            sx_i = data['sx_i']
            sy_i = data['sy_i']
            angle = data['angle']
            n = data['n']

            # Crear figura para mostrar ACF con elipse (ventana emergente)
            fig = plt.figure(figsize=(22, 6))  # Más ancho y alto
            fig.suptitle(f'Análisis de Elipse ACF - {filename}', fontsize=15, fontweight='bold', y=0.98)

            # Panel 1: ACF con contornos
            ax1 = plt.subplot(1, 4, 1)
            im1 = ax1.imshow(ACFm, cmap='jet', origin='lower', extent=[0, n, 0, n])
            plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
            try:
                contour = ax1.contour(ACFm, levels=[level], colors='cyan', linewidths=2,
                                      extent=[0, n, 0, n])
            except:
                pass
            ax1.set_title(f'ACF con contorno\n(cluster {cluster})', fontsize=11, fontweight='bold')
            ax1.set_xlabel('Píxeles', fontsize=10)
            ax1.set_ylabel('Píxeles', fontsize=10)
            ax1.grid(True, alpha=0.3, linestyle='--')

            # Panel 2: Elipse ajustada
            ax2 = plt.subplot(1, 4, 2)
            im2 = ax2.imshow(ACFm, cmap='jet', origin='lower', extent=[0, n, 0, n])
            plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)

            # Crear y agregar elipse
            try:
                ellipse = Ellipse(xy=(n / 2, n / 2),
                                  width=2 * sx_i,
                                  height=2 * sy_i,
                                  angle=angle,
                                  edgecolor='lime',
                                  facecolor='none',
                                  linewidth=3,
                                  linestyle='-',
                                  label='Elipse ajustada')
                ax2.add_patch(ellipse)
            except Exception as e:
                print(f"Error al crear elipse: {e}")

            # Agregar líneas de ejes
            try:
                # Convertir ángulo a radianes
                angle_rad = np.deg2rad(angle)

                # Eje mayor (en dirección del ángulo)
                x_major = [n / 2, n / 2 + sx_i * np.cos(angle_rad)]
                y_major = [n / 2, n / 2 + sx_i * np.sin(angle_rad)]
                ax2.plot(x_major, y_major, 'c-', linewidth=3,
                         label=f'sX (width septum): {sx_i:.1f}px', marker='o', markersize=8)

                # Eje menor (perpendicular al mayor)
                x_minor = [n / 2, n / 2 - sy_i * np.sin(angle_rad)]
                y_minor = [n / 2, n / 2 + sy_i * np.cos(angle_rad)]
                ax2.plot(x_minor, y_minor, 'm-', linewidth=3,
                         label=f'sY (width septum): {sy_i:.1f}px', marker='s', markersize=8)

                # Centro
                ax2.plot(n / 2, n / 2, 'yo', markersize=10, label='Centro')
            except Exception as e:
                print(f"Error al dibujar ejes: {e}")

            ax2.set_title(f'Elipse ajustada\nsXY: {(sx_i + sy_i) / 2:.1f}px',
                          fontsize=11, fontweight='bold')
            ax2.set_xlabel('Píxeles', fontsize=10)
            ax2.set_ylabel('Píxeles', fontsize=10)
            ax2.legend(loc='upper right', fontsize=9, framealpha=0.95)
            ax2.grid(True, alpha=0.3, linestyle='--')

            # Zoom en la región de interés
            zoom_size = min(200, n // 3)
            ax2.set_xlim(n / 2 - zoom_size, n / 2 + zoom_size)
            ax2.set_ylim(n / 2 - zoom_size, n / 2 + zoom_size)

            # Panel 3: Imagen original con barra de escala
            ax3 = plt.subplot(1, 4, 3)

            # Convertir imagen de BGR a RGB para matplotlib
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            ax3.imshow(image_rgb, extent=[0, n, 0, n])
            ax3.set_title('Imagen original\ncon barra de escala', fontsize=11, fontweight='bold')
            ax3.set_xlabel('Píxeles', fontsize=10)
            ax3.set_ylabel('Píxeles', fontsize=10)

            # Calcular sXY
            sxy = (sx_i + sy_i) / 2

            # Agregar barra de escala (abajo a la derecha)
            bar_length = sxy  # Longitud de la barra = width del septum
            bar_x_start = n - bar_length - 50  # 50 px del borde derecho
            bar_x_end = n - 50
            bar_y = 50  # 50 px del borde inferior
            bar_thickness = 5  # Grosor de la barra

            # Dibujar la barra de escala
            ax3.plot([bar_x_start, bar_x_end], [bar_y, bar_y],
                     'yellow', linewidth=bar_thickness, solid_capstyle='butt')

            # Dibujar marcas en los extremos
            ax3.plot([bar_x_start, bar_x_start], [bar_y - 15, bar_y + 15],
                     'yellow', linewidth=3)
            ax3.plot([bar_x_end, bar_x_end], [bar_y - 15, bar_y + 15],
                     'yellow', linewidth=3)

            # Texto con la medida
            ax3.text((bar_x_start + bar_x_end) / 2, bar_y - 35,
                     f'sXY = {sxy:.1f} px\n(width septum)',
                     color='yellow', fontsize=10, fontweight='bold',
                     ha='center', va='top',
                     bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.7))

            # Panel 4: Información textual
            ax4 = plt.subplot(1, 4, 4)
            ax4.axis('off')

            info_text = (
                f"PARÁMETROS DE AJUSTE\n"
                f"{'=' * 35}\n\n"
                f"Dimensiones de la elipse:\n"
                f"  • Eje mayor (sX):  {2 * sx_i:.2f} px\n"
                f"  • Eje menor (sY):  {2 * sy_i:.2f} px\n"
                f"  • Promedio (sXY): {(sx_i + sy_i) / 2:.2f} px\n"
                f"  • Semi-eje X:      {sx_i:.2f} px\n"
                f"  • Semi-eje Y:      {sy_i:.2f} px\n\n"
                f"Geometría:\n"
                f"  • Ángulo:          {angle:.2f}°\n"
                f"  • Ratio (sY/sX):   {sy_i / sx_i:.3f}\n"
                f"  • Excentricidad:   {np.sqrt(1 - (min(sx_i, sy_i) / max(sx_i, sy_i)) ** 2):.3f}\n\n"
                f"Clasificación:\n"
                f"  • Cluster:         {cluster}\n"
                f"  • FWHM:            {fwhm_val:.3f}\n"
                f"  • Ratio T/A:       {tissue_air_ratio:.2f}\n"
                f"  • Nivel contorno:  {level:.4f}\n\n"
                f"Interpretación:\n"
                f"  • Estado:          "
            )

            # Añadir clasificación según cluster
            notes = ["Highly Instilled", "Instilled", "Medium", "Control"]
            note = notes[cluster - 1] if 1 <= cluster <= 4 else "Unknown"
            has_edema = cluster <= 2

            info_text += f"{note}\n"
            info_text += f"  • Edema:           {'SÍ' if has_edema else 'NO'}\n"

            ax4.text(0.05, 0.95, info_text,
                     transform=ax4.transAxes,
                     fontsize=10,
                     verticalalignment='top',
                     fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            # Ajustar espaciado para aprovechar mejor el espacio
            plt.tight_layout(rect=[0, 0, 1, 0.96], pad=1.5, w_pad=2.0, h_pad=1.5)

            # Mostrar la figura en una ventana emergente (sin bloquear)
            plt.show(block=False)

            self.label_calib_status.setText(f"✓ Vista elipse - sXY: {(sx_i + sy_i) / 2:.1f}px")
            self.label_calib_status.setStyleSheet("padding: 8px; background-color: #c8e6c9; font-size: 12px;")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print("Error detallado en show_ellipse_analysis:")
            print(error_detail)

            self.label_calib_status.setText("Error al generar elipse")
            self.label_calib_status.setStyleSheet("padding: 8px; background-color: #ffcccc; font-size: 12px;")

            QMessageBox.warning(self, "Error",
                                f"Error al generar vista de elipse:\n\n{str(e)}\n\n"
                                f"Revisa la consola para más detalles.")

    def process_dataset(self):
        """Procesar todo el dataset"""
        if not self.image_paths:
            QMessageBox.warning(self, "Advertencia", "No hay imágenes cargadas")
            return

        # Obtener parámetros promediados
        avg_params = self.get_averaged_calibration_params()
        if avg_params is None:
            return

        # Confirmar con el usuario
        reply = QMessageBox.question(
            self,
            "Confirmar Procesamiento",
            f"Se procesarán {len(self.image_paths)} imágenes con los siguientes parámetros:\n\n"
            f"• Sigma Gaussiano: {avg_params['blur_sigma']:.1f}\n"
            f"• Kernel Size: {avg_params['kernel_size']}\n"
            f"• Tamaño min spots: {avg_params['min_spot_size']}\n"
            f"• K-means clusters: 3\n\n"
            f"¿Desea continuar?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        self.btn_process.setEnabled(False)
        self.processing_results = []
        self.progress_bar.setValue(0)

        # Crear thread de procesamiento con parámetros promediados
        self.processing_thread = ImageProcessingThread(self.image_paths, avg_params)
        self.processing_thread.progress.connect(self.update_progress)
        self.processing_thread.result.connect(self.add_result)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        self.label_progress.setText(f"Procesando... {value}% completado")

    def add_result(self, result):
        self.processing_results.append(result)
        edemas = sum(1 for r in self.processing_results if r['has_edema'])
        total = len(self.processing_results)
        self.processing_summary.setText(
            f"Procesadas: {total} | Edema detectado: {edemas} ({edemas / total * 100:.1f}%)"
        )

    def processing_finished(self):
        self.btn_process.setEnabled(True)
        self.label_progress.setText("✅ Procesamiento completado")

        # Actualizar tabla de resultados
        self.update_results_table()

        # Guardar si está habilitado
        if self.checkbox_save_results.isChecked():
            self.auto_save_results()

        # Cambiar a tab de resultados
        self.tabs.setCurrentIndex(3)

        QMessageBox.information(self, "Completado",
                                f"Procesamiento finalizado.\n{len(self.processing_results)} imágenes analizadas.")

    def update_results_table(self):
        """Actualizar tabla con resultados"""
        self.results_table.setRowCount(len(self.processing_results))

        edema_count = 0
        for idx, result in enumerate(self.processing_results):
            self.results_table.setItem(idx, 0, QTableWidgetItem(result['filename']))
            self.results_table.setItem(idx, 1, QTableWidgetItem(str(result['sxy'])))
            self.results_table.setItem(idx, 2, QTableWidgetItem(str(result['tissue_air_ratio'])))
            self.results_table.setItem(idx, 3, QTableWidgetItem(str(result['fwhm'])))
            self.results_table.setItem(idx, 4, QTableWidgetItem(result['note']))

            edema_text = "SÍ" if result['has_edema'] else "NO"
            item = QTableWidgetItem(edema_text)
            if result['has_edema']:
                item.setBackground(Qt.red)
            else:
                item.setBackground(Qt.green)
            self.results_table.setItem(idx, 5, item)

            if result['has_edema']:
                edema_count += 1

        # Actualizar resumen
        total = len(self.processing_results)
        percent = (edema_count / total * 100) if total > 0 else 0

        self.label_summary.setText(
            f"<h3>Resumen de Resultados</h3>"
            f"<p><b>Total de imágenes:</b> {total}</p>"
            f"<p><b>Con edema detectado:</b> <span style='color: red;'>{edema_count} ({percent:.1f}%)</span></p>"
            f"<p><b>Sin edema:</b> <span style='color: green;'>{total - edema_count} ({100 - percent:.1f}%)</span></p>"
        )

    def auto_save_results(self):
        """Guardar resultados automáticamente"""
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
        filename = f"Resultados_Edema_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Imagen', 'sXY', 'Ratio Tejido/Aire', 'FWHM', 'Clasificación', 'Tiene Edema'])

            for result in self.processing_results:
                writer.writerow([
                    result['filename'],
                    result['sxy'],
                    result['tissue_air_ratio'],
                    result['fwhm'],
                    result['note'],
                    'Sí' if result['has_edema'] else 'No'
                ])

    def export_csv(self):
        """Exportar resultados a CSV"""
        if not self.processing_results:
            QMessageBox.warning(self, "Advertencia", "No hay resultados para exportar")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar Resultados", "", "CSV Files (*.csv)"
        )

        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Imagen', 'sXY', 'Ratio Tejido/Aire', 'FWHM', 'Clasificación', 'Tiene Edema'])

                for result in self.processing_results:
                    writer.writerow([
                        result['filename'],
                        result['sxy'],
                        result['tissue_air_ratio'],
                        result['fwhm'],
                        result['note'],
                        'Sí' if result['has_edema'] else 'No'
                    ])

            QMessageBox.information(self, "Éxito", f"Resultados exportados a:\n{filename}")

    def export_summary(self):
        """Exportar resumen estadístico"""
        if not self.processing_results:
            QMessageBox.warning(self, "Advertencia", "No hay resultados para exportar")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar Resumen", "", "CSV Files (*.csv)"
        )

        if filename:
            # Calcular estadísticas por grupos
            groups = {}
            for result in self.processing_results:
                note = result['note']
                if note not in groups:
                    groups[note] = {'sxy': [], 'ratio': [], 'fwhm': []}
                groups[note]['sxy'].append(result['sxy'])
                groups[note]['ratio'].append(result['tissue_air_ratio'])
                groups[note]['fwhm'].append(result['fwhm'])

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Clasificación', 'N muestras', 'sXY promedio',
                                 'sXY std', 'Ratio promedio', 'Ratio std', 'FWHM promedio', 'FWHM std'])

                for note, data in sorted(groups.items()):
                    writer.writerow([
                        note,
                        len(data['sxy']),
                        round(np.mean(data['sxy']), 2),
                        round(np.std(data['sxy']), 2),
                        round(np.mean(data['ratio']), 2),
                        round(np.std(data['ratio']), 2),
                        round(np.mean(data['fwhm']), 2),
                        round(np.std(data['fwhm']), 2)
                    ])

            QMessageBox.information(self, "Éxito", f"Resumen exportado a:\n{filename}")

    def show_user_guide(self):
        """Mostrar guía de usuario en ventana emergente"""
        # Crear ventana de diálogo
        guide_dialog = QWidget()
        guide_dialog.setWindowTitle("📖 Guía de Usuario - Sistema de Análisis de Edema Pulmonar")
        guide_dialog.setGeometry(100, 100, 1200, 800)

        layout = QVBoxLayout()

        # Área de scroll con el contenido de la guía
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Widget de contenido
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        # Leer el archivo de la guía
        guide_path = os.path.join(os.path.dirname(__file__), "GUIA_DE_USUARIO.md")

        try:
            # Si existe el archivo, leerlo
            if os.path.exists(guide_path):
                with open(guide_path, 'r', encoding='utf-8') as f:
                    guide_text = f.read()
            else:
                # Si no existe, usar texto embebido
                guide_text = self.get_embedded_guide()
        except:
            guide_text = self.get_embedded_guide()

        # Convertir markdown a HTML simple para mejor visualización
        html_content = self.markdown_to_html(guide_text)

        # Label con el contenido
        text_browser = QTextBrowser()
        text_browser.setHtml(html_content)
        text_browser.setOpenExternalLinks(False)

        content_layout.addWidget(text_browser)
        content_widget.setLayout(content_layout)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Botón de cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.setMinimumHeight(35)
        btn_close.clicked.connect(guide_dialog.close)
        layout.addWidget(btn_close)

        guide_dialog.setLayout(layout)
        guide_dialog.show()

        # Mantener referencia para que no se destruya
        self.guide_window = guide_dialog

    def markdown_to_html(self, md_text):
        """Convertir markdown básico a HTML"""
        import re

        html = "<html><head><style>"
        html += """
            body { 
                font-family: Arial, sans-serif; 
                line-height: 1.6; 
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1 { 
                color: #2c3e50; 
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                font-size: 28px;
            }
            h2 { 
                color: #34495e; 
                border-bottom: 2px solid #95a5a6;
                padding-bottom: 5px;
                margin-top: 30px;
                font-size: 22px;
            }
            h3 { 
                color: #16a085;
                margin-top: 20px;
                font-size: 18px;
            }
            h4 {
                color: #7f8c8d;
                font-size: 16px;
            }
            p { 
                margin: 10px 0;
                text-align: justify;
            }
            ul { 
                margin: 10px 0 10px 20px;
                list-style-type: disc;
            }
            ol { 
                margin: 10px 0 10px 20px;
            }
            li {
                margin: 5px 0;
            }
            code, pre { 
                background-color: #ecf0f1;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            pre {
                padding: 15px;
                overflow-x: auto;
                display: block;
                margin: 10px 0;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }
            th, td {
                border: 1px solid #bdc3c7;
                padding: 10px;
                text-align: left;
            }
            th {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            tr:nth-child(even) {
                background-color: #ecf0f1;
            }
            .warning {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 10px;
                margin: 15px 0;
            }
            .success {
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 10px;
                margin: 15px 0;
            }
            .info {
                background-color: #d1ecf1;
                border-left: 4px solid #17a2b8;
                padding: 10px;
                margin: 15px 0;
            }
            strong {
                font-weight: bold;
                color: #2c3e50;
            }
            em {
                font-style: italic;
            }
        """
        html += "</style></head><body>"

        lines = md_text.split('\n')
        in_code_block = False
        in_table = False
        in_list = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Código de bloque
            if line.startswith('```'):
                if in_code_block:
                    html += "</pre>"
                    in_code_block = False
                else:
                    html += "<pre>"
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                html += line.replace('<', '&lt;').replace('>', '&gt;') + "\n"
                i += 1
                continue

            # Headers
            if line.startswith('#### '):
                html += f"<h4>{self.process_inline_markdown(line[5:])}</h4>"
            elif line.startswith('### '):
                html += f"<h3>{self.process_inline_markdown(line[4:])}</h3>"
            elif line.startswith('## '):
                html += f"<h2>{self.process_inline_markdown(line[3:])}</h2>"
            elif line.startswith('# '):
                html += f"<h1>{self.process_inline_markdown(line[2:])}</h1>"
            # Separadores
            elif line.strip() == '---':
                html += "<hr>"
            # Listas desordenadas
            elif line.startswith('- ') or line.startswith('* '):
                if not in_list:
                    html += "<ul>"
                    in_list = True
                html += f"<li>{self.process_inline_markdown(line[2:])}</li>"
            # Listas ordenadas
            elif re.match(r'^\d+\.\s', line):
                if not in_list:
                    html += "<ol>"
                    in_list = True
                content = re.sub(r'^\d+\.\s', '', line)
                html += f"<li>{self.process_inline_markdown(content)}</li>"
            else:
                # Cerrar lista si estaba abierta
                if in_list:
                    html += "</ul>" if lines[i - 1].startswith(('-', '*')) else "</ol>"
                    in_list = False

                # Tablas
                if '|' in line and not line.strip().startswith('|---'):
                    if not in_table:
                        html += "<table>"
                        in_table = True
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    # Detectar si es header (tiene **texto**)
                    if any('**' in cell for cell in cells):
                        html += "<tr>" + "".join(
                            f"<th>{self.process_inline_markdown(cell)}</th>" for cell in cells) + "</tr>"
                    else:
                        html += "<tr>" + "".join(
                            f"<td>{self.process_inline_markdown(cell)}</td>" for cell in cells) + "</tr>"
                elif line.strip().startswith('|---'):
                    pass  # Ignorar separador de tabla
                else:
                    if in_table:
                        html += "</table>"
                        in_table = False

                    # Texto normal
                    if line.strip():
                        processed_line = self.process_inline_markdown(line)

                        # Detectar bloques especiales
                        if '⚠️' in processed_line or processed_line.strip().startswith('⚠️'):
                            html += f'<div class="warning">{processed_line}</div>'
                        elif '✅' in processed_line:
                            html += f'<div class="success">{processed_line}</div>'
                        elif '💡' in processed_line or '📌' in processed_line:
                            html += f'<div class="info">{processed_line}</div>'
                        else:
                            html += f"<p>{processed_line}</p>"
                    else:
                        html += "<br>"

            i += 1

        if in_list:
            html += "</ul>"
        if in_table:
            html += "</table>"

        html += "</body></html>"
        return html

    def process_inline_markdown(self, text):
        """Procesar markdown inline (negrita, cursiva, código, enlaces)"""
        import re

        # Código inline `texto`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # Negrita **texto** o __texto__
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

        # Cursiva *texto* o _texto_ (solo si no está dentro de strong)
        text = re.sub(r'(?<!\*)\*([^\*]+?)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<em>\1</em>', text)

        # Enlaces [texto](url) - opcional, en tu caso no hay URLs
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)

        # Checkboxes
        text = text.replace('☑️', '✅').replace('☐', '◻')

        return text

    def get_embedded_guide(self):
        """Guía embebida en caso de que no exista el archivo"""
        return """# 📘 GUÍA DE USUARIO
## Sistema de Análisis de Edema Pulmonar - Método ACF

---

## 🎯 Introducción

Este software analiza imágenes de microscopía de tejido pulmonar para detectar automáticamente la presencia de edema pulmonar.

## 🔄 Flujo de Trabajo

1. **Cargar Imágenes**: Selecciona tus archivos TIFF
2. **Calibrar**: Ajusta parámetros en 10 imágenes aleatorias
3. **Procesar**: Analiza todo el dataset automáticamente
4. **Resultados**: Revisa y exporta resultados en CSV

## 📁 Pestaña 1: Carga de Imágenes

- Click en "Cargar Carpeta" o "Seleccionar Archivos"
- Solo acepta archivos .tif o .tiff
- El programa selecciona 10 imágenes aleatorias para calibración

## ⚙️ Pestaña 2: Calibración

### Parámetros ajustables:
- **Desenfoque Gaussiano**: Reduce ruido (1-30)
- **Kernel Size**: Tamaño del filtro (3-31, impar)
- **Tamaño mínimo spots**: Elimina artefactos (100-2000 px²)

### Proceso:
1. Ajusta parámetros observando las 4 vistas
2. Click "Guardar Parámetros" cuando estés satisfecho
3. Navega entre las 10 imágenes con ◀ ▶
4. El programa promedia todos los parámetros guardados

## 🔬 Pestaña 3: Procesamiento

1. Verifica parámetros promedio
2. ☑️ Activa "Guardar automáticamente" (opcional)
3. Click "Procesar Dataset Completo"
4. Espera a que termine (1-2 seg/imagen)

## 📊 Pestaña 4: Resultados

### Tabla de resultados:
- **sXY**: Width del septum (píxeles)
- **Ratio T/A**: Proporción tejido/aire
- **Clasificación**: Highly Instilled / Instilled / Medium / Control
- **Edema**: SÍ (rojo) / NO (verde)

### Exportar:
- **Resultados Completos**: CSV con todas las imágenes
- **Resumen Estadístico**: CSV con promedios por grupo

## 🔬 Análisis Avanzado de Elipse

En calibración, click "Ver Análisis de Elipse" para ver:
- ACF con contornos
- Elipse ajustada con ejes
- Imagen con barra de escala
- Parámetros detallados

## 🔧 Solución de Problemas

### No carga imágenes
- Verifica formato TIFF (.tif o .tiff)
- Comprueba permisos de lectura

### Calibración extraña
- Ajusta "Desenfoque" y "Spots"
- Prueba con otra imagen
- Vuelve a valores default

### Procesamiento lento
- Cierra otros programas
- Verifica tamaño de imágenes

## 📞 Ayuda

Para más información detallada, consulta el archivo GUIA_DE_USUARIO.md completo.

**Versión**: 3.0 | **Fecha**: Diciembre 2024
"""


def main():
    app = QApplication(sys.argv)

    # Estilo moderno
    app.setStyle('Fusion')

    # Estilo personalizado
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QPushButton {
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTableWidget {
            gridline-color: #d0d0d0;
            background-color: white;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QProgressBar {
            border: 2px solid #cccccc;
            border-radius: 5px;
            text-align: center;
            height: 25px;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
    """)

    gui = EdemaAnalysisGUI()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()