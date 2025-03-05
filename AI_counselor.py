import streamlit as st
import requests
import re
import random
import time
import base64
from io import BytesIO
from PIL import Image
from streamlit_chat import message  # pip install streamlit-chat

# ========================
# ここでモデル名と API キーを指定
# ========================
MODEL_NAME = "gemini-2.0-flash"  # 例: gemini-2.0-flash / chat-bison-001 / etc.
API_KEY = st.secrets["general"]["api_key"]  # secrets.toml などで管理

# ========================
# ページ設定
# ========================
st.set_page_config(page_title="メンタルケアボット", layout="wide")
st.title("メンタルケアボット V3.1")

# ========================
# テーマ設定（config.toml 読み込み：失敗したらデフォルト値）
# ========================
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

# ========================
# 共通スタイル（背景・固定入力エリアなど）
# ========================
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

# ========================
# セッション初期化
# ========================
if "conversation_turns" not in st.session_state:
    st.session_state["conversation_turns"] = []
# この messages は streamlit_chat 用に使う（任意機能）
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "show_selection_form" not in st.session_state:
    st.session_state["show_selection_form"] = False

# ========================
# サイドバー：ユーザー設定、相談タイプなど
# ========================
with st.sidebar:
    st.header("ユーザー設定")
    st.session_state["user_name"] = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員")
    st.session_state["consult_type"] = st.radio(
        "相談タイプを選択してください", 
        ("本人の相談", "他者の相談", "デリケートな相談")
    )

    st.header("機能")
    # 改善策のレポート
    if st.button("改善策のレポート"):
        if st.session_state.get("conversation_turns", []):
            all_turns = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            summary = generate_summary(all_turns)
            st.markdown("**まとめ:**\n" + summary)
        else:
            st.warning("まずは会話を開始してください。")

    # 続きを読み込む
    if st.button("続きを読み込む"):
        if st.session_state.get("conversation_turns", []):
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            new_answer = continue_discussion("続きをお願いします。", context)
            st.session_state["conversation_turns"].append({"user": "続き", "answer": new_answer})
            st.experimental_rerun()
        else:
            st.warning("会話がありません。")

    # 過去の会話の簡易表示
    st.header("過去の会話")
    if st.session_state.get("conversation_turns", []):
        for turn in st.session_state["conversation_turns"]:
            st.markdown(f"**あなた:** {turn['user'][:50]}...")
            st.markdown(f"**回答:** {turn['answer'][:50]}...")
    else:
        st.info("まだ会話はありません。")

# ========================
# (任意) 選択式相談フォームをサイドバー内に置く例
# ========================
with st.sidebar:
    if st.button("選択式相談フォームを開く"):
        st.session_state["show_selection_form"] = True

    if st.session_state["show_selection_form"]:
        st.header("選択式相談フォーム")
        category = st.selectbox("悩みの種類", ["人間関係", "仕事", "家庭", "経済", "健康", "その他"])
        st.subheader("身体の状態")
        physical_status = st.radio("身体の状態", ["良好", "普通", "不調"])
        physical_detail = st.text_area("身体の状態の詳細", placeholder="具体的な症状や変化")
        physical_duration = st.selectbox("身体の症状の持続期間", ["数日", "1週間", "1ヶ月以上", "不明"])
        st.subheader("心の状態")
        mental_status = st.radio("心の状態", ["落ち着いている", "やや不安", "とても不安"])
        mental_detail = st.text_area("心の状態の詳細", placeholder="感じる不安やストレス")
        mental_duration = st.selectbox("心の症状の持続期間", ["数日", "1週間", "1ヶ月以上", "不明"])
        stress_level = st.slider("ストレスレベル (1-10)", 1, 10, 5)
        recent_events = st.text_area("最近の大きな出来事（任意）")
        treatment_history = st.radio("通院歴がありますか？", ["はい", "いいえ"])
        ongoing_treatment = ""
        if treatment_history == "はい":
            ongoing_treatment = st.radio("現在も通院中ですか？", ["はい", "いいえ"])

        if st.button("選択内容を送信"):
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

            # 会話履歴に送信
            st.session_state["conversation_turns"].append({
                "user": selection_summary,
                "answer": "選択式相談フォームの内容が送信されました。"
            })
            st.success("選択内容を送信しました。")

