"""Auth endpoints: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    from app.security import hash_password

    user = User(
        name=payload.name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Registration conflict") from None
    db.refresh(user)

    token = create_access_token(str(user.id), extra={"role": user.role, "name": user.name})
    return TokenResponse(access_token=token, user=UserInfo.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    token = create_access_token(str(user.id), extra={"role": user.role, "name": user.name})
    return TokenResponse(access_token=token, user=UserInfo.model_validate(user))


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user)):
    return UserInfo.model_validate(current_user)
