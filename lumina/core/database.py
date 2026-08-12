import json
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from lumina.core.settings import Settings
from lumina.models import AuditMixin

settings = Settings()


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


try:
    from psycopg.types.json import set_json_dumps
except ImportError:
    pass
else:

    def _uuid_dumps(obj):
        return json.dumps(obj, cls=UUIDEncoder)

    set_json_dumps(_uuid_dumps)


engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    json_serializer=lambda obj: json.dumps(obj, cls=UUIDEncoder),
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@event.listens_for(Session, 'do_orm_execute')
def _add_filtering_criteria(execute_state: ORMExecuteState):
    skip_filter = execute_state.execution_options.get(
        'skip_soft_delete_filter', False
    )
    if execute_state.is_select and not skip_filter:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                AuditMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )


async def get_session():  # pragma: no cover
    async with async_session() as session:
        yield session
