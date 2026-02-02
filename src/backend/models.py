from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.sql import func
from .database import Base

class AnalysisSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="PENDING")
    
    count_a = Column(Integer, default=0)
    count_b = Column(Integer, default=0)
    seconds_a = Column(Float, default=0.0)
    seconds_b = Column(Float, default=0.0)
    
    video_duration = Column(Float, default=0.0) 

    events_data = Column(JSON, default=[])