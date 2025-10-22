from app.utils.celery_tasks import s3_upload
import os
from app.interfaces.planner_interfaces import AbstractPlannerInterface
from dataclasses import dataclass
from app.models.app_models import User, Trip, Destination, user_trip_association_course
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, insert, select, delete, func
from sqlalchemy.exc import IntegrityError
from app.models.app_models import Activity
from app.schemas import planner_schemas, user_schemas
from fastapi.exceptions import HTTPException
from fastapi import status
import uuid
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from dotenv import load_dotenv
from app.utils.boto3_client import s3_presigned_url
from datetime import date
from app.utils.logger import logger
from datetime import date
from sqlalchemy.orm import aliased, load_only
from datetime import time, datetime
from sqlalchemy import Time, desc
from decimal import Decimal

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
    trip_id: uuid.UUID | None = None
    number_of_participants: int | None = None
    number_of_activities: int | None = None
    date_of_birth: date | None = None
    user_id: uuid.UUID | None = None
    offset: int | None = None
    limit: int | None = None
    destination_id: uuid.UUID | None = None
    trip_id: uuid.UUID | None = None
    activity_start_time: time | None = None
    destination_id_for_activity: uuid.UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    activity_price: Decimal | None = None
    number_of_trips: int | None = None

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
                f"{key}/{image_name}" for image_name in images_name]
            # uploading to s3
            for image in self.destination_data.images:
                s3_upload.delay(
                    bucket=BUCKET_NAME,
                    key=f"{key}/{image.filename}",
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
                    select(Trip)
                    .options(
                        joinedload(Trip.destinations).joinedload(
                            Destination.activities
                        ),
                        selectinload(Trip.participants),
                    )
                    .offset(self.offset)
                    .limit(self.limit)
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
                        images=[
                            s3_presigned_url(bucket=BUCKET_NAME, key=key)
                            for key in dest.images or []
                        ],
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

    async def all_users_enlisted_in_a_specific_trip(
        self,
    ) -> list[planner_schemas.ParticipantsSchemaOut]:
        """
        Retrieve all users (participants) enlisted in a specific trip.

        This method first verifies that a trip with the provided `trip_id` exists.
        If the trip is found, it loads the trip along with all associated participants
        and returns them serialized through the `TripSchemaOut` schema.

        Returns:
            list[planner_schemas.TripSchemaOut]:
                A list containing the trip and its associated participants.
                Each trip includes metadata (title, description, budget, etc.)
                and a list of user details for participants.

        Raises:
            HTTPException (404): If no trip with the given `trip_id` exists.
        """

        trip_id = (
            await self.async_session.execute(
                select(Trip.trip_id).where(Trip.trip_id == self.trip_id)
            )
        ).scalar_one_or_none()
        if not trip_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no trip with id {self.trip_id} found.",
            )

        participants = (
            (
                await self.async_session.execute(
                    select(User)
                    .join(
                        user_trip_association_course,
                        User.user_id == user_trip_association_course.c.user_id,
                    )
                    .join(Trip, self.trip_id == user_trip_association_course.c.trip_id)
                )
            )
            .unique()
            .scalars()
            .all()
        )

        return [
            planner_schemas.ParticipantsSchemaOut(
                user_id=participant.user_id,
                username=participant.username,
                date_of_birth=participant.date_of_birth,
                email=participant.email,
                phone_number=participant.phone_number,
            )
            for participant in participants
        ]

    # give me trip that have more than a specified number of  participnats enlisted

    async def trips_with_participant(self) -> list[planner_schemas.TripSchemaOut]:
        """
        Retrieve trips that have at least a specified number of participants.

        This method queries the database for trips where the number of associated
        participants meets or exceeds `self.number_of_participants`. It uses an
        outer join with the association table and eager loads participants to avoid
        additional async queries. Each trip is returned as a `TripSchemaOut` object,
        including a list of participant details.

        Returns:
            list[planner_schemas.TripSchemaOut]:
                A list of trips matching the participant count criteria. Each trip
                includes metadata (title, description, type, dates, duration, budget)
                and a list of participants with their relevant details.
        """
        stmt = (
            select(Trip)
            .outerjoin(
                user_trip_association_course,
                Trip.trip_id == user_trip_association_course.c.trip_id,
            )
            .options(joinedload(Trip.participants))
            .group_by(Trip.trip_id)
            .having(
                func.count(user_trip_association_course.c.user_id)
                >= self.number_of_participants
            )
        )
        trips = (await self.async_session.execute(stmt)).unique().scalars().all()
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
                destinations=[],
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
            for trip in trips
        ]

        # give me destinations that have more than one activities

    async def destinations_with_more_than_a_specified_nr_activities(
        self,
    ) -> list[planner_schemas.DestinationSchemaOut]:
        """
        Retrieve destinations that have at least a specified number of activities.

        This method queries the database for destinations where the number of
        associated activities meets or exceeds `self.number_of_activities`.
        Activities are eagerly loaded using `joinedload` to avoid additional
        queries. Each destination is returned as a `DestinationSchemaOut` object,
        including a list of its activities.

        Returns:
            list[planner_schemas.DestinationSchemaOut]:
                A list of destinations matching the activity count criteria. Each
                destination includes metadata (name, description, country, language,
                best time to visit, images) and a list of associated activities
                with their details (name, description, start/end times, price, ID).
        """
        stmt = (
            select(Destination)
            .options(joinedload(Destination.activities))
            .join(Activity, Activity.destination_id == Destination.destination_id)
            .group_by(Destination.destination_id)
            .having(func.count(Activity.activity_id) >= self.number_of_activities)
        )
        result = (await self.async_session.execute(stmt)).unique().scalars().all()
        return [
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

    async def fetch_users_by_birth_date(
        self,
    ) -> list[user_schemas.UserProfileSchemaOut]:
        """
        Asynchronously query user records from the database that match specific criteria.

        This method selects all users whose `date_of_birth` is greater than the value of
        `self.date_of_birth` and whose username starts with the letter "f". It then maps
        each resulting database object into a `UserProfileSchemaOut` Pydantic schema
        instance for structured output.

        Returns:
            list[user_schemas.UserProfileSchemaOut]:
                A list of user profile schemas containing user details such as
                ID, username, email, activation status, date of birth, profile picture,
                and assigned scopes.

        Example:
            >>> repo = PlannerRepository(async_session, date_of_birth=date(2000, 1, 1))
            >>> users = await repo.query_data()
            >>> for user in users:
            ...     print(user.username)
        """

        stmt = select(User).where(
            User.date_of_birth > self.date_of_birth,
        )
        users = (await self.async_session.execute(stmt)).scalars().all()
        return [
            user_schemas.UserProfileSchemaOut(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                date_of_birth=user.date_of_birth,
                profile_picture=user.profile_picture,
                scopes=user.scopes,
            )
            for user in users
        ]

    async def get_user_enrolled_activities(
        self,
    ) -> list[planner_schemas.ActivitySchemaOut]:
        """
        Retrieve all activities in which the current user is enrolled.

        This method queries the database asynchronously to find activities associated
        with the user's trips. It joins the Activity, Destination, Trip, and User tables
        through the `user_trip_association_course` table to ensure that only activities
        for trips the user is enrolled in are returned. Each resulting Activity is
        serialized into an `ActivitySchemaOut` Pydantic schema for structured output.

        Returns:
            list[planner_schemas.ActivitySchemaOut]:
                A list of activity schemas including details such as activity ID,
                name, description, start and end times, and price.

        Raises:
            HTTPException:
                If any database or query error occurs during execution.

        """

        trip_alias = aliased(Trip)
        destination_alias = aliased(Destination)

        stmt = (
            select(Activity)
            # Join Destination first because Activity depends on it
            .join(
                destination_alias,
                Activity.destination_id == destination_alias.destination_id,
            )
            # Join Trip after Destination
            .join(trip_alias, destination_alias.trip_id == trip_alias.trip_id)
            # Join the association table
            .join(
                user_trip_association_course,
                user_trip_association_course.c.trip_id == trip_alias.trip_id,
            )
            # Join User last and filter by user_id
            .join(User, user_trip_association_course.c.user_id == User.user_id)
            .where(User.user_id == self.user_id)
        )

        result = (await self.async_session.execute(stmt)).scalars().all()
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

    async def get_trips_for_users_born_before(
        self,
    ) -> list[planner_schemas.TripSchemaOut]:
        """
        Retrieve all trips associated with users born before a specified date.

        This repository method performs a subquery to select users whose
        `date_of_birth` is earlier than the specified cutoff. It then queries
        the `Trip` table, joining with the `user_trip_association_course` table
        to find trips that include those users. Duplicate trips are removed
        using `.distinct()`. The results are returned as a list of
        `TripSchemaOut` Pydantic schemas with placeholders for destinations
        and participants.

        Returns:
            list[planner_schemas.TripSchemaOut]:
                A list of trips including trip ID, title, description, trip type,
                start and end dates, duration, estimated budget, and empty
                placeholders for destinations and participants.

        Raises:
            SQLAlchemyError:
                If a database query fails or an unexpected error occurs during execution.

        """

        subquery = (
            select(User.user_id)
            .where(User.date_of_birth < self.date_of_birth)
            .scalar_subquery()
        )
        stmt = (
            select(Trip)
            .join(
                user_trip_association_course,
                Trip.trip_id == user_trip_association_course.c.trip_id,
            )
            .where(user_trip_association_course.c.user_id.in_(subquery))
            .distinct()
        )

        result = (await self.async_session.execute(stmt)).scalars().all()
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
                destinations=[],
                participants=[],
            )
            for trip in result
        ]

    # let's count how many activites a specified destination has

    async def get_activities_by_destination(
        self,
    ) -> list[planner_schemas.ActivitiesByDestinationSchemaOut]:
        """
        Retrieve the number of activities associated with a specific destination.

        This repository method performs an aggregated SQL query that counts
        all activities linked to a given destination, identified by
        `self.destination_id`. It uses SQLAlchemy's `func.count()` for
        aggregation and `func.coalesce()` to ensure that destinations with
        no activities return a count of zero instead of null.

        Returns:
            list[planner_schemas.ActivitiesByDestinationSchemaOut]:
                A list containing objects with the destination identifier and
                the corresponding number of activities.

        Raises:
            SQLAlchemyError:
                If a database execution or query error occurs.
        """

        stmt = (
            select(
                Destination.destination_id,
                func.coalesce(func.count(Activity.activity_id), 0).label(
                    "number_of_activities"
                ),
            )
            .outerjoin(Activity, Activity.destination_id == Destination.destination_id)
            .where(Destination.destination_id == self.destination_id)
            .group_by(Destination.destination_id)
        )

        result = await self.async_session.execute(stmt)
        return [
            planner_schemas.ActivitiesByDestinationSchemaOut(
                destination=destination, nr_of_activities=nr_activities
            )
            for destination, nr_activities in result
        ]

    # lets count how many activities a trip has
    async def get_activities_by_trip(
        self,
    ) -> list[planner_schemas.ActivitiesByTripSchemaOut]:
        """
        Retrieve the total number of activities associated with a specific trip.

        This repository method executes an aggregated SQL query that counts
        the number of activities linked to a given trip through its destinations.
        It performs an outer join between `Trip`, `Destination`, and `Activity`
        tables to ensure that trips with no destinations or activities are
        still included in the results with a count of zero.

        Returns:
            list[planner_schemas.ActivitiesByTripSchemaOut]:
                A list of objects containing the trip identifier and the
                corresponding number of associated activities.

        Raises:
            SQLAlchemyError:
                If a database query or execution error occurs.
        """

        stmt = (
            select(Trip.trip_id, func.coalesce(
                func.count(Activity.activity_id), 0))
            .outerjoin(Destination, Destination.trip_id == Trip.trip_id)
            .outerjoin(Activity, Activity.destination_id == Destination.destination_id)
            .where(Trip.trip_id == self.trip_id)
            .group_by(Trip.trip_id)
        )
        result = await self.async_session.execute(stmt)
        return [
            planner_schemas.ActivitiesByTripSchemaOut(
                trip=trip, nr_of_activities=nr_activities
            )
            for trip, nr_activities in result
        ]

    # get all destinations where activities start after a specified time

    async def fetch_destinations_after_activity_start_time(
        self,
    ) -> list[planner_schemas.DestinationSchemaOut]:
        """
        Retrieve all destinations that have at least one activity starting after the specified time.

        This method executes an asynchronous SQL query joining the `Destination` and `Activity` tables,
        filtering activities whose `start_time` is later than the provided `activity_start_time`.
        The results are loaded with related activities using `subqueryload` for efficient eager loading.

        Returns:
            list[planner_schemas.DestinationSchemaOut]:
                A list of destinations, each including their associated activities that meet
                the time filter condition. Each destination and activity is serialized into
                its corresponding Pydantic schema.
        """
        stmt = (
            select(Destination)
            .join(Activity, Destination.destination_id == Activity.destination_id)
            .options(subqueryload(Destination.activities))
            .where(
                func.cast(Activity.start_time, Time)
                > func.cast(self.activity_start_time, Time)
            )
        )
        destinations = (await self.async_session.execute(stmt)).scalars().all()
        return [
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
            for dest in destinations
        ]

    # Create a typed function that accepts a Destination and a start/end datetime, returning
    # all activities happening in that time window.

    async def activities_in_a_specified_interval(
        self,
    ) -> list[planner_schemas.ActivitySchemaOut]:
        """
        Retrieve all activities for a specific destination that occur within a given time interval.

        This method queries the database asynchronously, joining the `Activity` and `Destination` tables,
        and filters activities that start on or after `self.start_time` and end on or before `self.end_time`.
        The results are returned as a list of Pydantic schemas (`ActivitySchemaOut`) for easy serialization.

        Returns:
            list[planner_schemas.ActivitySchemaOut]:
                A list of activities matching the destination ID and time interval, each represented
                as an `ActivitySchemaOut` object containing name, description, start and end times,
                price, and activity ID.
        """
        stmt = (
            select(Activity)
            .join(Destination, Destination.destination_id == Activity.destination_id)
            .where(Destination.destination_id == self.destination_id_for_activity)
            .where(
                and_(
                    Activity.start_time >= self.start_time,
                    Activity.end_time <= self.end_time,
                )
            )
        )
        result = (await self.async_session.execute(stmt)).scalars().all()
        return [
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

    # total cost of activities per destination

    async def total_cost_of_activities_per_destination(
        self,
    ) -> list[planner_schemas.TotalCostOfActivitiesOut]:
        """
        Calculate the total cost of all activities for a specific destination.

        This method performs an asynchronous SQL query that:
        - Joins the `Activity` and `Destination` tables
        - Filters by the specified `destination_id`
        - Aggregates the sum of `Activity.price` grouped by `destination_id`

        The results are returned as a list of Pydantic schema objects (`TotalCostOfActivitiesOut`),
        each containing the destination ID and the total sum of activity prices.

        Returns:
            list[planner_schemas.TotalCostOfActivitiesOut]:
                A list containing the total cost of activities for the specified destination.
                Each item includes:
                    - `destination_id` (UUID): The ID of the destination
                    - `total_sum` (Decimal/float): The total sum of activity prices
        """

        stmt = (
            select(Destination.destination_id, func.sum(Activity.price))
            .join(Destination, Destination.destination_id == Activity.destination_id)
            .where(Destination.destination_id == self.destination_id)
            .group_by(Destination.destination_id)
        )
        result = await self.async_session.execute(stmt)
        data = [
            planner_schemas.TotalCostOfActivitiesOut(
                destination_id=dest_id, total_sum=total_sum
            )
            for dest_id, total_sum in result
        ]
        return data

    # Identify the most expensive activity per destination

    async def most_expensive_activity_per_destination(
        self,
    ) -> list[planner_schemas.MostExpensiveActivityPerDestination]:
        """
        Retrieve the most expensive activity for a specific destination.

        Executes an aggregate query that finds the maximum activity price (`max_price`)
        for the given destination ID.

        Returns:
            list[planner_schemas.MostExpensiveActivityPerDestination]:
                A list containing the destination ID and the corresponding
                most expensive activity price.

        """

        stmt = (
            select(Destination.destination_id, func.max(Activity.price))
            .join(Activity, Activity.destination_id == Destination.destination_id)
            .where(Destination.destination_id == self.destination_id)
            .group_by(Destination.destination_id)
        )
        result = await self.async_session.execute(stmt)
        data = [
            planner_schemas.MostExpensiveActivityPerDestination(
                destination_id=dest_id, max_price=max_price
            )
            for dest_id, max_price in result
        ]
        return data

    # Find users who participated in trips that include destinations offering activities above a specific price
    # → Use nested CTEs: one for destinations with expensive activities, another joining users to those trips.

    async def get_users_in_trips_with_expensive_activities(
        self,
    ) -> list[planner_schemas.UsersInTripsWithExpnsiveActivities]:
        """
        Retrieve all users who participated in trips that include destinations
        offering activities above a specified price.

        This method uses nested Common Table Expressions (CTEs) to efficiently:
        1. Identify destinations with activities above `self.activity_price`.
        2. Find trips that include those destinations.
        3. Retrieve users who participated in those trips.

        Returns:
            list[planner_schemas.UsersInTripsWithExpnsiveActivities]:
                A list of users associated with trips containing at least one destination
                where an activity exceeds the specified price.

        Notes:
            - The query ensures uniqueness of usernames using DISTINCT.
            - The CTE approach avoids multiple subqueries for better performance.
        """
        # CTE for destinations with activities above a certain price
        destinations_cte = (
            select(Destination.destination_id.label("destination_id"))
            .join(Activity, Activity.destination_id == Destination.destination_id)
            .where(Activity.price >= self.activity_price)
            .group_by(Destination.destination_id)
        ).cte("destinations_cte")

        # CTE for trips that include those destinations
        trip_cte = (
            select(Trip.trip_id.label("trip_id"))
            .join(Destination, Destination.trip_id == Trip.trip_id)
            .join(
                destinations_cte,
                destinations_cte.c.destination_id == Destination.destination_id,
            )
            .distinct()
        ).cte("trip_cte")

        # Final query: get users who participated in those trips
        stmt = (
            select(User.username)
            .join(
                user_trip_association_course,
                user_trip_association_course.c.user_id == User.user_id,
            )
            .join(
                trip_cte, trip_cte.c.trip_id == user_trip_association_course.c.trip_id
            )
            .distinct()
        )

        result = (await self.async_session.execute(stmt)).scalars().all()
        return [
            planner_schemas.UsersInTripsWithExpnsiveActivities(
                username=username)
            for username in result
        ]

    async def most_expensive_trips(self) -> list[planner_schemas.TripSchemaOut]:
        """
        Retrieve a list of the most expensive trips based on their estimated budget.

        This query selects trips from the database, ordering them in descending order
        by their `estimated_budget`, and limits the results to the number specified
        by `self.number_of_trips`. The results are serialized into `TripSchemaOut`
        objects before being returned.

        Returns:
            list[planner_schemas.TripSchemaOut]:
                A list of the most expensive trips, including key trip details such as
                title, description, type, duration, start and end dates, and estimated budget.

        Notes:
            - The number of trips returned is limited by `self.number_of_trips`.
            - Destinations and participants are not loaded in this query and are returned as empty lists.
        """
        stmt = (
            select(Trip)
            .limit(self.number_of_trips)
            .order_by(desc(Trip.estimated_budget))
        )
        result = (await self.async_session.execute(stmt)).scalars().all()
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
                destinations=[],
                participants=[],
            )
            for trip in result
        ]

    async def get_trips_by_popularity(
        self,
    ) -> list[planner_schemas.TripByPopularitySchemaOut]:
        """
        Retrieve all trips ordered by their popularity, based on the number of participants.

        This method uses a Common Table Expression (CTE) to count the number of users
        associated with each trip via the `user_trip_association_course` table.
        Trips are then ordered in descending order of participant count, with trips
        that have no participants defaulting to zero using `COALESCE`.

        Returns:
            list[planner_schemas.TripByPopularitySchemaOut]:
                A list of trips sorted by popularity, each including:
                - trip_id: The unique identifier of the trip.
                - title: The title of the trip.
                - participants: The total number of participants.

        Notes:
            - Trips with no participants are still included, showing a count of 0.
            - The query uses an outer join to ensure all trips are represented.
        """
        nr_of_participants = (
            select(
                Trip.trip_id.label("trip_id"),
                func.coalesce(
                    func.count(user_trip_association_course.c.user_id), 0
                ).label("nr_of_participants"),
            )
            .outerjoin(
                user_trip_association_course,
                user_trip_association_course.c.trip_id == Trip.trip_id,
            )
            .group_by(Trip.trip_id)
            .cte("nr_of_participants")
        )
        stmt = (
            select(
                nr_of_participants.c.trip_id,
                Trip.title,
                nr_of_participants.c.nr_of_participants,
            )
            .outerjoin(Trip, Trip.trip_id == nr_of_participants.c.trip_id)
            .order_by(desc(nr_of_participants.c.nr_of_participants))
        )
        result = await self.async_session.execute(stmt)
        trips_by_popularity_list = [
            planner_schemas.TripByPopularitySchemaOut(
                trip_id=trip_id, title=title, participants=participants
            )
            for trip_id, title, participants in result
        ]
        return trips_by_popularity_list

    async def get_destination_with_most_activities(
        self,
    ) -> list[planner_schemas.DestinationWithMostActivities]:
        """
        Retrieve the destination with the highest number of activities.

        This method counts the number of activities associated with each destination
        and returns the destination with the largest count. If multiple destinations
        have the same highest number of activities, only one is returned.

        Returns:
            list[planner_schemas.DestinationWithMostActivities]:
                A list containing a single destination with the most activities, including:
                - dest_id: The unique identifier of the destination.
                - dest_name: The name of the destination.
                - nr_of_activities: The total number of activities associated with the destination.

        Notes:
            - Uses a Common Table Expression (CTE) to efficiently count activities per destination.
            - Orders results in descending order by number of activities and limits to 1.
        """
        nr_of_activities_cte = (
            select(
                Destination.destination_id.label("destination_id"),
                Destination.name.label("destination_name"),
                func.coalesce(func.count(Activity.activity_id), 0).label(
                    "nr_of_activities"
                ),
            )
            .join(Activity, Activity.destination_id == Destination.destination_id)
            .group_by(Destination.destination_id)
        ).cte("nr_of_activities_cte")
        stmt = (
            select(
                nr_of_activities_cte.c.destination_id,
                nr_of_activities_cte.c.destination_name,
                nr_of_activities_cte.c.nr_of_activities,
            )
            .order_by(desc(nr_of_activities_cte.c.nr_of_activities))
            .limit(1)
        )

        result = await self.async_session.execute(stmt)
        destination_with_most_activities_list = [
            planner_schemas.DestinationWithMostActivities(
                dest_id=dest_id, dest_name=dest_name, nr_of_activities=nr_of_activities
            )
            for dest_id, dest_name, nr_of_activities in result
        ]
        return destination_with_most_activities_list

    async def average_price_of_activities_in_each_destination(
        self,
    ) -> list[planner_schemas.AvreagePriceOfActivitiesInEachDestinationOut]:
        """
        Calculate the average price of activities for each destination.

        This method computes the average cost of activities grouped by destination.
        It uses a Common Table Expression (CTE) to first aggregate the total price
        and number of activities per destination, then divides these values to
        determine the average activity price for each destination.

        **Returns:**
            A list of `AvreagePriceOfActivitiesInEachDestinationOut` objects, each containing:
            - `dest_id`: The unique ID of the destination.
            - `destination_name`: The name of the destination.
            - `average_price`: The average price of activities at that destination,
                rounded to two decimal places.

        **Notes:**
            - Destinations without activities are excluded since they would have
                no associated activity records.
            - Uses `func.round` to ensure consistent two-decimal precision.

        **Raises:**
            - Propagates any database-related exceptions during query execution.
        """
        average_price_per_destination_cte = (
            select(
                Destination.destination_id.label("destination_id"),
                Destination.name.label("destination_name"),
                func.coalesce(func.count(Activity.activity_id), 0).label(
                    "nr_of_activities"
                ),
                func.sum(Activity.price).label("total_price"),
            )
            .join(Activity, Activity.destination_id == Destination.destination_id)
            .group_by(Destination.destination_id)
        ).cte("avreage_cte")

        stmt = select(
            average_price_per_destination_cte.c.destination_id,
            average_price_per_destination_cte.c.destination_name,
            func.round(
                average_price_per_destination_cte.c.total_price
                / average_price_per_destination_cte.c.nr_of_activities,
                2,
            ),
        )

        result = await self.async_session.execute(stmt)

        average_price_list = [
            planner_schemas.AvreagePriceOfActivitiesInEachDestinationOut(
                dest_id=dest_id,
                destination_name=destination_name,
                average_price=average_price,
            )
            for dest_id, destination_name, average_price in result
        ]
        return average_price_list
