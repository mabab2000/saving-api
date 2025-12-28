"""
Dynamic icon generator for app notifications
"""
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/app-icon.png")
async def get_app_icon():
    """
    Serve the app icon for push notifications
    """
    # Try to serve the PNG icon if it exists
    icon_path = "static/app-icon.png"
    if os.path.exists(icon_path):
        return FileResponse(icon_path, media_type="image/png")
    
    # Fallback to SVG if PNG doesn't exist
    svg_path = "static/app-icon.svg"
    if os.path.exists(svg_path):
        return FileResponse(svg_path, media_type="image/svg+xml")
    
    # Return a simple response if no icon exists
    return Response(
        content="Icon not found", 
        media_type="text/plain",
        status_code=404
    )