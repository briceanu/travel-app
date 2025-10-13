from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from datetime import datetime, date
from typing import Annotated
from decimal import Decimal
import uuid
from fastapi import UploadFile


class ActivitySchemaIn(BaseModel):
    name: Annotated[
        str,
        Field(
            max_length=100,
            description="The name or title of the activity to be created.",
        ),
    ]
    description: Annotated[
        str,
        Field(
            max_length=100,
            description="Short description of the activity.",
        ),
    ]
    start_time: Annotated[
        datetime,
        Field(
            description="The starting date and time of the activity. "
            "Must be a valid ISO 8601 datetime (e.g., '09:00:00').",
        ),
    ]

    end_time: Annotated[
        datetime,
        Field(
            description="The ending date and time of the activity. "
            "Must occur after the start time and follow the same ISO 8601 format.",
        ),
    ]

    price: Annotated[
        Decimal,
        Field(
            ge=0,
            max_digits=6,
            decimal_places=2,
            description="The cost associated with the activity in the selected currency. "
            "Must be a non-negative value (e.g., 49.99).",
        ),
    ]
    destination_id: Annotated[uuid.UUID, Field(
        description="The id of the destination")]
    model_config = ConfigDict(extra="forbid")


class ActivitySchemaOutResponse(BaseModel):
    success: str


class ActivitySchemaOut(BaseModel):
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    activity_id: uuid.UUID


class TripSchemaIn(BaseModel):
    title: Annotated[
        str, Field(max_length=100, description="The name or title of the trip.")
    ]
    description: Annotated[
        str, Field(max_length=300, description="Short description of the trip.")
    ]
    trip_type: Annotated[
        str,
        Field(
            max_length=100, description="Type of the trip (e.g., adventure, leisure)."
        ),
    ]
    start_date: Annotated[date, Field(
        description="The starting date of the trip.")]
    end_date: Annotated[date, Field(
        description="The ending date of the trip.")]
    estimated_budget: Annotated[
        Decimal, Field(description="Estimated budget for the trip.")
    ]

    model_config = ConfigDict(extra="forbid")


class TripSchemaOutResponse(BaseModel):
    success: str


class ParticipantsSchemaOut(BaseModel):
    user_id: uuid.UUID
    username: str
    date_of_birth: date | None
    email: EmailStr
    phone_number: str | None


class DestinationSchemaOut(BaseModel):
    name: str
    destination_id: uuid.UUID
    description: str
    country: str
    language: str
    best_time_to_visit: str
    images: list = []
    activities: list[ActivitySchemaOut] = []


class DestinationSchemaOutResponse(BaseModel):
    success: str


class TripSchemaOut(BaseModel):
    title: str
    trip_id: uuid.UUID
    description: str
    trip_type: str
    start_date: date
    end_date: date
    duration: str
    estimated_budget: Decimal
    destinations: list[DestinationSchemaOut]
    participants: list[ParticipantsSchemaOut] = []


class DestinationSchemaIn(BaseModel):
    name: Annotated[
        str,
        Field(max_length=100, description="The name of the destination."),
    ]
    description: Annotated[
        str,
        Field(max_length=300, description="Short description of the destination."),
    ]
    country: Annotated[
        str,
        Field(
            max_length=50, description="The country where the destination is located."
        ),
    ]
    language: Annotated[
        str,
        Field(
            max_length=50, description="The primary language spoken at the destination."
        ),
    ]
    best_time_to_visit: Annotated[
        str,
        Field(
            max_length=100, description="Best time or season to visit the destination."
        ),
    ]
    images: list[UploadFile]

    trip_id: Annotated[
        uuid.UUID,
        Field(description="The ID of the trip this destination belongs to."),
    ]

    @field_validator('images')
    @classmethod
    def validate_images(cls, value):
        if len(value) > 2:
            raise ValueError('Maximum 2 images can be uploaded.')
        allowed_extensions = ['jpg', 'jpeg', 'png']
        for image in value:
            filename = image.filename
            if "." not in filename:
                raise ValueError(f"File '{filename}' has no extension.")
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed_extensions:
                raise ValueError(
                    f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}.")

        return value

    model_config = ConfigDict(extra="forbid")


class TripReomveSchemaOut(BaseModel):
    success: str
