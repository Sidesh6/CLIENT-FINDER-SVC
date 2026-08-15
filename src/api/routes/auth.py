"""
FastAPI Authentication & User Identity REST Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.auth.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)
from src.auth.security import create_access_token
from src.auth.store import GLOBAL_TENANT_STORE

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user_and_workspace(req: UserRegisterRequest) -> TokenResponse:
    """
    Register a new user account and provision their initial tenant workspace.
    """
    try:
        user, tenant = GLOBAL_TENANT_STORE.register_user(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            workspace_name=req.workspace_name,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err

    token = create_access_token(
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=86400,
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
def login_for_access_token(req: UserLoginRequest) -> TokenResponse:
    """
    Authenticate credentials and issue a signed JWT access token.
    """
    user = GLOBAL_TENANT_STORE.authenticate(email=req.email, password=req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        role=user.role,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=86400,
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_authenticated_user_profile(
    user: UserProfileResponse = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Retrieve authenticated user identity and workspace subscription tier.
    """
    return user
