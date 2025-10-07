from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    model_validator,
    ConfigDict,
    field_validator,

)
from typing import Annotated
import re
from enum import Enum
from datetime import date
from fastapi import UploadFile, HTTPException, status
import uuid


def validate_password(value):
    if len(value) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must include at least one number.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include at least one upper letter.")
    return value


class UserAccountEnum(str, Enum):
    user = "user"


class UserSchemaIn(BaseModel):
    username: Annotated[
        str,
        Field(
            max_length=50,
            description="Unique identifier chosen by the user to log in and display on their profile",
        ),
    ]
    password: Annotated[
        str,
        Field(
            max_length=100,
            description="Secret string used to authenticate the user; must be kept private and secure.",
        ),
    ]

    confirm_password: Annotated[
        str,
        Field(
            max_length=100,
            description="Field to confirm the user's password."
            "Must match the 'password' field to ensure the user entered their desired password correctly.",
        ),
    ]

    email: Annotated[
        EmailStr,
        Field(
            max_length=100,
            description="User's email address used for login,"
            " communication, and account recovery; must be valid and unique",
        ),
    ]
    scopes: Annotated[
        list[UserAccountEnum],
        Field(
            description="List of roles or permissions assigned to the user, "
            "determining what actions and resources they can access."
        ),
    ]

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return validate_password(value)

    @model_validator(mode="before")
    @classmethod
    def validate_passoword(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values

    model_config = ConfigDict(extra='forbid')


class UserSchemaOut(BaseModel):
    success: str


class Token(BaseModel):
    token_type: str
    access_token: str
    refresh_token: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = []


class Loggout(BaseModel):
    success: str


class NewAccessTokenSchemaOut(BaseModel):
    token_type: str
    access_token: str


class UpdateNameScheamIn(BaseModel):
    new_name: Annotated[
        str, Field(max_length=50,
                   description="The new username to assign to the user.")
    ]
    model_config = ConfigDict(extra='forbid')


class UpdateNameScheamOut(BaseModel):
    success: str


class UpdateUserPasswordSchemaIn(BaseModel):
    new_password: Annotated[
        str,
        Field(
            max_length=100,
            description="Secret string used to authenticate the user; must be kept private and secure.",
        ),
    ]

    confirm_new_password: Annotated[
        str,
        Field(
            max_length=100,
            description="Field to confirm the user's password."
            "Must match the 'password' field to ensure the user entered their desired password correctly.",
        ),
    ]

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, value):
        return validate_password(value)

    @model_validator(mode='before')
    @classmethod
    def validate(cls, values):
        if values.get('new_password') != values.get('confirm_new_password'):
            raise ValueError('Passwords do not match!')
        return values
    model_config = ConfigDict(extra='forbid')


class UpdateUserPasswordSchemaOut(BaseModel):
    success: str


class UpdateUserEmailSchemaIn(BaseModel):
    new_email: EmailStr
    model_config = ConfigDict(extra='forbid')


class UpdateUserEmailSchemaOut(BaseModel):
    new_email: str


class UpdateUserPhoneNumberSchemaIn(BaseModel):
    phone_number: Annotated[str, Field(pattern=r'^\+[1-9]\d{7,14}$')]
    model_config = ConfigDict(extra='forbid')


class UpdateUserPhoneNumberSchemaOut(BaseModel):
    phone_number: str


class UpdateUserDateOfBirthSchemaIn(BaseModel):
    date_of_birth: Annotated[date, Field(
        title="user date of birth.", description='User can not be born before 1900.')]

    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        # Ensure date is not before 1900-01-01
        if value.year < 1900:
            raise ValueError("Date of birth cannot be before 1900.")

        # Optional: check that date is not in the future
        today = date.today()
        if value > today:
            raise ValueError("Date of birth cannot be in the future.")

        return value
    model_config = ConfigDict(extra='forbid')


class UpdateUserDateOfBirthSchemaOut(BaseModel):
    success: str


class UpdateProfilePictureSchemaIn(BaseModel):
    picture: UploadFile

    @field_validator("picture")
    @classmethod
    def validate_picture(cls, value):
        allowed_ext = ["jpeg", "jpg", "png"]
        parts = value.filename.split(".")
        if len(parts) > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file name: Double extensions are not allowed. No more than one dot allowed.",
            )
        ext = parts[-1]
        if ext not in allowed_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only jpeg, jpg, and png files are allowed for images.",
            )
        return value

    model_config = ConfigDict(extra='forbid')


class UpdateProfilePictureSchemaOut(BaseModel):
    success: str


class DeleteProfilePictureSchemaOut(BaseModel):
    success: str


class UserProfileSchemaOut(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    is_active: bool
    date_of_birth: date | None
    profile_picture: str | None


class ReactivateAccountScheamaOut(BaseModel):
    success: str


class DeactivateAccountSchemaOut(BaseModel):
    success: str

    # planner user admin
    # so when a regular user signs up he can only choose user.....
    # but inside scopes we have Socopes(admin,user,planner)
