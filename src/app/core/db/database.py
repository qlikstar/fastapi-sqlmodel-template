from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
import ssl
import asyncpg

from ..config import settings, DBOption

# Create an SSL context that doesn't verify certificates for development
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

if settings.DB_ENGINE == DBOption.SQLITE:
    DATABASE_URI = settings.SQLITE_URI
    DATABASE_PREFIX = settings.SQLITE_ASYNC_PREFIX
    DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"
    connect_args = {}
if settings.DB_ENGINE == DBOption.POSTGRES:
    DATABASE_URI = settings.POSTGRES_URI
    DATABASE_PREFIX = settings.POSTGRES_ASYNC_PREFIX
    DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"
    # Configure connect_args for PostgreSQL with PgBouncer compatibility
    connect_args = {
        "ssl": ssl_context,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {'statement_cache_mode': 'disable'}
    }

# Create engine with proper connection arguments and pool settings
async_engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,  # Check connection validity before using from pool
    pool_recycle=300,    # Recycle connections after 5 minutes
    pool_size=5,         # Maintain a pool of connections
    max_overflow=10      # Allow up to 10 additional connections when pool is full
)

local_session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def async_get_db() -> AsyncSession:
    async_session = local_session
    async with async_session() as db:
        try:
            yield db
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()


# Direct connection function for PgBouncer compatibility
async def get_pgbouncer_connection():
    conn = await asyncpg.connect(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        ssl=ssl_context,
        statement_cache_size=0,
        prepared_statement_cache_size=0,
        server_settings={'statement_cache_mode': 'disable'}
    )
    return conn
