Travel Planner API

A robust FastAPI project featuring JWT-based authentication, refresh tokens, token blacklisting, Celery task queues, role-based scopes, CRUD operations, and Dockerized deployment.

Features

JWT Authentication: Secure login with access and refresh tokens.

Refresh Tokens: Supports token refresh flow to maintain sessions.

Blacklist Tokens: Invalidate tokens upon logout or suspicious activity.

Role-Based Scopes: Granular access control for users (e.g., admin, planner, user).

CRUD Operations: Complete Create, Read, Update, Delete endpoints for all resources.

Celery Tasks & Queues: Background job processing (emails, notifications, reports).

Dockerized: Easily deployable with Docker and Docker Compose.

PostgreSQL: Persistent data storage.

Tech Stack

Python 3.13

FastAPI

SQLAlchemy (Async)

PostgreSQL

Redis (for Celery broker and token blacklist)

Celery

Docker & Docker Compose

Pytest / Pytest-Asyncio (for testing)
