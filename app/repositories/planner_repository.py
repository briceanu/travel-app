from app.utils.celery_tasks import s3_upload
import os
from app.interfaces.planner_interfaces import AbstractPlannerInterface
from dataclasses import dataclass
from app.models.app_models import User, Trip, Destination
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete
from sqlalchemy.exc import IntegrityError
from app.models.app_models import Activity
from app.schemas import planner_schemas
from fastapi.exceptions import HTTPException
from fastapi import status
import uuid
from sqlalchemy.orm import joinedload, selectinload
from dotenv import load_dotenv
from app.utils.boto3_client import s3_presigned_url

load_dotenv()

REFRESH_SECRET = os.getenv("REFRESH_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
BUCKET_NAME = os.getenv("BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")


@dataclass
class PlannerRepository(AbstractPlannerInterface):
    user: User | None = None
    async_session: AsyncSession | None = None
    activity_data: planner_schemas.ActivitySchemaIn | None = None
    trip_data: planner_schemas.TripSchemaIn | None = None
    destination_data: planner_schemas.DestinationSchemaIn | None = None
    trip_id_to_remove: uuid.UUID | None = None

    async def create_activity_interface(
        self,
    ) -> planner_schemas.ActivitySchemaOutResponse:
        """
        Create a new activity associated with an existing destination.

        This method performs the following steps:
        1. Verifies that the provided `destination_id` exists in the database.
        Raises an HTTP 400 error if the destination is not found.
        2. Calculates the duration of the activity as the difference between
        `end_time` and `start_time`.
        3. Inserts a new record into the `Activity` table with the provided data,
        including name, description, start and end times, price, duration,
        and the associated destination ID.
        4. Returns the newly created activity's ID in a success response.

        Returns:
            planner_schemas.ActivitySchemaOutResponse: A schema containing a
            success message with the newly created activity's ID.

        Raises:
            HTTPException 400: If the specified destination does not exist.
        """

        destination_id = (
            await self.async_session.execute(
                select(Destination.destination_id).where(
                    Destination.destination_id == self.activity_data.destination_id
                )
            )
        ).scalar_one_or_none()
        if not destination_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No destination with the id {self.activity_data.destination_id} found.",
            )
        duration = self.activity_data.end_time - self.activity_data.start_time

        stmt = (
            insert(Activity)
            .values(
                name=self.activity_data.name,
                description=self.activity_data.description,
                start_time=self.activity_data.start_time,
                end_time=self.activity_data.end_time,
                price=self.activity_data.price,
                duration=duration,
                destination_id=destination_id,
            )
            .returning(Activity.activity_id)
        )

        activity_id = (await self.async_session.execute(stmt)).scalar_one_or_none()
        await self.async_session.commit()
        return planner_schemas.ActivitySchemaOutResponse(
            success=f"Activity with id {activity_id} saved."
        )

    async def create_trip_interface(self) -> planner_schemas.TripSchemaOutResponse:
        """
        Create a new trip record in the database.

        This method performs the following steps:
        1. Calculates the trip duration in days as the difference between
        `end_date` and `start_date`.
        2. Inserts a new `Trip` record into the database with the provided
        title, description, trip type, start and end dates, duration,
        and estimated budget.
        3. Returns the newly created trip's ID in a success response if the
        insertion is successful.
        4. Rolls back the transaction and raises an HTTP 400 error if a
        database integrity error occurs (e.g., constraint violation).

        Returns:
            planner_schemas.TripSchemaOutResponse: A schema containing a
            success message with the newly created trip's ID.

        Raises:
            HTTPException 400: If a database integrity error occurs during trip creation.
        """
        # calculate duration in days
        duration = (self.trip_data.end_date - self.trip_data.start_date).days

        try:
            stmt = (
                insert(Trip)
                .values(
                    title=self.trip_data.title,
                    description=self.trip_data.description,
                    trip_type=self.trip_data.trip_type,
                    start_date=self.trip_data.start_date,
                    end_date=self.trip_data.end_date,
                    duration=duration,
                    estimated_budget=self.trip_data.estimated_budget,
                )
                .returning(Trip.trip_id)
            )

            trip_id = (await self.async_session.execute(stmt)).scalar_one_or_none()
            await self.async_session.commit()
            return planner_schemas.TripSchemaOutResponse(
                success=f"Trip with id {trip_id} successfully created"
            )

        except IntegrityError as e:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity error: {str(e)}",
            )

    async def create_destination_interface(
        self,
    ) -> planner_schemas.DestinationSchemaOutResponse:
        """
        Create a new destination associated with an existing trip.

        This method performs the following steps:
        1. Validates that the provided `trip_id` exists in the database.
        Raises an HTTP 404 error if no corresponding trip is found.
        2. Inserts a new record into the `Destination` table using the provided
        destination details such as name, description, country, language,
        best time to visit, and associated trip ID.
        3. Returns the newly created destination's ID in a success response
        upon successful insertion and commit.
        4. Handles database integrity errors by rolling back the transaction
        and raising an HTTP 400 error with the relevant error message.

        Returns:
            planner_schemas.DestinationSchemaOutResponse: A schema containing a
            success message and the newly created destination's ID.

        Raises:
            HTTPException 404: If the specified trip ID does not exist.
            HTTPException 400: If a database integrity error occurs during destination creation.
        """
        try:
            # save in the db only the key
            key = str(self.user.user_id)
            images_name = [
                image.filename for image in self.destination_data.images]
            destination_images = [
                f"{key}/{image_name}"
                for image_name in images_name
            ]
            # uploading to s3
            for image in self.destination_data.images:
                s3_upload.delay(
                    bucket=BUCKET_NAME,
                    key=f'{key}/{image.filename}',
                    content_type=f"image/{image.filename.split('.')[-1]}",
                    body=await image.read(),
                )

            trip_id = (
                await self.async_session.execute(
                    select(Trip.trip_id).where(
                        Trip.trip_id == self.destination_data.trip_id
                    )
                )
            ).scalar_one_or_none()
            if not trip_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"no trip with id {self.destination_data.trip_id} found.",
                )

            stmt = (
                insert(Destination)
                .values(
                    name=self.destination_data.name,
                    description=self.destination_data.description,
                    country=self.destination_data.country,
                    language=self.destination_data.language,
                    best_time_to_visit=self.destination_data.best_time_to_visit,
                    images=destination_images,
                    trip_id=self.destination_data.trip_id,
                )
                .returning(Destination.destination_id)
            )

            destination_id = (
                await self.async_session.execute(stmt)
            ).scalar_one_or_none()
            await self.async_session.commit()
            return planner_schemas.DestinationSchemaOutResponse(
                success=f"Destination with id {destination_id} successfully created."
            )

        except IntegrityError as e:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity error: {str(e)}",
            )

    async def remove_trip_interface(self) -> planner_schemas.TripSchemaOutResponse:
        """
        Delete a trip by its unique ID from the database.

        This method attempts to delete a trip (and all its related destinations and activities,
        if cascading deletes are configured) based on the `trip_id_to_remove` attribute.
        If the trip does not exist, an HTTP 404 error is raised.

        Returns:
            TripSchemaOutResponse: A response schema containing a success message
            confirming that the trip has been successfully removed.

        Raises:
            HTTPException (404): If no trip with the given ID exists in the database.
        """
        stmt = (
            delete(Trip)
            .where(Trip.trip_id == self.trip_id_to_remove)
            .returning(Trip.trip_id)
        )
        trip_id = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if not trip_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trip with the id {self.trip_id_to_remove} found.",
            )
        await self.async_session.commit()
        return planner_schemas.TripSchemaOutResponse(
            success=f"Trip with id {trip_id} successfully removed."
        )

    async def get_all_trips(self) -> planner_schemas.TripSchemaOut:
        """
        Retrieve all trips with their related destinations and activities.

        This method queries the database to fetch all `Trip` records, including
        their associated `Destination` and `Activity` data, using eager loading
        via `joinedload` to minimize the number of database round trips.

        The data is serialized into Pydantic response schemas for use in API responses.

        Returns:
            list[TripSchemaOut]: A list of trip objects, each containing nested
            destination and activity details.
        """
        result = (
            (
                await self.async_session.execute(
                    select(Trip).options(
                        joinedload(Trip.destinations).joinedload(
                            Destination.activities
                        ),
                        selectinload(Trip.participants),
                    )
                )
            )
            .unique()
            .scalars()
            .all()
        )

        return [
            planner_schemas.TripSchemaOut(
                title=trip.title,
                description=trip.description,
                trip_type=trip.trip_type,
                start_date=trip.start_date,
                end_date=trip.end_date,
                duration=f"{trip.duration} days",
                estimated_budget=trip.estimated_budget,
                trip_id=trip.trip_id,
                destinations=[
                    planner_schemas.DestinationSchemaOut(
                        name=dest.name,
                        description=dest.description,
                        country=dest.country,
                        language=dest.language,
                        best_time_to_visit=dest.best_time_to_visit,
                        images=[s3_presigned_url(
                            bucket=BUCKET_NAME, key=key)for key in dest.images or []],
                        destination_id=dest.destination_id,
                        activities=[
                            planner_schemas.ActivitySchemaOut(
                                name=activity.name,
                                description=activity.description,
                                start_time=activity.start_time,
                                end_time=activity.end_time,
                                price=activity.price,
                                activity_id=activity.activity_id,
                            )
                            for activity in dest.activities
                        ],
                    )
                    for dest in trip.destinations
                ],
                participants=[
                    planner_schemas.ParticipantsSchemaOut(
                        user_id=participant.user_id,
                        username=participant.username,
                        date_of_birth=participant.date_of_birth,
                        email=participant.email,
                        phone_number=participant.phone_number,
                    )
                    for participant in trip.participants
                ],
            )
            for trip in result
        ]

    async def get_all_destinations(self) -> list[planner_schemas.DestinationSchemaOut]:
        """
        Retrieve all destinations with their associated activities from the database.

        This method queries the `Destination` table, eagerly loading related `Activity`
        records using `joinedload` to optimize performance and minimize database queries.

        The results are serialized into Pydantic response schemas (`DestinationSchemaOut`
        and nested `ActivitySchemaOut`) for use in API responses.

        Returns:
            list[DestinationSchemaOut]: A list of destinations, each containing
            its details and a list of associated activities.
        """

        result = (
            (
                await self.async_session.execute(
                    select(Destination).options(
                        joinedload(Destination.activities))
                )
            )
            .unique()
            .scalars()
            .all()
        )
        destinations = [
            planner_schemas.DestinationSchemaOut(
                name=dest.name,
                description=dest.description,
                country=dest.country,
                language=dest.language,
                best_time_to_visit=dest.best_time_to_visit,
                images=dest.images,
                destination_id=dest.destination_id,
                activities=[
                    planner_schemas.ActivitySchemaOut(
                        name=activity.name,
                        description=activity.description,
                        start_time=activity.start_time,
                        end_time=activity.end_time,
                        price=activity.price,
                        activity_id=activity.activity_id,
                    )
                    for activity in dest.activities
                ],
            )
            for dest in result
        ]
        return destinations

    async def get_all_activities(self) -> list[planner_schemas.ActivitySchemaOut]:
        """
        Retrieve all activities from the database.

        This method queries the `Activity` table and retrieves all activity records.
        Each record is serialized into the Pydantic response schema `ActivitySchemaOut`
        for consistent API responses.

        Returns:
            list[ActivitySchemaOut]: A list of activities, each containing its
            name, description, start and end times, price, and unique activity ID.
        """
        result = (
            (await self.async_session.execute(select(Activity)))
            .unique()
            .scalars()
            .all()
        )
        activities = [
            planner_schemas.ActivitySchemaOut(
                name=activity.name,
                description=activity.description,
                start_time=activity.start_time,
                end_time=activity.end_time,
                price=activity.price,
                activity_id=activity.activity_id,
            )
            for activity in result
        ]
        return activities
