from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """Week 1 Foundation health check endpoint"""
    return {"status": "healthy"}
