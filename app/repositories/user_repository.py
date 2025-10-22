from dataclasses import dataclass
from app.interfaces.user_interface import AbstractUserInterface
from app.schemas import user_schemas
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_models import User, Trip
from sqlalchemy import insert, select, update
from pwdlib import PasswordHash
from app.utils.celery_tasks import send_welcome_email
from fastapi.security import OAuth2PasswordRequestForm
from app.utils import user_logic
from fastapi import HTTPException, status
from datetime import timedelta
import jwt
import os
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from app.utils import user_logic
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, selectinload
from app.utils.celery_tasks import s3_upload
from app.utils.boto3_client import s3_presigned_url, s3_delete, s3_get_object
from fastapi.responses import StreamingResponse
from fastapi.exceptions import HTTPException
from botocore.exceptions import ClientError, NoCredentialsError
import uuid
from app.utils.logger import logger

load_dotenv()
REFRESH_SECRET = os.getenv("REFRESH_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
BUCKET_NAME = os.getenv("BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

pwd_context = PasswordHash.recommended()


@dataclass
class UserRepository(AbstractUserInterface):
    """
    Repository class for handling user-related database operations.

    Attributes:
        user_data_sign_up (user_schemas.UserSchemaIn | None):
            Input schema containing user sign-up data such as username,
            email, password, and scopes. Used when creating a new user.
        async_session (AsyncSession | None):
            SQLAlchemy asynchronous session for interacting with the database.
        form_data (OAuth2PasswordRequestForm | None):
            OAuth2 form data containing username, password, and scopes.
            Used during user login and authentication.

    Responsibilities:
        - Managing user persistence and retrieval from the database.
        - Creating new user records.
        - Authenticating users via login credentials.
        - Acting as the main interface between the service layer and the database.
    """

    user_data_sign_up: user_schemas.UserSchemaIn | None = None
    async_session: AsyncSession | None = None
    form_data: OAuth2PasswordRequestForm | None = None
    refresh_token: str | None = None
    update_name_data: user_schemas.UpdateNameScheamIn | None = None
    user: User | None = None
    update_user_password_data: user_schemas.UpdateUserPasswordSchemaIn | None = None
    update_user_email_data: user_schemas.UpdateUserEmailSchemaIn | None = None
    update_user_phone_number_data: user_schemas.UpdateUserPhoneNumberSchemaIn | None = (
        None
    )
    update_user_date_of_birth_data: (
        user_schemas.UpdateUserDateOfBirthSchemaIn | None
    ) = None
    user_profile_picture: user_schemas.UpdateProfilePictureSchemaIn | None = None
    user_profile: User | None = None
    trip_id: uuid.UUID | None = None

    async def create_user(self) -> user_schemas.UserSchemaOut:
        """
        Create a new user in the database and enqueue a welcome email task.

        This method performs the following actions:
        1. Hashes the user's password.
        2. Inserts the user record into the database using an asynchronous session.
        3. Commits the transaction.
        4. Enqueues a Celery task to send a welcome email to the new user.

        Returns:
            app_schemas.UserSchemaOut: A schema object containing a success message
            indicating that the user was created and a welcome email will be sent.

        Notes:
            - This method is asynchronous and should be awaited.
            - The welcome email is sent asynchronously using Celery; this method
            does not wait for the email to be sent.
        """

        user_data = {
            "username": self.user_data_sign_up.username,
            "email": self.user_data_sign_up.email,
            "password": pwd_context.hash(self.user_data_sign_up.password),
            "scopes": self.user_data_sign_up.scopes,
            "is_active": True,
        }
        try:
            stmt = insert(User).values(**user_data)
            await self.async_session.execute(stmt)
            await self.async_session.commit()
            # using a celery task we send a email to the user
            send_welcome_email.delay(
                self.user_data_sign_up.email, self.user_data_sign_up.username
            )
            return user_schemas.UserSchemaOut(
                success="Your account has been created, and a welcome email will be sent to your email."
            )
        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=400, detail="Username or email already exists."
            )

    async def login_user(self) -> user_schemas.Token:
        """
        Authenticate a user with the provided username, password, and scopes,
        and return JWT access and refresh tokens upon successful login.

        Steps:
            1. Validates the user's credentials against the database.
            2. Raises a 401 Unauthorized exception if authentication fails.
            3. Creates an access token (short-lived) and a refresh token (longer-lived).
            4. Returns both tokens in a standardized Token schema.

        Returns:
            user_schemas.Token: A schema containing:
                - token_type (str): The token type, e.g. "bearer".
                - access_token (str): The signed JWT access token with an expiry of 30 minutes.
                - refresh_token (str): The signed JWT refresh token with an expiry of 3 hours.

        Raises:
            HTTPException: If the provided credentials are invalid or authentication fails.
        """
        unauthorized_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        user = await user_logic.authenticate_user(
            username=self.form_data.username,
            password=self.form_data.password,
            scopes=self.form_data.scopes,
            async_session=self.async_session,
        )

        if not user:
            raise unauthorized_exception

        data = {"sub": user.username, "scopes": user.scopes}
        access_token = user_logic.create_acess_token(
            expires_delta=timedelta(minutes=30), data=data
        )
        refresh_token = user_logic.create_refresh_token(
            expires_delta=timedelta(hours=3), data=data
        )
        return user_schemas.Token(
            token_type="bearer", access_token=access_token, refresh_token=refresh_token
        )

    async def logout_user(self) -> user_schemas.Loggout:
        """
        Logs out the user by blacklisting the provided JWT token.

        This function extracts the unique token identifier (JTI) from the given
        JWT, calculates its remaining time-to-live (TTL), and stores it in a
        Redis blacklist. This ensures that the token can no longer be used for
        authentication, effectively logging the user out.

        Args:
            token (str): The JWT access or refresh token to be invalidated.

        Returns:
            dict: A confirmation message indicating successful logout.

        Raises:
            HTTPException: If the token is invalid or malformed.
        """

        invalid_token_error = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
        )
        try:
            payload = jwt.decode(
                self.refresh_token, REFRESH_SECRET, algorithms=ALGORITHM
            )
            jti = payload.get("jti")
            exp = payload.get("exp")
            if not jti or not exp:
                raise invalid_token_error
            if user_logic.is_token_blacklisted(jti=jti) == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token already black listed.",
                )
            ttl = int(exp) - int(datetime.now(timezone.utc).timestamp())
            user_logic.black_list_token(jti, ttl)

        except (InvalidTokenError, ExpiredSignatureError):
            raise invalid_token_error

        return user_schemas.Loggout(success="Loggedout successfully.")

    async def access_token_from_refresh_token(
        self,
    ) -> user_schemas.NewAccessTokenSchemaOut:
        """
        Generate a new access token from a valid refresh token.

        This method performs the following steps:
        1. Decodes the provided refresh JWT token using the REFRESH_SECRET and algorithm.
        2. Validates the existence of the token's JWT ID (`jti`) and associated user (`sub`).
        3. Checks whether the refresh token has been blacklisted.
        4. Verifies that the token's scopes are present and still permitted for the user.
        5. Issues a new access token with the user's current scopes and returns it.

        Returns:
            NewAccessTokenResponseSchema: A Pydantic response schema containing the new access token.

        Raises:
            HTTPException (400): If the token is malformed or the user doesn't exist.
            HTTPException (401): If the token is expired, revoked, or permissions are insufficient.
        """

        try:
            payload = jwt.decode(
                self.refresh_token, REFRESH_SECRET, algorithms=ALGORITHM
            )

            jti = payload.get("jti")
            username = payload.get("sub")
            token_scopes = payload.get("scopes", [])
            if not jti or not username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid refresh token.",
                )
            if user_logic.is_token_blacklisted(jti) == 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token has been revoked.",
                )
            user_in_db = (
                await self.async_session.execute(
                    select(User).where(User.username == username)
                )
            ).scalar_one_or_none()
            if not user_in_db:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid refresh token.",
                )
            user_in_db_set_scopes = set(user_in_db.scopes)
            token_scopes_set = set(token_scopes)
            if not (user_in_db_set_scopes.intersection(token_scopes_set)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not enough permissions",
                )

            access_token = user_logic.create_acess_token(
                data={"sub": user_in_db.username, "scopes": user_in_db.scopes},
                expires_delta=timedelta(minutes=30),
            )
            return user_schemas.NewAccessTokenSchemaOut(
                token_type="bearer", access_token=access_token
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail="Refresh token has expired")
        except InvalidTokenError:
            raise HTTPException(
                status_code=401, detail="Invalid refresh token")

    async def update_user_name(self) -> user_schemas.UpdateNameScheamOut:
        """
        Update the current user's username in the database.

        This method attempts to update the username for the user identified
        by `self.user.username` to a new value provided in
        `self.update_name_data.new_name`.

        Workflow:
            1. Executes a SQL UPDATE statement to change the username.
            2. If no rows are affected (`rowcount == 0`), raises an HTTP 400 error.
            3. If the new username violates a uniqueness constraint, rolls back
            the transaction and raises an HTTP 400 error with a proper message.
            4. On success, commits the transaction and returns a success schema.

        Raises:
            HTTPException(400): If no user is found to update or if the new
                                username is already in use.

        Returns:
            UpdateNameScheamOut: Pydantic schema indicating success.
        """

        try:
            result = await self.async_session.execute(
                update(User)
                .where(User.username == self.user.username)
                .values(username=self.update_name_data.new_name)
            )
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Could not update name",
                )
            await self.async_session.commit()
            return user_schemas.UpdateNameScheamOut(
                success="Your name has been updated."
            )
        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Name already in use."
            )

    async def update_user_password(self) -> user_schemas.UpdateUserPasswordSchemaOut:
        """
        Update the password of the current user using the ORM without loading the full user object.

        This method performs the following steps:
            1. Efficiently fetches the user from the database, loading only the `user_id` and `password` fields.
            2. Checks if the user exists; raises HTTP 404 if not found.
            3. Hashes the new password and assigns it to the user object.
            4. Commits the changes to the database.
            5. Rolls back the transaction and raises HTTP 500 if any database error occurs during the commit.

        Notes:
            - Only minimal columns are loaded to reduce memory usage.
            - ORM change tracking ensures that the password update is persisted.
            - Relationships and cascading updates will apply if configured in the ORM model.

        Raises:
            HTTPException(404): If the user does not exist.
            HTTPException(500): If any database error occurs during the update.

        Returns:
            UpdateUserPasswordSchemaOut: Pydantic schema indicating successful password update.
        """

        try:
            stmt = (
                select(User)
                .options(load_only(User.user_id, User.password))
                .where(User.username == self.user.username)
            )

            user = (await self.async_session.execute(stmt)).scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            user.password = pwd_context.hash(
                self.update_user_password_data.new_password
            )
            await self.async_session.commit()
            return user_schemas.UpdateUserPasswordSchemaOut(
                success="Your password has been updated."
            )
        except Exception as e:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Could not update password due to a database error. {str(e)}",
            )

    async def update_user_email(self) -> user_schemas.UpdateUserEmailSchemaOut:
        """
        Update the email address of the current user.

        This asynchronous method updates the `email` field of the user identified
        by `self.user.username` (hardcoded as "awd" in this example). The new email
        is taken from `self.update_user_email_data.new_email`. The update operation
        is executed via SQLAlchemy's asynchronous session.

        Returns:
            UpdateUserEmailSchemaOut: A schema containing the updated email.

        Raises:
            HTTPException:
                - 404 Not Found: If no user was found or the update did not occur.
                - 400 Bad Request: If an `IntegrityError` occurs, typically due to
                  a duplicate email violating a unique constraint.
        """

        try:
            result = (
                await self.async_session.execute(
                    update(User)
                    .values(email=self.update_user_email_data.new_email)
                    .where(User.username == "awd")
                    .returning(User.email)
                )
            ).scalar_one_or_none()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Email update failed."
                )

            await self.async_session.commit()
            return user_schemas.UpdateUserEmailSchemaOut(
                new_email=f"Your new email is: {result}"
            )

        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use."
            )

    async def update_user_phone_number(
        self,
    ) -> user_schemas.UpdateUserPhoneNumberSchemaOut:
        """
        Update the phone number of the current user.

        This method updates the `phone_number` field for the user identified
        by `self.user.username`. The new phone number is provided via
        `self.update_user_phone_number_data`. The operation is executed
        asynchronously using SQLAlchemy.

        Returns:
            UpdateUserPhoneNumberSchemaOut: A schema containing the updated
            phone number.

        Raises:
            HTTPException:
                - 404 Not Found: If the update did not affect any row, which may
                  indicate that the user does not exist or no changes were applied.
                - 400 Bad Request: If an `IntegrityError` occurs (e.g., a duplicate
                  phone number or constraint violation).
        """

        try:
            stmt = (
                update(User)
                .where(User.username == self.user.username)
                .values(phone_number=self.update_user_phone_number_data.phone_number)
                .returning(User.phone_number)
            )
            result = (await self.async_session.execute(stmt)).scalar_one_or_none()
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Phone number update failed.",
                )
            await self.async_session.commit()
        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update phone number.",
            )

        return user_schemas.UpdateUserPhoneNumberSchemaOut(
            phone_number=f"Your phone number is: {result}"
        )

    async def update_date_of_birth(self) -> user_schemas.UpdateUserDateOfBirthSchemaOut:
        """
        Update the date of birth for the current user.

        This asynchronous method updates the `date_of_birth` field of the user
        identified by `self.user.username` using the value provided in
        `self.update_user_date_of_birth_data`. The operation is executed via
        SQLAlchemy's asynchronous session.

        Returns:
            UpdateUserDateOfBirthSchemaOut: A schema confirming the successful
            update of the user's date of birth.

        Raises:
            HTTPException:
                - 404 Not Found: If the update did not affect any rows, indicating
                  that the user may not exist.
                - 400 Bad Request: If an `IntegrityError` occurs during the update,
                  such as a database constraint violation.
        """

        try:
            stmt = (
                update(User)
                .where(User.username == self.user.username)
                .values(date_of_birth=self.update_user_date_of_birth_data.date_of_birth)
            )
            result = await self.async_session.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Date of birth update failed.",
                )
            await self.async_session.commit()
        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update date of birth.",
            )

        return user_schemas.UpdateUserDateOfBirthSchemaOut(
            success="Your date of birth has been updated."
        )

    async def update_profile_picture(self):
        """
        Update the profile picture of the currently authenticated user.

        This method handles reading the uploaded image file, deleting any
        existing profile picture from S3, uploading the new picture to S3
        asynchronously via Celery tasks, and updating the user's database
        record with the new image URL.

        Steps:
            1. Generate a unique S3 key based on the user's ID.
            2. If the user already has a profile picture, delete it from S3.
            3. Read the new image file content.
            4. Upload the new image to S3 asynchronously using a Celery task.
            5. Save the new S3 URL in the database.
            6. Return a success response or raise an HTTPException on failure.

        Returns:
            UpdateProfilePictureSchemaOut: Contains a success message
            confirming that the image was uploaded.

        Raises:
            HTTPException:
                - 404 if the database update fails after S3 upload.
                - 400 if a database integrity error occurs during the update.
        """
        try:
            key = str(self.user.user_id)
            file_extension = self.user_profile_picture.picture.filename.split(
                '.')[-1]
            # check to see if the user has already a url picture in db
            # if it has we delete it
            if self.user.profile_picture:
                # call the delete function to remove the previous picture
                s3_delete(key=key, bucket=BUCKET_NAME)
            # proceed to upload the images to s3
            file_content = await self.user_profile_picture.picture.read()
            s3_upload.delay(
                content_type=f"image/{file_extension}",
                body=file_content,
                key=key,
                bucket=BUCKET_NAME,
            )
            # save the url image string in db
            profile_picture_url = (
                f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
            )

            stmt = (
                update(User)
                .values(profile_picture=profile_picture_url)
                .where(User.username == self.user.username)
                .returning(User.username)
            )

            username = (await self.async_session.execute(stmt)).scalar_one_or_none()
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Image upload failed."
                )
            await self.async_session.commit()
            return user_schemas.UpdateProfilePictureSchemaOut(
                success=f"{username}, your profile picture has been uploaded."
            )
        except NoCredentialsError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AWS credentials not found.",
            )
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete image from S3: {e.response['Error']['Message']}",
            )
        except IntegrityError:
            await self.async_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update image.",
            )

    async def delete_profile_picture(
        self,
    ) -> user_schemas.DeleteProfilePictureSchemaOut:
        """
        Delete the authenticated user's profile picture.

        This method removes the profile picture reference from the database
        for the authenticated user and triggers an asynchronous deletion
        from the S3 bucket using a Celery task. If no profile picture exists,
        or the database update fails, an HTTPException is raised.

        Raises:
            HTTPException:
                - 400 if the user has no profile picture.
                - 404 if the database update fails.

        Returns:
            DeleteProfilePictureSchemaOut: A schema confirming successful deletion.
        """

        key = str(self.user.user_id)
        if not self.user.profile_picture:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user profile picture found.",
            )
        result = (
            await self.async_session.execute(
                update(User)
                .where(User.username == self.user.username)
                .values(profile_picture=None)
                .returning(User.username)
            )
        ).scalar_one_or_none()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not delete profile picture.",
            )

        await self.async_session.commit()
        s3_delete(key=key, bucket=BUCKET_NAME)
        return user_schemas.DeleteProfilePictureSchemaOut(
            success=f"{result}'s profile picture removed successfully."
        )

    async def get_user_profile(self) -> user_schemas.UserProfileSchemaOut:
        """
        Asynchronously retrieves the authenticated user's profile information.

        This method generates a presigned URL for the user's profile picture stored in S3
        and returns the complete profile data serialized as a `UserProfileSchemaOut` object.

        Returns:
            UserProfileSchemaOut: An object containing the user's profile details, including
            the S3 presigned URL for the profile picture.

        Raises:
            Exception: If an unexpected error occurs while generating the presigned URL.
        """
        presigned_url = (
            s3_presigned_url(bucket=BUCKET_NAME, key=str(
                self.user_profile.user_id))
            if self.user_profile and self.user_profile.profile_picture
            else None
        )
        return user_schemas.UserProfileSchemaOut(
            user_id=self.user_profile.user_id,
            username=self.user_profile.username,
            email=self.user_profile.email,
            is_active=self.user_profile.is_active,
            date_of_birth=self.user_profile.date_of_birth,
            profile_picture=presigned_url,
            scopes=self.user_profile.scopes,
        )

    async def get_user_profile_image(self) -> StreamingResponse:
        """
        Retrieve the user's profile image from the S3 bucket and stream it back as a response.

        This method:
            - Checks if the user has an existing profile picture in the database.
            - Fetches the corresponding image object from the configured S3 bucket using the user's ID as the key.
            - Streams the image file back to the client as a `StreamingResponse`.

        Raises:
            HTTPException:
                - 400 if the user does not have a profile picture set.
                - 500 if there is an error retrieving the image from S3.

        Returns:
            StreamingResponse: A streaming response containing the user's profile image file.
        """

        if not self.user.profile_picture:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no profile image.",
            )
        s3_object = s3_get_object(
            bucket=BUCKET_NAME, key=str(self.user.user_id))
        file_stream = s3_object["Body"]  # this is a stream
        return StreamingResponse(
            file_stream,
            media_type="application/octet-stream",
        )

    async def deactivate_user_account(self) -> user_schemas.DeactivateAccountSchemaOut:
        """
        Deactivate the currently authenticated user's account.

        This method performs the following:
        - Checks if the user's account is already inactive.
        - Updates the user's `is_active` field to `False` in the database.
        - Commits the transaction and returns a confirmation message upon success.

        Returns:
            str: A confirmation message indicating the account has been successfully deactivated.

        Raises:
            HTTPException 400: If the account is already inactive.
            HTTPException 404: If the account could not be found or updated.
        """
        if not self.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is already inactive.",
            )
        stmt = (
            update(User)
            .where(User.user_id == self.user.user_id)
            .values(is_active=False)
            .returning(User.username)
        )
        username_response = (
            await self.async_session.execute(stmt)
        ).scalar_one_or_none()
        if not username_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not deactivate account.",
            )
        await self.async_session.commit()
        return user_schemas.DeactivateAccountSchemaOut(
            success="your account has been successfully deactivated."
        )

    async def reactivate_user_account(self) -> user_schemas.ReactivateAccountScheamaOut:
        """
        Reactivate the currently authenticated user's account.

        This method performs the following steps:
        - Checks if the user's account is already active.
        - Updates the user's `is_active` field to `True` in the database.
        - Commits the transaction upon success.
        - Returns a success message confirming reactivation.

        Returns:
            ReactivateAccountScheamaOut: A schema containing a success message.

        Raises:
            HTTPException 400: If the account is already active.
            HTTPException 404: If the account could not be found or updated.
        """
        if self.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is already active.",
            )
        stmt = (
            update(User)
            .where(User.user_id == self.user.user_id)
            .values(is_active=True)
            .returning(User.username)
        )
        username_response = (
            await self.async_session.execute(stmt)
        ).scalar_one_or_none()
        if not username_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not deactivate account.",
            )
        await self.async_session.commit()
        return user_schemas.ReactivateAccountScheamaOut(
            success="your account has been successfully reactivated."
        )

    async def register_for_trip(self) -> user_schemas.RegisterForTripSchemaOut:
        """
        Enroll the current user in a specific trip.

        This method adds the user to the `participants` list of the trip identified
        by `self.trip_id`. It ensures the user is attached to the current session
        and prevents duplicate enrollments.

        Returns:
            user_schemas.RegisterForTripSchemaOut: A schema containing a success message
            confirming that the user has been enrolled in the trip.

        Raises:
            HTTPException (404): If no trip with the specified `trip_id` exists.
            HTTPException (400): If the user is already enrolled in the trip.
            HTTPException (500): If an unexpected error occurs during the database operation.
        """
        trip = (
            await self.async_session.execute(
                select(Trip)
                .options(selectinload(Trip.participants))
                .where(Trip.trip_id == self.trip_id)
            )
        ).scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trip with id {self.trip_id} found.",
            )
        user = await self.async_session.merge(self.user)
        if user in trip.participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.username} is already enrolled in this trip.",
            )

        trip.participants.append(user)
        await self.async_session.commit()
        return user_schemas.RegisterForTripSchemaOut(
            success=f"Congradulations {self.user.username} you enlisted in trip."
        )

    async def unregister_from_trip(self) -> user_schemas.UnRegisterForTripSchemaOut:
        """
        Unregisters the current user from a specific trip.

        This method removes the association between the authenticated user
        and the target trip by updating the many-to-many relationship table.
        It ensures that the trip exists and that the user is currently
        enrolled before proceeding with the unregistration.

        Returns:
            user_schemas.UnRegisterForTripSchemaOut: A response schema containing
            a success message confirming that the user has successfully left
            the trip.

        Raises:
            HTTPException (404): If no trip with the specified `trip_id` exists.
            HTTPException (400): If the user is not enrolled in the specified trip.
            HTTPException (500): If an unexpected database or session error occurs.
        """

        trip = (
            await self.async_session.execute(
                select(Trip)
                .options(selectinload(Trip.participants))
                .where(Trip.trip_id == self.trip_id)
            )
        ).scalar_one_or_none()

        if not trip:
            logger.warning(f'No trip with id {self.trip_id} found.')
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trip with id {self.trip_id} found.",
            )
        user = await self.async_session.merge(self.user)
        if not user in trip.participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.username} is not enrolled in this trip.",
            )

        trip.participants.remove(user)
        await self.async_session.commit()
        return user_schemas.RegisterForTripSchemaOut(
            success=f"{self.user.username}, your trip enrollment has been canceled successfully."
        )
