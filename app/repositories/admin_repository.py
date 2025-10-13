from app.interfaces.admin_interfaces import AbstractAdminInterface
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from sqlalchemy import delete, update, select
from app.models.app_models import User
from fastapi import HTTPException, status
from app.schemas import admin_schemas


@dataclass
class AdminRepository(AbstractAdminInterface):
    user_id: uuid.UUID | None = None
    async_session: AsyncSession | None = None
    status: admin_schemas.IsActiveSchemaIn | None = None

    async def remove_user(self) -> admin_schemas.RemoveUserSchemaOut:
        """
        Delete a user from the database by their unique ID.

        This method executes a deletion query for the user with `self.user_id`.
        If the user exists, they are removed from the database and a confirmation
        message is returned. If the user does not exist, an HTTP 404 error is raised.

        Returns:
            RemoveUserSchemaOut: A Pydantic schema containing a success message
            confirming the user has been deleted.

        Raises:
            HTTPException (404): If no user with the specified ID exists in the database.
        """
        stmt = delete(User).where(User.user_id ==
                                  self.user_id).returning(User.username)
        username = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if not username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user with the id {self.user_id} found.",
            )
        await self.async_session.commit()
        return admin_schemas.RemoveUserSchemaOut(
            success=f"User {username} successfully removed."
        )

    async def update_user_is_active_status(self) -> admin_schemas.IsActiveSchemaOut:
        """
        Deactivate a user by setting their `is_active` status to False.

        This method updates the `is_active` field of a specific user identified by their
        `user_id`. It returns a success message if the operation is successful, or raises
        an HTTPException if the user does not exist.

        Returns:
            admin_schemas.IsActiveSchemaOut: A response schema containing a success message.

        Raises:
            HTTPException (404): If no user with the specified `user_id` is found in the database.
            HTTPException (500): If an unexpected error occurs during the database operation.
        """
        stmt = (
            update(User)
            .where(User.user_id == self.user_id)
            .values(is_active=self.status.is_active)
            .returning(User.username)
        )
        username = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if not username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user with the id {self.user_id} found.",
            )
        await self.async_session.commit()
        return admin_schemas.IsActiveSchemaOut(
            success=f"User's {username} active status changed."
        )

    async def get_planners_and_users(self) -> list[admin_schemas.GetUsersPlannersSchemaOut]:
        """
        Fetch all planner and user accounts from the database.

        This method retrieves all user records from the database, serializes them into
        `GetUsersPlannersSchemaOut` objects, and returns the complete list. It is primarily 
        used by admin services to display all registered users and planners.

        Returns:
            list[admin_schemas.GetUsersPlannersSchemaOut]: 
                A list of serialized user and planner data, including fields such as 
                `user_id`, `username`, `email`, `is_active`, `phone_number`, 
                `date_of_birth`, `profile_picture`, and `scopes`.

        Raises:
            HTTPException (500): If an unexpected error occurs while querying the database.
        """

        users = (await self.async_session.execute(select(User))).scalars().all()
        serialized_users = [
            admin_schemas.GetUsersPlannersSchemaOut(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                phone_number=user.phone_number,
                date_of_birth=user.date_of_birth,
                profile_picture=user.profile_picture,
                scopes=user.scopes
            )
            for user in users
        ]
        return serialized_users
