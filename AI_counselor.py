import streamlit as st
import requests
import re
import random
from streamlit_chat import message  # streamlit-chat のメッセージ表示用関数

# ------------------------
# ページ設定
# ------------------------
st.set_page_config(page_title="ぼくのともだち", layout="wide")
st.title("ぼくのともだち V2.2.1")

# ------------------------
# 背景・共通スタイルの設定
# ------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #e9edf5;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 15px;
        border: 1px solid #ccc;
        border-radius: 10px;
        margin-bottom: 20px;
        background-color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------
# ユーザーの名前入力（上部）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="ユーザー", key="user_name")

# ------------------------
# キャラクター定義
# ------------------------
USER_NAME = "user"
ASSISTANT_NAME = "assistant"
YUKARI_NAME = "ゆかり"
SHINYA_NAME = "しんや"
MINORU_NAME = "みのる"
NEW_CHAR_NAME = "新キャラクター"

# ------------------------
# 定数／設定（APIキーなど）
# ------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
NAMES = [YUKARI_NAME, SHINYA_NAME, MINORU_NAME]

# ------------------------
# セッション初期化
# ------------------------
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

# ------------------------
# アイコンの設定（今回はゆかりのみ絵文字）
# ------------------------
avatar_img_dict = {
    YUKARI_NAME: "🎉",
}

# ------------------------
# 関数定義
# ------------------------

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
    score = analyze_question(question)
    params = {}
    params["ゆかり"] = {"style": "明るくはっちゃけた", "detail": "楽しい雰囲気で元気な回答"}
    if score > 0:
        params["しんや"] = {"style": "共感的", "detail": "心情を重視した解説"}
        params["みのる"] = {"style": "柔軟", "detail": "状況に合わせた多面的な視点"}
    else:
        params["しんや"] = {"style": "分析的", "detail": "データや事実を踏まえた説明"}
        params["みのる"] = {"style": "客観的", "detail": "中立的な視点からの考察"}
    return params

def remove_json_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned.strip()

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

def generate_discussion(question: str, persona_params: dict) -> str:
    """最初の会話生成。ユーザーの質問と各キャラクターのパラメータを元にプロンプトを構築"""
    current_user = st.session_state.get("user_name", "ユーザー")
    prompt = f"【{current_user}さんの質問】\n{question}\n\n"
    for name, params in persona_params.items():
        prompt += f"{name}は【{params['style']}な視点】で、{params['detail']}。\n"
    new_name, new_personality = generate_new_character()
    prompt += f"さらに、新キャラクターとして {new_name} は【{new_personality}】な性格です。彼/彼女も会話に加わってください。\n"
    prompt += (
        "\n上記情報を元に、4人が友達同士のように自然な会話をしてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        f"{new_name}: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def continue_discussion(additional_input: str, current_discussion: str) -> str:
    """会話の続き生成。既存の会話と追加発言を元にプロンプトを構築"""
    prompt = (
        "これまでの会話:\n" + current_discussion + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記を踏まえ、4人がさらに自然な会話を続けてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "新キャラクター: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は4人の会話内容です。\n" + discussion + "\n\n" +
        "この会話を踏まえ、質問に対するまとめ回答を生成してください。\n"
        "自然な日本語文で出力し、余計なJSON形式は不要です。"
    )
    return call_gemini_api(prompt)

def generate_new_character() -> tuple:
    candidates = [
        ("たけし", "冷静沈着で皮肉屋、どこか孤高な存在"),
        ("さとる", "率直かつ辛辣で、常に現実を鋭く指摘する"),
        ("りさ", "自由奔放で斬新なアイデアを持つ、ユニークな感性の持ち主"),
        ("けんじ", "クールで合理的、論理に基づいた意見を率直に述べる"),
        ("なおみ", "独創的で個性的、常識にとらわれず新たな視点を提供する")
    ]
    return random.choice(candidates)

def display_chat_log(chat_log: list):
    """
    chat_log の各メッセージを、LINE風のチャットバブル形式で表示する。
    ユーザーの発言は右寄せ、友達の発言は左寄せで表示され、テキストは自動で折り返されます。
    最新のメッセージが入力バーの直上に表示されるよう、チャットログは逆順に表示します。
    """
    from streamlit_chat import message as st_message
    for msg in reversed(chat_log):
        sender = msg["sender"]
        text = msg["message"]
        if sender == "user":
            st_message(text, is_user=True)
        else:
            st_message(f"{sender}: {text}", is_user=False)

# ------------------------
# 初回会話の自動生成（会話ログが空の場合は何もしない）
# ------------------------
# ※初回に自動で会話を始めるのではなく、ユーザーが発言したときにその発言に対して応答する

# ------------------------
# 固定フッター（入力エリア）の配置
# ------------------------
with st.container():
    st.markdown(
        '<div style="position: fixed; bottom: 0; width: 100%; background: #FFF; padding: 10px; box-shadow: 0 -2px 5px rgba(0,0,0,0.1);">',
        unsafe_allow_html=True,
    )
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_input")
        col1, col2 = st.columns(2)
        with col1:
            send_button = st.form_submit_button("送信")
        with col2:
            continue_button = st.form_submit_button("続きを話す")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 送信ボタンの処理
    if send_button:
        if user_input.strip():
            st.session_state.chat_log.append({"sender": "user", "message": user_input})
            # 初回の発言なら generate_discussion を使用
            if len(st.session_state.chat_log) == 1:
                persona_params = adjust_parameters(user_input)
                discussion = generate_discussion(user_input, persona_params)
            else:
                discussion = continue_discussion(user_input, "\n".join(
                    [f'{chat["sender"]}: {chat["message"]}' for chat in st.session_state.chat_log if chat["sender"] in NAMES or chat["sender"] == NEW_CHAR_NAME]
                ))
            for line in discussion.split("\n"):
                line = line.strip()
                if line:
                    parts = line.split(":", 1)
                    sender = parts[0]
                    message_text = parts[1].strip() if len(parts) > 1 else ""
                    st.session_state.chat_log.append({"sender": sender, "message": message_text})
        else:
            st.warning("発言を入力してください。")
    
    # 続きを話すボタンの処理
    if continue_button:
        if st.session_state.chat_log:
            default_input = "続きをお願いします。"
            new_discussion = continue_discussion(default_input, "\n".join(
                [f'{chat["sender"]}: {chat["message"]}' for chat in st.session_state.chat_log if chat["sender"] in NAMES or chat["sender"] == NEW_CHAR_NAME]
            ))
            for line in new_discussion.split("\n"):
                line = line.strip()
                if line:
                    parts = line.split(":", 1)
                    sender = parts[0]
                    message_text = parts[1].strip() if len(parts) > 1 else ""
                    st.session_state.chat_log.append({"sender": sender, "message": message_text})
        else:
            st.warning("まずは会話を開始してください。")
            
# ------------------------
# 会話ウィンドウの表示
# ------------------------
st.header("会話履歴")
if st.session_state.chat_log:
    display_chat_log(st.session_state.chat_log)
else:
    st.markdown("<p style='color: gray;'>ここに会話が表示されます。</p>", unsafe_allow_html=True)
