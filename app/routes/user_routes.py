from app.utils.user_logic import get_current_active_user
from fastapi import APIRouter, status, HTTPException, Depends, Header, Form, UploadFile
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.schemas import user_schemas
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_connection import get_async_db
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from fastapi import Security
from app.models.app_models import User
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(tags=["the routes for the user"], prefix="/v1/user")


@router.post(
    "/sign-up",
    status_code=status.HTTP_201_CREATED,
    response_model=user_schemas.UserSchemaOut,
)
async def create_user_account(
    user_data_sign_up: user_schemas.UserSchemaIn,
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> user_schemas.UserSchemaOut:
    """
    Create a new user account.

    This endpoint receives user registration data, validates it,
    and creates a new user in the system. Passwords are securely
    hashed before storing. Returns the created user data (excluding the password).

    Args:
        user_data_sign_up (UserSchemaIn): A Pydantic model containing
            user registration information including:
            - username
            - email
            - password
            - confirm_password
            - scopes

    Returns:
        success message
    """
    try:
        repo = UserRepository(
            async_session=async_session, user_data_sign_up=user_data_sign_up
        )
        service = UserService(repo)
        return await service.create_user_account()
    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.post(
    "/sign-in",
    response_model=user_schemas.Token,
    status_code=status.HTTP_200_OK,
)
async def perform_user_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> user_schemas.Token:
    """
    Authenticate a user and issue JWT access and refresh tokens.

    Args:
        form_data (OAuth2PasswordRequestForm):
            OAuth2 form data containing the username, password, and optional scopes.
        async_session (AsyncSession):
            Asynchronous SQLAlchemy session dependency for database operations.

    Returns:
        user_schemas.Token:
            A token schema containing the `access_token`, `refresh_token`,
            and `token_type` ("bearer").

    Raises:
        HTTPException (401 Unauthorized):
            If the provided credentials are invalid.
        HTTPException (400 Bad Request):
            If a database integrity error occurs (e.g., invalid schema or constraint).
        HTTPException (500 Internal Server Error):
            If an unexpected error occurs during authentication.

    Notes:
        - Uses `UserRepository` and `UserService` to encapsulate business logic.
        - Returns both short-lived access tokens and longer-lived refresh tokens.
    """
    try:
        repo = UserRepository(form_data=form_data, async_session=async_session)
        service = UserService(repo)
        return await service.sign_in_user()

    except HTTPException:
        raise
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"an error occured: {str(e.orig)}",
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.post(
    "/logout", status_code=status.HTTP_200_OK, response_model=user_schemas.Loggout
)
async def sign_out_user(
    refresh_token: Annotated[str, Header()],
) -> user_schemas.Loggout:
    """
    Log out the currently authenticated user.

    This endpoint blacklists the provided JWT (access or refresh token),
    preventing further use until it naturally expires. The token is stored
    in Redis with a TTL equal to its remaining lifetime, after which Redis
    automatically deletes it.

    Args:
        sign_out_token (str): The JWT provided in the request header.

    Returns:
        schemas.LogoutResponseSchema: A response confirming successful logout.

    Raises:
        HTTPException (500): If an unexpected server error occurs during logout.
    """

    try:
        repo = UserRepository(refresh_token=refresh_token)
        service = UserService(repo)
        return await service.sign_out_user()
    except HTTPException:
        raise
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"an error occured: {str(e.orig)}",
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.post("/new-access-token", status_code=status.HTTP_200_OK)
async def get_new_access_token_from_refresh_token(
    refresh_token: Annotated[str, Header()],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
):
    """
    Generate a new access token from a valid refresh token.

    This endpoint accepts a refresh token in the request header, validates it,
    and if the token is valid and not blacklisted/expired, issues a new access token
    for the client. This allows clients to maintain authentication without requiring
    the user to log in again.

    Args:
        refresh_token (str): The refresh token provided in the request header.

    Returns:
        dict: A response containing the newly issued access token (and potentially
        related metadata, such as expiration time).

    Raises:
        HTTPException: If the refresh token is missing, invalid, expired, or revoked.
    """

    repo = UserRepository(refresh_token=refresh_token,
                          async_session=async_session)
    service = UserService(repo)
    return await service.get_new_access_token_from_refresh_token()


@router.patch(
    "/update-name",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateNameScheamOut,
)
async def update_user_name(
    update_name_data: Annotated[user_schemas.UpdateNameScheamIn, Form()],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateNameScheamOut:
    """
    Update the username of the currently authenticated user.

    This endpoint allows a user to change their existing username
    to a new one, provided the new username meets validation rules
    (e.g., uniqueness, format restrictions).

    Args:
        update_name_data (str): The new username to be set.

    Returns:
        JSONResponse: A success message and the updated user details
        if the operation is successful.
    """
    try:
        repo = UserRepository(
            update_name_data=update_name_data, async_session=async_session, user=user
        )
        service = UserService(repo)
        return await service.rename_user()
    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch(
    "/update-password",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateUserPasswordSchemaOut,
)
async def update_user_password(
    update_user_password_data: Annotated[
        user_schemas.UpdateUserPasswordSchemaIn, Form()
    ],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateUserPasswordSchemaOut:
    """
    Update the password of the currently authenticated user.

    This endpoint allows a user to securely change their password.
    It validates the input data, applies hashing, and updates the
    password in the database. The operation is performed using the
    UserService which interacts with the UserRepository.

    Args:
        update_user_password_data (UpdateUserPasswordSchemaIn):
            The current and new password information provided by the user.
        async_session (AsyncSession): The database session dependency.
        user (User): The currently authenticated user.

    Returns:
        UpdateUserPasswordSchemaOut: The result of the password update,
        typically confirming success or returning updated user info.

    Raises:
        HTTPException:
            - 400/401/403 for authentication or validation errors.
            - 500 for unexpected server errors during password update.
    """

    try:
        repo = UserRepository(
            update_user_password_data=update_user_password_data,
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.reset_password()
    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch(
    "/update-email",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateUserEmailSchemaOut,
)
async def update_user_email(
    update_user_email_data: Annotated[user_schemas.UpdateUserEmailSchemaIn, Form()],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateUserEmailSchemaOut:
    """
    Update the email address of the currently authenticated user.

    This endpoint allows a user to update their email address by submitting
    a PATCH request with the new email data. The update operation is handled
    asynchronously through the `UserService` and `UserRepository` layers.

    Args:
        update_user_email_data (UpdateUserEmailSchemaIn): The new email data
            provided via a form submission.
        async_session (AsyncSession): The asynchronous SQLAlchemy session
            dependency for database operations.
        user (User): The currently authenticated user, obtained via
            dependency injection and scope validation.

    Returns:
        UpdateUserEmailSchemaOut: The updated user data, typically including
        the new email address and other relevant fields.

    Raises:
        HTTPException: If the update fails, a 500 Internal Server Error
        is raised with details of the exception.
    """

    try:
        repo = UserRepository(
            update_user_email_data=update_user_email_data,
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.reset_email()

    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch(
    "/update-phone-number",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateUserPhoneNumberSchemaOut,
)
async def update_user_phone_number(
    update_user_phone_number_data: Annotated[
        user_schemas.UpdateUserPhoneNumberSchemaIn, Form()
    ],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateUserPhoneNumberSchemaOut:
    try:
        repo = UserRepository(
            update_user_phone_number_data=update_user_phone_number_data,
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.reset_phone_number()

    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch(
    "/update-date-of-birth",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateUserDateOfBirthSchemaOut,
)
async def update_user_date_of_birth(
    update_user_date_of_birth_data: Annotated[
        user_schemas.UpdateUserDateOfBirthSchemaIn, Form()
    ],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateUserDateOfBirthSchemaOut:
    """
    Update the date of birth for the currently authenticated user.

    This endpoint allows a user to update their date of birth by submitting
    a PATCH request with the new date. The update operation is handled
    asynchronously via the `UserService` and `UserRepository` layers.

    Args:
        update_user_date_of_birth_data (UpdateUserDateOfBirthSchemaIn):
            The new date of birth provided via form data.
        async_session (AsyncSession): The asynchronous database session.
        user (User): The currently authenticated user, obtained via
            dependency injection and security scope validation.

    Returns:
        The result of the `update_date_of_birth` method, typically
        the updated date of birth or a confirmation of the update.

    Raises:
        HTTPException:
            - 500 Internal Server Error: If any unexpected error occurs
              during the update process.
    """

    try:
        repo = UserRepository(
            update_user_date_of_birth_data=update_user_date_of_birth_data,
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.update_date_of_birth()

    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch(
    "/update-profile-picture",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.UpdateProfilePictureSchemaOut,
)
async def update_user_profile_picture(
    user_profile_picture: Annotated[
        user_schemas.UpdateProfilePictureSchemaIn, Depends()
    ],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.UpdateProfilePictureSchemaOut:
    """
    Update the authenticated user's profile picture.

    This endpoint allows an authenticated user to update their profile picture.
    It accepts an image upload (via `UpdateProfilePictureSchemaIn`) and stores
    the new profile picture in the database through the `UserService`.

    Args:
        user_profile_picture (UpdateProfilePictureSchemaIn): The input schema containing the new profile image data.
        async_session (AsyncSession): The database session dependency.
        user (User): The currently authenticated user, obtained via JWT authentication.

    Returns:
        UpdateProfilePictureSchemaOut: A response schema containing the updated profile picture data.

    Raises:
        HTTPException (401): If the user is not authenticated.
        HTTPException (500): If an unexpected error occurs during update.
    """

    try:
        repo = UserRepository(
            user_profile_picture=user_profile_picture,
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.update_profile_img()

    except HTTPException:
        raise
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.delete(
    "/delete-profile-picture",
    status_code=status.HTTP_200_OK,
    response_model=user_schemas.DeleteProfilePictureSchemaOut,
)
async def delete_user_profile_picture(
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
) -> user_schemas.DeleteProfilePictureSchemaOut:
    """
    Delete the authenticated user's profile picture.

    This endpoint allows an authenticated user to permanently delete their
    current profile picture. The deletion is processed through the
    `UserService`, which ensures that both the database reference and the
    stored image (if applicable) are removed.

    Args:
        async_session (AsyncSession): The asynchronous database session dependency.
        user (User): The currently authenticated user, verified through JWT authentication.

    Returns:
        DeleteProfilePictureSchemaOut: A response schema confirming the successful
        deletion of the user's profile picture.

    Raises:
        HTTPException (401): If the user is not authenticated.
        HTTPException (404): If no profile picture exists for the user.
        HTTPException (500): If an unexpected error occurs during deletion.
    """
    try:
        repo = UserRepository(
            async_session=async_session,
            user=user,
        )
        service = UserService(repo)
        return await service.delete_profile_img()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.get("/profile", status_code=status.HTTP_200_OK, response_model=user_schemas.UserProfileSchemaOut)
async def get_user_profile(
    user_profile: Annotated[User, Security(get_current_active_user, scopes=["user"])],
    async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> user_schemas.UserProfileSchemaOut:
    """
    Retrieve the currently authenticated user's profile.

    This endpoint uses the `UserService` and `UserRepository` layers to fetch
    the profile data for the authenticated user. The user is authenticated via
    JWT token and must have the `"user"` scope.

    Args:
        user (User): The authenticated user, provided by the dependency `get_current_active_user`.
        async_session (AsyncSession): The asynchronous SQLAlchemy database session.

    Returns:
        JSONResponse: The user's profile data as returned by the service layer.

    Raises:
        HTTPException: If the user is not found or an internal error occurs.
    """

    try:
        repo = UserRepository(user_profile=user_profile,
                              async_session=async_session)
        service = UserService(repo)
        return await service.fetch_user_profile()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.get("/profile-image", status_code=status.HTTP_200_OK)
async def get_user_profile_image(
        user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
        async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> StreamingResponse:
    """
    Retrieve and stream the authenticated user's profile image from the S3 bucket.

    This endpoint:
        - Authenticates the user using JWT and verifies their `user` scope.
        - Fetches the user's profile image from AWS S3 if one exists.
        - Streams the image back to the client as binary content.

    Dependencies:
        - `get_current_active_user`: Ensures the request is made by an authenticated and active user.
        - `get_async_db`: Provides an asynchronous database session for user data access.

    Raises:
        HTTPException:
            - 400 if the user does not have a profile picture.
            - 401 if authentication fails or the token is invalid.
            - 404 if the image could not be found.
            - 500 if an unexpected error occurs while retrieving the image.

    Returns:
        StreamingResponse: A streaming response containing the user's profile image.
    """

    try:
        repo = UserRepository(user=user,
                              async_session=async_session)
        service = UserService(repo)
        return await service.fetch_user_profile_image()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch("/deactivate", status_code=status.HTTP_200_OK, response_model=user_schemas.DeactivateAccountSchemaOut)
async def deactivate_account(
        user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
        async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> user_schemas.DeactivateAccountSchemaOut:
    """
    Deactivate the currently authenticated user's account.

    This endpoint allows an authenticated user to deactivate their account,
    effectively setting the `is_active` field to `False` in the database.

    Workflow:
    - Retrieves the current user from the JWT token.
    - Checks if the account is already inactive.
    - Updates the user's `is_active` status in the database to `False`.
    - Returns a success message upon successful deactivation.

    Args:
        user (User): The currently authenticated user, obtained via dependency injection.
        async_session (AsyncSession): SQLAlchemy asynchronous database session.

    Returns:
        DeactivateAccountSchemaOut: A success message confirming account deactivation.

    Raises:
        HTTPException 400: If the account is already inactive.
        HTTPException 404: If the user could not be found or the update failed.
        HTTPException 500: If an unexpected server error occurs.
    """

    try:
        repo = UserRepository(user=user,
                              async_session=async_session)
        service = UserService(repo)
        return await service.deactivate_account()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )


@router.patch("/reactivate", status_code=status.HTTP_200_OK, response_model=user_schemas.ReactivateAccountScheamaOut)
async def reactivate_account(
        user: Annotated[User, Security(get_current_active_user, scopes=["user"])],
        async_session: Annotated[AsyncSession, Depends(get_async_db)],
) -> user_schemas.ReactivateAccountScheamaOut:
    """
    Reactivate the authenticated user's account.

    This endpoint performs the following actions:
    - Ensures the user is authenticated and has the required "user" scope.
    - Uses the `UserService` to reactivate the user's account.
    - Returns a success message if the account is successfully reactivated.

    Args:
        user (User): The currently authenticated user, injected via security dependency.
        async_session (AsyncSession): The SQLAlchemy asynchronous session, injected via dependency.

    Returns:
        ReactivateAccountScheamaOut: A schema containing a success message confirming account reactivation.

    Raises:
        HTTPException 400: If the user's account is already active.
        HTTPException 404: If the user's account could not be found or updated.
        HTTPException 500: If an unexpected error occurs during the process.
    """

    try:
        repo = UserRepository(user=user,
                              async_session=async_session)
        service = UserService(repo)
        return await service.reactivate_account()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: {str(e)}",
        )
