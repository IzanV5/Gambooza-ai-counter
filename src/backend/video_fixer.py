import cv2
import os

def check_video_is_healthy(input_path):
    """
    Comprueba rápidamente si el vídeo tiene metadatos válidos (índice).
    Devuelve True si está sano, False si necesita reparación.
    """
    try:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return False
            
        # Comprobamos si tiene frames contados y FPS válidos
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        cap.release()
        
        # Si frame_count es 0 o menor, es un stream sin índice (CORRUPTO para web)
        if frame_count <= 0 or fps <= 0:
            print(f"⚠ Diagnóstico: Video sin índice (Frames: {frame_count}, FPS: {fps}) -> NECESITA REPARACIÓN")
            return False
        
        print(f"✅ Diagnóstico: Video sano (Frames: {frame_count}, FPS: {fps}) -> OK")
        return True
        
    except:
        return False

def fix_video_for_web(input_path):
    """
    Repara el vídeo reescribiéndolo.
    Reduce la resolución para ir MUCHO más rápido.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video no encontrado: {input_path}")

    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    name, ext = os.path.splitext(base_name)
    output_filename = f"{name}_fixed.mp4"
    output_path = os.path.join(dir_name, output_filename)

    # Si ya existe el arreglado de una vez anterior, no lo repetimos
    if os.path.exists(output_path):
        print("✅ Video reparado ya existente. Saltando proceso.")
        return output_filename

    print(f"🔧 REPARADOR: Iniciando optimización rápida de {base_name}...")

    cap = cv2.VideoCapture(input_path)
    
    # Datos originales
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 25.0 # Fallback estándar

    # Si el video es muy grande (> 720p), lo reducimos para la web.
    # Esto acelera la escritura exponencialmente.
    scale = 1.0
    if orig_w > 1280:
        scale = 0.5 
    elif orig_w > 800:
        scale = 0.7
        
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    
    print(f"   ℹ Redimensionando: {orig_w}x{orig_h} -> {new_w}x{new_h} (Escala: {scale})")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_w, new_h))

    frames_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # Solo redimensionamos si es necesario
            if scale != 1.0:
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            out.write(frame)
            frames_count += 1
            
            # Log menos frecuente para no saturar consola
            if frames_count % 300 == 0:
                print(f"   ...procesando frame {frames_count}")
                
    except Exception as e:
        print(f"⚠ Error durante reparación: {e}")
    finally:
        cap.release()
        out.release()
        print(f"✅ REPARADOR: Finalizado en {output_filename}")

    return output_filename