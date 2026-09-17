import pytest
from app.database import get_connection


@pytest.mark.asyncio
async def test_database_connection():
    connection = await get_connection()

    try:
        result = await connection.fetchval("SELECT 1")
        assert result == 1
    finally:
        await connection.close()
