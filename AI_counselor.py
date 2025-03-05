import streamlit as st
import requests
import re
import time
import base64
import concurrent.futures
from io import BytesIO
from PIL import Image
from streamlit_chat import message  # pip install streamlit-chat

# ========================
# ページ設定
# ========================
st.set_page_config(page_title="メンタルケアボット", layout="wide")
st.title("メンタルケアボット V3.1 (非同期対応)")

# ========================
# テーマ等のCSS調整 (省略可)
# ========================
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

# ========================
# セッション初期化
# ========================
if "conversation_turns" not in st.session_state:
    st.session_state["conversation_turns"] = []
if "show_selection_form" not in st.session_state:
    st.session_state["show_selection_form"] = False

# ========================
# サイドバー: ユーザー設定
# ========================
with st.sidebar:
    st.header("ユーザー設定")
    st.session_state["user_name"] = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="sidebar_user_name")
    st.session_state["consult_type"] = st.radio(
        "相談タイプを選択してください", 
        ("本人の相談", "他者の相談", "デリケートな相談"), 
        key="sidebar_consult_type"
    )

    # 改善策のレポートボタン
    if st.button("改善策のレポート", key="report_sidebar"):
        if st.session_state.get("conversation_turns", []):
            # ここで会話をまとめる処理
            all_turns = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            summary = "(会話まとめ) ここでAIによるレポートを生成する"
            st.session_state["summary"] = summary
            st.markdown("**まとめ:**\n" + summary)
        else:
            st.warning("まずは会話を開始してください。")

    # 続きを読み込む
    if st.button("続きを読み込む", key="continue_sidebar"):
        if st.session_state.get("conversation_turns", []):
            # 追加の回答を読み込む処理
            st.success("続きの回答を取得しました。")
        else:
            st.warning("会話がありません。")

    # 選択式相談フォームを開くボタン
    if st.button("選択式相談フォームを開く", key="open_form_btn"):
        st.session_state["show_selection_form"] = True

# ========================
# 選択式相談フォーム & 過去の会話履歴
# ========================
def add_selection_form_data():
    """選択式相談フォームの内容を conversation_turns に追加。"""
    summary = "(フォーム入力内容)"
    st.session_state["conversation_turns"].append({
        "user": summary,
        "answer": "選択式相談フォームが送信されました。"
    })
    st.success("送信しました！")

if st.session_state["show_selection_form"]:
    with st.sidebar:
        st.header("選択式相談フォーム")
        # 例: 悩みの種類、身体の状態など
        category = st.selectbox("悩みの種類", ["人間関係", "仕事", "家庭", "経済", "健康", "その他"], key="category_form")
        # ... 以下フォーム項目 ...
        if st.button("選択内容を送信", key="submit_selection"):
            add_selection_form_data()

    # 過去の会話履歴
    with st.sidebar:
        st.header("過去の会話")
        if st.session_state.get("conversation_turns", []):
            for turn in st.session_state["conversation_turns"]:
                st.markdown(f"**あなた:** {turn['user'][:50]}...")
                st.markdown(f"**回答:** {turn['answer'][:50]}...")
        else:
            st.info("まだ会話はありません。")

# ========================
# 専門家一覧 (例)
# ========================
EXPERTS = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]
st.markdown("### 専門家一覧")
cols = st.columns(len(EXPERTS))
for i, expert in enumerate(EXPERTS):
    with cols[i]:
        st.markdown(f"**{expert}**")
        st.markdown("🤖")  # 実際は画像を表示する

# ========================
# メインエリア：チャット表示領域 (省略可)
# ========================
conversation_container = st.empty()

# ========================
# 非同期処理のための関数
# ========================
def call_api_async(prompt: str):
    """APIを別スレッドで呼び出す例。"""
    # 実際はGoogle Gemini等を呼び出す
    time.sleep(1.0)
    return f"(AIの回答) 入力: {prompt}"

def generate_expert_answers(question: str) -> str:
    """初回回答(非同期)"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(call_api_async, question)
        result = future.result()  # 完了まで待機
    return result

def continue_discussion(additional_input: str, current_turns: str) -> str:
    """継続回答(非同期)"""
    prompt = f"(追加回答)\nこれまでの会話:\n{current_turns}\nユーザーの追加発言:{additional_input}"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(call_api_async, prompt)
        result = future.result()
    return result

# ========================
# 下部固定のLINE風チャットバー
# ========================
with st.container():
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        # text_area の label は空文字にしない
        user_message = st.text_area(
            "メッセージ入力",
            placeholder="Your message",
            height=50,
            key="user_message_input"
        )
        arrow_button = st.form_submit_button("➤", key="arrow_button_1")
    st.markdown("</div>", unsafe_allow_html=True)

    if arrow_button:
        if user_message.strip():
            # conversation_turns に追加
            if "conversation_turns" not in st.session_state:
                st.session_state["conversation_turns"] = []
            user_text = user_message

            # 初回 or 継続判定
            if len(st.session_state["conversation_turns"]) == 0:
                # 初回回答(非同期)
                answer_text = generate_expert_answers(user_text)
            else:
                # 継続回答(非同期)
                context = "\n".join([
                    f"あなた: {turn['user']}\n回答: {turn['answer']}"
                    for turn in st.session_state["conversation_turns"]
                ])
                answer_text = continue_discussion(user_text, context)

            st.session_state["conversation_turns"].append({"user": user_text, "answer": answer_text})
            st.success("送信しました！")

            # 会話表示など
            st.experimental_rerun()  # 画面再描画
        else:
            st.warning("メッセージを入力してください。")
