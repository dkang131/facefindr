import logging, io, qrcode
from fastapi import APIRouter, Request, HTTPException, Form, Depends, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from jose import jwt 
from jose.exceptions import JWTError
from database import get_db
from models import Admin, EventName, PhotoVideo
from config import settings
from services.minio_service import minio_service
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="cms/templates")

# JWT Config
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def create_minio_bucket(bucket_name: str):
    """Create a MinIO bucket for storing event images"""
    # This would contain the actual implementation to create a MinIO bucket
    # For now, we'll just log that it was called
    logger.info(f"Creating MinIO bucket: {bucket_name}")
    # In a real implementation, you would use the MinIO client to create the bucket

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    items_per_page: int = Query(10, le=100)
):
    # Check if user is authenticated by validating JWT token
    token = request.cookies.get("access_token")
    logger.info(f"Token from cookie: {token}")
    
    if not token:
        # Redirect to login if not authenticated
        logger.info("No access token found")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            logger.info("Invalid token payload")
            raise HTTPException(status_code=401, detail="Not authenticated")
    except JWTError as e:
        logger.info(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.info(f"User email from token: {user_email}")
    
    # Build query for events
    query = db.query(EventName)
    
    # Apply search filter if provided
    if search:
        query = query.filter(EventName.event_name.contains(search))
    
    # Get total count for pagination
    total_events = query.count()
    
    # Apply pagination
    offset = (page - 1) * items_per_page
    events = query.offset(offset).limit(items_per_page).all()
    
    # Calculate pagination info
    total_pages = (total_events + items_per_page - 1) // items_per_page
    
    return templates.TemplateResponse("cms.html", {
        "request": request,
        "events": events,
        "current_page": page,
        "total_pages": total_pages,
        "total_events": total_events,
        "search_query": search or "",
        "items_per_page": items_per_page
    })

@router.post("/upload-event")
async def upload_event(
    request: Request,
    event_name: str = Form(...),
    event_images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # Check if user is authenticated by validating JWT token
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
    except JWTError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.info(f"User {user_email} uploading event: {event_name} with {len(event_images)} images")
    
    # Save the event to the database
    new_event = EventName(
        event_name=event_name
    )
    
    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        logger.info(f"Event saved to database with ID: {new_event.id}")
        
        # Create MinIO bucket for this event
        bucket_name = f"event-{new_event.id}"
        minio_service.create_bucket(bucket_name)
        
        # Upload images to MinIO
        for image in event_images:
            if image.filename:
                # Generate a unique filename
                file_extension = os.path.splitext(image.filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                # Save temporary file
                temp_file_path = f"temp_{unique_filename}"
                with open(temp_file_path, "wb") as buffer:
                    buffer.write(await image.read())
                
                # Upload to MinIO
                minio_service.upload_file(bucket_name, unique_filename, temp_file_path)
                
                # Remove temporary file
                os.remove(temp_file_path)
                
                # Save image info to database
                photo_video = PhotoVideo(
                    event_id=new_event.id,
                    file_path=f"{bucket_name}/{unique_filename}"
                )
                db.add(photo_video)
        
        db.commit()
        logger.info(f"Uploaded {len(event_images)} images to MinIO for event ID: {new_event.id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving event to database: {e}")
        raise HTTPException(status_code=500, detail="Error saving event")
    
    return RedirectResponse(url="/cms/dashboard", status_code=303)

@router.post("/edit-event/{event_id}")
async def edit_event(
    event_id: int,
    request: Request,
    event_name: str = Form(...),
    new_images: List[UploadFile] = File(default=None),
    db: Session = Depends(get_db)
):
    # Check if user is authenticated by validating JWT token
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
    except JWTError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.info(f"User {user_email} editing event ID: {event_id}")
    
    # Get the event from the database
    event = db.query(EventName).filter(EventName.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update event name if provided
    if event_name:
        event.event_name = event_name
    
    try:
        # Upload new images to MinIO if provided
        if new_images and any(image.filename for image in new_images):
            bucket_name = f"event-{event_id}"
            
            # Upload new images to MinIO
            for image in new_images:
                if image.filename:
                    # Generate a unique filename
                    file_extension = os.path.splitext(image.filename)[1]
                    unique_filename = f"{uuid.uuid4()}{file_extension}"
                    
                    # Save temporary file
                    temp_file_path = f"temp_{unique_filename}"
                    with open(temp_file_path, "wb") as buffer:
                        buffer.write(await image.read())
                    
                    # Upload to MinIO
                    minio_service.upload_file(bucket_name, unique_filename, temp_file_path)
                    
                    # Remove temporary file
                    os.remove(temp_file_path)
                    
                    # Save image info to database
                    photo_video = PhotoVideo(
                        event_id=event_id,
                        file_path=f"{bucket_name}/{unique_filename}"
                    )
                    db.add(photo_video)
        
        db.commit()
        logger.info(f"Event ID {event_id} updated successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail="Error updating event")
    
    return RedirectResponse(url="/cms/dashboard", status_code=303)

@router.post("/delete-event/{event_id}")
async def delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Check if user is authenticated by validating JWT token
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
    except JWTError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.info(f"User {user_email} deleting event ID: {event_id}")
    
    # Get the event from the database
    event = db.query(EventName).filter(EventName.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    try:
        # Delete all associated photos/videos
        db.query(PhotoVideo).filter(PhotoVideo.event_id == event_id).delete()
        
        # Delete the event
        db.delete(event)
        
        # Delete MinIO bucket (optional)
        # minio_service.delete_bucket(f"event-{event_id}")
        
        db.commit()
        logger.info(f"Event ID {event_id} deleted successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail="Error deleting event")
    
    return RedirectResponse(url="/cms/dashboard", status_code=303)

@router.get("/qr/{event_id}")
async def generate_qr_code(event_id: int, db: Session = Depends(get_db)):
    """Generate a QR code for an event that links to the download page."""
    # Get the event from the database
    event = db.query(EventName).filter(EventName.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Generate QR code linking to the download page for this event
    download_url = f"{settings.FRONTEND_URL}/download?event_id={event_id}"
    
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(download_url)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return StreamingResponse(img_bytes, media_type="image/png")