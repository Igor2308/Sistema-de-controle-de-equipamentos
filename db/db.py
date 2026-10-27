from sqlmodel import create_engine, Session
from config.Config import settings
import urllib.parse


encoded_password = urllib.parse.quote_plus(settings.db_password)

url = (
    f"mysql+pymysql://{settings.db_user}:{encoded_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    url,
    echo=True,
    pool_pre_ping=True
)


def get_db():
    with Session(engine) as session:
        yield session