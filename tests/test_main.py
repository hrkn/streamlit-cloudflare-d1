import pytest
import sqlalchemy
import sqlalchemy.orm
from streamlit.testing.v1 import AppTest

import streamlit_cloudflare_d1.main as main
import streamlit_cloudflare_d1.model as model


@pytest.fixture(autouse=True)
def mock_env():
    yield
    # エンジン接続を破棄
    try:
        main.get_engine().dispose()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def db_reset():
    # 各テストの実行前にデータベースをクリーンアップして初期化する
    engine = main.get_engine()
    model.Base.metadata.drop_all(engine)
    model.Base.metadata.create_all(engine)
    with sqlalchemy.orm.Session(engine) as session:
        user1 = model.User(name="Alice", email="alice@example.com")
        user2 = model.User(name="Bob", email="bob@example.com")
        session.add_all([user1, user2])
        session.commit()
    yield


def test_streamlit_app_rendering() -> None:
    # 統合テスト: 初期描画のテスト
    at = AppTest.from_file("src/streamlit_cloudflare_d1/main.py")
    at.run(timeout=30)
    assert at.title[0].value == "ユーザー管理システム (Cloudflare D1)"
    assert "df" in at.session_state

    df = at.session_state.df
    assert len(df) == 2
    assert df.iloc[0]["name"] == "Alice"
    assert df.iloc[1]["name"] == "Bob"


def test_save_changes_crud() -> None:
    # 単体テスト: save_changes関数のCRUDロジックをテスト
    engine = main.get_engine()

    # テスト開始時のデータ取得
    original_df = main.load_users()
    assert len(original_df) == 2

    # 1. 編集(Aliceの更新)、2. 削除(Bobの削除)、3. 追加(Charlieの追加)
    changes = {
        "edited_rows": {"0": {"name": "Alice Updated"}},
        "added_rows": [{"name": "Charlie", "email": "charlie@example.com"}],
        "deleted_rows": [1],  # Bob
    }

    # ロジックの実行
    main.save_changes(changes, original_df)

    # 実行後の検証
    updated_df = main.load_users()
    assert len(updated_df) == 2

    # 変更結果の確認
    assert updated_df.iloc[0]["name"] == "Alice Updated"
    assert updated_df.iloc[1]["name"] == "Charlie"
    assert updated_df.iloc[1]["email"] == "charlie@example.com"

    # データベースからBobが消えているか検証
    with sqlalchemy.orm.Session(engine) as session:
        stmt = sqlalchemy.select(model.User).where(model.User.name == "Bob")
        bob = session.scalars(stmt).first()
        assert bob is None
