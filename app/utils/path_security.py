import os
import re
from pathlib import Path
from fastapi import HTTPException, status

UNSAFE_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def sanitize_filename(filename: str) -> str:

    if not filename or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty"
        )
    
    # Strip path components to prevent path traversal
    clean_name = Path(filename).name
    
    # Replace dangerous character sequences
    clean_name = UNSAFE_CHARS_PATTERN.sub('_', clean_name)
    
    # Trim excessive length
    if len(clean_name) > 200:
        base, ext = os.path.splitext(clean_name)
        clean_name = base[:190] + ext[:10]
        
    if clean_name in ('.', '..', ''):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
        
    return clean_name

def validate_safe_path(base_dir: str, target_path: str) -> bool:

    try:
        resolved_base = Path(base_dir).resolve()
        resolved_target = Path(target_path).resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except Exception:
        return False
