from fastapi import Header, HTTPException, status
from app.core.config import settings

def verify_internal_secret(x_internal_secret: str = Header(None, alias="x-internal-secret")):
    """Verifies that the request carries the pre-shared internal communication secret."""
    if not x_internal_secret or x_internal_secret != settings.INTERNAL_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing internal communication secret."
        )
    return True
