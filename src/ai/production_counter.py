import cv2
import numpy as np
import os
import time
import sys
import math

# --- CONFIGURACIÓN ---
IDLE_SKIP_FRAMES = 50    
COOLDOWN_FRAMES = 30    
SECONDS_PER_BEER = 12.0  
THRESHOLD_ROUNDING = 0.6 

class SingleTap:
    def __init__(self, name, roi, refs_folder):
        self.name = name
        self.roi = roi 
        self.count = 0
        self.total_beer_seconds = 0.0 
        
        self.current_state = 'closed'
        self.state_start_frame = 0
        self.state_start_time = 0.0 
        
        self.timeline_events = []
        
        # Cargar referencias
        self.refs = {}
        for state in ['closed', 'beer', 'foam']:
            filename = f"{name}_{state}.jpg"
            path = os.path.join(refs_folder, filename)
            if os.path.exists(path):
                self.refs[state] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            else:
                self.refs[state] = np.zeros((roi[3], roi[2]), dtype=np.uint8)

    def get_state(self, frame_gray):
        """Devuelve el estado visual actual"""
        x, y, w, h = self.roi
        
        # Protección por si las coordenadas se salen de la imagen al escalar
        h_img, w_img = frame_gray.shape
        if x < 0 or y < 0 or x+w > w_img or y+h > h_img:
            return 'closed'

        crop = frame_gray[y:y+h, x:x+w]
        
        if crop.shape[0] == 0 or crop.shape[1] == 0: return 'closed'

        best_state = 'closed'
        min_diff = float('inf')
        
        for state, ref_img in self.refs.items():
            # Si el video es más pequeño/grande que la referencia, redimensionamos la referencia
            if crop.shape != ref_img.shape:
                try: ref_img = cv2.resize(ref_img, (crop.shape[1], crop.shape[0]))
                except: continue

            diff = cv2.absdiff(crop, ref_img)
            score = np.mean(diff)
            if score < min_diff:
                min_diff = score
                best_state = state
        return best_state

    def update_logic(self, detected_state, frame_idx, fps):
        is_pouring_beer = (detected_state == 'beer')
        was_pouring_beer = (self.current_state == 'beer')
        current_time_sec = frame_idx / fps

        # 1. INICIO
        if is_pouring_beer and not was_pouring_beer:
            self.current_state = 'beer'
            self.state_start_frame = frame_idx
            self.state_start_time = current_time_sec 

        # 2. FIN
        elif not is_pouring_beer and was_pouring_beer:
            duration = current_time_sec - self.state_start_time
            self.total_beer_seconds += duration

            # REGLA DE NEGOCIO:
            if duration > 2.0:
                raw_beers = duration / SECONDS_PER_BEER
                int_part = int(raw_beers)      
                decimal_part = raw_beers - int_part 
                
                if decimal_part > THRESHOLD_ROUNDING:
                    final_beers = int_part + 1
                else:
                    final_beers = int_part
                
                if final_beers < 1: final_beers = 1
                
                self.count += final_beers
                
                event = {
                    "tap": self.name,
                    "start": round(self.state_start_time, 2),
                    "end": round(current_time_sec, 2),
                    "duration": round(duration, 2),
                    "beers": final_beers
                }
                self.timeline_events.append(event)
            
            self.current_state = detected_state 

