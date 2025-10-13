from pydantic import BaseModel, EmailStr
import uuid
from datetime import date


class RemoveUserSchemaOut(BaseModel):
    success: str


class IsActiveSchemaOut(BaseModel):
    success: str


class IsActiveSchemaIn(BaseModel):
    is_active: bool


class GetUsersPlannersSchemaOut(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr | None
    is_active: bool
    phone_number: str | None
    date_of_birth: date | None
    profile_picture: str | None
    scopes: list[str] = []
