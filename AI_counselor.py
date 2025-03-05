import streamlit as st
import requests
import re
import random
import time
import base64
from io import BytesIO
from PIL import Image
from streamlit_chat import message  # pip install streamlit-chat

# ------------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------------
st.set_page_config(page_title="メンタルケアボット", layout="wide")
st.title("メンタルケアボット V3.0")

# ------------------------------------------------------------------
# テーマ設定 (config.toml 読み込み)
# ------------------------------------------------------------------
try:
    try:
        import tomllib  # Python 3.11以降
    except ImportError:
        import toml as tomllib
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    theme_config = config.get("theme", {})
    primaryColor = theme_config.get("primaryColor", "#729075")
    backgroundColor = theme_config.get("backgroundColor", "#f1ece3")
    secondaryBackgroundColor = theme_config.get("secondaryBackgroundColor", "#fff8ef")
    textColor = theme_config.get("textColor", "#5e796a")
    font = theme_config.get("font", "monospace")
except Exception:
    primaryColor = "#729075"
    backgroundColor = "#f1ece3"
    secondaryBackgroundColor = "#fff8ef"
    textColor = "#5e796a"
    font = "monospace"

# ------------------------------------------------------------------
# 背景・共通スタイル
# ------------------------------------------------------------------
st.markdown(f"""
<style>
body {{
    background-color: {backgroundColor};
    font-family: {font}, sans-serif;
    color: {textColor};
}}
.chat-container {{
    max-height: 600px;
    overflow-y: auto;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 5px;
    margin-bottom: 20px;
    background-color: {secondaryBackgroundColor};
}}
.chat-bubble {{
    background-color: #d4f7dc;
    border-radius: 10px;
    padding: 8px;
    display: inline-block;
    max-width: 80%;
    word-wrap: break-word;
    white-space: pre-wrap;
    margin: 4px 0;
}}
.chat-header {{
    font-weight: bold;
    margin-bottom: 4px;
    color: {primaryColor};
}}
.fixed-input {{
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #FFF;
    padding: 10px;
    box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
    z-index: 100;
}}
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
# サイドバー：ユーザー情報／相談タイプ／レポート／続きボタン
# ------------------------------------------------------------------
with st.sidebar:
    st.header("ユーザー設定")
    st.session_state["user_name"] = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="sidebar_user_name")
    st.session_state["consult_type"] = st.radio("相談タイプを選択してください", 
                                               ("本人の相談", "他者の相談", "デリケートな相談"), key="sidebar_consult_type")

    st.header("機能")
    if st.button("改善策のレポート", key="report_sidebar"):
        if st.session_state.get("conversation_turns", []):
            all_turns = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            summary = generate_summary(all_turns)
            st.session_state["summary"] = summary
            st.markdown("**まとめ:**\n" + summary)
        else:
            st.warning("まずは会話を開始してください。")

    if st.button("続きを読み込む", key="continue_sidebar"):
        if st.session_state.get("conversation_turns", []):
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            new_answer = None
            new_answer = continue_discussion("続きをお願いします。", context)
            st.session_state["conversation_turns"].append({"user": "続き", "answer": new_answer})
            st.experimental_rerun()
        else:
            st.warning("会話がありません。")

    if st.button("選択式相談フォームを開く", key="open_form"):
        st.session_state["show_selection_form"] = True

# ------------------------------------------------------------------
# 選択式相談フォーム＆過去の会話履歴
# ------------------------------------------------------------------
if st.session_state["show_selection_form"]:
    with st.sidebar:
        st.header("選択式相談フォーム")
        category = st.selectbox("悩みの種類", ["人間関係", "仕事", "家庭", "経済", "健康", "その他"], key="category_form")
        st.subheader("身体の状態")
        physical_status = st.radio("身体の状態", ["良好", "普通", "不調"], key="physical_form")
        physical_detail = st.text_area("身体の状態の詳細", key="physical_detail_form", placeholder="具体的な症状や変化")
        physical_duration = st.selectbox("身体の症状の持続期間", ["数日", "1週間", "1ヶ月以上", "不明"], key="physical_duration_form")

        st.subheader("心の状態")
        mental_status = st.radio("心の状態", ["落ち着いている", "やや不安", "とても不安"], key="mental_form")
        mental_detail = st.text_area("心の状態の詳細", key="mental_detail_form", placeholder="感じる不安やストレス")
        mental_duration = st.selectbox("心の症状の持続期間", ["数日", "1週間", "1ヶ月以上", "不明"], key="mental_duration_form")

        stress_level = st.slider("ストレスレベル (1-10)", 1, 10, 5, key="stress_form")
        recent_events = st.text_area("最近の大きな出来事（任意）", key="events_form")
        treatment_history = st.radio("通院歴がありますか？", ["はい", "いいえ"], key="treatment_form")
        ongoing_treatment = ""
        if treatment_history == "はい":
            ongoing_treatment = st.radio("現在も通院中ですか？", ["はい", "いいえ"], key="ongoing_form")

        if st.button("選択内容を送信", key="submit_selection"):
            selection_summary = (
                f"【選択式相談フォーム】\n"
                f"悩みの種類: {category}\n"
                f"身体の状態: {physical_status}\n"
                f"身体の詳細: {physical_detail}\n"
                f"身体の症状の持続期間: {physical_duration}\n"
                f"心の状態: {mental_status}\n"
                f"心の詳細: {mental_detail}\n"
                f"心の症状の持続期間: {mental_duration}\n"
                f"ストレスレベル: {stress_level}\n"
                f"最近の出来事: {recent_events}\n"
                f"通院歴: {treatment_history}\n"
            )
            if treatment_history == "はい":
                selection_summary += f"現在の通院状況: {ongoing_treatment}\n"
            st.session_state["conversation_turns"].append({
                "user": selection_summary, 
                "answer": "選択式相談フォームの内容が送信され、反映されました。"
            })
            st.success("送信しました！")

        st.header("過去の会話")
        if st.session_state.get("conversation_turns", []):
            for turn in st.session_state["conversation_turns"]:
                st.markdown(f"**あなた:** {turn['user'][:50]}...")
                st.markdown(f"**回答:** {turn['answer'][:50]}...")
        else:
            st.info("まだ会話はありません。")

# ------------------------------------------------------------------
# キャラクター定義
# ------------------------------------------------------------------
EXPERTS = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]

# ------------------------------------------------------------------
# 画像読み込み
# ------------------------------------------------------------------
try:
    img_psychiatrist = Image.open("avatars/Psychiatrist.png")
    img_counselor = Image.open("avatars/counselor.png")
    img_mentalist = Image.open("avatars/MENTALIST.png")
    img_doctor = Image.open("avatars/doctor.png")
except Exception as e:
    st.error(f"画像読み込みエラー: {e}")
    img_psychiatrist = "🧠"
    img_counselor = "👥"
    img_mentalist = "💡"
    img_doctor = "💊"

avatar_img_dict = {
    "user": "👤",
    "精神科医師": img_psychiatrist,
    "カウンセラー": img_counselor,
    "メンタリスト": img_mentalist,
    "内科医": img_doctor,
    "assistant": "🤖",
}

def get_image_base64(image):
    if isinstance(image, str):
        return image
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ------------------------------------------------------------------
# Gemini API 関数
# ------------------------------------------------------------------
def remove_json_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()

def call_gemini_api(prompt: str) -> str:
    # ここにGoogle Gemini API呼び出し処理
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{st.secrets['general']['api_key']}:generateContent?key=..."
    # 省略（実装例）
    return "（AIからの回答が入ります）"

def analyze_question(question: str) -> int:
    score = 0
    keywords_emotional = ["困った", "悩み", "苦しい", "辛い"]
    keywords_logical = ["理由", "原因", "仕組み", "方法"]
    for word in keywords_emotional:
        if re.search(word, question):
            score += 1
    for word in keywords_logical:
        if re.search(word, question):
            score -= 1
    return score

def adjust_parameters(question: str) -> dict:
    # 省略（専門家のスタイル設定）
    return {}

def generate_expert_answers(question: str) -> str:
    # 省略（初回回答用）
    return "(初回回答) AIの専門家4人が回答します。"

def continue_discussion(additional_input: str, current_turns: str) -> str:
    # 省略（継続回答用）
    return "(追加回答) さらに会話を続けます。"

def generate_summary(discussion: str) -> str:
    return "(会話内容をまとめたレポート)"

# ------------------------------------------------------------------
# 会話履歴の表示関数
# ------------------------------------------------------------------
def display_chat():
    # 省略
    pass

def typewriter_bubble(sender: str, full_text: str, align: str, delay: float = 0.05):
    # 省略
    pass

# ------------------------------------------------------------------
# 上部：専門家一覧
# ------------------------------------------------------------------
st.markdown("### 専門家一覧")
cols = st.columns(len(EXPERTS))
for idx, expert in enumerate(EXPERTS):
    with cols[idx]:
        st.markdown(f"**{expert}**")
        if expert in avatar_img_dict and not isinstance(avatar_img_dict[expert], str):
            st.image(avatar_img_dict[expert], width=60)
        else:
            st.markdown("🤖")

# ------------------------------------------------------------------
# メインエリア：チャット表示領域
# ------------------------------------------------------------------
conversation_container = st.empty()

# ------------------------------------------------------------------
# 下部：LINE風チャットバー（テキスト入力 + ➤ ボタン）
# ------------------------------------------------------------------
with st.container():
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        user_message = st.text_area("", placeholder="Your message", height=50, key="user_message_input")
        arrow_button = st.form_submit_button("➤", key="arrow_button")
    st.markdown("</div>", unsafe_allow_html=True)

    if arrow_button:
        if user_message.strip():
            if "conversation_turns" not in st.session_state:
                st.session_state["conversation_turns"] = []
            user_text = user_message

            if len(st.session_state["conversation_turns"]) == 0:
                # 初回回答
                answer_text = generate_expert_answers(user_text)
            else:
                # 継続回答
                context = "\n".join([
                    f"あなた: {turn['user']}\n回答: {turn['answer']}"
                    for turn in st.session_state["conversation_turns"]
                ])
                answer_text = continue_discussion(user_text, context)

            st.session_state["conversation_turns"].append({"user": user_text, "answer": answer_text})

            # ここで会話を表示（実装例）
            conversation_container.markdown("")
            message(user_text, is_user=True)
            # タイプライター風に回答を表示するなら:
            # typewriter_bubble("回答", answer_text, "left")
            # あるいは一括表示
            message(answer_text, is_user=False)
        else:
            st.warning("発言を入力してください。")
