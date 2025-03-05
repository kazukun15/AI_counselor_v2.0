import streamlit as st

st.set_page_config(page_title="テスト", layout="wide")
st.title("シンプルなチャット入力テスト")

st.markdown("""
<style>
.fixed-input {
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #FFF;
    padding: 10px;
    box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
    z-index: 100;
}
</style>
""", unsafe_allow_html=True)

# 下部に固定したフォーム
st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area(
        "メッセージ入力", 
        placeholder="ここに入力", 
        height=50, 
        key="unique_user_message_input"  # 他とかぶらない名前にする
    )
    submitted = st.form_submit_button("送信")
st.markdown("</div>", unsafe_allow_html=True)

if submitted:
    if user_message.strip():
        st.success(f"送信されたメッセージ: {user_message}")
    else:
        st.warning("メッセージが空です。")
