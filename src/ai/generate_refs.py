import cv2
import os
import sys
import tkinter as tk 

# --- CONFIGURACIÓN ---
# Ajusta la ruta si tu video está en otro lado
VIDEO_PATH = os.path.join('uploads', 'cerveza_config.mp4') 
OUTPUT_DIR = 'referencias'

# Crear carpeta si no existe
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_screen_resolution():
    """Detecta el tamaño de tu pantalla para ajustar la ventana"""
    try:
        root = tk.Tk()
        root.withdraw() 
        return root.winfo_screenwidth(), root.winfo_screenheight()
    except:
        return 1920, 1080 

def calculate_view_scale(vid_w, vid_h):
    """Calcula el factor de escala para que quepa en el 85% de la pantalla"""
    screen_w, screen_h = get_screen_resolution()
    target_w = screen_w * 0.85
    target_h = screen_h * 0.85
    if vid_w == 0 or vid_h == 0: return 1.0
    return min(target_w / vid_w, target_h / vid_h, 1.0)

def draw_ui_overlay(image, lines, color=(0, 0, 0)):
    """Dibuja el cuadro de instrucciones sobre el video"""
    h, w, _ = image.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    line_height = 25
    margin = 20
    
    max_text_w = 0
    for line in lines:
        (tw, th), _ = cv2.getTextSize(line, font, font_scale, 1)
        if tw > max_text_w: max_text_w = tw
    
    box_w = max_text_w + 40
    box_h = (len(lines) * line_height) + 20
    
    # Posición: Arriba a la derecha
    top_left_x = w - box_w - margin
    top_left_y = margin
    bottom_right_x = w - margin
    bottom_right_y = margin + box_h
    
    overlay = image.copy()
    cv2.rectangle(overlay, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), color, -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
    cv2.rectangle(image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (255, 255, 255), 1)
    
    for i, line in enumerate(lines):
        y_pos = top_left_y + 25 + (i * line_height)
        cv2.putText(image, line, (top_left_x + 15, y_pos), font, font_scale, (255, 255, 255), 1)

def smart_selector(window_name, frame, scale, title, desc):
    """Muestra el frame ajustado a pantalla para seleccionar, pero guarda coords reales"""
    display = cv2.resize(frame, (0,0), fx=scale, fy=scale)
    msg = [f"SELECCION: {title}", "-"*20, desc, "", "Dibuja el recuadro y pulsa ENTER", "C para cancelar"]
    draw_ui_overlay(display, msg, color=(100, 50, 0)) # Color naranja/marrón
    
    # Selección visual sobre imagen escalada
    roi = cv2.selectROI(window_name, display, showCrosshair=True, fromCenter=False)
    
    # Convertir a coordenadas reales del video original
    real_x = int(roi[0] / scale)
    real_y = int(roi[1] / scale)
    real_w = int(roi[2] / scale)
    real_h = int(roi[3] / scale)
    
    return (real_x, real_y, real_w, real_h)

