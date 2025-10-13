from fastapi.routing import APIRouter
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Security, status, Form, File
from app.db.db_connection import get_async_db
from app.models.app_models import User
from fastapi.exceptions import HTTPException
from app.repositories.planner_repository import PlannerRepository
from app.services.planner_services import PlannerService
from app.utils.user_logic import get_current_active_planner
from app.schemas import planner_schemas
from sqlalchemy.exc import IntegrityError
import uuid
from pydantic import Field


router = APIRouter(tags=["planner routes"], prefix="/v1/planner")


@router.post(
    "/create-activity",
    status_code=status.HTTP_201_CREATED,
    response_model=planner_schemas.ActivitySchemaOutResponse,
)
async def create_activity(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    activity_data: planner_schemas.ActivitySchemaIn,
) -> planner_schemas.ActivitySchemaOutResponse:
    """
    Create a new activity in the system.

    This endpoint allows an authenticated planner to create a new activity.
    The activity is persisted in the database using the PlannerRepository
    and PlannerService layers.

    Args:
        async_session (AsyncSession): The asynchronous database session.
        user (User): The currently authenticated planner user.
        activity_data (ActivitySchemaIn): The data required to create the activity.

    Returns:
        The newly created activity object.

    Raises:
        HTTPException:
            - 500 Internal Server Error if something goes wrong during creation.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, user=user, activity_data=activity_data
        )
        service = PlannerService(repo)
        return await service.add_activity()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occured: {str(e)}",
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Intergrity error: {str(e)}",
        )


@router.post(
    "/create-trip",
    status_code=status.HTTP_201_CREATED,
    response_model=planner_schemas.TripSchemaOutResponse,
)
async def create_trip(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    trip_data: planner_schemas.TripSchemaIn,
) -> planner_schemas.TripSchemaOutResponse:
    """
    Create a new trip in the system.

    This endpoint allows an authenticated planner to create a new trip.
    The trip is persisted in the database via the PlannerRepository
    and PlannerService layers.

    Args:
        async_session (AsyncSession): The asynchronous database session.
        user (User): The currently authenticated planner user.
        trip_data (TripSchemaIn): Data required to create the trip.

    Returns:
        The newly created trip object.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, user=user, trip_data=trip_data
        )
        service = PlannerService(repo)
        return await service.add_trip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.post(
    "/create-destination",
    status_code=status.HTTP_201_CREATED,
    response_model=planner_schemas.DestinationSchemaOutResponse,
)
async def create_destination(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    destination_data: Annotated[planner_schemas.DestinationSchemaIn, File()],
) -> planner_schemas.DestinationSchemaOutResponse:
    """
    Create a new destination in the system.

    This endpoint allows an authenticated planner to create a new destination.
    The destination is persisted in the database via the PlannerRepository
    and PlannerService layers.

    Args:
        async_session (AsyncSession): The asynchronous database session.
        user (User): The currently authenticated planner user.
        destination_data (DestinationSchemaIn): Data required to create the destination.

    Returns:
        The newly created destination object.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, user=user, destination_data=destination_data
        )
        service = PlannerService(repo)
        return await service.add_destination()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/trip",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripSchemaOut],
)
async def get_all_trips(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
) -> list[planner_schemas.TripSchemaOut]:
    """
    Retrieve all trips (secured endpoint).

    Requires the "planner" scope but does not use the user object.
    """
    try:
        repo = PlannerRepository(async_session=async_session)
        service = PlannerService(repo)
        return await service.all_trips()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/destination",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.DestinationSchemaOut],
)
async def get_all_destinations(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
) -> list[planner_schemas.DestinationSchemaOut]:
    """
    Retrieve all destinations (secured endpoint).

    This endpoint fetches all destinations from the database via the
    `PlannerService`. Each destination may include related activities if
    included in the repository query.

    Security:
        Requires an authenticated user with the "planner" scope, but the
        user object is not used directly in this endpoint.

    Returns:
        list[DestinationSchemaOut]: A list of destination objects, including
        their details and associated activities.

    Raises:
        HTTPException (500): If an unexpected server error occurs.
    """
    try:
        repo = PlannerRepository(async_session=async_session)
        service = PlannerService(repo)
        return await service.all_destinations()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/activity",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ActivitySchemaOut],
)
async def get_all_activities(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
) -> list[planner_schemas.ActivitySchemaOut]:
    """
    Retrieve all activities (secured endpoint).

    This endpoint fetches all activity records from the database via the
    `PlannerService`. Each activity includes details such as name, description,
    start and end times, price, and its unique ID.

    Security:
        Requires an authenticated user with the "planner" scope. The user object
        is not used directly in this endpoint.

    Returns:
        list[ActivitySchemaOut]: A list of activity objects, each containing
        its details for API response.

    Raises:
        HTTPException (500): If an unexpected server error occurs.
    """
    try:
        repo = PlannerRepository(async_session=async_session)
        service = PlannerService(repo)
        return await service.all_activities()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.delete(
    "/delete-trip/{trip_id_to_remove}",
    status_code=status.HTTP_200_OK,
    response_model=planner_schemas.TripSchemaOutResponse,
)
async def remove_trip(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    trip_id_to_remove: Annotated[uuid.UUID, Field(description="the id of the trip")],
) -> planner_schemas.TripSchemaOutResponse:
    """
    Delete a trip owned by the currently authenticated planner.

    This endpoint performs the following steps:
    1. Validates the authenticated planner using scoped access control.
    2. Instantiates the `PlannerRepository` and `PlannerService` to handle
       the business logic for trip deletion.
    3. Delegates the deletion process to the service layer, which removes
       the specified trip from the database.

    Args:
        async_session (AsyncSession): SQLAlchemy asynchronous session used
            for interacting with the database.
        user (User): The currently authenticated planner user, retrieved
            via the `get_current_active_planner` dependency.
        trip_id_to_remove (planner_schemas.TripRemoveSchemaIn): Schema
            containing the ID of the trip to be deleted.

    Returns:
        planner_schemas.TripSchemaOutResponse: A success message confirming
        the trip was successfully deleted.

    Raises:
        HTTPException 404: If the trip to delete is not found.
        HTTPException 401: If the user is not authorized to perform this action.
        HTTPException 500: If an unexpected server error occurs.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, user=user, trip_id_to_remove=trip_id_to_remove
        )
        service = PlannerService(repo)
        return await service.delete_trip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
