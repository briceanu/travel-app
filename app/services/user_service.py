from app.repositories.user_repository import UserRepository
from dataclasses import dataclass


@dataclass
class UserService:
    """
    Service class responsible for handling user-related business logic.

    This class acts as an intermediary between the API layer and the
    UserRepository. It encapsulates operations such as creating a user,
    updating user data, and other business rules related to users.
    """

    def __init__(self, repository: UserRepository):
        """
        Initialize the UserService with a user repository.

        Args:
            repository (UserRepository): An instance of UserRepository
                used to interact with the database for user operations.
        """
        self.repository = repository

    async def create_user_account(self):
        """
        Create a new user account using the repository.

        This method delegates the creation of the user to the repository,
        which handles database interaction, including hashing the password
        and saving the user record.

        Returns:
            dict: The newly created user data (excluding sensitive information like password).
        """
        return await self.repository.create_user()

    async def sign_in_user(self):
        """
        Sign in a user by delegating authentication to the repository.

        This method calls the repository's `login_user` method to authenticate
        the user and retrieve any necessary authentication tokens or session data.

        Returns:
            Any: The result of the repository's `login_user` method, typically
            authentication tokens or user session information.

        Notes:
            - This method is asynchronous and should be awaited.
            - Actual authentication logic is handled in the repository layer.
        """
        return await self.repository.login_user()

    async def sign_out_user(self):
        """
        Logs out the currently authenticated user by calling the repository's
        logout_user method. Typically, this involves invalidating the user's
        access and/or refresh tokens, clearing session data, or performing any
        other necessary cleanup to ensure the user is fully signed out.

        Returns:
            Any: The result returned by the repository's logout_user method,
            which may include a success message or confirmation of logout.
        """
        return await self.repository.logout_user()

    async def get_new_access_token_from_refresh_token(self):
        """
        Retrieve a new access token using the refresh token.

        This method delegates the operation to the repository layer, where the
        refresh token is validated and, if valid, a new access token is issued.
        It is typically used when a client's current access token has expired
        and the client presents a valid refresh token to obtain a new one.

        Returns:
            str | dict: The newly generated access token (or a response object
            containing the token and additional metadata, depending on the repository implementation).

        Raises:
            HTTPException: If the refresh token is invalid, expired, or revoked.
        """
        return await self.repository.access_token_from_refresh_token()

    async def rename_user(self):
        """
        Rename the current user by delegating the update operation
        to the underlying repository.

        Returns:
            Any: The result of the repository's update operation,
            typically the updated user object or a status indicator.

        Raises:
            Exception: Propagates any exceptions raised by the repository
            during the update process.
        """

        return await self.repository.update_user_name()

    async def reset_password(self):
        """
        Reset the password of the current user by delegating the operation
        to the underlying repository.

        This method handles the logic for updating the user's password
        securely, typically including hashing and validation, through the
        repository layer.

        Returns:
            Any: The result of the repository's password update operation,
            usually the updated user object or a status confirmation.

        Raises:
            Exception: Propagates any exceptions raised by the repository
            during the password reset process.
        """

        return await self.repository.update_user_password()

    async def reset_email(self):
        """
        Reset the email address of a user.

        This asynchronous method delegates the email update operation
        to the `update_user_email` method of the repository. The repository
        is responsible for performing the actual update in the database.

        Returns:
            The result of the `update_user_email` operation, typically
            the updated user object or confirmation of the email change.
        """
        return await self.repository.update_user_email()

    async def reset_phone_number(self):
        """
        Reset the phone number of the current user.

        This asynchronous method delegates the update operation to the
        repository layer, which performs the actual database update.

        Returns:
            The result of the `update_user_phone_number` operation,
            typically an object or schema containing the updated phone number.
        """
        return await self.repository.update_user_phone_number()

    async def update_date_of_birth(self):
        """
        Update the date of birth of the current user.

        This asynchronous method delegates the update operation to the
        repository layer, which performs the actual database update.

        Returns:
            The result of the `update_user_date_of_birth` operation,
            typically a schema containing the updated date of birth.
        """
        return await self.repository.update_date_of_birth()

    async def update_profile_img(self):
        """
        Update the profile image of the current user by delegating the
        operation to the repository.

        This method handles updating the user's profile picture, which
        may include storing the image, validating its format/size, and
        saving the reference in the database.

        Returns:
            Any: The result of the repository's update operation, typically
            the updated user object or a status confirmation.

        Raises:
            Exception: Propagates any exceptions raised by the repository
            during the profile image update process.
        """

        return await self.repository.update_profile_picture()

    async def delete_profile_img(self):
        """
        Delete the authenticated user's profile image.

        This method removes the current profile image associated with the user
        from both the database and storage (if applicable). It ensures that the
        user's profile no longer references an outdated or invalid image.

        Returns:
            UpdateProfilePictureSchemaOut: A response schema confirming the successful
            deletion of the user's profile image.

        Raises:
            HTTPException (404): If the user does not have a profile image set.
            HTTPException (500): If an unexpected error occurs during the deletion process.
        """
        return await self.repository.delete_profile_picture()

    async def fetch_user_profile(self):
        """
        Asynchronously fetches the authenticated user's profile data.

        This method delegates the actual database retrieval to the repository layer
        by calling `self.repository.get_user_profile()`. It returns the user profile
        information, typically as a Pydantic schema or dictionary.

        Returns:
            UserProfileSchema | dict: The user's profile data retrieved from the repository.
        """

        return await self.repository.get_user_profile()

    async def fetch_user_profile_image(self):
        """
        Asynchronously fetches the authenticated user's profile image.

        This method delegates the retrieval of the user's profile image to the
        repository layer by calling `self.repository.get_user_profile_image()`.
        The returned result is typically a URL, file path, or serialized data
        representing the user's profile image.

        Returns:
            str | Any: The user's profile image data or URL as returned by the repository.
        """

        return await self.repository.get_user_profile_image()

    async def deactivate_account(self):
        """
        Deactivate the currently authenticated user's account.

        This method delegates the deactivation process to the repository layer,
        which updates the user's status in the database (e.g., sets `is_active` to False).

        Raises:
            HTTPException:
                - 404 if the user could not be found.
                - 500 if a database or unexpected error occurs during deactivation.

        Returns:
            DeactivateAccountSchemaOut: A schema confirming successful account deactivation.
        """
        return await self.repository.deactivate_user_account()

    async def reactivate_account(self):
        """
        Reactivate the currently authenticated user's account.

        This method delegates the reactivation logic to the repository layer,
        which updates the user's `is_active` status to `True` in the database.

        Returns:
            str: A confirmation message indicating that the account has been successfully reactivated.

        Raises:
            HTTPException 400: If the account is already active.
            HTTPException 404: If the account could not be found or updated.
        """
        return await self.repository.reactivate_user_account()

    async def join_trip(self):
        """
        Registers the current user for a trip.

        This method calls the repository's `register_for_trip` function to
        handle the actual registration logic asynchronously.

        Returns:
            Any: The result returned by `repository.register_for_trip()`,
            typically a confirmation of registration or trip details.
        """
        return await self.repository.register_for_trip()

    async def leave_trip(self):
        """
        Unregisters the current user from a trip.

        This method calls the repository's `unregister_from_trip` function to
        handle the process of leaving the trip asynchronously.

        Returns:
            Any: The result returned by `repository.unregister_from_trip()`,
            typically a confirmation message or updated trip details.
        """
        return await self.repository.unregister_from_trip()
