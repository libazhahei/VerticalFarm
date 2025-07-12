import os
from tortoise import Tortoise, run_async

async def init_schema():
    """
    Initializes the Tortoise ORM schema with the necessary configurations.
    """
    db_url = os.getenv('DATABASE_URL', ':memory:')
    if db_url == ':memory:':
        print("Using in-memory SQLite database for testing purposes.")
    run_async(Tortoise.init(
        db_url=f"sqlite://{db_url}",
        modules={'models': ['data.tables']}
    ))
    await Tortoise.generate_schemas()
    