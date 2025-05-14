from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "postgresql+asyncpg://gostdockeasy_user:tri4Wq1P0hKuUTAOi0jMx41nHoyGYftL@dpg-d0ido1mmcj7s73dif520-a.oregon-postgres.render.com:5432/gostdockeasy"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
