from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import DateTime, Time, MetaData, Interval, String, Date, Integer, Numeric, JSON, Column, Table, ForeignKey
from datetime import datetime, date, time, timedelta
import uuid
from decimal import Decimal


class Base(DeclarativeBase, AsyncAttrs):
    """Base class for all models"""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class User(Base):
    __tablename__ = "user_table"

    user_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=lambda: uuid.uuid4(), unique=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=True)
    profile_picture: Mapped[str] = mapped_column(
        String(200), nullable=True, default=None)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=[], nullable=False)
    trips: Mapped[list['Trip']] = relationship(
        back_populates='participants', secondary='user_trip_association_course', cascade='all')


class Trip(Base):
    __tablename__ = "trip_table"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=lambda: uuid.uuid4(), unique=True, nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    trip_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_budget: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False)

    participants: Mapped[list['User']] = relationship(
        back_populates='trips', secondary='user_trip_association_course'
    )
    destinations: Mapped[list['Destination']] = relationship(
        back_populates='trip', cascade='all, delete-orphan'
    )


class Destination(Base):
    __tablename__ = "destination_table"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=lambda: uuid.uuid4(), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    best_time_to_visit: Mapped[str] = mapped_column(
        String(100), nullable=False)
    images: Mapped[list[str]] = mapped_column(JSON, default=[], nullable=False)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Trip.trip_id, ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    trip: Mapped['Trip'] = relationship(back_populates='destinations')
    activities: Mapped[list['Activity']] = relationship(
        back_populates='destination', cascade='all, delete-orphan'
    )


class Activity(Base):
    __tablename__ = "activity_table"

    activity_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=lambda: uuid.uuid4(), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    duration: Mapped[timedelta] = mapped_column(Interval, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(Destination.destination_id, ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    destination: Mapped['Destination'] = relationship(
        back_populates='activities')


user_trip_association_course = Table(
    'user_trip_association_course',
    Base.metadata,
    Column('user_id', ForeignKey(User.user_id, ondelete='CASCADE',
           onupdate='CASCADE'), primary_key=True),
    Column('trip_id', ForeignKey(Trip.trip_id, ondelete='CASCADE',
           onupdate='CASCADE'), primary_key=True)

)


# 1. Decide relationships clearly:

# Trip has many Destinations

# Destination belongs to one Trip

# Destination has many Activities

# Activity belongs to one Destination