def save_ref(frame, roi, prefix, state_name):
    """Guarda el recorte en escala de grises"""
    x, y, w, h = roi
    if w == 0 or h == 0: return
    
    crop = frame[y:y+h, x:x+w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    filename = f"{prefix}_{state_name}.jpg"
    path = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(path, gray)
    print(f"✅ Guardado: {filename}")

def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: No se encuentra el video en: {VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    ret, frame = cap.read()
    if not ret: return

    # Datos originales
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calcular escala para que quepa en tu pantalla
    scale = calculate_view_scale(orig_w, orig_h)
    
    WINDOW_NAME = "Entrenador Simple"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    # --- FASE 1: SELECCIÓN DE GRIFOS ---
    # Solo seleccionamos la "Palanca" (o la zona principal) de cada grifo
    roi_a = smart_selector(WINDOW_NAME, frame, scale, "GRIFO A (Izq)", "Selecciona la zona de la palanca")
    roi_b = smart_selector(WINDOW_NAME, frame, scale, "GRIFO B (Der)", "Selecciona la zona de la palanca")

    # Guardar Coordenadas (Incluimos la resolución al final para que los otros scripts funcionen bien)
    coords_file = os.path.join(OUTPUT_DIR, "coords_dual.txt")
    with open(coords_file, "w") as f:
        # Formato: x,y,w,h (A) | x,y,w,h (B) | ResolucionOriginal
        line_a = ",".join(map(str, roi_a))
        line_b = ",".join(map(str, roi_b))
        f.write(f"{line_a}|{line_b}|{orig_w},{orig_h}")
    print(f"💾 Coordenadas guardadas en {coords_file}")

    # --- FASE 2: CAPTURA DE REFERENCIAS ---
    paused = False
    speed = 1
    
    while True:
        if not paused:
            # Lógica de velocidad (Adelante / Atrás)
            if speed == 1:
                ret, frame = cap.read()
            elif speed > 1:
                # Saltar frames para ir rápido
                for _ in range(speed - 1): cap.grab()
                ret, frame = cap.read()
            elif speed < 0:
                # Rebobinar
                current = cap.get(cv2.CAP_PROP_POS_FRAMES)
                target = max(0, current + speed - 1)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                ret, frame = cap.read()
            else: 
                ret, frame = cap.read()

            if not ret: 
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
        
        display = frame.copy()
        
        # Dibujar Cajas
        cv2.rectangle(display, (roi_a[0], roi_a[1]), (roi_a[0]+roi_a[2], roi_a[1]+roi_a[3]), (255, 0, 0), 2)
        cv2.putText(display, "A", (roi_a[0], roi_a[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)
        
        cv2.rectangle(display, (roi_b[0], roi_b[1]), (roi_b[0]+roi_b[2], roi_b[1]+roi_b[3]), (0, 255, 0), 2)
        cv2.putText(display, "B", (roi_b[0], roi_b[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        
        # Redimensionar para mostrar en pantalla
        display_small = cv2.resize(display, (0,0), fx=scale, fy=scale)
        
        # Texto de estado
        speed_txt = f"x{speed}" if speed > 0 else f"ATRAS x{abs(speed)}"
        if paused: speed_txt = "PAUSA"
        
        instructions = [
            f"VELOCIDAD: {speed_txt}",
            "-" * 25,
            "[ESPACIO] Play / Pausa",
            "[D] Mas Rapido | [A] Atras",
            "",
            "GRIFO A (Izquierda):",
            " [1] Cerrado",
            " [2] Cerveza",
            " [3] Espuma",
            "",
            "GRIFO B (Derecha):",
            " [4] Cerrado",
            " [5] Cerveza",
            " [6] Espuma",
            "",
            "[Q] Salir"
        ]
        
        draw_ui_overlay(display_small, instructions)
        cv2.imshow(WINDOW_NAME, display_small)
        
        # Reducir delay si vamos rápido para que se sienta fluido
        wait_time = 30 if speed <= 1 else 1
        key = cv2.waitKey(wait_time) & 0xFF
        
        # --- CONTROLES ---
        if key == ord('q'): break
        elif key == ord(' '): paused = not paused
        
        # Control Velocidad
        elif key == ord('d'): # Acelerar
            if speed < 5: speed += 1
            if speed == 0: speed = 1
        elif key == ord('a'): # Frenar/Atrás
            if speed > -5: speed -= 1
            if speed == 0: speed = -1
        
        # --- GUARDAR REFERENCIAS ---
        # Grifo A
        elif key == ord('1'): save_ref(frame, roi_a, "A", "closed")
        elif key == ord('2'): save_ref(frame, roi_a, "A", "beer")
        elif key == ord('3'): save_ref(frame, roi_a, "A", "foam")
        
        # Grifo B
        elif key == ord('4'): save_ref(frame, roi_b, "B", "closed")
        elif key == ord('5'): save_ref(frame, roi_b, "B", "beer")
        elif key == ord('6'): save_ref(frame, roi_b, "B", "foam")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()