class BeerCounterEngine:
    def __init__(self, coords_file, refs_folder):
        self.refs_folder = refs_folder
        
        # Variables para guardar las coordenadas RAW (sin escalar)
        self.raw_roi_a = (0,0,0,0)
        self.raw_roi_b = (0,0,0,0)
        self.ref_w = 1920 
        self.ref_h = 1080

        try:
            with open(coords_file, 'r') as f:
                line = f.read().strip()
                parts = line.split('|')
                
                self.raw_roi_a = tuple(map(int, parts[0].split(',')))
                self.raw_roi_b = tuple(map(int, parts[1].split(',')))
                
                # Si existe la 3ª parte (resolución), la cargamos
                if len(parts) > 2:
                    ref_dims = tuple(map(int, parts[2].split(',')))
                    self.ref_w, self.ref_h = ref_dims
                    print(f"📏 Referencia original cargada: {self.ref_w}x{self.ref_h}")
                else:
                    print("⚠️ No se encontró resolución en coords. Asumiendo 1920x1080.")
        except Exception as e:
            print(f"❌ Error leyendo coordenadas: {e}")

    def _apply_scale(self, roi, sx, sy):
        return (int(roi[0] * sx), int(roi[1] * sy), int(roi[2] * sx), int(roi[3] * sy))

    def process_video(self, video_path):
        if not os.path.exists(video_path):
            print("❌ Video no encontrado")
            return {"error": "Video no encontrado"}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
             return {"error": "No se pudo abrir el video"}

        # --- DETECTAR ESCALA Y CREAR GRIFOS ---
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calcular factor de escala
        scale_x = vid_w / self.ref_w
        scale_y = vid_h / self.ref_h
        
        print(f"🎬 Video: {vid_w}x{vid_h} | Escala: X={scale_x:.2f}, Y={scale_y:.2f}")

        # Aplicar escala y crear los objetos SingleTap AHORA
        roi_a_scaled = self._apply_scale(self.raw_roi_a, scale_x, scale_y)
        roi_b_scaled = self._apply_scale(self.raw_roi_b, scale_x, scale_y)
        
        self.tap_a = SingleTap("A", roi_a_scaled, self.refs_folder)
        self.tap_b = SingleTap("B", roi_b_scaled, self.refs_folder)
        # ----------------------------------------------------

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        security_cooldown = 0 
        
        print(f"🎬 Procesando: {os.path.basename(video_path)}")
        start_time = time.time()

        while True:
            # Barra de progreso simple para consola
            if frame_idx % 60 == 0: 
                percent = int(frame_idx / total_frames * 100) if total_frames > 0 else 0
                sys.stdout.write(f'\rProgress: {percent}% ')
                sys.stdout.flush()

            frames_to_skip = 0
            if security_cooldown == 0:
                frames_to_skip = IDLE_SKIP_FRAMES
            
            for _ in range(frames_to_skip):
                cap.grab()
                frame_idx += 1
            
            ret, frame = cap.read()
            if not ret: break
            frame_idx += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            state_a = self.tap_a.get_state(gray)
            state_b = self.tap_b.get_state(gray)
            
            any_active = (state_a != 'closed') or (state_b != 'closed')
            if any_active:
                security_cooldown = COOLDOWN_FRAMES
            else:
                if security_cooldown > 0: security_cooldown -= 1

            self.tap_a.update_logic(state_a, frame_idx, fps)
            self.tap_b.update_logic(state_b, frame_idx, fps)

        cap.release()
        elapsed = time.time() - start_time
        sys.stdout.write('\n') 

        # --- UNIFICAR EVENTOS ---
        all_events = self.tap_a.timeline_events + self.tap_b.timeline_events
        all_events.sort(key=lambda x: x['start'])

        final_duration = 0.0
        if fps > 0 and total_frames > 0:
            final_duration = total_frames / fps
        
        print("-" * 40)
        print(f"✅ Completado en {elapsed:.2f}s")
        print(f"Duración calculada del vídeo: {final_duration:.2f}s")
        print(f"TOTAL: {self.tap_a.count + self.tap_b.count} Cervezas")
        print(f"Eventos registrados: {len(all_events)}")

        return {
        "grifo_a": self.tap_a.count,
        "grifo_b": self.tap_b.count,
        "total": self.tap_a.count + self.tap_b.count,
        "seconds_a": round(self.tap_a.total_beer_seconds, 2),
        "seconds_b": round(self.tap_b.total_beer_seconds, 2),
        "events": all_events,
        "video_duration": round(final_duration, 2)
        }