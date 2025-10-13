from fastapi import APIRouter, status, HTTPException, Security, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_async_db
from typing import Annotated
import uuid
from pydantic import Field
from app.models.app_models import User
from app.utils.user_logic import get_current_active_admin
from app.repositories.admin_repository import AdminRepository
from app.services.admin_service import AdminService
from app.schemas import admin_schemas

router = APIRouter(tags=["the routes for the admin"], prefix="/v1/admin")


@router.delete(
    "/remove/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=admin_schemas.RemoveUserSchemaOut,
)
async def delete_user_or_planner(
    user_id: Annotated[uuid.UUID, Field(description="the user of the user or planner")],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_admin, scopes=["admin"])],
) -> admin_schemas.RemoveUserSchemaOut:
    """
    Delete a user or planner from the system (admin-only endpoint).

    This endpoint allows an authenticated admin to delete a specific user or planner
    by their UUID. The deletion logic is handled by the `AdminService`, which
    delegates to the `AdminRepository`.

    Security:
        Requires the current user to be an active admin.

    Args:
        user_id (UUID): The unique identifier of the user or planner to delete.
        async_session (AsyncSession): The asynchronous database session.
        _ (User): The authenticated admin user (required for security).

    Returns:
        Any: The result of the deletion operation, typically a confirmation
        message or the ID of the deleted user.

    Raises:
        HTTPException (400/404/500): If the deletion fails or the user does not exist.
    """

    try:
        repo = AdminRepository(async_session=async_session, user_id=user_id)
        service = AdminService(repo)
        return await service.delete_user()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.put(
    "/update/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=admin_schemas.IsActiveSchemaOut,
)
async def change_user_is_active_status(
    user_id: Annotated[uuid.UUID, Field(description="the user of the user or planner")],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_admin, scopes=["admin"])],
    status: Annotated[bool, admin_schemas.IsActiveSchemaIn, Body()]

) -> admin_schemas.IsActiveSchemaOut:
    """
    Update the active status of a specific user.

    This endpoint allows an admin user to toggle or modify the `is_active` status of a
    user or planner account identified by their UUID. It ensures that only users
    with the `admin` scope can perform this action.

    Args:
        user_id (uuid.UUID): The UUID of the user or planner whose active status should be updated.
        async_session (AsyncSession): The asynchronous SQLAlchemy session dependency for database operations.
        _ (User): The currently authenticated admin user, obtained via dependency injection and scope verification.

    Returns:
        JSONResponse: The updated user status after modification.

    Raises:
        HTTPException (404): If the specified user is not found.
        HTTPException (403): If the authenticated user lacks admin privileges.
        HTTPException (500): If an unexpected error occurs during the update process.
    """
    try:
        repo = AdminRepository(async_session=async_session,
                               user_id=user_id, status=status)
        service = AdminService(repo)
        return await service.update_user_status()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.get(
    "/all-users",
    status_code=status.HTTP_200_OK,
    response_model=list[admin_schemas.GetUsersPlannersSchemaOut],
)
async def get_all_planner_and_users(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    _: Annotated[User, Security(get_current_active_admin, scopes=["admin"])],
) -> list[admin_schemas.GetUsersPlannersSchemaOut]:
    """
    Retrieve all planner and user accounts.

    This endpoint allows an admin to fetch all users and planners from the system.
    Access is restricted to users with the `admin` scope.

    Args:
        async_session (AsyncSession): The asynchronous SQLAlchemy session dependency for database operations.
        _ (User): The currently authenticated admin user, obtained through dependency injection.

    Returns:
        list: A list of user and planner records retrieved from the database.

    Raises:
        HTTPException (403): If the authenticated user lacks admin privileges.
        HTTPException (500): If an unexpected error occurs during data retrieval.
    """

    try:
        repo = AdminRepository(async_session=async_session)
        service = AdminService(repo)
        return await service.all_planners_and_users()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
