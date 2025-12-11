import logging, os
import tempfile
from fastapi import APIRouter, Depends, Request, Form, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
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

# Import FaceVerif class for face matching
from utils.face_verif import FaceVerif

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

@router.get("/image/{photo_id}")
async def serve_image(photo_id: int, db: Session = Depends(get_db)):
    """Serve an image from MinIO by photo ID"""
    try:
        # Get photo record from database
        photo = db.query(PhotoVideo).filter(PhotoVideo.id == photo_id).first()
        if not photo:
            return JSONResponse(
                status_code=404,
                content={"error": "Photo not found"}
            )
        
        # Parse file path to get bucket and object name
        # Expected format: bucket_name/object_name
        path_parts = photo.file_path.split('/', 1)
        if len(path_parts) != 2:
            return JSONResponse(
                status_code=500,
                content={"error": "Invalid file path format"}
            )
        
        bucket_name = path_parts[0]
        object_name = path_parts[1]
        
        # Download file from MinIO
        try:
            # Create a temporary file to store the downloaded image
            temp_file_path = None
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                temp_file_path = tmp_file.name
            
            # Download the file to the temporary location
            minio_service.download_file(bucket_name, object_name, temp_file_path)
            
            # Read the file data
            with open(temp_file_path, "rb") as f:
                image_data = f.read()
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            # Determine content type based on file extension
            content_type = "image/jpeg"
            if object_name.lower().endswith('.png'):
                content_type = "image/png"
            elif object_name.lower().endswith('.gif'):
                content_type = "image/gif"
            
            return StreamingResponse(BytesIO(image_data), media_type=content_type)
                
        except Exception as e:
            # Clean up temporary file if it exists
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            logger.error(f"Error downloading file from MinIO: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Error retrieving image from storage"}
            )
            
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

@router.post("/selfie-match", response_class=JSONResponse)
async def selfie_match(
    request: Request,
    selfie_data: str = Form(...),
    person_name: str = Form(...),
    event_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """Process selfie and match against event images using FaceVerif class"""
    try:
        # Decode the selfie image
        selfie_img = decode_base64_image(selfie_data)
        
        if selfie_img is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid image data"}
            )
        
        # Save selfie to temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_selfie:
            cv2.imwrite(tmp_selfie.name, selfie_img)
            selfie_path = tmp_selfie.name
        
        # Get event
        if event_id:
            event = db.query(EventName).filter(EventName.id == event_id).first()
            if not event:
                # Clean up temporary file
                os.unlink(selfie_path)
                return JSONResponse(
                    status_code=404,
                    content={"error": "Event not found"}
                )
        else:
            # Clean up temporary file
            os.unlink(selfie_path)
            return JSONResponse(
                status_code=400,
                content={"error": "Event ID is required for face matching"}
            )
        
        # Get the bucket name from an existing photo in this event
        sample_photo = db.query(PhotoVideo).filter(PhotoVideo.event_id == event_id).first()
        if not sample_photo:
            # Clean up temporary file
            os.unlink(selfie_path)
            return JSONResponse(
                status_code=404,
                content={"error": f"No images found for event: {event.event_name}"}
            )
        
        # Extract bucket name from the file path (format: bucket_name/filename)
        bucket_name = sample_photo.file_path.split('/')[0]
        
        # Check if bucket exists
        try:
            file_list = minio_service.list_files(bucket_name)
        except Exception as e:
            # Clean up temporary file
            os.unlink(selfie_path)
            logger.error(f"Error accessing bucket {bucket_name}: {e}")
            return JSONResponse(
                status_code=404,
                content={"error": f"No images found for event: {event.event_name}"}
            )
        
        # Use FaceVerif to match selfie with images in the bucket
        face_verif = FaceVerif()
        
        # Match selfie with all images in the bucket
        matches = face_verif.match_selfie_with_bucket_images(selfie_path, bucket_name, threshold=0.5)
        
        # Clean up temporary file
        os.unlink(selfie_path)
        
        # Format matches for response
        matched_photos = []
        for file_name, similarity in matches[:10]:  # Limit to top 10 matches
            # Find the corresponding PhotoVideo record
            photo = db.query(PhotoVideo).filter(
                PhotoVideo.file_path == f"{bucket_name}/{file_name}"
            ).first()
            if photo:
                matched_photos.append({
                    "id": photo.id,
                    "file_path": photo.file_path,
                    "similarity": similarity
                })
        
        return JSONResponse({
            "success": True,
            "matches": matched_photos,
            "message": f"Found {len(matched_photos)} potential matches for {person_name} in event {event.event_name}"
        })
        
    except Exception as e:
        logger.error(f"Error processing selfie match: {e}")
        # Clean up temporary file if it exists
        try:
            os.unlink(selfie_path)
        except:
            pass
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error processing selfie"}
        )