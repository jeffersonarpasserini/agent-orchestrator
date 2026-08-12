from contextlib import closing

import psycopg

from orchestrator.settings import Settings


def check_database(settings: Settings) -> dict[str, str]:
    with closing(psycopg.connect(settings.database_url, connect_timeout=3)) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database, user = cursor.fetchone()
    return {"database": database, "user": user}
