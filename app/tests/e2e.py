import httpx
import pytest


@pytest.mark.asyncio
async def test_sign_up():
    data = {
        "username": "dumitruawdaawdwdadw",
        "password": "dumitru123A",
        "confirm_password": "dumitru123A",
        "email": "uwdwseraawdadwwawddaawdwdadw@example.com",
        "scopes": [
            "user"
        ]
    }
    async with httpx.AsyncClient() as client:

        response = await client.post(url='http://localhost:8000/v1/user/sign-up', json=data)
        data = response.json()
        assert response.status_code == 201

        assert data['success'] == 'Your account has been created, and a welcome email will be sent to your email.'
