import os
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid
from pathlib import Path
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://klgiypbuqblpzaihabda.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_7xpZog5lcHCCQyd0UWglSA_5u1G-iXN")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "policy_files")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_image_to_supabase(file_content: bytes, filename: str, folder: str = "saving-image") -> str:
    """
    Upload an image to Supabase storage
    
    Args:
        file_content: The binary content of the file
        filename: The name of the file
        folder: The folder path within the bucket (default: 'saving-image')
        
    Returns:
        str: The public URL of the uploaded file
    """
    try:
        # Generate unique filename
        file_ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Full path in bucket
        file_path = f"{folder}/{unique_filename}"
        
        logger.info(f"Uploading file to Supabase: {file_path}")
        
        # Upload file to Supabase storage
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_path)
        
        logger.info(f"File uploaded successfully: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Error uploading to Supabase: {str(e)}")
        raise


def delete_image_from_supabase(file_path: str) -> bool:
    """
    Delete an image from Supabase storage
    
    Args:
        file_path: The path of the file in the bucket (e.g., 'saving-image/filename.jpg')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract the path from URL if a full URL is provided
        if file_path.startswith("http"):
            # Extract path after bucket name
            parts = file_path.split(f"{SUPABASE_BUCKET}/")
            if len(parts) > 1:
                file_path = parts[1]
        
        logger.info(f"Deleting file from Supabase: {file_path}")
        
        response = supabase.storage.from_(SUPABASE_BUCKET).remove([file_path])
        
        logger.info(f"File deleted successfully: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting from Supabase: {str(e)}")
        return False
