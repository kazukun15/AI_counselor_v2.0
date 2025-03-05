import streamlit as st
import os
import requests
from PIL import Image
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor

# ---------------------------
# グローバル設定
# ---------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 指定されたモデル名

# ---------------------------
# Streamlitページ設定
# ---------------------------
st.set_page_config(page_title="メンタルヘルスボット", layout="wide")

# ---------------------------
# カスタムCSS（若草色を基調に癒しの色合いを設定）
# ---------------------------
st.markdown(
    """
    <style>
    /* 全体の背景色（若草色ベース） */
    .main { background-color: #d8e6d2; }
    /* サイドバーの背景色（若草色を少し薄め） */
    .sidebar .sidebar-content { background-color: #e5f2e5; }
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
    .character-icon { border-radius: 50%; width: 60px; height: 60px; object-fit: cover; }
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
        "role_description": "専門知識に基づき、現状の症状や悩みを整理し、改善のための具体的なアドバイスを提示します。"
    },
    "心理カウンセラー": {
        "image": "avatars/counselor.png",
        "role_description": "利用者の心情に寄り添い、安心感を与えながら、対話を通じたサポートを行います。"
    },
    "メンタリスト": {
        "image": "avatars/MENTALIST.png",
        "role_description": "独自の視点と経験から、柔軟な発想で問題解決のヒントや新たな視点を提供します。"
    },
    "内科医": {
        "image": "avatars/doctor.png",
        "role_description": "精神面だけでなく、身体的な不調にも着目し、総合的な健康状態の改善策を示します。"
    }
}

# ---------------------------
# サイドバー：相談フォーム
# ---------------------------
with st.sidebar.form(key="consultation_form"):
    st.markdown("### 相談フォーム")
    form_problem = st.selectbox("現在の悩み", ["仕事のストレス", "人間関係", "家族の問題", "金銭問題", "その他"])
    form_physical = st.selectbox("体調", ["良好", "普通", "やや不調", "不調"])
    form_mental = st.selectbox("心理的健康", ["安定", "やや不安定", "不安定", "かなり不安定"])
    form_stress = st.selectbox("ストレス度", ["低い", "普通", "高い", "非常に高い"])
    form_submitted = st.form_submit_button(label="送信")

if form_submitted:
    st.session_state["form_data"] = {
        "problem": form_problem,
        "physical": form_physical,
        "mental": form_mental,
        "stress": form_stress
    }
    st.success("相談フォームの内容が反映されました。")

# ---------------------------
# 会話履歴の管理
# ---------------------------
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

# ---------------------------
# Gemini API 呼び出し用関数
# ---------------------------
def call_gemini_api(prompt_text: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            gemini_output = data.get("candidates", [])
            if gemini_output and len(gemini_output) > 0:
                parts = gemini_output[0].get("content", {}).get("parts", [])
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
    prompt = (
        f"あなたは{character_name}です。役割は「{role_desc}」です。\n"
        "以下の利用者の相談内容に対して、具体的なアドバイスや改善策を提示してください。\n"
        "医療行為は行わず、あくまで情報提供の範囲で正確な知見に基づいた回答をお願いします。\n"
        "回答は日本語で簡潔に述べ、利用者に安心感や前向きな提案が伝わるようにしてください。\n\n"
        f"【利用者の相談】\n{user_input}\n"
    )
    return prompt

# ---------------------------
# マルチスレッドで4キャラクターの応答を取得
# ---------------------------
def get_all_responses(user_input: str):
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_dict = {}
        for char_name, char_info in characters.items():
            prompt = build_prompt(user_input, char_name, char_info["role_description"])
            future_dict[char_name] = executor.submit(call_gemini_api, prompt)
        for char_name, future in future_dict.items():
            results[char_name] = future.result()
    return results

# ---------------------------
# チャット入力（日本語固定）
# ---------------------------
user_input = st.chat_input("ここにメッセージを入力してください...")
if user_input:
    responses = get_all_responses(user_input)
    st.session_state["conversation"].append({
        "user": user_input,
        "responses": responses
    })

# ---------------------------
# チャット履歴の表示（タブ形式）
# ---------------------------
for turn in st.session_state["conversation"]:
    st.markdown(f"<div class='bubble user-bubble'>{turn['user']}</div><br><br>", unsafe_allow_html=True)
    tabs = st.tabs(list(characters.keys()))
    for idx, char_name in enumerate(characters.keys()):
        with tabs[idx]:
            image_path = characters[char_name]["image"]
            if os.path.exists(image_path):
                char_img = Image.open(image_path)
                st.image(char_img, width=60)
            st.markdown(f"**{char_name}**")
            st.markdown(f"<div class='bubble character-bubble'>{turn['responses'][char_name]}</div>", unsafe_allow_html=True)
    st.write("---")

# ---------------------------
# レポート生成関数
# ---------------------------
def generate_report():
    form_data = st.session_state.get("form_data", {
        "problem": "未入力",
        "physical": "未入力",
        "mental": "未入力",
        "stress": "未入力"
    })
    conversation_text = ""
    for turn in st.session_state["conversation"]:
        conversation_text += f"【利用者】 {turn['user']}\n"
        for char_name, response in turn["responses"].items():
            conversation_text += f"【{char_name}】 {response}\n"
        conversation_text += "\n"
    report = f"""
# レポート

## 現状の把握
- **現在の悩み:** {form_data['problem']}
- **体調:** {form_data['physical']}
- **心理的健康:** {form_data['mental']}
- **ストレス度:** {form_data['stress']}

## 会話内容
{conversation_text}

## 具体的な対策案
(ここに各専門家の回答を踏まえた改善策やアドバイスをまとめる)

## 今後の対策・展望
(将来的なサポートや目標などを記載)

## 所見
(全体を通した所見や補足事項)
"""
    return report

# ---------------------------
# PDF生成 (日本語フォント対応)
# ---------------------------
def create_pdf(report_text: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    # fontsフォルダに NotoSansJP-VariableFont_wght.ttf がある前提
    pdf.add_font("NotoSansJP", "", "fonts/NotoSansJP-VariableFont_wght.ttf", uni=True)
    pdf.set_font("NotoSansJP", "", 12)
    for line in report_text.split("\n"):
        pdf.cell(0, 7, txt=line, ln=True)
    # FPDF.output(dest="S") が bytearray を返す場合は、明示的に bytes() に変換
    pdf_data = pdf.output(dest="S")
    return bytes(pdf_data)

# ---------------------------
# サイドバーに「レポートを出力」ボタンのみ配置
# ---------------------------
if st.sidebar.button("レポートを出力"):
    report_text = generate_report()
    pdf_data = create_pdf(report_text)
    st.sidebar.download_button(
        label="PDFをダウンロード",
        data=pdf_data,
        file_name="report.pdf",
        mime="application/pdf"
    )

st.markdown("---")
st.markdown("**注意:** このアプリは情報提供を目的としており、医療行為を行うものではありません。")
st.markdown("緊急の場合や深刻な症状がある場合は、必ず医師などの専門家に直接ご相談ください。")
