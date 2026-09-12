#!/bin/bash
set -e

echo "Waiting for database..."

until python << END
import asyncio
import asyncpg
import os

async def check():
    try:
        conn = await asyncpg.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_SERVER"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB"),
        )
        await conn.close()
    except Exception:
        raise

asyncio.run(check())
END
do
  echo "Database not ready, retrying..."
  sleep 2
done

echo "Database is ready!"

echo "Running migrations..."
alembic upgrade head

echo "Creating initial data..."
python app/initial_data.py

echo "Prestart finished."