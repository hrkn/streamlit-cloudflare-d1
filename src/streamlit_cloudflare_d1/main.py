import os

import dotenv
import pandas as pd
import sqlalchemy
import sqlalchemy.orm
import streamlit as st
import streamlit.runtime.scriptrunner

import streamlit_cloudflare_d1.model as model

# .envファイルをロード
dotenv.load_dotenv()

# 1. 環境変数から接続URLを構築
ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
DATABASE_ID = os.environ.get("CLOUDFLARE_DATABASE_ID")

if not all([ACCOUNT_ID, API_TOKEN, DATABASE_ID]):
    st.error("必要な環境変数が設定されていません。.envファイルを確認してください。")
    st.stop()

DATABASE_URL = f"cloudflare_d1://{ACCOUNT_ID}:{API_TOKEN}@{DATABASE_ID}"


# 2. Engineの作成
def get_engine() -> sqlalchemy.Engine:
    engine = sqlalchemy.create_engine(
        DATABASE_URL,
        echo=False,
    )
    return engine


get_engine = st.cache_resource(get_engine)
engine = get_engine()


# 3. データの読み込み
def load_users() -> pd.DataFrame:
    with sqlalchemy.orm.Session(engine) as session:
        stmt = sqlalchemy.select(model.User)
        users = session.scalars(stmt).all()
        # DataFrameに変換
        data = []
        for u in users:
            data.append(
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": u.role,
                    "created_at": u.created_at,
                }
            )
        return pd.DataFrame(data)


# CRUD処理
def save_changes(edited_data: dict, original_df: pd.DataFrame) -> None:
    with sqlalchemy.orm.Session(engine) as session:
        try:
            # 1. 削除処理
            if "deleted_rows" in edited_data and edited_data["deleted_rows"]:
                for row_idx in edited_data["deleted_rows"]:
                    user_id = int(original_df.iloc[row_idx]["id"])
                    stmt = sqlalchemy.select(model.User).where(model.User.id == user_id)
                    user = session.scalars(stmt).first()
                    if user:
                        session.delete(user)

            # 2. 編集処理
            if "edited_rows" in edited_data and edited_data["edited_rows"]:
                for row_idx_str, changes in edited_data["edited_rows"].items():
                    row_idx = int(row_idx_str)
                    user_id = int(original_df.iloc[row_idx]["id"])
                    stmt = sqlalchemy.select(model.User).where(model.User.id == user_id)
                    user = session.scalars(stmt).first()
                    if user:
                        for col, val in changes.items():
                            setattr(user, col, val)

            # 3. 追加処理
            if "added_rows" in edited_data and edited_data["added_rows"]:
                for new_row in edited_data["added_rows"]:
                    name = new_row.get("name")
                    email = new_row.get("email")
                    role = new_row.get("role", "user")
                    if name:
                        user = model.User(name=name, email=email, role=role)
                        session.add(user)

            session.commit()
            st.success("変更を保存しました。")
        except Exception as e:
            session.rollback()
            st.error(f"保存中にエラーが発生しました: {e}")


# Streamlit UI Execution Guard
if streamlit.runtime.scriptrunner.get_script_run_ctx() is not None:
    # Streamlit UI
    st.title("ユーザー管理システム (Cloudflare D1)")

    # データ読み込み
    if "df" not in st.session_state or st.button("最新の情報に更新"):
        st.session_state.df = load_users()

    df = st.session_state.df

    st.subheader("ユーザー一覧")
    st.write(
        "テーブル内でセルの値をダブルクリックして編集したり、最下行で新規追加、行を選択してDeleteキーで削除できます。"
    )

    # st.data_editorの表示
    edited_output = st.data_editor(
        df,
        key="users_editor",
        num_rows="dynamic",
        disabled=["id", "created_at"],
        column_config={
            "id": st.column_config.NumberColumn("ID", help="自動採番されます"),
            "name": st.column_config.TextColumn("名前", required=True),
            "email": st.column_config.TextColumn("メールアドレス"),
            "role": st.column_config.TextColumn("ロール"),
            "created_at": st.column_config.DatetimeColumn("作成日時", disabled=True),
        },
        width="stretch",
    )

    # 変更の有無を確認
    changes = st.session_state.get("users_editor", {})

    has_changes = isinstance(changes, dict) and (
        len(changes.get("edited_rows", {})) > 0
        or len(changes.get("added_rows", [])) > 0
        or len(changes.get("deleted_rows", [])) > 0
    )

    if has_changes:
        if st.button("変更を保存", type="primary"):
            save_changes(changes, df)
            st.session_state.df = load_users()
            st.rerun()
