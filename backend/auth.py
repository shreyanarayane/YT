from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from backend.supabase_store import AuthenticatedUser, SupabaseConfigurationError, store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[AuthenticatedUser]:
    if not token:
        return None
    try:
        return store.current_user(token)
    except (PermissionError, SupabaseConfigurationError):
        return None
    except RuntimeError as exc:
        # A valid user must not be treated as anonymous merely because the
        # Supabase project is temporarily unreachable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service is unavailable: {exc}",
        ) from exc


def require_current_user(user: Optional[AuthenticatedUser] = Depends(get_current_user)) -> AuthenticatedUser:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: AuthenticatedUser = Depends(require_current_user)) -> AuthenticatedUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user
