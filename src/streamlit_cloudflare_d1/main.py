import logging

import streamlit as st
import streamlit.runtime.scriptrunner

import streamlit_cloudflare_d1.database as database


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname).4s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
LOGGER = logging.getLogger(__name__)

# Streamlit UI Execution Guard
if streamlit.runtime.scriptrunner.get_script_run_ctx() is not None:
    # アプリ全体の起動時に一度だけ初期化を実行（ページリロードでは実行されない）
    database.initialize_app_once()

    # Streamlit UI
    st.title("ユーザー管理システム (Cloudflare D1 - Local Cache)")

    # データ読み込み
    if "df" not in st.session_state or st.button("最新の情報に更新"):
        st.session_state.df = database.load_users()

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
            database.save_changes(changes, df)
            st.session_state.df = database.load_users()
            st.rerun()
