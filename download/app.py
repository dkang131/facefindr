import logging, os
from fastapi import APIRouter, Depends, Request, Form, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from jose import jwt 
from jose.exceptions import JWTError
from database import get_db
from models import Admin, EventName, PhotoVideo
from config import settings
from services.minio_service import minio_service
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

# utils for MTCNN face matching
try:
    from facenet_pytorch import MTCNN
    mtcnn = MTCNN(keep_all=True)
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logging.warning("MTCNN not available. Face recognition features will be disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="download/templates")

router = APIRouter()

def decode_base64_image(image_data):
    """Decode base64 image data to OpenCV image"""
    # Remove the data URL prefix if present
    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
    
    # Decode base64 string to bytes
    image_bytes = base64.b64decode(image_data)
    
    # Convert bytes to numpy array
    np_arr = np.frombuffer(image_bytes, np.uint8)
    
    # Decode image using OpenCV
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    return img

def extract_faces_from_image(image):
    """Extract faces from an image using MTCNN"""
    if not FACE_RECOGNITION_AVAILABLE:
        return []
    
    try:
        # Convert BGR to RGB (OpenCV uses BGR, PIL uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Detect faces
        boxes, _ = mtcnn.detect(pil_image)
        
        if boxes is None:
            return []
            
        faces = []
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            # Extract face region
            face = image[y1:y2, x1:x2]
            faces.append(face)
            
        return faces
    except Exception as e:
        logger.error(f"Error extracting faces: {e}")
        return []

def compare_faces(face1, face2):
    """Compare two faces and return similarity score (placeholder implementation)"""
    # This is a placeholder - in a real implementation, you would use a face recognition model
    # to generate embeddings and compare them
    if not FACE_RECOGNITION_AVAILABLE:
        return 0.0
    
    try:
        # Convert to RGB
        face1_rgb = cv2.cvtColor(face1, cv2.COLOR_BGR2RGB)
        face2_rgb = cv2.cvtColor(face2, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Images
        pil_face1 = Image.fromarray(face1_rgb)
        pil_face2 = Image.fromarray(face2_rgb)
        
        # Get embeddings (this is a simplified approach)
        embedding1 = mtcnn(pil_face1)
        embedding2 = mtcnn(pil_face2)
        
        if embedding1 is None or embedding2 is None:
            return 0.0
            
        # Calculate cosine similarity
        similarity = np.dot(embedding1[0], embedding2[0]) / (
            np.linalg.norm(embedding1[0]) * np.linalg.norm(embedding2[0])
        )
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error comparing faces: {e}")
        return 0.0

@router.get("/", response_class=HTMLResponse)
async def download_page(request: Request, event_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    # Get the event if specified
    event = None
    if event_id:
        event = db.query(EventName).filter(EventName.id == event_id).first()
    else:
        # Get the first event as default
        events = db.query(EventName).all()
        if events:
            event = events[0]  # Default to first event for now
    
    return templates.TemplateResponse("download.html", {
        "request": request,
        "event": event,
        "media_found": None,
        "drive_link": None
    })

@router.post("/selfie-match", response_class=JSONResponse)
async def selfie_match(
    request: Request,
    selfie_data: str = Form(...),
    person_name: str = Form(...),
    event_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Process selfie and match against event images"""
    try:
        # Decode the selfie image
        selfie_img = decode_base64_image(selfie_data)
        
        if selfie_img is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid image data"}
            )
        
        # Extract face from selfie
        selfie_faces = extract_faces_from_image(selfie_img)
        
        if not selfie_faces:
            return JSONResponse(
                status_code=400,
                content={"error": "No face detected in selfie"}
            )
        
        # Get event images
        if event_id:
            event_photos = db.query(PhotoVideo).filter(
                PhotoVideo.event_id == event_id
            ).all()
        else:
            # Get photos from all events
            event_photos = db.query(PhotoVideo).all()
        
        if not event_photos:
            return JSONResponse(
                status_code=404,
                content={"error": "No photos found for matching"}
            )
        
        # For demo purposes, we'll return a simplified response
        # In a real implementation, you would compare the selfie with each photo
        matched_photos = []
        
        # This is a placeholder implementation - in reality, you would:
        # 1. Download each photo from MinIO
        # 2. Extract faces from each photo
        # 3. Compare each face with the selfie
        # 4. Return matches above a threshold
        
        # For now, we'll just return the first few photos as examples
        for photo in event_photos[:5]:  # Limit to first 5 for demo
            matched_photos.append({
                "id": photo.id,
                "file_path": photo.file_path,
                "similarity": 0.85  # Placeholder similarity score
            })
        
        return JSONResponse({
            "success": True,
            "matches": matched_photos,
            "message": f"Found {len(matched_photos)} potential matches for {person_name}"
        })
        
    except Exception as e:
        logger.error(f"Error processing selfie match: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error processing selfie"}
        )