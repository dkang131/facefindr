import logging, io, qrcode
from fastapi import APIRouter, Request, HTTPException, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from jose import jwt 
from jose.exceptions import JWTError
from database import get_db
from models import Admin, EventName, PhotoVideo
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="cms/templates")

# JWT Config
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def populate_photo_video_table(gsheet_link: str, event_id: int, db: Session):
    """Placeholder function to populate photo/video table from Google Sheet"""
    # This would contain the actual implementation to read from Google Sheets
    # For now, we'll just log that it was called
    logger.info(f"Populating photo/video table for event {event_id} from {gsheet_link}")
    # In a real implementation, you would parse the Google Sheet and create PhotoVideo entries

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
    gsheet_link: str = Form(...),
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
    
    logger.info(f"User {user_email} uploading event: {event_name} with link: {gsheet_link}")
    
    # Save the event to the database
    new_event = EventName(
        event_name=event_name,
        gsheet_link=gsheet_link
    )
    
    try:
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        logger.info(f"Event saved to database with ID: {new_event.id}")
        
        # Now populate the PhotoVideo table by reading from the Google Sheet
        populate_photo_video_table(gsheet_link, new_event.id, db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving event to database: {e}")
        raise HTTPException(status_code=500, detail="Error saving event")
    
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