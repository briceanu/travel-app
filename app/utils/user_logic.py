from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_models import User
from sqlalchemy import select
from pwdlib import PasswordHash
from datetime import timedelta, timezone, datetime
import jwt
import uuid
from dotenv import load_dotenv
import os
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from app.db.db_connection import get_async_db
from fastapi import Depends, Security, HTTPException, status
from typing import Annotated
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from app.schemas import user_schemas
import redis
from sqlalchemy.orm import load_only

load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')


redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=3)

REFRESH_SECRET = os.getenv("REFRESH_SECRET")
SECRET = os.getenv("SECRET")
ALGORITHM = os.getenv("ALGORITHM")

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/user/sign-in",
    scopes={
        "user": "A regular user who can browse trips, activities, and destinations.",
        "planner": "A user with permission to create and manage travel destinations and trips.",
        "admin": "A system administrator with full access, including managing users, planners, and application settings.",
    },
)


async def authenticate_user(
    username: str, password: str, scopes: list[str] | None, async_session: AsyncSession
) -> User | None:
    """
    Authenticate a user by validating their username, password.

    This function checks whether a user with the provided username exists in the
    database, verifies the password using the configured password context, and
    ensures the user's scopes match the required scopes.

    Args:
        `username (str)`: The username provided by the client.
        `password (str)`: The plain-text password provided by the client.
        `async_session (AsyncSession)`: The SQLAlchemy async session used to query the database.

    Returns:
        User | None: The authenticated `User` object if authentication is successful,
        or `None` if any validation fails.
    """
    user = (
        await async_session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if not user:
        return False
    if not password_hash.verify(password, user.password):
        return False
    if not scopes:
        return False
    for scope in scopes:
        if scope not in user.scopes:
            return False
    return user


def create_acess_token(data: dict, expires_delta: timedelta) -> str:
    """
    Generates a JWT access token containing the provided user data.

    The token is encoded using a secret key and a specified algorithm,
    and includes an expiration time based on the given time delta.

    Args:
        expires_delta (timedelta): The duration after which the token should expire.
        data (dict): The payload data to include in the token (e.g., user identity).

    Returns:
        str: The encoded JWT access token.
    """

    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expires})
    access_token = jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)
    return access_token


def create_refresh_token(data: dict, expires_delta: timedelta) -> str:
    """
    Returns an refresh token after encoding the username, the secret,
    and the algorithm.
    The expiration time for the refresh token is longer than the access
    token
    """
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + expires_delta
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expires, "jti": jti})
    refresh_token = jwt.encode(to_encode, REFRESH_SECRET, algorithm=ALGORITHM)
    return refresh_token


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    security_scopes: SecurityScopes,
    async_session: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Retrieve and validate the currently authenticated user using the provided JWT token.

    This function performs the following steps:
    - Extracts and decodes the JWT token.
    - Validates the token signature and expiration.
    - Extracts the user's username and scopes from the token payload.
    - Fetches the user from the database using the username.
    - Ensures the token has all required scopes as specified by the route dependencies.

    Args:
        security_scopes (SecurityScopes): Required scopes for accessing the route.
        token (str): JWT access token provided via the Authorization header.
        async_session (AsyncSession): Dependency-injected SQLAlchemy asynchronous session.

    Returns:
        User: The authenticated user from the database.

    Raises:
        HTTPException 401:
            - If the token is missing, invalid, or expired.
            - If the username is not present in the token.
            - If the user does not exist in the database.
            - If the token lacks the required scopes for the requested resource.
    """

    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, SECRET, algorithms=ALGORITHM)
        username = payload.get("sub")
        if not username:
            raise credentials_exception
        token_scopes = payload.get('scopes', [])
        token_data = user_schemas.TokenData(
            username=username, scopes=token_scopes)
    except (InvalidTokenError, ValidationError):
        raise credentials_exception
    user_in_db = (
        await async_session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if not user_in_db:
        raise credentials_exception
    # we validate for both scopes that are in the token and in the user_db
    # if a client forges a token and passes scopes that are not in the db
    # only the tokens from db will be taken into consideration
    user_scopes_set = set(user_in_db.scopes).intersection(
        set(token_data.scopes))
    security_scopes_set = set(security_scopes.scopes)

    if not (user_scopes_set.intersection(security_scopes_set)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": authenticate_value},
        )
    return user_in_db


def get_current_active_user(user: Annotated[User,  Security(get_current_user, scopes=['user'])]):
    """
    Ensures the currently authenticated user is active.

    This function is typically used as a FastAPI dependency to enforce that
    only active users can access certain routes.

    Args:
        current_user (User): The authenticated user, provided by `get_current_user`.

    Returns:
        User: The current active user.

    Raises:
        HTTPException 400: If the user is not active.
    """

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


def get_current_active_planner(planner: Annotated[User,  Security(get_current_user, scopes=['planner'])]):
    """
    Ensure that the currently authenticated planner is active.

    This dependency is used in FastAPI routes that require the user to have
    the 'planner' scope and an active account. If the planner is inactive,
    it raises an HTTP 400 error.

    Args:
        planner (User): The authenticated planner user, provided by the
            `get_current_user` dependency after scope validation.

    Returns:
        User: The currently active planner user.

    Raises:
        HTTPException: If the planner account is inactive (HTTP 400).
    """

    if not planner.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive planner.")
    return planner


def get_current_active_admin(admin: Annotated[User, Security(get_current_user, scopes=['admin'])]):
    """
    Validate and return the currently authenticated active admin user.

    This dependency checks that the user obtained via `get_current_user`:
        1. Has the 'admin' scope.
        2. Is marked as active in the database.

    Args:
        admin (User): The currently authenticated user injected by FastAPI
            via the Security dependency.

    Returns:
        User: The authenticated and active admin user.

    Raises:
        HTTPException (400): If the user is inactive.
    """

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive planner.")
    return admin


def black_list_token(jti: str, ttl: int) -> None:
    """
    blacklists the token using the token's id and setting
    and setting a time to live.
    """
    redis_client.setex(f"blacklist:{jti}", ttl, 'true')


def is_token_blacklisted(jti: str) -> bool:
    """checks to see if the token is already blacklisted"""
    return redis_client.exists(f"blacklist:{jti}") == 1
