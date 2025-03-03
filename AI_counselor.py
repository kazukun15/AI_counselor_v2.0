import streamlit as st
import requests
import re
import time
import random
import base64
from io import BytesIO
from streamlit_chat import message  # pip install streamlit-chat
from PIL import Image

# ------------------------
# ページ設定（最初に実行）
# ------------------------
st.set_page_config(page_title="メンタルケアボット", layout="wide")

# ------------------------
# カスタムCSSの挿入（柔らかい薄いピンク・黄色）
# ------------------------
st.markdown(
    """
    <style>
    /* メイン画面の背景を薄いピンクに設定 */
    .reportview-container {
        background: #FFF0F5;
    }
    /* サイドバーの背景を柔らかい黄色に設定 */
    .sidebar .sidebar-content {
        background: #FFF5EE;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------
# タイトル表示
# ------------------------
st.title("メンタルケアボット")

# ------------------------
# ユーザー情報入力（上部）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="user_name")
col1, col2 = st.columns([3, 1])
with col1:
    consult_type = st.radio("相談タイプを選択してください", 
                            ("本人の相談", "他者の相談", "デリケートな相談"), key="consult_type")
with col2:
    if st.button("選択式相談フォームを開く", key="open_form"):
        st.session_state["show_selection_form"] = True

# ------------------------
# 定数／設定
# ------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
ROLES = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]

# ------------------------
# セッションステート初期化
# ------------------------
if "conversation_turns" not in st.session_state:
    st.session_state["conversation_turns"] = []
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []
if "show_selection_form" not in st.session_state:
    st.session_state["show_selection_form"] = False

# ------------------------
# アバター画像の読み込み
#   画像はスクリプトと同じディレクトリ内の「avatars」フォルダに配置
# ------------------------
try:
    img_psychiatrist = Image.open("./avatars/Psychiatrist.png")
    img_counselor = Image.open("./avatars/counselor.png")
    img_mentalist = Image.open("./avatars/MENTALIST.png")
    img_doctor = Image.open("./avatars/doctor.png")
except Exception as e:
    st.error(f"画像読み込みエラー: {e}")
    img_psychiatrist = "🧠"
    img_counselor = "👥"
    img_mentalist = "💡"
    img_doctor = "💊"

avatar_dict = {
    "あなた": "👤",  # ユーザー用（画像があれば差し替え）
    "精神科医師": img_psychiatrist,
    "カウンセラー": img_counselor,
    "メンタリスト": img_mentalist,
    "内科医": img_doctor
}

def get_image_base64(image):
    if isinstance(image, str):
        return image  # 絵文字の場合
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ------------------------
# 選択式相談フォーム（サイドバーに収納）
# ------------------------
if st.session_state.get("show_selection_form", False):
    st.sidebar.header("選択式相談フォーム")
    category = st.sidebar.selectbox("悩みの種類", 
                                    ["人間関係", "仕事", "家庭", "経済", "健康", "その他"], key="category")
    
    st.sidebar.subheader("身体の状態")
    physical_status = st.sidebar.radio("身体の状態", ["良好", "普通", "不調"], key="physical")
    physical_detail = st.sidebar.text_area("身体の状態の詳細", key="physical_detail", placeholder="具体的な症状や変化を記入")
    physical_duration = st.sidebar.selectbox("身体の症状の持続期間", 
                                               ["数日", "1週間", "1ヶ月以上", "不明"], key="physical_duration")
    
    st.sidebar.subheader("心の状態")
    mental_status = st.sidebar.radio("心の状態", ["落ち着いている", "やや不安", "とても不安"], key="mental")
    mental_detail = st.sidebar.text_area("心の状態の詳細", key="mental_detail", placeholder="感じている不安やストレスの内容を記入")
    mental_duration = st.sidebar.selectbox("心の症状の持続期間", 
                                             ["数日", "1週間", "1ヶ月以上", "不明"], key="mental_duration")
    
    stress_level = st.sidebar.slider("ストレスレベル (1-10)", 1, 10, 5, key="stress")
    recent_events = st.sidebar.text_area("最近の大きな出来事（任意）", key="events")
    treatment_history = st.sidebar.radio("通院歴がありますか？", ["はい", "いいえ"], key="treatment")
    ongoing_treatment = ""
    if treatment_history == "はい":
        ongoing_treatment = st.sidebar.radio("現在も通院中ですか？", ["はい", "いいえ"], key="ongoing")
    
    if st.sidebar.button("選択内容を送信", key="submit_selection"):
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
        st.sidebar.success("送信しました！")

# ------------------------
# ヘルパー関数（チャット生成・表示）
# ------------------------
def truncate_text(text, max_length=400):
    return text if len(text) <= max_length else text[:max_length] + "…"

def split_message(message: str, chunk_size=200) -> list:
    chunks = []
    while len(message) > chunk_size:
        break_point = -1
        for punct in ["。", "！", "？"]:
            pos = message.rfind(punct, 0, chunk_size)
            if pos > break_point:
                break_point = pos
        if break_point == -1:
            break_point = chunk_size
        else:
            break_point += 1
        chunks.append(message[:break_point].strip())
        message = message[break_point:].strip()
    if message:
        chunks.append(message)
    return chunks

def remove_json_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()

def call_gemini_api(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        return f"エラー: リクエスト送信時に例外が発生しました -> {str(e)}"
    if response.status_code != 200:
        return f"エラー: ステータスコード {response.status_code} -> {response.text}"
    try:
        rjson = response.json()
        candidates = rjson.get("candidates", [])
        if not candidates:
            return "回答が見つかりませんでした。"
        candidate0 = candidates[0]
        content_val = candidate0.get("content", "")
        if isinstance(content_val, dict):
            parts = content_val.get("parts", [])
            content_str = " ".join([p.get("text", "") for p in parts])
        else:
            content_str = str(content_val)
        content_str = content_str.strip()
        if not content_str:
            return "回答が見つかりませんでした。"
        return remove_json_artifacts(content_str)
    except Exception as e:
        return f"エラー: レスポンス解析に失敗しました -> {str(e)}"

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
    # 今回は専門家は固定回答のため、ロジックは省略
    return {}

def generate_expert_answers(question: str) -> str:
    current_user = st.session_state.get("user_name", "ユーザー")
    consult_type = st.session_state.get("consult_type", "本人の相談")
    if consult_type == "デリケートな相談":
        consult_info = ("この相談は大人の発達障害（例：ADHDなど）を含む、デリケートな相談です。"
                        "公的機関や学術論文を参照し、正確な情報に基づいた回答をお願いします。")
    elif consult_type == "他者の相談":
        consult_info = "この相談は、他者が抱える障害に関するものです。専門的かつ客観的な視点をお願いします。"
    else:
        consult_info = "この相談は本人が抱える悩みに関するものです。"
        
    prompt = f"【{current_user}さんの質問】\n{question}\n\n{consult_info}\n"
    prompt += (
        "以下は、4人の専門家からの個別回答です。必ず以下の形式で出力してください:\n"
        "精神科医師: <回答>\n"
        "カウンセラー: <回答>\n"
        "メンタリスト: <回答>\n"
        "内科医: <回答>\n"
        "各回答は300～400文字程度で、自然な日本語で出力してください。"
    )
    return truncate_text(call_gemini_api(prompt), 400)

def continue_expert_answers(additional_input: str, current_turns: str) -> str:
    prompt = (
        "これまでの会話:\n" + current_turns + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記を踏まえ、4人の専門家として回答を更新してください。必ず以下の形式で出力:\n"
        "精神科医師: <回答>\n"
        "カウンセラー: <回答>\n"
        "メンタリスト: <回答>\n"
        "内科医: <回答>\n"
        "各回答は300～400文字程度で、自然な日本語で出力してください。"
    )
    return truncate_text(call_gemini_api(prompt), 400)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は4人の専門家からの回答を含む会話内容です:\n" + discussion + "\n\n" +
        "この内容を踏まえて、愛媛県庁職員向けのメンタルヘルスケアに関するまとめレポートを、"
        "分かりやすいマークダウン形式で生成してください。"
    )
    return call_gemini_api(prompt)

def display_chat_bubble(sender: str, message: str, align: str):
    avatar_html = ""
    display_sender = sender if sender != "あなた" else "ユーザー"
    if display_sender in avatar_dict:
        avatar = avatar_dict[display_sender]
        if isinstance(avatar, str):
            avatar_html = f"<span style='font-size: 24px;'>{avatar}</span> "
        else:
            img_str = get_image_base64(avatar)
            avatar_html = f"<img src='data:image/png;base64,{img_str}' style='width:30px; height:30px; margin-right:5px;'>"
    if align == "right":
        bubble_html = f"""
        <div style="
            background-color: #DCF8C6;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
            text-align: right;
            width: 50%;
            float: right;
            clear: both;
        ">
            {avatar_html}<strong>{display_sender}</strong>: {message} 😊
        </div>
        """
    else:
        bubble_html = f"""
        <div style="
            background-color: #FFFACD;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
            text-align: left;
            width: 50%;
            float: left;
            clear: both;
        ">
            {avatar_html}<strong>{display_sender}</strong>: {message} 👍
        </div>
        """
    st.markdown(bubble_html, unsafe_allow_html=True)

def display_conversation_turns(turns: list):
    for turn in reversed(turns):
        display_chat_bubble("あなた", turn["user"], "right")
        lines = turn["answer"].split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                role, ans = line.split(":", 1)
                display_chat_bubble(role.strip(), ans.strip(), "left")
            else:
                display_chat_bubble("回答", line, "left")

# タイプライター風表示用関数
def create_bubble(sender: str, message: str, align: str) -> str:
    avatar_html = ""
    display_sender = sender if sender != "あなた" else "ユーザー"
    if display_sender in avatar_dict:
        avatar = avatar_dict[display_sender]
        if isinstance(avatar, str):
            avatar_html = f"<span style='font-size: 24px;'>{avatar}</span> "
        else:
            img_str = get_image_base64(avatar)
            avatar_html = f"<img src='data:image/png;base64,{img_str}' style='width:30px; height:30px; margin-right:5px;'>"
    if align == "right":
        return f"""
        <div style="
            background-color: #DCF8C6;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
            text-align: right;
            width: 50%;
            float: right;
            clear: both;
        ">
            {avatar_html}<strong>{display_sender}</strong>: {message} 😊
        </div>
        """
    else:
        return f"""
        <div style="
            background-color: #FFFACD;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
            text-align: left;
            width: 50%;
            float: left;
            clear: both;
        ">
            {avatar_html}<strong>{display_sender}</strong>: {message} 👍
        </div>
        """

def typewriter_bubble(sender: str, full_text: str, align: str, delay: float = 0.05):
    container = st.empty()
    displayed_text = ""
    for char in full_text:
        displayed_text += char
        container.markdown(create_bubble(sender, displayed_text, align), unsafe_allow_html=True)
        time.sleep(delay)
    container.markdown(create_bubble(sender, full_text, align), unsafe_allow_html=True)

# ------------------------
# Streamlit アプリ本体
# ------------------------
st.title("メンタルケアボット")
st.header("会話履歴")
conversation_container = st.empty()

# 改善策のレポートボタン
if st.button("改善策のレポート"):
    if st.session_state["conversation_turns"]:
        all_turns = "\n".join([
            f"あなた: {turn['user']}\n回答: {turn['answer']}"
            for turn in st.session_state["conversation_turns"]
        ])
        summary = generate_summary(all_turns)
        st.session_state["summary"] = summary
        st.markdown("### 改善策のレポート\n" + "**まとめ:**\n" + summary)
    else:
        st.warning("まずは会話を開始してください。")

# 続きボタン
if st.button("続きを読み込む"):
    if st.session_state["conversation_turns"]:
        context = "\n".join([
            f"あなた: {turn['user']}\n回答: {turn['answer']}"
            for turn in st.session_state["conversation_turns"]
        ])
        new_answer = continue_expert_answers("続きをお願いします。", context)
        st.session_state["conversation_turns"].append({"user": "続き", "answer": new_answer})
        conversation_container.markdown("### 会話履歴")
        display_conversation_turns(st.session_state["conversation_turns"])
    else:
        st.warning("会話がありません。")

st.header("メッセージ入力")
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_message")
    submitted = st.form_submit_button("送信")

if submitted:
    if user_message.strip():
        if "conversation_turns" not in st.session_state:
            st.session_state["conversation_turns"] = []
        user_text = user_message
        if len(st.session_state["conversation_turns"]) == 0:
            answer_text = generate_expert_answers(user_text)
        else:
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state["conversation_turns"]
            ])
            answer_text = continue_expert_answers(user_text, context)
        st.session_state["conversation_turns"].append({"user": user_text, "answer": answer_text})
        conversation_container.markdown("### 会話履歴")
        display_conversation_turns(st.session_state["conversation_turns"])
        display_chat_bubble("あなた", user_text, "right")
        typewriter_bubble("回答", answer_text, "left")
    else:
        st.warning("発言を入力してください。")
