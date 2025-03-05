import streamlit as st
import os
from PIL import Image

# Streamlitのページ基本設定
st.set_page_config(
    page_title="メンタルヘルスボット",
    layout="wide"
)

# ------------------------------------
# カスタムCSS（若草色を基調に癒しの色合いを設定）
# ------------------------------------
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

# タイトル表示
st.title("メンタルヘルスボット")

# ------------------------------------
# キャラクター設定
# ------------------------------------
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

# ------------------------------------
# サイドバー：担当キャラクター選択
# ------------------------------------
st.sidebar.header("担当キャラクター")
selected_character = st.sidebar.selectbox(
    "どの専門家と話しますか？",
    list(characters.keys())
)

# 選択されたキャラクター情報を取得
char_data = characters[selected_character]
char_image_path = char_data["image"]
char_role_description = char_data["role"]

# ------------------------------------
# サイドバー：選択式相談フォーム
# ------------------------------------
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

# ------------------------------------
# 会話履歴の管理
# ------------------------------------
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

# ------------------------------------
# キャラクター表示と役割
# ------------------------------------
# 上部にキャラクターアイコンと説明を表示
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists(char_image_path):
        char_img = Image.open(char_image_path)
        st.image(char_img, use_column_width=False, width=80, caption=selected_character)
with col2:
    st.markdown(f"**{selected_character}**：{char_role_description}")

st.markdown("---")

# ------------------------------------
# レスポンス生成（簡易的な例）
# ------------------------------------
def generate_response(user_input: str, role: str) -> str:
    """
    ※ 本番では専門家の知見やLLMを適切に利用する。
      （ここではハルシネーション回避のため、あえて簡易な固定応答にとどめる）
    """
    response_text = (
        f"あなたのメッセージ：「{user_input}」\n\n"
        f"{role}からのアドバイス：\n"
        "まずは少しずつ、どのような状況なのかを整理していきましょう。\n"
        "気になることや不安な点があれば、遠慮なくお話しください。"
    )
    return response_text

# ------------------------------------
# チャット入力（LINE風）
# ------------------------------------
user_input = st.chat_input("Enter your message here...")
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

# ------------------------------------
# チャット履歴の表示
# ------------------------------------
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

# ------------------------------------
# レポート作成ボタン（サイドバー）
# ------------------------------------
if st.sidebar.button("レポートを作成する"):
    """
    会話全体から得られた情報をまとめる。
    実際にはNLPやデータ解析で内容を要約しても良い。
    """
    # 例として固定文面でまとめ
    known_info = f"- 現在の悩み: {problem}\n- 体調: {physical_condition}\n- 心理的健康: {mental_health}\n- ストレス度: {stress_level}"
    current_issues = "会話の中で感じた主な悩みを整理します。"
    improvements = "専門的な視点から提案できる具体的な改善案を記載します。"
    future_outlook = "将来的にどのようなサポートが考えられるかを展望します。"
    remarks = "全体を通しての所見や補足事項など。"

    # 実際は、会話内容（st.session_state["conversation"]）を分析し要約して追記するとよい
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

# ------------------------------------
# 注意書き・免責事項
# ------------------------------------
st.markdown("---")
st.markdown("**注意:** このアプリは情報提供を目的としており、医療行為を行うものではありません。")
st.markdown("緊急の場合や深刻な症状がある場合は、必ず医師などの専門家に直接ご相談ください。")

