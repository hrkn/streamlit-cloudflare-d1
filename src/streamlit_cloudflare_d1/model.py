import datetime
import typing

import sqlalchemy
import sqlalchemy.orm


class Base(sqlalchemy.orm.DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "Users"
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(
        primary_key=True, autoincrement=True
    )
    name: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String, nullable=False
    )
    email: sqlalchemy.orm.Mapped[typing.Optional[str]] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String, nullable=True
    )
    role: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String, nullable=False, server_default="user"
    )
    created_at: sqlalchemy.orm.Mapped[datetime.datetime] = sqlalchemy.orm.mapped_column(
        sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.sql.func.now()
    )
