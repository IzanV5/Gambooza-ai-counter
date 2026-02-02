from src.backend.video_fixer import fix_video_for_web, check_video_is_healthy
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, database
import shutil
import os

# --- IMPORTAMOS EL MOTOR DE IA ---
from src.ai.production_counter import BeerCounterEngine

# Configuramos las rutas a las referencias
BASE_DIR = os.getcwd() # Directorio raíz del proyecto
REFS_FOLDER = os.path.join(BASE_DIR, "src", "ai", "referencias")
COORDS_FILE = os.path.join(REFS_FOLDER, "coords_dual.txt")

# Inicializamos la DB
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Gambooza Beer Counter")

# Permitir que el frontend acceda a los vídeos subidos y reparados
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def process_video_background(session_id: int, video_path: str, db: Session):
    print(f"👷 WORKER: Iniciando procesamiento para ID {session_id}...")
    
    session = db.query(models.AnalysisSession).filter(models.AnalysisSession.id == session_id).first()
    session.status = "PROCESSING"
    db.commit()
    
    try:
        # --- PASO 1: DIAGNÓSTICO Y REPARACIÓN CONDICIONAL ---
        final_video_path = video_path
        final_filename = os.path.basename(video_path)

        # Chequeamos si está sano
        if check_video_is_healthy(video_path):
            print("✨ Video SANO. Omitiendo reparación para máxima velocidad.")
        else:
            print("🩹 Video CORRUPTO/RAW detectado. Ejecutando reparación rápida...")
            fixed_filename = fix_video_for_web(video_path)
            # Actualizamos rutas para usar el arreglado
            final_filename = fixed_filename
            final_video_path = os.path.join(UPLOAD_DIR, fixed_filename)
            
            # Actualizamos BD para que el frontend cargue el bueno
            session.filename = fixed_filename
            db.commit()
        
        # --- PASO 2: USO DE LA IA ---
        engine = BeerCounterEngine(COORDS_FILE, REFS_FOLDER)
        results = engine.process_video(final_video_path)
        
        session.count_a = results["grifo_a"]
        session.count_b = results["grifo_b"]
        session.seconds_a = results["seconds_a"]
        session.seconds_b = results["seconds_b"]
        session.video_duration = results["video_duration"]
        session.events_data = results["events"]
        
        session.status = "COMPLETED"
        print(f"✅ WORKER: ID {session_id} Terminado.")

    except Exception as e:
        print(f"❌ WORKER ERROR: {e}")
        session.status = "ERROR"
    
    finally:
        db.commit()
        db.close()

app.mount("/static", StaticFiles(directory="src/frontend"), name="static")
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("src/frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/upload/")
def upload_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db)
):
    # 1. Guardar archivo
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. Crear registro DB (PENDING)
    db_session = models.AnalysisSession(filename=file.filename, status="PENDING")
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # 3. ENCOLAR TAREA EN SEGUNDO PLANO
    # Pasamos una nueva sesión de DB porque la principal se cierra al retornar
    db_for_worker = database.SessionLocal() 
    background_tasks.add_task(process_video_background, db_session.id, file_location, db_for_worker)
    
    # 4. Responder INMEDIATAMENTE al usuario
    return {
        "id": db_session.id,
        "status": "PENDING",
        "message": "Video recibido. Procesamiento iniciado en segundo plano."
    }

@app.get("/results/{session_id}")
def get_result(session_id: int, db: Session = Depends(database.get_db)):
    """Consultar estado del análisis"""
    session = db.query(models.AnalysisSession).filter(models.AnalysisSession.id == session_id).first()
    if not session:
        return {"error": "Session not found"}
    
    return session