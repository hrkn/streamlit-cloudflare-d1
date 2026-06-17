import typing

import pytest
import sqlalchemy
import sqlalchemy.orm

import streamlit_cloudflare_d1.model


@pytest.fixture
def session() -> typing.Generator[sqlalchemy.orm.Session]:
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    streamlit_cloudflare_d1.model.Base.metadata.create_all(engine)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_user(session: sqlalchemy.orm.Session) -> None:
    # ユーザーの作成
    user = streamlit_cloudflare_d1.model.User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    # ユーザーの取得
    stmt = sqlalchemy.select(streamlit_cloudflare_d1.model.User).where(
        streamlit_cloudflare_d1.model.User.name == "Alice"
    )
    db_user = session.scalars(stmt).first()

    assert db_user is not None
    assert db_user.id == 1
    assert db_user.name == "Alice"
    assert db_user.email == "alice@example.com"
    assert db_user.role == "user"
    assert db_user.created_at is not None


def test_update_user(session: sqlalchemy.orm.Session) -> None:
    # ユーザーの作成
    user = streamlit_cloudflare_d1.model.User(name="Bob", email="bob@example.com")
    session.add(user)
    session.commit()

    # ユーザーの更新
    stmt = sqlalchemy.select(streamlit_cloudflare_d1.model.User).where(
        streamlit_cloudflare_d1.model.User.name == "Bob"
    )
    db_user = session.scalars(stmt).first()
    assert db_user is not None
    db_user.email = "bob_updated@example.com"
    session.commit()

    # 更新の確認
    stmt_updated = sqlalchemy.select(streamlit_cloudflare_d1.model.User).where(
        streamlit_cloudflare_d1.model.User.name == "Bob"
    )
    db_user_updated = session.scalars(stmt_updated).first()
    assert db_user_updated is not None
    assert db_user_updated.email == "bob_updated@example.com"


def test_delete_user(session: sqlalchemy.orm.Session) -> None:
    # ユーザーの作成
    user = streamlit_cloudflare_d1.model.User(
        name="Charlie", email="charlie@example.com"
    )
    session.add(user)
    session.commit()

    # ユーザーの削除
    stmt = sqlalchemy.select(streamlit_cloudflare_d1.model.User).where(
        streamlit_cloudflare_d1.model.User.name == "Charlie"
    )
    db_user = session.scalars(stmt).first()
    assert db_user is not None
    session.delete(db_user)
    session.commit()

    # 削除の確認
    stmt_deleted = sqlalchemy.select(streamlit_cloudflare_d1.model.User).where(
        streamlit_cloudflare_d1.model.User.name == "Charlie"
    )
    db_user_deleted = session.scalars(stmt_deleted).first()
    assert db_user_deleted is None
