import os
import time

import pytest
import sqlalchemy
import sqlalchemy.orm

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


def test_save_changes_crud() -> None:
    # 単体テスト: save_changes関数のCRUDロジックをテスト
    d1_engine = get_d1_engine()

    # テスト開始時のデータ取得
    original_df = db.load_users()
    assert len(original_df) == 2

    # 1. 編集(Aliceの更新)、2. 削除(Bobの削除)、3. 追加(Charlieの追加)
    changes = {
        "edited_rows": {"0": {"name": "Alice Updated"}},
        "added_rows": [{"name": "Charlie", "email": "charlie@example.com"}],
        "deleted_rows": [1],  # Bob
    }

    # ロジックの実行
    db.save_changes(changes, original_df)
    # D1へ同期を強制実行
    db.flush_sync_queue()

    # 実行後の検証
    updated_df = db.load_users()
    assert len(updated_df) == 2

    # 変更結果の確認
    assert updated_df.iloc[0]["name"] == "Alice Updated"
    assert updated_df.iloc[1]["name"] == "Charlie"
    assert updated_df.iloc[1]["email"] == "charlie@example.com"

    # データベースからBobが消えているか検証
    with sqlalchemy.orm.Session(d1_engine) as session:
        stmt = sqlalchemy.select(model.User).where(model.User.name == "Bob")
        bob = session.scalars(stmt).first()
        assert bob is None


def test_empty_batch_coverage() -> None:
    # _send_batch が空の場合の早期リターンをカバー
    db._send_batch([], [])


def test_executemany_coverage() -> None:
    # executemany のルートをカバー
    local_engine = db.get_local_engine()
    # executemany を発生させるため、直接 raw execute を使用
    with local_engine.begin() as conn:
        conn.execute(
            sqlalchemy.text(
                'INSERT INTO "Users" (name, email, role) VALUES (:name, :email, :role)'
            ),
            [
                {"name": "UserA", "email": "usera@example.com", "role": "user"},
                {"name": "UserB", "email": "userb@example.com", "role": "user"},
            ],
        )
    # キューをクリアしておく
    db.flush_sync_queue()


def test_sync_thread_coverage() -> None:
    # start_sync_thread が機能することを簡易的にテスト
    thread = db.start_sync_thread()
    assert thread.is_alive()

    # キューに入れる
    db.sync_queue.put(
        {
            "sql": 'INSERT INTO "Users" (name, email, role) VALUES (?, ?, ?)',
            "params": ["UserC", "userc@example.com", "user"],
            "table": "Users",
            "pk": 3,
        }
    )
    # スレッドが 3秒スリープ + 送信するのを少し待つ
    time.sleep(3.5)
