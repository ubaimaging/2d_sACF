# 📘 GUÍA DE USUARIO
## Sistema de Análisis de Edema Pulmonar - Método ACF

---

## 📑 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Requisitos del Sistema](#requisitos-del-sistema)
3. [Instalación](#instalación)
4. [Preparación de las Imágenes](#preparación-de-las-imágenes)
5. [Inicio del Programa](#inicio-del-programa)
6. [Flujo de Trabajo Completo](#flujo-de-trabajo-completo)
7. [Pestaña 1: Carga de Imágenes](#pestaña-1-carga-de-imágenes)
8. [Pestaña 2: Calibración de Filtros](#pestaña-2-calibración-de-filtros)
9. [Pestaña 3: Procesamiento del Dataset](#pestaña-3-procesamiento-del-dataset)
10. [Pestaña 4: Resultados](#pestaña-4-resultados)
11. [Análisis Avanzado de Elipse](#análisis-avanzado-de-elipse)
12. [Interpretación de Resultados](#interpretación-de-resultados)
13. [Solución de Problemas](#solución-de-problemas)
14. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 🎯 Introducción

### ¿Qué hace este programa?

Este software analiza imágenes de microscopía de tejido pulmonar para **detectar automáticamente la presencia de edema pulmonar** utilizando el método de Función de Autocorrelación (ACF).

### ¿Cómo funciona?

El programa:
1. Analiza la estructura espacial de los septos alveolares
2. Calcula el ancho característico del septum (sXY)
3. Clasifica cada imagen en 4 categorías según el nivel de edema
4. Genera reportes detallados con estadísticas

### Usuarios objetivo

- **Médicos** e investigadores clínicos
- **Biólogos** especializados en tejido pulmonar
- **Técnicos de laboratorio** sin experiencia en programación

---

## 💻 Requisitos del Sistema

### Hardware mínimo
- **Procesador**: Intel Core i5 o equivalente
- **RAM**: 8 GB mínimo (16 GB recomendado)
- **Espacio en disco**: 500 MB libres
- **Pantalla**: Resolución mínima 1920x1080

### Software requerido
- **Sistema Operativo**: Windows 10 o Windows 11 (64-bit)
- **Permisos**: Usuario normal (no requiere administrador)
- **NO requiere**: Python ni instalación de librerías

### Formato de imágenes
- **Tipo**: Archivos TIFF (.tif o .tiff)
- **Formato**: RGB (color)
- **Resoluciones soportadas**: 
  - 1024 x 1024 píxeles (óptimo)
  - 2048 x 2448 píxeles (se redimensiona automáticamente)

---

## 🔧 Instalación

### ✅ Para usuarios médicos (Recomendado)

**El programa viene como ejecutable - ¡No necesitas instalar nada!**

#### Paso 1: Descargar el programa

Recibirás un archivo comprimido (.zip) que contiene:
- `AnalizadorEdema.exe` (programa principal)
- `GUIA_DE_USUARIO.md` (esta guía)
- `README.txt` (instrucciones breves)

#### Paso 2: Extraer archivos

1. Haz click derecho en el archivo .zip
2. Selecciona "Extraer todo..."
3. Elige una ubicación (ejemplo: `C:\Programas\AnalizadorEdema\`)
4. Click en "Extraer"

#### Paso 3: Ejecutar el programa

1. Abre la carpeta donde extrajiste los archivos
2. Doble click en `AnalizadorEdema.exe`
3. **Si aparece advertencia de Windows Defender:**
   - Click en "Más información"
   - Click en "Ejecutar de todas formas"
   - Esto es normal para programas sin firma digital

#### Paso 4: (Opcional) Crear acceso directo

1. Click derecho en `AnalizadorEdema.exe`
2. Selecciona "Crear acceso directo"
3. Arrastra el acceso directo al Escritorio

**¡Listo! Ya puedes usar el programa.**

---

### 🔧 Para desarrolladores (Avanzado)

Si eres desarrollador y quieres ejecutar el código fuente:

```bash
# Crear entorno virtual
conda create -n edema_analysis python=3.11 -y
conda activate edema_analysis

# Instalar dependencias
conda install pyqt -y
conda install numpy matplotlib opencv scipy scikit-learn pandas pillow scikit-image -y

# Ejecutar desde código fuente
python edema-analysis-gui-v3.py
```

---

## 📂 Preparación de las Imágenes

### Requisitos de las imágenes

1. **Formato**: Solo archivos TIFF (.tif o .tiff)
2. **Contenido**: Imágenes de microscopía de tejido pulmonar
3. **Calidad**: Imágenes claras, bien enfocadas
4. **Cantidad mínima**: Al menos 10 imágenes para calibración adecuada

### Organización recomendada

```
MiEstudio/
├── Imagenes/
│   ├── muestra_001.tif
│   ├── muestra_002.tif
│   ├── muestra_003.tif
│   └── ...
└── Resultados/
    (aquí se guardarán los resultados)
```

### ⚠️ Importante

- Las imágenes deben estar **sin procesar** (raw)
- **No** aplicar filtros previos en otro software
- Todas las imágenes deben tener la **misma ampliación**

---

## 🚀 Inicio del Programa

### Para usuarios médicos (Ejecutable)

**Método simple:**
1. Ve a la carpeta donde instalaste el programa
2. Doble click en `AnalizadorEdema.exe`
3. Espera unos segundos a que se abra la ventana

**Método con acceso directo:**
1. Doble click en el acceso directo del Escritorio
2. El programa se iniciará automáticamente

### Para desarrolladores (Código fuente)

```bash
# Activar entorno (si usas Anaconda)
conda activate edema_analysis

# Ejecutar programa
python edema-analysis-gui-v3.py
```

### Ventana principal

Al iniciar verás una ventana con 4 pestañas:
1. **Carga de Imágenes**
2. **Calibración de Filtros**
3. **Procesamiento del Dataset**
4. **Resultados**

### ⚠️ Primera vez que inicias

El programa puede tardar 10-20 segundos en abrir la primera vez. Esto es normal.

### Si el programa no inicia

1. **Verifica que extrajiste todos los archivos** del .zip
2. **Revisa que no bloqueó Windows Defender** (ver instrucciones de instalación)
3. **Cierra otros programas** que consuman mucha memoria
4. **Reinicia tu PC** e intenta de nuevo

---

## 🔄 Flujo de Trabajo Completo

### Proceso general (4 pasos)

```
PASO 1: Cargar Imágenes
    ↓
PASO 2: Calibrar Parámetros (10 imágenes aleatorias)
    ↓
PASO 3: Procesar Todo el Dataset
    ↓
PASO 4: Revisar y Exportar Resultados
```

### Tiempo estimado

- **Carga**: < 1 minuto
- **Calibración**: 5-15 minutos (depende del usuario)
- **Procesamiento**: 1-2 segundos por imagen
- **Total**: ~20-30 minutos para 100 imágenes

---

## 📁 Pestaña 1: Carga de Imágenes

### Objetivo
Seleccionar las imágenes TIFF que deseas analizar.

### Pasos detallados

#### 1. Cargar imágenes

**Opción A: Cargar carpeta completa**
1. Click en **"📁 Cargar Carpeta de Imágenes"**
2. Navega hasta la carpeta con tus imágenes TIFF
3. Selecciona la carpeta
4. El programa cargará **todos** los archivos .tif/.tiff

**Opción B: Seleccionar archivos individuales**
1. Click en **"📄 Seleccionar Archivos Individuales"**
2. Mantén presionado `Ctrl` (Windows/Linux) o `Cmd` (Mac)
3. Click en cada imagen que quieras incluir
4. Click en "Abrir"

#### 2. Verificar carga

Después de cargar verás:
- ✅ Mensaje: "X imágenes cargadas | 10 seleccionadas para calibración"
- Tabla con lista de imágenes
- Columna "Calibración" indica cuáles se usarán para calibrar

#### 3. Avanzar a calibración

El programa automáticamente:
- Selecciona **10 imágenes aleatorias** para calibración
- Te lleva a la **Pestaña 2: Calibración**

### ⚠️ Notas importantes

- Las 10 imágenes se eligen **aleatoriamente** para representar todo el dataset
- No puedes elegir manualmente cuáles usar (esto evita sesgo)
- Si cargas menos de 10 imágenes, usa todas las disponibles

---

## ⚙️ Pestaña 2: Calibración de Filtros

### Objetivo
Ajustar los parámetros de filtrado para optimizar la detección del septum alveolar.

### Interfaz

La pantalla se divide en:
- **Izquierda**: Controles y parámetros
- **Derecha**: 4 visualizaciones de la imagen actual

### Visualizaciones (Panel derecho)

1. **Original**: Imagen sin procesar
2. **Gaussian Filtered**: Después del desenfoque gaussiano
3. **K-means Clustering**: Segmentación en 3 regiones
4. **Spots Removed**: Resultado final (limpio)

### Parámetros ajustables (Panel izquierdo)

#### 1. Desenfoque Gaussiano (sigma)
- **Rango**: 1 - 30
- **Default**: 20
- **Función**: Suaviza la imagen para reducir ruido
- **Cómo ajustar**: 
  - ↑ Aumentar si hay mucho ruido
  - ↓ Disminuir para preservar detalles finos

#### 2. Tamaño kernel Gaussian
- **Rango**: 3 - 31 (solo valores impares)
- **Default**: 11
- **Función**: Define el área del filtro gaussiano
- **Cómo ajustar**: 
  - Debe ser **impar** (el programa lo ajusta automáticamente)
  - ↑ Aumentar para desenfoque más amplio

#### 3. Tamaño mínimo spots (px²)
- **Rango**: 100 - 2000
- **Default**: 900
- **Función**: Elimina manchas pequeñas (artefactos)
- **Cómo ajustar**:
  - ↑ Aumentar para eliminar más artefactos
  - ↓ Disminuir si se pierden estructuras importantes

#### 🔒 K-means clusters
- **Valor fijo**: 3
- **No ajustable**: Valor óptimo predeterminado

### Proceso de calibración

#### Paso 1: Observar la imagen actual
Revisa las 4 visualizaciones de la imagen actual.

#### Paso 2: Ajustar parámetros
Mueve los sliders y observa cómo cambia el resultado en tiempo real.

**¿Qué buscar en "Spots Removed"?**
- ✅ Septos alveolares claramente definidos
- ✅ Áreas de tejido y aire bien separadas
- ✅ Mínimo ruido o artefactos
- ❌ Evitar que se pierdan estructuras importantes
- ❌ Evitar demasiados artefactos residuales

#### Paso 3: Guardar parámetros
Cuando estés satisfecho con el resultado:
1. Click en **"✓ Guardar Parámetros de Esta Imagen"**
2. Los parámetros actuales se guardan
3. Se actualiza el promedio en el panel amarillo

#### Paso 4: Navegar entre imágenes
- Click **"◀ Anterior"** o **"Siguiente ▶"**
- El indicador muestra: "X / 10"
- Repite el proceso para cada imagen

#### Paso 5: Revisar parámetros promedio
El panel amarillo muestra:
- Promedio de todos los parámetros guardados
- Estos valores se usarán para procesar **todo** el dataset

### 🎯 Estrategia recomendada

**Para principiantes:**
1. Usa los valores por defecto
2. Ajusta solo si hay problemas evidentes
3. Calibra al menos 3-5 imágenes

**Para usuarios avanzados:**
1. Calibra las 10 imágenes completas
2. Busca parámetros que funcionen bien en todas
3. Ajusta fino imagen por imagen

### 🔬 Análisis Avanzado de Elipse (Opcional)

Si entiendes el método ACF en profundidad:

1. Click en **"🔬 Ver Análisis de Elipse (avanzado)"**
2. Se abre ventana con 4 paneles:
   - ACF con contornos
   - Elipse ajustada con ejes
   - Imagen original con barra de escala
   - Parámetros detallados
3. Cierra la ventana cuando termines de revisar

**Utilidad:**
- Verificar calidad del ajuste de la elipse
- Visualizar el width del septum directamente
- Entender la geometría de la ACF

### Botones adicionales

#### 🔄 Refrescar Vista
- Re-procesa la imagen actual
- Útil si cambiaste parámetros manualmente

#### Ratio tejido/aire
- Se actualiza automáticamente
- Indica la proporción de tejido vs aire en la imagen

### ⚠️ Consejos importantes

- **No apresures** la calibración - es el paso más importante
- Si una imagen es muy diferente, ajusta parámetros específicos
- Los parámetros se **promedian**, no necesitas ser perfecto en todas
- Puedes volver a calibrar en cualquier momento

---

## 🔬 Pestaña 3: Procesamiento del Dataset

### Objetivo
Procesar todas las imágenes con los parámetros calibrados.

### Interfaz

- **Arriba**: Información de parámetros y controles
- **Centro**: Barra de progreso
- **Abajo**: Resumen en tiempo real

### Inicio del procesamiento

#### 1. Verificar parámetros

El programa muestra:
```
Parámetros calibrados (promedio de X imágenes):
• Sigma Gaussiano: XX.X
• Kernel Size: XX
• Tamaño min spots: XXX
• K-means clusters: 3
```

#### 2. Configurar guardado automático

**Checkbox**: ☑️ "Guardar resultados automáticamente al finalizar"
- **Activado**: Guarda CSV automáticamente con timestamp
- **Desactivado**: Puedes guardar manualmente después

Nombre automático: `Resultados_Edema_YYYY-MM-DD-HH-MM.csv`

#### 3. Iniciar procesamiento

1. Click en **"▶️ Procesar Dataset Completo"**
2. Aparece diálogo de confirmación:
   ```
   Se procesarán XXX imágenes con los siguientes parámetros:
   • Sigma Gaussiano: XX.X
   • Kernel Size: XX
   • Tamaño min spots: XXX
   • K-means clusters: 3
   
   ¿Desea continuar?
   ```
3. Click **"Sí"**

### Durante el procesamiento

#### Barra de progreso
```
Procesando... XX% completado
[████████░░░░░░░░░░] XX%
```

#### Resumen en tiempo real
```
Procesadas: XX | Edema detectado: XX (XX.X%)
```

**Velocidad típica:** 1-2 segundos por imagen

### ⚠️ Importante durante el procesamiento

- **NO cierres** el programa
- **NO cambies** de pestaña
- Puedes minimizar la ventana
- El proceso no se puede pausar (debe terminar)

### Al finalizar

Verás:
- ✅ "Procesamiento completado"
- Mensaje: "XXX imágenes analizadas"
- Automáticamente cambia a **Pestaña 4: Resultados**

---

## 📊 Pestaña 4: Resultados

### Objetivo
Revisar, analizar y exportar los resultados del análisis.

### Sección 1: Resumen General

Panel superior con estadísticas clave:

```
Resumen de Resultados

Total de imágenes: XXX

Con edema detectado: XX (XX.X%) [en rojo]

Sin edema: XX (XX.X%) [en verde]
```

### Sección 2: Tabla de Resultados Detallados

Tabla con todas las imágenes procesadas:

| Columna | Descripción | Valores |
|---------|-------------|---------|
| **Imagen** | Nombre del archivo | muestra_001.tif |
| **sXY** | Width del septum (promedio) | 45.2 px |
| **Ratio Tejido/Aire** | Proporción tejido/aire | 12.5 |
| **FWHM** | Ancho medio de la ACF | 0.45 |
| **Clasificación** | Estado del pulmón | Highly Instilled / Instilled / Medium / Control |
| **Tiene Edema** | Detección binaria | SÍ (rojo) / NO (verde) |

**Colores:**
- 🔴 **Rojo**: Edema detectado
- 🟢 **Verde**: Sin edema

### Clasificaciones posibles

| Clasificación | sXY típico | Tiene Edema | Descripción |
|---------------|------------|-------------|-------------|
| **Highly Instilled** | > 60 px | ✅ SÍ | Edema severo |
| **Instilled** | 45-60 px | ✅ SÍ | Edema moderado |
| **Medium** | 30-45 px | ❌ NO | Leve acumulación |
| **Control** | < 30 px | ❌ NO | Tejido normal |

*Nota: Rangos aproximados, pueden variar según el tejido*

### Sección 3: Exportar Resultados

#### Botón: Exportar Resultados Completos (CSV)

1. Click en **"💾 Exportar Resultados Completos"**
2. Elige ubicación y nombre
3. Se guarda archivo CSV con:
   - Todas las columnas de la tabla
   - Una fila por imagen
   - Formato compatible con Excel

**Contenido del CSV:**
```csv
Imagen,sXY,Ratio Tejido/Aire,FWHM,Clasificación,Tiene Edema
muestra_001.tif,45.23,12.5,0.45,Instilled,Sí
muestra_002.tif,28.34,8.2,0.38,Control,No
...
```

#### Botón: Exportar Resumen Estadístico

1. Click en **"📈 Exportar Resumen Estadístico"**
2. Se guarda CSV con estadísticas **por grupo**:

**Contenido:**
```csv
Clasificación,N muestras,sXY promedio,sXY std,Ratio promedio,Ratio std,FWHM promedio,FWHM std
Highly Instilled,5,65.2,8.3,15.2,2.1,0.52,0.05
Instilled,12,48.5,6.1,11.8,1.8,0.46,0.04
Medium,28,38.2,5.2,9.5,1.5,0.41,0.03
Control,55,25.1,4.8,7.2,1.2,0.36,0.03
```

**Útil para:**
- Análisis estadístico en R, Python o SPSS
- Gráficos de barras o box plots
- Comparaciones entre grupos

### Interpretación de los datos

#### sXY (Width del Septum)
- **Valor en píxeles** del ancho característico del septum
- ↑ **Mayor valor** = Septum más grueso = Más edema
- ↓ **Menor valor** = Septum más delgado = Menos edema

#### Ratio Tejido/Aire
- Proporción de área de tejido vs aire
- ↑ **Mayor ratio** = Más tejido = Posible edema
- ↓ **Menor ratio** = Más aire = Pulmón más sano

#### FWHM (Full Width Half Maximum)
- Medida del ancho de la ACF
- Relacionado con la escala característica
- Valor técnico para usuarios avanzados

---

## 🔬 Análisis Avanzado de Elipse

### ¿Qué es?

Herramienta para usuarios avanzados que entienden el método ACF y quieren visualizar el ajuste de la elipse y verificar la calidad del análisis.

### ¿Cuándo usar?

- Verificar calidad del ajuste en imágenes dudosas
- Entender la geometría de la autocorrelación
- Validar resultados antes de publicación científica
- Debugging y control de calidad

### Cómo acceder

**Desde la Pestaña 2 (Calibración):**
1. Selecciona una imagen de calibración
2. Click en **"🔬 Ver Análisis de Elipse (avanzado)"**
3. Se abre ventana emergente con 4 paneles

### Ventana de Análisis de Elipse

#### Panel 1: ACF con Contorno
- Muestra la función de autocorrelación 2D (ACF)
- Contorno en cyan al nivel del cluster detectado
- Colorbar: Intensidad de la correlación

#### Panel 2: Elipse Ajustada
- ACF con elipse superpuesta en verde
- **Línea cyan**: Eje mayor (sX)
- **Línea magenta**: Eje menor (sY)
- **Punto amarillo**: Centro
- Zoom en región de interés

**Leyenda:**
- `sX (width septum): XX.X px`
- `sY (width septum): XX.X px`

#### Panel 3: Imagen Original con Escala
- Imagen RGB original
- **Barra amarilla** en esquina inferior derecha
- La barra representa visualmente el valor de sXY
- Texto: "sXY = XX.X px (width septum)"

**Utilidad:**
- Compara el tamaño de la escala con estructuras reales
- Visualiza qué tan grande es el septum en la imagen

#### Panel 4: Parámetros Detallados

Información completa:

```
PARÁMETROS DE AJUSTE
===================================

Dimensiones de la elipse:
  • Eje mayor (sX):  XX.XX px
  • Eje menor (sY):  XX.XX px
  • Promedio (sXY): XX.XX px
  • Semi-eje X:      XX.XX px
  • Semi-eje Y:      XX.XX px

Geometría:
  • Ángulo:          XX.XX°
  • Ratio (sY/sX):   X.XXX
  • Excentricidad:   X.XXX

Clasificación:
  • Cluster:         X
  • FWHM:            X.XXX
  • Ratio T/A:       XX.XX
  • Nivel contorno:  X.XXXX

Interpretación:
  • Estado:          Instilled
  • Edema:           SÍ
```

### Interpretación avanzada

#### Calidad del ajuste
- **Elipse bien ajustada**: Sigue el contorno de la ACF
- **Elipse desajustada**: No coincide → revisar imagen

#### Geometría
- **Ratio sY/sX ≈ 1**: Septum isotrópico (igual en todas direcciones)
- **Ratio sY/sX > 2**: Septum anisotrópico → posible artefacto

#### Excentricidad
- **0**: Círculo perfecto
- **→ 1**: Elipse muy alargada

### Controles de la ventana

La ventana de matplotlib tiene herramientas:
- 🏠 **Home**: Reset view
- ⬅️➡️ **Flechas**: Navegación
- 🔍 **Zoom**: Click y arrastra
- 🖱️ **Pan**: Mueve la vista
- 💾 **Save**: Guarda la figura

### Cerrar ventana

- Click en X de la ventana
- O presiona `Ctrl+W`
- Vuelves automáticamente a la calibración

---

## 📖 Interpretación de Resultados

### Criterios de detección de edema

El programa clasifica como **"CON EDEMA"** si:
- Cluster = 1 (Highly Instilled), **O**
- Cluster = 2 (Instilled)

El programa clasifica como **"SIN EDEMA"** si:
- Cluster = 3 (Medium), **O**
- Cluster = 4 (Control)

### Valores de referencia

| Parámetro | Sin Edema | Con Edema | Edema Severo |
|-----------|-----------|-----------|--------------|
| **sXY** | < 35 px | 40-60 px | > 60 px |
| **Ratio T/A** | < 8 | 10-15 | > 15 |
| **Clasificación** | Control/Medium | Instilled | Highly Instilled |

*Nota: Valores orientativos, pueden variar según el protocolo experimental*

### Casos especiales

#### Resultados mixtos
Si en un mismo paciente hay imágenes con y sin edema:
- **Normal**: El edema puede ser focal (no uniforme)
- **Recomendación**: Analizar la proporción (% con edema)
- **Criterio clínico**: Definir umbral según protocolo

#### Valores intermedios
Imágenes clasificadas como "Medium":
- Zona gris entre normal y patológico
- Puede indicar edema incipiente
- Recomendación: Evaluar caso por caso

#### Ratio Tejido/Aire muy alto
Si Ratio T/A > 20:
- Puede indicar colapso alveolar
- Verificar calidad de la imagen
- Considerar atelectasia

### Validación de resultados

**Siempre recomendado:**
1. Revisar algunas imágenes manualmente
2. Comparar con evaluación histológica (gold standard)
3. Calcular sensibilidad/especificidad vs diagnóstico clínico
4. Documentar casos atípicos

---

## 🔧 Solución de Problemas

### Problema 0: El programa no inicia (Ejecutable)

**Síntomas:**
- Doble click en .exe pero no pasa nada
- Se cierra inmediatamente
- Windows Defender bloquea

**Soluciones:**
1. **Windows Defender bloqueando:**
   - Click derecho en el archivo → Propiedades
   - Abajo marca "Desbloquear" → Aplicar
   - O: Click "Más información" → "Ejecutar de todas formas"

2. **Falta archivo:**
   - Asegúrate de extraer **TODOS** los archivos del .zip
   - No ejecutes desde dentro del .zip

3. **Antivirus bloqueando:**
   - Agrega excepción en tu antivirus
   - O deshabilita temporalmente

4. **Problema con Visual C++:**
   - Descarga e instala: https://aka.ms/vs/17/release/vc_redist.x64.exe

5. **PC sin recursos:**
   - Cierra otros programas
   - Reinicia la PC

### Problema 1: No carga imágenes

**Síntomas:**
- Click en cargar pero no aparecen imágenes
- Mensaje de error al cargar

**Soluciones:**
1. Verifica que sean archivos **.tif** o **.tiff**
2. Comprueba que las imágenes no estén corruptas:
   - Ábrelas en otro programa (ImageJ, Fiji)
3. Verifica permisos de lectura en la carpeta
4. Intenta cargar una sola imagen para probar

### Problema 2: Calibración da resultados extraños

**Síntomas:**
- Imagen "Spots Removed" muy diferente a la original
- Septos no se ven bien definidos

**Soluciones:**
1. **Ajusta parámetros**:
   - ↓ Disminuye "Desenfoque Gaussiano" si se pierde detalle
   - ↑ Aumenta "Tamaño mínimo spots" si hay muchos artefactos
2. **Prueba con otra imagen** de calibración
3. **Vuelve a valores default** y ajusta gradualmente
4. Verifica calidad de la imagen original (foco, contraste)

### Problema 3: Procesamiento muy lento

**Síntomas:**
- Tarda más de 5 segundos por imagen

**Soluciones:**
1. Cierra otros programas pesados
2. Verifica que las imágenes no sean demasiado grandes
3. Si tienes 1000+ imágenes, procesa en lotes
4. Considera usar PC con más RAM

### Problema 4: Error al exportar resultados

**Síntomas:**
- Mensaje de error al guardar CSV
- Archivo no se crea

**Soluciones:**
1. Verifica permisos de escritura en la carpeta
2. Cierra Excel si el archivo estaba abierto
3. Elige otra ubicación (Escritorio, Documentos)
4. Verifica espacio libre en disco

### Problema 5: Ventana de elipse no se abre

**Síntomas:**
- Click en "Ver Elipse" pero no pasa nada
- Error en consola

**Soluciones:**
1. Espera unos segundos (puede tardar la primera vez)
2. Verifica que la imagen de calibración se haya procesado
3. Intenta con "Refrescar Vista" primero
4. Reinicia el programa

### Problema 6: Resultados inconsistentes

**Síntomas:**
- Dos imágenes similares dan resultados muy diferentes
- Clasificación no tiene sentido

**Posibles causas:**
1. **Calibración pobre**: Re-calibra con más cuidado
2. **Imágenes de mala calidad**: Descártalas
3. **Artefactos**: Aumenta filtro de spots
4. **Heterogeneidad real**: El tejido es variable (normal)

**Verificación:**
1. Usa "Ver Análisis de Elipse" para revisar ajuste
2. Compara imágenes manualmente
3. Revisa historial de calibración

---

## ❓ Preguntas Frecuentes

### General

**P: ¿Necesito instalar Python?**
R: **No**. El ejecutable incluye todo lo necesario. Solo descarga y ejecuta.

**P: ¿Funciona en Mac o Linux?**
R: El ejecutable es solo para Windows. Usuarios de Mac/Linux deben usar el código fuente con Python.

**P: ¿Es seguro? ¿Tiene virus?**
R: Sí es seguro. Windows Defender puede dar advertencia porque el programa no tiene firma digital (es caro). El código es verificable.

**P: ¿Cuántas imágenes necesito mínimo?**
R: Mínimo 10 para calibración. Para estudio confiable, recomendamos 30+ por grupo experimental.

**P: ¿Puedo procesar imágenes de diferentes experimentos juntas?**
R: No recomendado. Calibra por separado si:
- Diferente ampliación
- Diferente protocolo de tinción
- Diferente especie animal
- Diferentes condiciones de iluminación

**P: ¿Los resultados son reproducibles?**
R: Sí, si usas los mismos parámetros. Guarda los parámetros de calibración para cada experimento.

**P: ¿Necesito conocimientos de programación?**
R: No. La interfaz es completamente visual y guiada.

### Calibración

**P: ¿Debo calibrar todas las 10 imágenes?**
R: Recomendado. Mínimo 3-5 para resultados confiables.

**P: ¿Puedo cambiar los parámetros después de procesar?**
R: Sí, debes volver a la calibración y re-procesar todo el dataset.

**P: ¿Por qué usa 10 imágenes aleatorias?**
R: Para que sean representativas de todo el dataset y evitar sesgo de selección.

**P: ¿Qué pasa si una imagen de calibración es muy diferente?**
R: Normal. El promedio compensa. Ajusta parámetros específicos para esa imagen.

### Procesamiento

**P: ¿Puedo interrumpir el procesamiento?**
R: No se recomienda. Si lo haces, debes reiniciar desde cero.

**P: ¿Se procesan en orden?**
R: Sí, en orden alfabético por nombre de archivo.

**P: ¿Qué pasa si el programa se cierra durante el procesamiento?**
R: Debes reiniciar y procesar todo de nuevo. No guarda progreso parcial.

### Resultados

**P: ¿Cómo valido que los resultados son correctos?**
R: Compara con evaluación manual de un experto en algunas imágenes (validación cruzada).

**P: ¿Puedo modificar los resultados en el CSV?**
R: Sí, puedes editar el CSV en Excel, pero documenta los cambios.

**P: ¿Qué hago si muchas imágenes salen como "Medium"?**
R: Medium es zona intermedia. Define criterio según tu protocolo:
- ¿Medium cuenta como edema? → Depende de tu investigación
- Consulta literatura de tu área

### Técnicas

**P: ¿Qué es sXY exactamente?**
R: Es el promedio del ancho característico del septum alveolar en píxeles, calculado desde la función de autocorrelación.

**P: ¿Por qué usar ACF y no medir directamente?**
R: ACF es más robusto:
- No depende de medir manualmente
- Captura escala característica global
- Menos sensible a artefactos locales

**P: ¿El método funciona con otras especies?**
R: Sí, siempre que sean alvéolos. Puede requerir re-calibración.

**P: ¿Funciona con diferentes tinciones?**
R: Sí, pero calibra por separado para cada tipo de tinción.

---

## 📞 Soporte y Contacto

### Antes de contactar soporte

1. Lee esta guía completa
2. Revisa "Solución de Problemas"
3. Verifica que tienes la última versión del programa
4. Anota el mensaje de error exacto (captura de pantalla)

### Información para reportar problemas

Cuando contactes soporte, proporciona:
- Versión del programa
- Sistema operativo
- Mensaje de error completo
- Pasos para reproducir el problema
- Ejemplo de imagen problema (si aplica)

### Recursos adicionales

- **Manual técnico**: Para detalles del método ACF
- **Publicaciones**: Referencia científica del método
- **Actualizaciones**: Nuevas versiones del software

---

## 📄 Apéndice A: Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl + O` | Abrir carpeta de imágenes |
| `Ctrl + S` | Guardar parámetros de calibración |
| `Ctrl + E` | Exportar resultados |
| `Ctrl + Q` | Cerrar programa |
| `F5` | Refrescar vista actual |
| `Ctrl + W` | Cerrar ventana de elipse |

---

## 📄 Apéndice B: Glosario

- **ACF**: Función de Autocorrelación (Autocorrelation Function)
- **sXY**: Promedio del width del septum en dirección X e Y
- **FWHM**: Full Width Half Maximum - ancho a media altura
- **Ratio T/A**: Ratio Tejido/Aire
- **Septum**: Pared delgada entre alvéolos
- **TIFF**: Formato de imagen sin compresión (Tagged Image File Format)
- **K-means**: Algoritmo de clustering (agrupamiento)
- **GMM**: Gaussian Mixture Model - modelo de mezcla gaussiana

---

## 📝 Registro de Cambios

### Versión 3.0 (Actual)
- ✅ Interfaz gráfica completa con 4 pestañas
- ✅ Calibración interactiva con visualización en tiempo real
- ✅ Procesamiento batch optimizado
- ✅ Análisis avanzado de elipse para usuarios expertos
- ✅ Exportación de resultados en CSV
- ✅ Resumen estadístico por grupos

---

## 📜 Licencia y Créditos

### Desarrollo
- **Método científico**: Basado en análisis ACF de estructuras alveolares
- **Implementación**: Python con PyQt5 y bibliotecas científicas
- **Interfaz**: Diseñada para usuarios no programadores

### Cita científica
Si usas este software en una publicación, cita:
```
[Pendiente: Incluir referencia bibliográfica del método]
```

---

**Versión de la guía**: 1.0  
**Fecha**: Diciembre 2024  
**Software**: edema-analysis-gui-v3.py

---

¡Gracias por usar el Sistema de Análisis de Edema Pulmonar!
