from fastapi import HTTPException, status
from app.config.settings import settings

ALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".gif", 
    ".zip", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".json"
}

ALLOWED_MIME_TYPES = {
    "text/plain", "application/pdf", "image/png", "image/jpeg", "image/gif",
    "application/zip", "application/x-zip-compressed", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/json", "text/csv",
    "application/octet-stream"  # allowed fallback for binary payload
}

def validate_file_metadata(filename: str, file_size: int, content_type: str = None):
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded. File size must be greater than 0 bytes."
        )
        
    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size limit of {settings.MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB."
        )
        
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

def validate_email_format(email: str) -> bool:

    import re
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_regex, email))
