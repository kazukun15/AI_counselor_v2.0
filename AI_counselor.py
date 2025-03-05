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
# ページ設定（最初に呼び出す）
# ------------------------------------------------------------------
st.set_page_config(page_title="メンタルケアボット", layout="wide")
st.title("メンタルケアボット V3.0")

# ------------------------------------------------------------------
# config.toml のテーマ設定読み込み
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
# 背景・共通スタイルの設定（テーマ設定を反映）
# ------------------------------------------------------------------
st.markdown(
    f"""
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
    /* 下部固定入力エリア */
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
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------------
# サイドバー：ユーザー情報、相談タイプ、改善策レポートボタン
# ------------------------------------------------------------------
with st.sidebar:
    user_name = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="sidebar_user_name")
    consult_type = st.radio("相談タイプを選択してください", ("本人の相談", "他者の相談", "デリケートな相談"), key="sidebar_consult_type")
    if st.button("改善策のレポート", key="report_sidebar_1"):
        if st.session_state.get("conversation_turns", []):
            all_turns = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state.get("conversation_turns", [])
            ])
            summary = generate_summary(all_turns)
            st.session_state["summary"] = summary
            st.markdown("**まとめ:**\n" + summary)
        else:
            st.warning("まずは会話を開始してください。")

# ------------------------------------------------------------------
# サイドバー：選択式相談フォームと過去の会話履歴
# ------------------------------------------------------------------
if st.session_state.get("show_selection_form", False):
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
        if st.button("選択内容を送信", key="submit_selection_1"):
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
            if "conversation_turns" not in st.session_state:
                st.session_state.conversation_turns = []
            st.session_state.conversation_turns.append({
                "user": selection_summary, 
                "answer": "選択式相談フォームの内容が送信され、反映されました。"
            })
            st.success("送信しました！")
        st.header("過去の会話")
        if st.session_state.get("conversation_turns", []):
            for turn in st.session_state.get("conversation_turns", []):
                st.markdown(f"**あなた:** {turn['user'][:50]}...")
                st.markdown(f"**回答:** {turn['answer'][:50]}...")
        else:
            st.info("まだ会話はありません。")

# ------------------------------------------------------------------
# キャラクター定義（4人専門家）
# ------------------------------------------------------------------
EXPERTS = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]

# ------------------------------------------------------------------
# アイコン画像の読み込み（avatars/ に配置、ユーザーは絵文字固定）
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
    "user": "👤",  # ユーザーは絵文字固定
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
# Gemini API 呼び出し関連関数（キャッシュなし）
# ------------------------------------------------------------------
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
            return "回答が見つかりませんでした。(candidatesが空)"
        candidate0 = candidates[0]
        content_val = candidate0.get("content", "")
        if isinstance(content_val, dict):
            parts = content_val.get("parts", [])
            content_str = " ".join([p.get("text", "") for p in parts])
        else:
            content_str = str(content_val)
        content_str = content_str.strip()
        if not content_str:
            return "回答が見つかりませんでした。(contentが空)"
        return remove_json_artifacts(content_str)
    except Exception as e:
        return f"エラー: レスポンス解析に失敗しました -> {str(e)}"

# ------------------------------------------------------------------
# 会話生成関連関数
# ------------------------------------------------------------------
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
    params = {}
    params["精神科医師"] = {"style": "温かく落ち着いた", "detail": "豊富な経験に基づいた判断を下す"}
    if analyze_question(question) > 0:
        params["カウンセラー"] = {"style": "共感的", "detail": "深い理解と共感で心に寄り添う"}
        params["メンタリスト"] = {"style": "柔軟", "detail": "実務的な知見を活かした意見を提供する"}
    else:
        params["カウンセラー"] = {"style": "分析的", "detail": "論理的な視点で根拠をもって説明する"}
        params["メンタリスト"] = {"style": "客観的", "detail": "中立的な観点から問題点を整理する"}
    params["内科医"] = {"style": "実直な", "detail": "身体の不調や他の病気の有無を慎重にチェックする"}
    return params

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
    return call_gemini_api(prompt)

def continue_discussion(additional_input: str, current_turns: str) -> str:
    prompt = (
        "これまでの会話:\n" + current_turns + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記を踏まえ、4人の専門家として回答を更新してください。必ず以下の形式で出力:\n"
        "精神科医師: <回答>\n"
        "カウンセラー: <回答>\n"
        "メンタリスト: <回答>\n"
        "内科医: <回答>\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は4人の専門家からの回答を含む会話内容です:\n" + discussion + "\n\n" +
        "この内容を踏まえて、愛媛県庁職員向けのメンタルヘルスケアに関するまとめレポートを、"
        "分かりやすいマークダウン形式で生成してください。"
    )
    return call_gemini_api(prompt)

# ------------------------------------------------------------------
# Streamlit Chat を使った会話履歴の表示関数
# ------------------------------------------------------------------
def display_chat():
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        display_name = st.session_state.get("user_name", "ユーザー") if role == "user" else role
        if role == "user":
            with st.chat_message("user", avatar=avatar_img_dict.get("user", "👤")):
                st.markdown(
                    f'<div style="text-align: right;"><div class="chat-bubble"><div class="chat-header">{display_name}</div>{content}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message(role, avatar=avatar_img_dict.get(role, "🤖")):
                st.markdown(
                    f'<div style="text-align: left;"><div class="chat-bubble"><div class="chat-header">{display_name}</div>{content}</div></div>',
                    unsafe_allow_html=True,
                )

# ------------------------------------------------------------------
# タイプライター風表示用関数
# ------------------------------------------------------------------
def create_bubble(sender: str, message: str, align: str) -> str:
    avatar_html = ""
    display_sender = sender if sender != "あなた" else "ユーザー"
    if display_sender in avatar_img_dict:
        avatar = avatar_img_dict[display_sender]
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
            font-family: {font}, sans-serif;
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
            font-family: {font}, sans-serif;
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

# ------------------------------------------------------------------
# メインエリア：専門家キャラクターの固定表示（上部）
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
# メインエリア：チャットバブル表示領域（上部）
# ------------------------------------------------------------------
conversation_container = st.empty()

# ------------------------------------------------------------------
# サイドバー：過去の会話履歴とサイドボタン
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 過去の会話")
    if st.session_state.get("conversation_turns", []):
        for turn in st.session_state.get("conversation_turns", []):
            st.markdown(f"**あなた:** {turn['user'][:50]}...")
            st.markdown(f"**回答:** {turn['answer'][:50]}...")
    else:
        st.info("まだ会話はありません。")
    if st.button("改善策のレポート", key="report_sidebar_2"):
        if st.session_state.get("conversation_turns", []):
            all_turns = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state.get("conversation_turns", [])
            ])
            summary = generate_summary(all_turns)
            st.session_state["summary"] = summary
            st.markdown("**まとめ:**\n" + summary)
        else:
            st.warning("まずは会話を開始してください。")
    if st.button("続きを読み込む", key="continue_sidebar_2"):
        if st.session_state.get("conversation_turns", []):
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state.get("conversation_turns", [])
            ])
            new_answer = continue_discussion("続きをお願いします。", context)
            st.session_state.conversation_turns.append({"user": "続き", "answer": new_answer})
            conversation_container.markdown("")
            display_chat()
        else:
            st.warning("会話がありません。")

# ------------------------------------------------------------------
# 下部固定のユーザー入力エリア（LINE風チャットバー）
# ------------------------------------------------------------------
with st.container():
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        user_message = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_message")
        col1, col2 = st.columns(2)
        with col1:
            send_button = st.form_submit_button("送信", key="send_button")
        with col2:
            continue_button = st.form_submit_button("続きを話す", key="continue_button")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 送信ボタン処理
    if send_button:
        if user_message.strip():
            if "conversation_turns" not in st.session_state:
                st.session_state.conversation_turns = []
            user_text = user_message
            if len(st.session_state.get("conversation_turns", [])) == 0:
                answer_text = generate_expert_answers(user_text)
            else:
                context = "\n".join([
                    f"あなた: {turn['user']}\n回答: {turn['answer']}"
                    for turn in st.session_state.get("conversation_turns", [])
                ])
                answer_text = continue_discussion(user_text, context)
            st.session_state.conversation_turns.append({"user": user_text, "answer": answer_text})
            conversation_container.markdown("")
            display_chat()
            message(user_text, is_user=True)
            typewriter_bubble("回答", answer_text, "left")
        else:
            st.warning("発言を入力してください。")
    
    # 続きボタン処理（下部固定）
    if continue_button:
        if st.session_state.get("conversation_turns", []):
            context = "\n".join([
                f"あなた: {turn['user']}\n回答: {turn['answer']}"
                for turn in st.session_state.get("conversation_turns", [])
            ])
            new_discussion = continue_discussion("続きをお願いします。", context)
            st.session_state.conversation_turns.append({"user": "続き", "answer": new_discussion})
            conversation_container.markdown("")
            display_chat()
        else:
            st.warning("まずは会話を開始してください。")