# ========================
# アイコン画像の読み込み
# ========================
try:
    img_psychiatrist = Image.open("avatars/Psychiatrist.png")
    img_counselor = Image.open("avatars/counselor.png")
    img_mentalist = Image.open("avatars/MENTALIST.png")
    img_doctor = Image.open("avatars/doctor.png")
except Exception as e:
    # 読み込めなかったら絵文字にフォールバック
    st.error(f"画像読み込みエラー: {e}")
    img_psychiatrist = "🧠"
    img_counselor = "👥"
    img_mentalist = "💡"
    img_doctor = "💊"

avatar_img_dict = {
    "user": "👤",  # ユーザーは絵文字で固定
    "精神科医師": img_psychiatrist,
    "カウンセラー": img_counselor,
    "メンタリスト": img_mentalist,
    "内科医": img_doctor,
    "assistant": "🤖",
}

def get_image_base64(image):
    """PIL画像をbase64エンコードしてHTMLで表示できるようにする"""
    if isinstance(image, str):
        return image  # 絵文字等
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ========================
# Gemini API 呼び出し
# ========================
def call_gemini_api(prompt: str) -> str:
    """Google Gemini (PaLM 2) APIを呼び出して回答を取得する関数"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        return f"エラー: リクエスト送信時に例外が発生しました -> {str(e)}"

    if response.status_code != 200:
        return f"エラー: ステータスコード {response.status_code} -> {response.text}"

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return "回答が見つかりませんでした。（candidatesが空）"

    candidate0 = candidates[0]
    content_val = candidate0.get("content", "")
    if isinstance(content_val, dict):
        # content_val が辞書の場合（{"parts":[{"text": ...}]}）を想定
        parts = content_val.get("parts", [])
        return "".join([p.get("text", "") for p in parts]).strip()
    else:
        return str(content_val).strip()

# ========================
# 回答生成系関数
# ========================
def generate_expert_answers(user_text: str) -> str:
    current_user = st.session_state.get("user_name", "ユーザー")
    consult_type = st.session_state.get("consult_type", "本人の相談")

    if consult_type == "デリケートな相談":
        consult_info = (
            "この相談はデリケートな内容を含みます。"
            "公的機関や学術論文に基づいた正確な情報を提供してください。"
        )
    elif consult_type == "他者の相談":
        consult_info = "この相談は他者についての内容です。客観的・専門的な視点で対応してください。"
    else:
        consult_info = "この相談は本人の悩みです。"

    # 4人専門家の回答をまとめて取得するためのプロンプト例
    prompt = (
        f"【{current_user}さんの質問】\n{user_text}\n\n"
        f"{consult_info}\n"
        "以下の4人がそれぞれ回答してください:\n"
        "精神科医師: <回答>\n"
        "カウンセラー: <回答>\n"
        "メンタリスト: <回答>\n"
        "内科医: <回答>\n"
        "各回答は300文字程度で、わかりやすい日本語で。"
    )
    return call_gemini_api(prompt)

def continue_discussion(additional_input: str, current_turns: str) -> str:
    prompt = (
        f"これまでの会話:\n{current_turns}\n\n"
        f"ユーザーの追加発言: {additional_input}\n\n"
        "上記を踏まえ、4人の専門家として回答を更新してください。"
        "必ず以下の形式で出力:\n"
        "精神科医師: <回答>\n"
        "カウンセラー: <回答>\n"
        "メンタリスト: <回答>\n"
        "内科医: <回答>\n"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        f"以下は4人の専門家が回答する会話内容です:\n{discussion}\n\n"
        "この内容を踏まえ、愛媛県庁職員向けに役立つメンタルケアのまとめをマークダウン形式で書いてください。"
    )
    return call_gemini_api(prompt)

# ========================
# チャット表示用（タイプライター風）
# ========================
def create_bubble(sender: str, message: str, align: str) -> str:
    avatar_html = ""
    if sender in avatar_img_dict:
        avatar = avatar_img_dict[sender]
        if isinstance(avatar, str):
            avatar_html = f"<span style='font-size:24px;'>{avatar}</span> "
        else:
            img_str = get_image_base64(avatar)
            avatar_html = f"<img src='data:image/png;base64,{img_str}' style='width:30px; height:30px; margin-right:5px;'>"
    # 背景色などを左右で変えている例
    if align == "right":
        bg_color = "#DCF8C6"
    else:
        bg_color = "#FFFACD"

    return f"""
    <div style="
        background-color: {bg_color};
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 8px;
        margin: 5px 0;
        color: #000;
        font-family: {font}, sans-serif;
        text-align: {align};
        width: 50%;
        float: {align};
        clear: both;
    ">
        {avatar_html}<strong>{sender}</strong>: {message}
    </div>
    """

def typewriter_bubble(sender: str, full_text: str, align: str, delay: float = 0.0):
    """
    1文字ずつ表示したい場合は delay を 0.02 などに設定
    遅延なしなら 0.0
    """
    container = st.empty()
    displayed_text = ""
    for char in full_text:
        displayed_text += char
        container.markdown(create_bubble(sender, displayed_text, align), unsafe_allow_html=True)
        time.sleep(delay)  # タイピング演出
    container.markdown(create_bubble(sender, full_text, align), unsafe_allow_html=True)

# ========================
# 上部：専門家一覧の表示
# ========================
st.markdown("### 専門家一覧")
EXPERTS = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]
cols = st.columns(len(EXPERTS))
for i, expert in enumerate(EXPERTS):
    with cols[i]:
        st.markdown(f"**{expert}**")
        icon = avatar_img_dict.get(expert, "🤖")
        if isinstance(icon, str):
            st.markdown(icon)  # 絵文字ならそのまま表示
        else:
            st.image(icon, width=60)

# ========================
# メインのチャット表示領域（上に空のコンテナ）
# ========================
conversation_container = st.container()

# ========================
# フォーム付きの下部固定入力エリア（LINE風チャットバー）
# ========================
st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area(
        "メッセージ入力", 
        placeholder="ここに入力", 
        height=50, 
        key="user_message_input"
    )
    submitted = st.form_submit_button("➤")

st.markdown("</div>", unsafe_allow_html=True)

# ========================
# フォーム送信時の処理
# ========================
if submitted:
    if user_message.strip():
        user_text = user_message.strip()
        # 新しい発言としてリストに格納
        if len(st.session_state.get("conversation_turns", [])) == 0:
            # 会話がまだ無い → 初回
            answer_text = generate_expert_answers(user_text)
        else:
            # 会話が既にある → 続き
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            answer_text = continue_discussion(user_text, context)

        st.session_state["conversation_turns"].append({"user": user_text, "answer": answer_text})

        # 画面に反映
        conversation_container.empty()
        with conversation_container:
            # ユーザー発言 (右寄せ)
            typewriter_bubble("あなた", user_text, align="right", delay=0.0)
            # 回答 (左寄せ)
            typewriter_bubble("回答", answer_text, align="left", delay=0.0)

    else:
        st.warning("メッセージを入力してください。")

# ========================
# すでにある会話をロードして表示 (リロード時用)
# ========================
else:
    if st.session_state.get("conversation_turns", []):
        conversation_container.empty()
        with conversation_container:
            for turn in st.session_state["conversation_turns"]:
                # ユーザー発言
                typewriter_bubble("あなた", turn["user"], "right", delay=0.0)
                # AI回答
                typewriter_bubble("回答", turn["answer"], "left", delay=0.0)
    else:
        # まだ会話が無い状態
        st.info("メッセージを入力し、送信してください。")
