from app.repositories.admin_repository import AdminRepository


class AdminService:
    """
    Service layer for administrative operations.

    This class provides business logic related to administrative tasks,
    delegating database operations to the `AdminRepository`.
    """

    def __init__(self, repository: AdminRepository):
        """
        Initialize the AdminService with a repository instance.

        Args:
            repository (AdminRepository): The repository responsible for
                performing database operations related to admin tasks.
        """
        self.repository = repository

    async def delete_user(self):
        """
        Delete a user from the database.

        This method delegates the deletion operation to the `AdminRepository`.

        Returns:
            Any: The result returned by `AdminRepository.remove_user()`,
            typically a confirmation of deletion or the removed user ID.

        Raises:
            HTTPException: If the user does not exist or deletion fails.
        """
        return await self.repository.remove_user()

    async def update_user_status(self):
        """
        Update the active status of a user.

        This method delegates to the repository layer's `update_user_is_active_status`
        method to modify the `is_active` field of a user in the database. It can be
        used to activate or deactivate a user account.

        Returns:
            Any: The result returned by the repository, typically a confirmation
            message or the updated user record.

        Raises:
            HTTPException: If the user does not exist or the update operation fails.
        """

        return await self.repository.update_user_is_active_status()

    async def all_planners_and_users(self):
        """
        Retrieve all planner and user accounts.

        This method fetches and returns a list of all users and planners
        from the repository layer.

        Returns:
            list: A list of user and planner records retrieved from the database.

        Raises:
            HTTPException (500): If an unexpected error occurs while fetching data.
        """

        return await self.repository.get_planners_and_users()
