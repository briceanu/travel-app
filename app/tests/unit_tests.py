from app.utils.user_logic import create_acess_token
import pytest
from datetime import timedelta


@pytest.mark.asyncio
async def test_create_access_token():
    token = create_acess_token(
        data={"sub": "andrei", "scopes": ["planner"]}, expires_delta=timedelta(hours=1)
    )

    assert isinstance(token, str) == True
