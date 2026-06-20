import os

import pytest
import sqlalchemy
import sqlalchemy.orm
import streamlit.testing.v1

import streamlit_cloudflare_d1.database as db
import streamlit_cloudflare_d1.model as model

_d1_engine = None


def get_d1_engine() -> sqlalchemy.Engine:
    global _d1_engine
    if _d1_engine is None:
        database_url = (
            f"cloudflare_d1://{db.ACCOUNT_ID}:{db.API_TOKEN}@{db.DATABASE_ID}"
        )
        _d1_engine = sqlalchemy.create_engine(database_url, echo=False)
    return _d1_engine


@pytest.fixture(autouse=True)
def mock_env():
    yield
    # エンジン接続を破棄
    try:
        get_d1_engine().dispose()
        db.get_local_engine().dispose()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def db_reset():
    # 各テストの実行前にデータベースをクリーンアップして初期化する
    d1_engine = get_d1_engine()
    local_engine = db.get_local_engine()

    # D1 (Mock Server) 側の初期化
    model.Base.metadata.drop_all(d1_engine)
    model.Base.metadata.create_all(d1_engine)
    with sqlalchemy.orm.Session(d1_engine) as session:
        user1 = model.User(name="Alice", email="alice@example.com")
        user2 = model.User(name="Bob", email="bob@example.com")
        session.add_all([user1, user2])
        session.commit()

    # ローカル DB (test_local_d1.db) のファイルを物理削除する
    # これにより、テスト実行時に main.py の download_db が走り、D1から最新データをロードする
    db_file = os.environ.get("LOCAL_DB_PATH", "test_local_d1.db")
    if os.path.exists(db_file):
        try:
            local_engine.dispose()
            os.remove(db_file)
        except Exception:
            pass

    # ローカル DB をダウンロードして初期化
    db.download_db(local_engine)

    yield


def test_streamlit_app_rendering() -> None:
    # 統合テスト: 初期描画のテスト
    at = streamlit.testing.v1.AppTest.from_file("src/streamlit_cloudflare_d1/main.py")
    at.run(timeout=30)
    assert at.title[0].value == "ユーザー管理システム (Cloudflare D1 - Local Cache)"
    assert "df" in at.session_state

    df = at.session_state.df
    assert len(df) == 2
    assert df.iloc[0]["name"] == "Alice"
    assert df.iloc[1]["name"] == "Bob"
