import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.db.models import Base

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    os.environ.get(
        "DATABASE_URL",
        (config.get_main_option("sqlalchemy.url") or "sqlite:///codesentinel.db"),
    ).replace("%", "%%"),
)
if context.is_offline_mode():
    context.configure(
        url=(config.get_main_option("sqlalchemy.url") or "sqlite:///codesentinel.db"),
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
