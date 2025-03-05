import streamlit as st
import requests
import re
import random
import time
import base64
from io import BytesIO
from PIL import Image
from streamlit_chat import message

# ------------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------------
st.set_page_config(page_title="メンタルケアボット", layout="wide")
st.title("メンタルケアボット V3.1")

# ------------------------------------------------------------------
# テーマ設定 (省略: config.toml 読み込み)
# ------------------------------------------------------------------
# ...省略...

# ------------------------------------------------------------------
# CSS調整
# ------------------------------------------------------------------
st.markdown("""
<style>
.fixed-input {
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #FFF;
    padding: 10px;
    box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
    z-index: 100;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# セッションステート初期化
# ------------------------------------------------------------------
if "conversation_turns" not in st.session_state:
    st.session_state["conversation_turns"] = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_selection_form" not in st.session_state:
    st.session_state["show_selection_form"] = False

# ------------------------------------------------------------------
# サイドバー：ユーザー情報など
# ------------------------------------------------------------------
with st.sidebar:
    st.header("ユーザー設定")
    user_name = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="sidebar_user_name")
    consult_type = st.radio("相談タイプを選択してください", 
                            ("本人の相談", "他者の相談", "デリケートな相談"), key="sidebar_consult_type")

    st.header("機能")
    # 改善策のレポートボタン
    if st.button("改善策のレポート", key="report_sidebar_btn"):
        if st.session_state.get("conversation_turns", []):
            # ... レポート生成ロジック ...
            st.success("レポート生成完了！")
        else:
            st.warning("まずは会話を開始してください。")

    # 続きを読み込むボタン
    if st.button("続きを読み込む", key="continue_sidebar_btn"):
        if st.session_state.get("conversation_turns", []):
            # ... 続きを読み込むロジック ...
            st.success("続きの回答を読み込みました。")
        else:
            st.warning("会話がありません。")

    # 選択式相談フォーム
    if st.button("選択式相談フォームを開く", key="open_form_btn"):
        st.session_state["show_selection_form"] = True

    # 選択式相談フォームが True の場合に表示
    if st.session_state["show_selection_form"]:
        st.header("選択式相談フォーム")
        category = st.selectbox("悩みの種類", ["人間関係", "仕事", "家庭", "経済", "健康", "その他"], key="category_form")
        # ... 省略（身体の状態・心の状態など） ...
        if st.button("選択内容を送信", key="submit_selection_btn"):
            # ... フォーム内容を会話に追加 ...
            st.success("送信しました！")

    # 過去の会話履歴
    st.header("過去の会話")
    if st.session_state.get("conversation_turns", []):
        for turn in st.session_state["conversation_turns"]:
            st.markdown(f"**あなた:** {turn['user'][:50]}...")
            st.markdown(f"**回答:** {turn['answer'][:50]}...")
    else:
        st.info("まだ会話はありません。")

# ------------------------------------------------------------------
# 上部：専門家一覧（例）
# ------------------------------------------------------------------
st.markdown("### 専門家一覧")
EXPERTS = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]
cols = st.columns(len(EXPERTS))
for idx, expert in enumerate(EXPERTS):
    with cols[idx]:
        st.markdown(f"**{expert}**")
        st.markdown("🤖")  # 画像があるなら st.image(...)

# ------------------------------------------------------------------
# メインエリア：チャット表示領域（省略）
# ------------------------------------------------------------------
conversation_container = st.empty()

# ------------------------------------------------------------------
# 下部：LINE風チャットバー
# ------------------------------------------------------------------
with st.container():
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)

    # フォームにラベルを付ける or 空文字は避ける
    with st.form("chat_form", clear_on_submit=True):
        # ラベルは省略できるが、空文字("")にするとエラーになることがある
        user_message = st.text_area(
            "メッセージ",  # <-- ラベルを明示
            placeholder="Your message",
            height=50,
            key="user_message_input"
        )
        # 右矢印ボタンを表示（label="➤"）
        arrow_button = st.form_submit_button("➤", key="arrow_button_1")

    st.markdown("</div>", unsafe_allow_html=True)

    # 送信ボタンが押されたときの処理
    if arrow_button:
        if user_message.strip():
            # ここでAPI呼び出しなどの会話ロジックを実行
            st.session_state["conversation_turns"].append({
                "user": user_message,
                "answer": "（ここにAIの回答が入ります）"
            })
            st.success("メッセージを送信しました。")
            st.experimental_rerun()
        else:
            st.warning("メッセージを入力してください。")
