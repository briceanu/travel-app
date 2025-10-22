from fastapi.routing import APIRouter
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Security, status, File, Query
from app.db.db_connection import get_async_db
from app.models.app_models import User
from fastapi.exceptions import HTTPException
from app.repositories.planner_repository import PlannerRepository
from app.services.planner_services import PlannerService
from app.utils.user_logic import get_current_active_planner
from app.schemas import planner_schemas, user_schemas
from sqlalchemy.exc import IntegrityError
import uuid
from pydantic import Field
from datetime import date, time, datetime
from decimal import Decimal


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
    "/trips",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripSchemaOut],
)
async def get_all_trips(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    offset: Annotated[
        int, Query(ge=0, description="Skip the profided nr of trips")
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Provided number of trips per page"),
    ] = 20,
) -> list[planner_schemas.TripSchemaOut]:
    """
    Retrieve all trips (secured endpoint).

    Requires the "planner" scope but does not use the user object.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, offset=offset, limit=limit
        )
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


@router.get(
    "/all-users-enlisted-in-trip",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ParticipantsSchemaOut],
)
async def get_all_destinations(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    trip_id: Annotated[uuid.UUID, Query()],
    # ) -> list[planner_schemas.TripSchemaOut]:
) -> list[planner_schemas.ParticipantsSchemaOut]:
    """
    Retrieve all users (participants) enlisted in a specific trip.

    This endpoint is accessible only to authenticated planners. It fetches
    the trip specified by the `trip_id` query parameter, validates its existence,
    and returns the trip data along with all participants associated with it.

    Args:
        async_session (AsyncSession): The database session dependency.
        _ (User): The currently authenticated planner (validated via JWT scopes).
        trip_id (uuid.UUID): The unique identifier of the trip to retrieve participants for.

    Returns:
        list[planner_schemas.TripSchemaOut]:
            A list containing the trip and its associated participants, serialized
            according to the `TripSchemaOut` schema.

    Raises:
        HTTPException (404): If no trip with the provided `trip_id` exists.
        HTTPException (500): If an unexpected server error occurs.
    """

    try:
        repo = PlannerRepository(async_session=async_session, trip_id=trip_id)
        service = PlannerService(repo)
        return await service.get_users_registered_for_trip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/trips-with-participant-count",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripSchemaOut],
)
async def get_trips_over_participant_count(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    number_of_participants: Annotated[
        int, Query(ge=1, description="it uses the grater than sign")
    ],
) -> list[planner_schemas.TripSchemaOut]:
    """
    Retrieve trips that have a minimum number of participants.

    This endpoint allows authenticated planners to fetch trips where the
    number of participants meets or exceeds the specified `number_of_participants`.
    Each trip returned includes its metadata and a list of participants.

    Args:
        async_session (AsyncSession): Database session dependency.
        _ (User): The currently authenticated planner (validated via JWT scopes).
        number_of_participants (int): The minimum number of participants a trip must have.

    Returns:
        list[planner_schemas.TripSchemaOut]:
            A list of trips matching the participant count criteria, including
            their participants and metadata.

    Raises:
        HTTPException (404): If no trips match the criteria (handled in service/repository).
        HTTPException (500): If an unexpected server error occurs.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, number_of_participants=number_of_participants
        )
        service = PlannerService(repo)
        return await service.fetch_trips_with_participants()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/destinations-by-min-activities",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.DestinationSchemaOut],
)
async def get_trips_over_participant_count(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    number_of_activities: Annotated[
        int, Query(ge=1, description="i uses the grater than sign")
    ],
) -> list[planner_schemas.DestinationSchemaOut]:
    """
    Retrieve destinations with a minimum number of activities.

    This endpoint allows authenticated planners to fetch destinations where
    the number of associated activities meets or exceeds the specified
    `number_of_activities`. Each destination returned is serialized according
    to the `DestinationSchemaOut` schema.

    Args:
        async_session (AsyncSession): Database session dependency.
        _ (User): The currently authenticated planner (validated via JWT scopes).
        number_of_activities (int): Minimum number of activities required for a destination
            to be included in the results.

    Returns:
        list[planner_schemas.DestinationSchemaOut]:
            A list of destinations matching the activity count criteria.

    Raises:
        HTTPException (500): If an unexpected server error occurs.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, number_of_activities=number_of_activities
        )
        service = PlannerService(repo)
        return await service.fetch_destinations_with_nr_of_participants()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-users-by-date-of-birth",
    status_code=status.HTTP_200_OK,
    response_model=list[user_schemas.UserProfileSchemaOut],
)
async def fetch_users_by_birth_date(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    date_of_birth: Annotated[
        date, Query(description="Format: YYYY-MM-DD, e.g., 1990-10-01")
    ],
) -> list[user_schemas.UserProfileSchemaOut]:
    """
    Retrieve all users whose date of birth is later than the specified date.

    This endpoint allows a planner (authorized user) to fetch users born after a given
    `date_of_birth`. The request requires valid planner credentials and will return
    a list of user profiles that match the criteria.

    Args:
        async_session (AsyncSession):
            The SQLAlchemy asynchronous session used for database access.
        _ (User):
            The currently authenticated planner user (validated via security scopes).
        date_of_birth (date):
            The cutoff date used to filter users. Only users with a later date of birth
            will be included in the response. Example: `2010-02-20`.

    Returns:
        list[user_schemas.UserProfileSchemaOut]:
            A list of user profiles containing fields such as user ID, username, email,
            activation status, date of birth, profile picture, and assigned scopes.

    Raises:
        HTTPException(401):
            If authentication or authorization fails.
        HTTPException(500):
            If an unexpected error occurs during database access or processing.

    Example:
        GET /get-users-by-date-of-birth?date_of_birth=2010-02-20
    """

    try:
        repo = PlannerRepository(
            async_session=async_session, date_of_birth=date_of_birth
        )
        service = PlannerService(repo)
        return await service.get_users_by_birth_date()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-user-activities",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ActivitySchemaOut],
)
async def get_user_activities(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    user_id: Annotated[uuid.UUID, Query(description="the id of the user")],
) -> list[planner_schemas.ActivitySchemaOut]:
    """
    Retrieve all activities in which a specified user is enrolled.

    This endpoint allows an authorized planner to fetch all activities associated
    with a given user's trips. The user is identified by their `user_id`. The route
    constructs a repository and service layer to perform the query asynchronously
    and returns a list of activity schemas.

    Args:
        async_session (AsyncSession):
            The SQLAlchemy asynchronous session used to access the database.
        _ (User):
            The currently authenticated planner (validated via security scopes).
        user_id (uuid.UUID):
            The ID of the user whose enrolled activities are being retrieved.

    Returns:
        list[planner_schemas.ActivitySchemaOut]:
            A list of activity schemas including fields such as activity ID, name,
            description, start and end times, and price.

    Raises:
        HTTPException(401):
            If the current planner is not authenticated or lacks the required scope.
        HTTPException(500):
            If an unexpected error occurs during database access or processing.

    Example:
        GET /get-user-activities?user_id=578c987a-1980-4efb-b89a-fa724f12ef88
    """

    try:
        repo = PlannerRepository(async_session=async_session, user_id=user_id)
        service = PlannerService(repo)
        return await service.find_user_activities()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/find-trips-by-user-birth-date",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripSchemaOut],
)
async def find_trips_by_user_birth_date(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    date_of_birth: Annotated[
        date, Query(description="Format: YYYY-MM-DD, e.g., 1990-10-01")
    ],
) -> list[planner_schemas.TripSchemaOut]:
    """
    Retrieve trips associated with users born before a specified date.

    This endpoint allows an authorized planner to fetch all trips that include
    users whose `date_of_birth` is earlier than the provided date. The query is
    executed asynchronously through the repository and service layers, and the
    results are returned as a list of `TripSchemaOut` schemas.

    Args:
        async_session (AsyncSession):
            The SQLAlchemy asynchronous session used for database access.
        _ (User):
            The currently authenticated planner (validated via security scopes).
        date_of_birth (date):
            The cutoff birth date used to filter users. Format must be `YYYY-MM-DD`.

    Returns:
        list[planner_schemas.TripSchemaOut]:
            A list of trips including fields such as trip ID, title, description,
            trip type, start and end dates, duration, estimated budget, and placeholders
            for destinations and participants.

    Raises:
        HTTPException(401):
            If the current planner is not authenticated or lacks the required scope.
        HTTPException(500):
            If an unexpected error occurs during database access or processing.

    Example:
        GET /find-trips-by-user-birth-date?date_of_birth=1990-10-01
    """

    try:
        repo = PlannerRepository(
            async_session=async_session, date_of_birth=date_of_birth
        )
        service = PlannerService(repo)
        return await service.find_trips_by_user_birth_date()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-activities_by_destination",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ActivitiesByDestinationSchemaOut],
)
async def get_activities_by_destination(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    destination_id: Annotated[uuid.UUID, Query(description="id of the destination")],
) -> list[planner_schemas.ActivitiesByDestinationSchemaOut]:
    """
    Retrieve all activities associated with a specific destination.

    Args:
        async_session (AsyncSession): The active asynchronous database session.
        _ (User): The currently authenticated planner (requires 'planner' scope).
        destination_id (uuid.UUID): The unique identifier of the destination
            whose activities will be retrieved.

    Returns:
        list[planner_schemas.ActivitiesByDestinationSchemaOut]:
            A list of activities belonging to the specified destination,
            including their details such as name, description, duration,
            start and end times, and price.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR: If an unexpected error occurs during processing.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, destination_id=destination_id
        )
        service = PlannerService(repo)
        return await service.fetch_activities_by_destination()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-activities_by_trip",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ActivitiesByTripSchemaOut],
)
async def get_activities_by_trip(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    trip_id: Annotated[uuid.UUID, Query(description="id of the trip")],
) -> list[planner_schemas.ActivitiesByTripSchemaOut]:
    """
    Retrieve the number of activities associated with a specific trip.

    This endpoint allows planners to view how many activities are linked
    to a given trip, based on the trip’s destinations. The query uses
    aggregated SQL joins to ensure that trips with no activities still
    appear with a count of zero. Access is restricted to authenticated
    users with the `planner` scope.

    Args:
        async_session (AsyncSession): The asynchronous SQLAlchemy session
            provided through dependency injection.
        _ (User): The currently authenticated planner user.
        trip_id (uuid.UUID): The unique identifier of the trip to query.

    Returns:
        list[planner_schemas.ActivitiesByTripSchemaOut]:
            A list containing the trip ID and the corresponding
            number of associated activities.

    Raises:
        HTTPException:
            - 401 Unauthorized: If the user lacks valid authentication.
            - 500 Internal Server Error: If an unexpected error occurs
              during query execution.

    Example:
        GET /planner/get-activities_by_trip?trip_id=22da4bb9-9935-467c-9f32-0890f5fd066d
    """
    try:
        repo = PlannerRepository(async_session=async_session, trip_id=trip_id)
        service = PlannerService(repo)
        return await service.fetch_activities_by_trip()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-destinations-where-activities-start-after",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.DestinationSchemaOut],
)
async def get_destinations_where_activities_start_after(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    activity_start_time: Annotated[
        time,
        Query(
            description="Filter activities that start after this time (HH:MM format)"
        ),
    ],
) -> list[planner_schemas.DestinationSchemaOut]:
    """
    Retrieve all destinations that have at least one activity starting after a specified time.

    Args:
        async_session (AsyncSession): The database session for async queries.
        _ (User): The currently authenticated planner (with 'planner' scope).
        activity_start_time (time): Filter activities that start **after** this time (HH:MM format).

    Returns:
        list[planner_schemas.DestinationSchemaOut]: A list of destinations with activities
        starting after the specified time.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR if any unexpected error occurs during retrieval.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, activity_start_time=activity_start_time
        )
        service = PlannerService(repo)
        return await service.find_destinations_after_activity_start_time()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/activities-in-specified-interval",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.ActivitySchemaOut],
)
async def get_activities_in_specified_interval(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    destination_id_for_activity: Annotated[
        uuid.UUID,
        Query(
            description="Id of the destination",
        ),
    ],
    start_time: Annotated[
        datetime,
        Query(description="Start datetime in ISO format, e.g. 2025-11-14T09:11:21"),
    ],
    end_time: Annotated[
        datetime,
        Query(description="End datetime in ISO format, e.g. 2025-11-14T19:11:21"),
    ],
) -> list[planner_schemas.ActivitySchemaOut]:
    """
    Retrieve all activities for a specific destination within a specified time interval.

    This endpoint allows a planner to query activities that:
    - Belong to the given destination (`destination_id_for_activity`)
    - Start on or after the provided `start_time`
    - End on or before the provided `end_time`

    The query is performed asynchronously via the `PlannerService` and `PlannerRepository`.
    Results are returned as a list of `ActivitySchemaOut` Pydantic models.

    Args:
        async_session (AsyncSession): Async SQLAlchemy session dependency for database access.
        _: User: The currently authenticated planner (scoped security dependency).
        destination_id_for_activity (uuid.UUID): ID of the destination to filter activities.
        start_time (datetime): Start datetime for filtering activities (ISO format).
        end_time (datetime): End datetime for filtering activities (ISO format).

    Returns:
        list[planner_schemas.ActivitySchemaOut]: A list of activities matching the destination
        and time interval, each including name, description, start/end times, price, and ID.

    Raises:
        HTTPException: Raises 500 Internal Server Error for unexpected exceptions,
        or propagates existing HTTP exceptions.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session,
            destination_id_for_activity=destination_id_for_activity,
            start_time=start_time,
            end_time=end_time,
        )
        service = PlannerService(repo)
        return await service.activities_by_time_interval()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/total-amount-per-destination",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TotalCostOfActivitiesOut],
)
async def total_amount_per_destination(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    destination_id: Annotated[
        uuid.UUID,
        Query(
            description="Id of the destination",
        ),
    ],
) -> list[planner_schemas.TotalCostOfActivitiesOut]:
    """
    Retrieve the total cost of all activities for a specific destination.

    Args:
        async_session (AsyncSession): The active asynchronous database session.
        _ (User): The currently authenticated planner user (requires 'planner' scope).
        destination_id (uuid.UUID): The unique identifier of the destination for which
            the total activity cost will be calculated.

    Returns:
        list[planner_schemas.TotalCostOfActivitiesOut]:
            A list containing the total amount of all activities associated
            with the specified destination.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR: If an unexpected error occurs during processing.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, destination_id=destination_id
        )
        service = PlannerService(repo)
        return await service.total_amount_of_payment_per_destination()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/most-expensive-activity-per-destination",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.MostExpensiveActivityPerDestination],
)
async def get_most_expensive_activity_per_destination(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    destination_id: Annotated[
        uuid.UUID,
        Query(
            description="Id of the destination",
        ),
    ],
) -> list[planner_schemas.MostExpensiveActivityPerDestination]:
    """
    Retrieve the most expensive activity for a specific destination.

    Args:
        async_session (AsyncSession): The active asynchronous database session.
        _ (User): The currently authenticated planner (requires 'planner' scope).
        destination_id (uuid.UUID): The unique identifier of the destination
            for which the most expensive activity will be retrieved.

    Returns:
        list[planner_schemas.MostExpensiveActivityPerDestination]:
            A list containing the most expensive activity associated
            with the specified destination.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR: If an unexpected error occurs during processing.
    """

    try:
        repo = PlannerRepository(
            async_session=async_session, destination_id=destination_id
        )
        service = PlannerService(repo)
        return await service.get_the_most_expensive_activity_per_destination()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-users-in-trips-with-expensive-activities",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.UsersInTripsWithExpnsiveActivities]
)
async def get_users_in_trips_with_expensive_activities(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    activity_price: Annotated[
        Decimal,
        Query(description="Activity price",
              max_digits=6, decimal_places=2),
    ] = 1,
) -> list[planner_schemas.UsersInTripsWithExpnsiveActivities]:
    """
    Retrieve all users who participated in trips that include destinations 
    offering activities above a specified price.

    Args:
        async_session (AsyncSession): The active asynchronous database session.
        _ (User): The currently authenticated planner (requires 'planner' scope).
        activity_price (Decimal): The minimum price threshold for activities to consider 
            a destination as "expensive" (default: 1).

    Returns:
        list[planner_schemas.UsersInTripsWithExpnsiveActivities]:
            A list of users who are associated with trips containing at least one 
            destination where an activity exceeds the given price.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR: If an unexpected error occurs during processing.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, activity_price=activity_price
        )
        service = PlannerService(repo)
        return await service.fetch_users_in_trips_with_expensive_activities()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/most-expensive-trips",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripSchemaOut]
)
async def get_most_expensive_trips(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],
    number_of_trips: Annotated[
        int,
        Query(description="Number of trips", ge=1),
    ] = 1,
) -> list[planner_schemas.TripSchemaOut]:
    """
    Retrieve the most expensive trips based on their estimated budget.

    This endpoint returns a list of trips ordered by their estimated budget in 
    descending order, limited by the specified `number_of_trips`. It is accessible 
    only to authenticated planners.

    Args:
        async_session (AsyncSession): The active asynchronous database session.
        _ (User): The currently authenticated planner (must have 'planner' scope).
        number_of_trips (int): The maximum number of trips to return. Must be at least 1.

    Returns:
        list[planner_schemas.TripSchemaOut]:
            A list of the most expensive trips, including their title, description,
            trip type, duration, start and end dates, and estimated budget.

    Raises:
        HTTPException:
            - 500 INTERNAL SERVER ERROR: If an unexpected error occurs during processing.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session, number_of_trips=number_of_trips
        )
        service = PlannerService(repo)
        return await service.get_most_expensive_trips()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/get-trips-by-popularity",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.TripByPopularitySchemaOut]
)
async def get_trips_by_popularity(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],

) -> list[planner_schemas.TripByPopularitySchemaOut]:
    """
    Retrieve all trips ordered by their popularity.

    This endpoint returns a list of trips sorted by the number of participants, 
    from most popular to least popular. Popularity is determined by counting 
    how many users are associated with each trip.

    Args:
        async_session (AsyncSession): The asynchronous database session dependency.
        _ (User): The authenticated planner user (validated by scope "planner").

    Returns:
        list[planner_schemas.TripByPopularitySchemaOut]:
            A list of trips ordered by participant count. Each item includes:
            - trip_id: Unique identifier of the trip.
            - title: Title of the trip.
            - participants: Number of participants in the trip.

    Raises:
        HTTPException (500): If an unexpected error occurs during processing.

    Notes:
        - Only accessible to users with the "planner" scope.
        - Trips with zero participants are still included in the response.
    """

    try:
        repo = PlannerRepository(
            async_session=async_session,
        )
        service = PlannerService(repo)
        return await service.trips_by_popularity()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/destination-with-most-activities",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.DestinationWithMostActivities]
)
async def get_destination_with_most_activities(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],

) -> list[planner_schemas.DestinationWithMostActivities]:
    """
    Retrieve the destination with the highest number of activities.

    This endpoint returns the destination that has the most activities associated 
    with it. If multiple destinations have the same highest number of activities, 
    only one will be returned. Access is restricted to authenticated planners.

    Args:
        async_session (AsyncSession): The asynchronous database session.
        _ (User): The currently authenticated planner (must have 'planner' scope).

    Returns:
        list[planner_schemas.DestinationWithMostActivities]:
            A list containing the destination with the most activities, including:
            - dest_id: The unique identifier of the destination.
            - dest_name: The name of the destination.
            - nr_of_activities: The total number of activities at that destination.

    Raises:
        HTTPException (500): If an unexpected error occurs during query execution.

    Notes:
        - Only accessible to users with the "planner" scope.
        - Currently returns a single destination, even if multiple have the same max count.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session,
        )
        service = PlannerService(repo)
        return await service.destination_with_most_activities()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/average-activity-price-for-each-destination",
    status_code=status.HTTP_200_OK,
    response_model=list[planner_schemas.AvreagePriceOfActivitiesInEachDestinationOut]
)
async def get_average_activity_price_for_each_destination(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_planner, scopes=["planner"])],

) -> list[planner_schemas.AvreagePriceOfActivitiesInEachDestinationOut]:
    """
    Retrieve the average activity price for each destination.

    This endpoint calculates and returns the average price of all activities 
    grouped by their respective destinations. It helps planners analyze 
    which destinations tend to have higher or lower average activity costs.

    **Returns:**
        A list of objects, each containing:
        - `dest_id`: The unique ID of the destination.
        - `destination_name`: The name of the destination.
        - `average_price`: The average price of activities for that destination.

    **Raises:**
        - `HTTPException (500)`: If an unexpected error occurs while retrieving the data.
    """
    try:
        repo = PlannerRepository(
            async_session=async_session,
        )
        service = PlannerService(repo)
        return await service.get_average_price_of_activities_in_each_destination()

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
