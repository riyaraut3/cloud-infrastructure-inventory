"""Database lifecycle. SQLite is supported only for lightweight local tests."""
from functools import lru_cache
import json
import os
from urllib.parse import quote_plus

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def database_url() -> str:
    if os.getenv("APP_DB_SECRET_ARN"):
        secret = boto3.client("secretsmanager").get_secret_value(
            SecretId=os.environ["APP_DB_SECRET_ARN"]
        )
        item = json.loads(secret["SecretString"])
        # RDS managed master credentials contain username/password; AWS does not
        # guarantee that every secret contains the dbname field.
        return (
            "postgresql+psycopg2://"
            f"{quote_plus(item['username'])}:{quote_plus(item['password'])}"
            f"@{item.get('host') or os.environ['APP_DB_HOST']}:"
            f"{item.get('port', 5432)}/{os.getenv('APP_DB_NAME', 'inventory')}"
        )
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL or APP_DB_SECRET_ARN must be configured")
    return value


@lru_cache(maxsize=1)
def get_engine():
    url = database_url()
    options = {"pool_pre_ping": True}
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        options["poolclass"] = NullPool  # Lambda concurrency: no stale pooled connections
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


def create_schema():
    # Import models so their tables are registered with Base.metadata.
    from . import models  # noqa: F401
    Base.metadata.create_all(get_engine())


def session_dependency():
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
