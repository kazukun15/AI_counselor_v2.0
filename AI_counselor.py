import streamlit as st
import os
import requests
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

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
        max-width: 90%;
        line-height: 1.4;
        word-wrap: break-word;
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
        width: 60px;
        height: 60px;
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
# 4人のキャラクター設定
# ---------------------------
characters = {
    "精神科医": {
        "image": "avatars/Psychiatrist.png",
        "role_description": "専門知識をもとに改善案を提示する"
    },
    "心理カウンセラー": {
        "image": "avatars/counselor.png",
        "role_description": "専門知識を元に心に寄り添う"
    },
    "メンタリスト": {
        "image": "avatars/MENTALIST.png",
        "role_description": "メンタリストの経験をもとに新たな発想で改善案を提示する"
    },
    "内科医": {
        "image": "avatars/doctor.png",
        "role_description": "精神以外の内科的な不調を探り、改善案を提示する"
    }
}

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
# 会話履歴の管理（統一した形式）
# ---------------------------
# 各ターンは {"user": ユーザ入力, "responses": {各キャラクターの回答}} の形式で保存
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

# ---------------------------
# Gemini API呼び出し用関数
# ---------------------------
def call_gemini_api(prompt_text: str) -> str:
    """
    Gemini API (Google Generative Language API) を呼び出して日本語での回答を取得します。
    Secretsファイルの [general] セクションから api_key を取得します。
    """
    api_key = st.secrets["general"]["api_key"]
    # エンドポイントはモデル名 "gemini-2.0-flash" を利用
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text}
            ]
        }]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        # デバッグ用：レスポンスのステータスコードとJSONを表示
        st.write("DEBUG: Gemini API response status:", response.status_code)
        try:
            st.write("DEBUG: Gemini API response JSON:", response.json())
        except:
            st.write("DEBUG: Could not parse JSON from response.")

        if response.status_code == 200:
            data = response.json()
            gemini_output = data.get("contents", [])
            if gemini_output and len(gemini_output) > 0:
                parts = gemini_output[0].get("parts", [])
                if parts and len(parts) > 0:
                    return parts[0].get("text", "回答を取得できませんでした。")
            return "回答を取得できませんでした。"
        else:
            return f"APIエラー（ステータスコード: {response.status_code}）"
    except Exception as e:
        return f"API呼び出しエラー: {str(e)}"

# ---------------------------
# 応答生成用のプロンプト関数
# ---------------------------
def build_prompt(user_input: str, character_name: str, role_desc: str) -> str:
    """
    各キャラクター向けのプロンプト文字列を生成
    """
    return (
        f"あなたは{character_name}です。役割は「{role_desc}」です。\n"
        "ユーザの悩みに寄り添い、専門的な視点から助言を行います。\n"
        "ただし、医療行為ではなく、あくまで情報提供のみを行い、正確性を重視してください。\n"
        "日本語で答えてください。\n\n"
        f"【ユーザのメッセージ】\n{user_input}\n"
    )

# ---------------------------
# マルチスレッドで4キャラクターの応答を取得
# ---------------------------
def get_all_responses(user_input: str):
    """
    4キャラの回答を並列に取得して返す。
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_dict = {}
        for char_name, char_info in characters.items():
            prompt = build_prompt(user_input, char_name, char_info["role_description"])
            future_dict[char_name] = executor.submit(call_gemini_api, prompt)

        results = {}
        for char_name, future in future_dict.items():
            results[char_name] = future.result()
        return results

# ---------------------------
# チャット入力（日本語固定）
# ---------------------------
user_input = st.chat_input("ここにメッセージを入力してください...")
if user_input:
    # 並列実行で4人分の回答をまとめて取得
    responses = get_all_responses(user_input)

    # 統一した形式で会話履歴に追加
    st.session_state["conversation"].append({
        "user": user_input,
        "responses": responses
    })

# ---------------------------
# チャット履歴の表示
# ---------------------------
for turn in st.session_state["conversation"]:
    # ユーザの発言（右寄せ）
    st.markdown(
        f"<div class='bubble user-bubble'>{turn['user']}</div><br><br>",
        unsafe_allow_html=True
    )
    # 4人の回答を横並びに表示
    cols = st.columns(4)
    i = 0
    for char_name in characters:
        with cols[i]:
            # キャラクター画像の表示
            image_path = characters[char_name]["image"]
            if os.path.exists(image_path):
                char_img = Image.open(image_path)
                st.image(char_img, width=60)
            st.markdown(f"**{char_name}**")
            st.markdown(
                f"<div class='bubble character-bubble'>{turn['responses'][char_name]}</div>",
                unsafe_allow_html=True
            )
        i += 1
    st.write("---")

# ---------------------------
# レポート作成ボタン（サイドバー）
# ---------------------------
if st.sidebar.button("レポートを作成する"):
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
