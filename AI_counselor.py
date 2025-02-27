import streamlit as st
import requests
import re
from streamlit_chat import message  # pip install streamlit-chat

# ------------------------
# ページ設定（最初に実行）
# ------------------------
st.set_page_config(page_title="役場メンタルケア - チャット", layout="wide")

# ------------------------
# ユーザー情報入力（画面上部）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="愛媛県庁職員", key="user_name")
consult_type = st.radio("相談タイプを選択してください", ("本人の相談", "他者の相談", "デリケートな相談"), key="consult_type")

# ------------------------
# 定数／設定
# ------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
ROLES = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]

# ------------------------
# セッションステート初期化（会話ターン単位で管理）
# ------------------------
if "conversation_turns" not in st.session_state:
    st.session_state["conversation_turns"] = []
if "show_selection_form" not in st.session_state:
    st.session_state["show_selection_form"] = False

# ------------------------
# ヘルパー関数
# ------------------------
def truncate_text(text, max_length=400):
    return text if len(text) <= max_length else text[:max_length] + "…"

def split_message(message: str, chunk_size=200) -> list:
    return [message[i:i+chunk_size] for i in range(0, len(message), chunk_size)]

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

def adjust_parameters(question: str) -> dict:
    params = {}
    params["精神科医師"] = {"style": "専門的", "detail": "精神科のナレッジを基に的確な判断を下す"}
    params["カウンセラー"] = {"style": "共感的", "detail": "寄り添いながら優しくサポートする"}
    params["メンタリスト"] = {"style": "洞察力に富んだ", "detail": "多角的な心理学的視点から分析する"}
    params["内科医"] = {"style": "実直な", "detail": "身体面の不調や他の病気を慎重にチェックする"}
    return params

def generate_combined_answer(question: str, persona_params: dict) -> str:
    current_user = st.session_state.get("user_name", "ユーザー")
    consult_type = st.session_state.get("consult_type", "本人の相談")
    if consult_type == "デリケートな相談":
        consult_info = ("この相談は大人の発達障害（例：ADHDなど）を含む、デリケートな相談です。"
                        "信頼できる公的機関や学術論文を参照し、正確な情報に基づいた回答をお願いします。")
    elif consult_type == "他者の相談":
        consult_info = "この相談は、他者が抱える障害に関するものです。専門的な視点から客観的な判断をお願いします。"
    else:
        consult_info = "この相談は本人が抱える悩みに関するものです。"
        
    prompt = f"【{current_user}さんの質問】\n{question}\n\n{consult_info}\n"
    prompt += (
        "以下は、4人の専門家の意見を内部で統合した結果です。"
        "内部の議論内容は伏せ、あなたに対する一対一の自然な会話として、"
        "たとえば「どうしたの？もう少し詳しく教えて」といった返答を含む回答を生成してください。"
        "回答は300～400文字程度で、自然な日本語で出力してください。"
    )
    return truncate_text(call_gemini_api(prompt), 400)

def continue_combined_answer(additional_input: str, current_turns: str) -> str:
    prompt = (
        "これまでの会話の流れ:\n" + current_turns + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記の流れを踏まえ、さらに自然な会話として、"
        "たとえば「それでどうなったの？」といった返答を含む回答を生成してください。"
        "回答は300～400文字程度で、自然な日本語で出力してください。"
    )
    return truncate_text(call_gemini_api(prompt), 400)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は4人の統合された会話内容です:\n" + discussion + "\n\n" +
        "この内容を踏まえて、愛媛県庁職員向けのメンタルヘルスケアに関するまとめレポートを、"
        "分かりやすいマークダウン形式で生成してください。"
    )
    return call_gemini_api(prompt)

# ------------------------
# 選択式相談フォーム（サイドバー）
# ------------------------
if st.button("選択式相談フォームを開く"):
    st.session_state["show_selection_form"] = True

if st.session_state.get("show_selection_form", False):
    st.sidebar.header("選択式相談フォーム")
    category = st.sidebar.selectbox("悩みの種類", ("人間関係", "仕事", "人生", "その他"), key="category")
    physical_status = st.sidebar.radio("体の状態", ("良好", "普通", "不調"), key="physical")
    mental_status = st.sidebar.radio("心の状態", ("落ち着いている", "やや不安", "とても不安"), key="mental")
    additional_comments = st.sidebar.text_area("その他のコメント", key="comments")
    if st.sidebar.button("選択内容を送信"):
        selection_summary = f"【選択式相談フォーム】\n悩みの種類: {category}\n体の状態: {physical_status}\n心の状態: {mental_status}\nコメント: {additional_comments}"
        if "conversation_turns" not in st.session_state or not isinstance(st.session_state["conversation_turns"], list):
            st.session_state["conversation_turns"] = []
        st.session_state["conversation_turns"].append({"user": selection_summary, "answer": "選択式相談フォームの内容が送信されました。"})
        st.sidebar.success("送信しました！")

# ------------------------
# Streamlit Chat 表示（streamlit-chat を利用）
# ------------------------
def display_conversation_turns(turns: list):
    for turn in reversed(turns):
        # ユーザーの発言（右寄せ）
        message(turn["user"], is_user=True)
        # 回答が長い場合は分割して表示（途中は「👉」付き）
        answer_chunks = split_message(turn["answer"], 200)
        for i, chunk in enumerate(answer_chunks):
            suffix = " 👉" if i < len(answer_chunks) - 1 else ""
            message(chunk + suffix, is_user=False)

# ------------------------
# Streamlit アプリ本体
# ------------------------
st.title("役場メンタルケア - チャットサポート")

# --- 上部：会話履歴表示エリア ---
st.header("会話履歴")
conversation_container = st.empty()

# --- 上部：まとめ回答ボタン ---
if st.button("会話をまとめる"):
    if st.session_state.get("conversation_turns", []):
        all_turns = "\n".join([f"あなた: {turn['user']}\n回答: {turn['answer']}" for turn in st.session_state["conversation_turns"]])
        summary = generate_summary(all_turns)
        st.session_state["summary"] = summary
        st.markdown("### まとめ回答\n" + "**まとめ:**\n" + summary)
    else:
        st.warning("まずは会話を開始してください。")

# --- 下部：ユーザー入力エリア ---
st.header("メッセージ入力")
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_message")
    submitted = st.form_submit_button("送信")

if submitted:
    if user_message.strip():
        if "conversation_turns" not in st.session_state or not isinstance(st.session_state["conversation_turns"], list):
            st.session_state["conversation_turns"] = []
        user_text = user_message
        persona_params = adjust_parameters(user_message)
        if len(st.session_state["conversation_turns"]) == 0:
            answer_text = generate_combined_answer(user_message, persona_params)
        else:
            context = "\n".join([f"あなた: {turn['user']}\n回答: {turn['answer']}" for turn in st.session_state["conversation_turns"]])
            answer_text = continue_combined_answer(user_message, context)
        st.session_state["conversation_turns"].append({"user": user_text, "answer": answer_text})
        conversation_container.markdown("### 会話履歴")
        display_conversation_turns(st.session_state["conversation_turns"])
    else:
        st.warning("発言を入力してください。")
