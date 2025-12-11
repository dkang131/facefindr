from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from extensions import Base  # ← import from extensions
from datetime import datetime

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

class EventName(Base):
    __tablename__ = "event_names"
    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PhotoVideo(Base):
    __tablename__ = "photo_videos"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("event_names.id"))
    file_path = Column(String)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("EventName", back_populates="photos_videos")

# Add relationship to EventName
EventName.photos_videos = relationship("PhotoVideo", back_populates="event")