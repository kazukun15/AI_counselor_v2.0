import streamlit as st
import os
import requests
from PIL import Image

# ---------------------------
# Streamlitページ設定
# ---------------------------
st.set_page_config(
    page_title="メンタルヘルスボット",
    layout="wide"
)

# ---------------------------
# カスタムCSS（若草色を基調に癒しの色合いを設定）
# ---------------------------
st.markdown(
    """
    <style>
    /* 全体の背景色（若草色ベース） */
    .main {
        background-color: #d8e6d2;
    }
    /* サイドバーの背景色（若草色を少し薄め） */
    .sidebar .sidebar-content {
        background-color: #e5f2e5;
    }
    /* チャット吹き出しの共通スタイル */
    .bubble {
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        display: inline-block;
        max-width: 70%;
        line-height: 1.4;
    }
    /* ユーザの吹き出し（右寄せ、淡い緑系） */
    .user-bubble {
        background-color: #dcf8c6;
        text-align: right;
        float: right;
        clear: both;
    }
    /* キャラクターの吹き出し（左寄せ、白ベース） */
    .character-bubble {
        background-color: #ffffff;
        text-align: left;
        float: left;
        clear: both;
    }
    /* キャラクターアイコンを円形に */
    .character-icon {
        border-radius: 50%;
        width: 80px;
        height: 80px;
        object-fit: cover;
    }
    /* タイトルなどの中央寄せ */
    .center {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# タイトル表示
# ---------------------------
st.title("メンタルヘルスボット")

# ---------------------------
# キャラクター設定
# ---------------------------
characters = {
    "精神科医": {
        "image": "avatars/Psychiatrist.png",
        "role": "専門知識をもとに改善案を提示する"
    },
    "心理カウンセラー": {
        "image": "avatars/counselor.png",
        "role": "専門知識を元に心に寄り添う"
    },
    "メンタリスト": {
        "image": "avatars/MENTALIST.png",
        "role": "メンタリストの経験をもとに新たな発想により改善案を提示する"
    },
    "内科医": {
        "image": "avatars/doctor.png",
        "role": "精神的なもの以外の内科的な不調を調書から探し、改善案を提示する"
    }
}

# ---------------------------
# サイドバー：担当キャラクター選択
# ---------------------------
st.sidebar.header("担当キャラクター")
selected_character = st.sidebar.selectbox(
    "どの専門家と話しますか？",
    list(characters.keys())
)

char_data = characters[selected_character]
char_image_path = char_data["image"]
char_role_description = char_data["role"]

# ---------------------------
# サイドバー：選択式相談フォーム
# ---------------------------
st.sidebar.header("相談フォーム（選択式）")

problem = st.sidebar.selectbox(
    "現在の悩み",
    ["仕事のストレス", "人間関係", "家族の問題", "金銭問題", "その他"]
)

physical_condition = st.sidebar.selectbox(
    "体調",
    ["良好", "普通", "やや不調", "不調"]
)

mental_health = st.sidebar.selectbox(
    "心理的健康",
    ["安定", "やや不安定", "不安定", "かなり不安定"]
)

stress_level = st.sidebar.selectbox(
    "ストレス度",
    ["低い", "普通", "高い", "非常に高い"]
)

# ---------------------------
# 会話履歴の管理
# ---------------------------
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

# ---------------------------
# キャラクター表示と役割
# ---------------------------
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists(char_image_path):
        char_img = Image.open(char_image_path)
        st.image(char_img, use_column_width=False, width=80, caption=selected_character)
with col2:
    st.markdown(f"**{selected_character}**：{char_role_description}")

st.markdown("---")

# ---------------------------
# Gemini API呼び出し用関数
# ---------------------------
def call_gemini_api(prompt_text: str) -> str:
    """
    Gemini API (Google Generative Language API) を呼び出して日本語での回答を取得する。
    ハルシネーションを完全に防ぐことは困難だが、エラー処理を行うことで安全に失敗できるようにする。
    """
    try:
        # StreamlitのSecretsからAPIキーを取得
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        # APIキーが設定されていない場合
        return "APIキーが設定されていません。"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # Gemini API用のリクエストボディ
    payload = {
        "contents": [{
            "parts": [
                {
                    # 日本語で会話を続けるためのプロンプト
                    "text": prompt_text
                }
            ]
        }]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # レスポンス構造から回答を取り出す
            # 例: data["contents"][0]["parts"][0]["text"] に回答が入る想定
            gemini_output = data.get("contents", [])
            if gemini_output and len(gemini_output) > 0:
                parts = gemini_output[0].get("parts", [])
                if parts and len(parts) > 0:
                    return parts[0].get("text", "回答を取得できませんでした。")
            return "回答を取得できませんでした。"
        else:
            return f"APIエラーが発生しました（ステータスコード: {response.status_code}）"
    except Exception as e:
        return f"API呼び出し中にエラーが発生しました: {str(e)}"

# ---------------------------
# 応答生成関数
# ---------------------------
def generate_response(user_input: str, role: str) -> str:
    """
    ユーザ入力とキャラクターの役割を踏まえ、Gemini APIを使って日本語の回答を生成。
    """
    # キャラクター名を踏まえて簡単な指示を付与しつつ、ユーザの日本語入力を渡す例
    # 実際にはプロンプトデザインを工夫し、ハルシネーションを減らす。
    system_prompt = (
        f"あなたは{role}として、ユーザの悩みに寄り添い、専門的な視点から助言を行います。"
        "ただし、医療行為ではなく、あくまで情報提供のみを行い、正確性を重視してください。"
        "日本語で答えてください。"
    )

    # 実際のAPI呼び出し用プロンプト
    # 例として「system的指示 + ユーザのメッセージ」を結合
    # Gemini APIは会話文脈を保持するため、より高度な構成にする場合は複数ターンの履歴をまとめて渡す。
    prompt_for_api = system_prompt + "\nユーザの質問: " + user_input

    # Gemini API呼び出し
    response_text = call_gemini_api(prompt_for_api)
    return response_text

# ---------------------------
# チャット入力
# ---------------------------
user_input = st.chat_input("ここにメッセージを入力してください...")
if user_input:
    # ユーザのメッセージを会話履歴に追加
    st.session_state["conversation"].append({
        "role": "user",
        "content": user_input
    })
    # キャラクターからの返信生成
    reply_text = generate_response(user_input, selected_character)
    st.session_state["conversation"].append({
        "role": selected_character,
        "content": reply_text
    })

# ---------------------------
# チャット履歴の表示
# ---------------------------
for message in st.session_state["conversation"]:
    if message["role"] == "user":
        # ユーザの吹き出し（右寄せ）
        st.markdown(
            f"<div class='bubble user-bubble'>{message['content']}</div><br><br>",
            unsafe_allow_html=True
        )
    else:
        # キャラクターの吹き出し（左寄せ）
        st.markdown(
            f"<div class='bubble character-bubble'>{message['content']}</div><br><br>",
            unsafe_allow_html=True
        )

# ---------------------------
# レポート作成ボタン（サイドバー）
# ---------------------------
if st.sidebar.button("レポートを作成する"):
    """
    会話全体やフォーム入力内容をまとめたレポートをMarkdown形式で表示。
    """
    known_info = f"- 現在の悩み: {problem}\n- 体調: {physical_condition}\n- 心理的健康: {mental_health}\n- ストレス度: {stress_level}"
    current_issues = "会話の中で感じた主な悩みを整理します。"
    improvements = "専門的な視点から提案できる具体的な改善案を記載します。"
    future_outlook = "将来的にどのようなサポートが考えられるかを展望します。"
    remarks = "全体を通しての所見や補足事項など。"

    report_md = f"""
## レポート

### わかっていること
{known_info}

### 現在の悩み
{current_issues}

### 具体的な改善案
{improvements}

### 将来的な展望
{future_outlook}

### 所見
{remarks}
    """
    st.sidebar.markdown(report_md)

# ---------------------------
# 注意書き・免責事項
# ---------------------------
st.markdown("---")
st.markdown("**注意:** このアプリは情報提供を目的としており、医療行為を行うものではありません。")
st.markdown("緊急の場合や深刻な症状がある場合は、必ず医師などの専門家に直接ご相談ください。")
