import os, uvicorn, logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from config import settings

from sqlalchemy import create_engine
from extensions import Base
from models import Admin, EventName, PhotoVideo

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
logger.info("Initializing database...")
engine = create_engine(settings.DATABASE_URL)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")
    raise

# Import routers
from auth.app import router as auth_router
from cms.app import router as cms_router
from download.app import router as download_router

app = FastAPI()

# Mount static
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static directories mounted successfully")
except Exception as e:
    logger.error(f"Failed to mount static directories: {e}")

app.include_router(auth_router, prefix="/auth")
app.include_router(cms_router, prefix="/cms")
app.include_router(download_router, prefix="/download")

@app.get("/")
async def root():
    # return {"message": "FaceFindr API"}
    return RedirectResponse(url="/auth/login")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7219)