# 🍺 Gambooza AI - Sistema de Auditoría de Tiraje

**Sistema integral de Visión Artificial para el conteo y análisis temporal de tirajes de cerveza.**

![Status](https://img.shields.io/badge/Status-Stable-success)
![Python](https://img.shields.io/badge/Python-3.9-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![OpenCV](https://img.shields.io/badge/CV-OpenCV-red)
![Docker](https://img.shields.io/badge/Deploy-Docker%20Ready-2496ED)

---

## 📖 Descripción del Proyecto

Este proyecto implementa una solución *End-to-End* para monitorizar el consumo en grifos de cerveza utilizando cámaras de seguridad estándar. A diferencia de los contadores de flujo físicos, **Gambooza AI** es una solución no intrusiva basada en software.

El sistema procesa vídeo, detecta estados visuales (Cerrado/Cerveza/Espuma), reconstruye la línea de tiempo de cada servicio y expone los resultados en un Dashboard interactivo.

### ✨ Características Clave

1.  **Motor de IA Híbrido**: Combina *Computer Vision* (Template Matching) con una *Máquina de Estados* temporal para distinguir entre una tirada real, limpieza o simple espuma.
2.  **Reparación Automática de Vídeo**: Módulo inteligente que detecta archivos de vídeo corruptos (sin índice/MOOV atom) y los transcodifica en tiempo real para permitir su reproducción en la web.
3.  **Lógica de Negocio Avanzada**: Implementación de algoritmos de umbralización para estimar el volumen (litros/cañas) basándose en la duración del flujo.
4.  **Arquitectura Asíncrona**: Backend desacoplado que permite la subida inmediata del archivo mientras un *worker* procesa la IA en segundo plano.
5.  **Dashboard Interactivo**: Visualización con *Timeline* sincronizado: al hacer clic en un evento, el vídeo salta al momento exacto de la tirada.

---

## ⚙️ Arquitectura Técnica

El proyecto sigue una arquitectura monolítica modular:

* **Core AI (`src/ai`)**: Scripts de procesamiento de imagen. Utiliza una lógica de *cooldown* dinámico para optimizar el rendimiento (salta frames cuando no hay actividad).
* **Backend (`src/backend`)**: API REST construida con **FastAPI**. Gestiona la cola de tareas (`BackgroundTasks`), la persistencia en **SQLite** y sirve los archivos estáticos.
* **Frontend (`src/frontend`)**: SPA (Single Page Application) sin frameworks pesados, estilizada con **TailwindCSS**. Realiza *polling* inteligente al servidor para actualizar el estado.

---

## 🧠 Lógica del Algoritmo de Conteo

Para garantizar la precisión en entornos reales, el sistema aplica las siguientes reglas heurísticas:

1.  **Discriminación de Estado**: Se analiza cada grifo independientemente comparando el frame actual con referencias calibradas (Cerrado vs. Abierto).
2.  **Filtro de Ruido**: Cualquier evento con duración **< 2.0 segundos** se descarta automáticamente (goteo o limpieza rápida).
3.  **Estimación de Unidades (Regla del 0.6)**:
    * Se define una constante de tirada (ej. 12 segundos = 1 Caña).
    * Se calcula la proporción: `Duración / 12`.
    * **Umbral**: Si la parte decimal supera **0.6**, se contabiliza una unidad extra.
    * *Ejemplo*: Una tirada de 1.7 unidades se redondea a 2. Una de 1.4 se queda en 1.

---

## 🚀 Guía de Instalación y Uso

### Opción A: Ejecución Local (Recomendada para Desarrollo)

1.  **Crear entorno virtual**:
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

2.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Iniciar el Servidor**:
    ```bash
    uvicorn src.backend.main:app --reload
    ```

4.  **Acceder**: Abre tu navegador en `http://127.0.0.1:8000`

### Opción B: Despliegue con Docker

El proyecto incluye configuración completa para contenerización.

1.  **Construir y arrancar**:
    ```bash
    docker-compose up --build
    ```
    *El sistema se encargará de instalar las librerías de sistema (`libgl1`) necesarias para OpenCV.*

---

## 📂 Estructura de Carpetas

```text
gambooza_case/
├── src/
│   ├── ai/                 # Motor de Visión Artificial y Referencias
│   ├── backend/            # API, Modelos DB y Reparador de Vídeo
│   └── frontend/           # Interfaz Web (HTML/JS)
├── uploads/                # Almacenamiento temporal de vídeos
├── gambooza.db             # Base de datos SQLite (Historial)
├── Dockerfile              # Configuración de imagen
└── requirements.txt        # Dependencias Python

---

## 🛡️ Notas de la Defensa

- Persistencia: Los datos se guardan en gambooza.db. Si se desea reiniciar el historial, basta con borrar este archivo.

- Formatos de Vídeo: El sistema acepta MP4 y MOV. Si el navegador no soporta el códec original, el backend intentará repararlo automáticamente.

---

Autor: Izan Rodríguez Cuerdo. Caso Práctico de Ingeniería de Software y Visión Artificial.