import time

from agent.react_agent import ReactAgent
import streamlit as st
from mcp.ttl_paly import _play_audio
import uuid

st.set_page_config(page_title="AI心理陪伴", page_icon="💖")
st.title("AI心理陪伴系统")

# ===========================
# 🔥 会话管理（核心）
# ===========================
if "sessions" not in st.session_state:
    st.session_state.sessions = {
        "默认对话": "default_user"
    }

if "current_session_name" not in st.session_state:
    st.session_state.current_session_name = "默认对话"

# 侧边栏：会话管理
with st.sidebar:
    st.subheader("💬 会话管理")

    # 1. 新建会话
    new_session = st.text_input("新建会话名称")
    if st.button("➕ 创建会话") and new_session:
        if new_session not in st.session_state.sessions:
            st.session_state.sessions[new_session] = str(uuid.uuid4())
            st.session_state.current_session_name = new_session
            st.rerun()

    # 2. 切换会话
    session_names = list(st.session_state.sessions.keys())
    selected = st.selectbox("切换会话", session_names, index=session_names.index(st.session_state.current_session_name))
    st.session_state.current_session_name = selected

    # 3. 重命名当前会话
    rename = st.text_input("重命名当前会话")
    if st.button("✏️ 重命名") and rename and rename != selected:
        th_id = st.session_state.sessions[selected]
        del st.session_state.sessions[selected]
        st.session_state.sessions[rename] = th_id
        st.session_state.current_session_name = rename
        st.rerun()

    # 4. 当前会话 ID
    current_thread_id = st.session_state.sessions[st.session_state.current_session_name]
    st.caption(f"会话ID：{current_thread_id[:8]}...")

# ===========================
# 消息历史
# ===========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = ReactAgent()

# 渲染消息
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# ===========================
# 聊天逻辑
# ===========================
prompt = st.chat_input("输入消息...")

if prompt:
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    size = 0
    full_response = ""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("思考中..."):
            # 🔥 传入当前会话 ID
            for chunk in st.session_state.agent.execute_stream(
                prompt,
                thread_id=current_thread_id
            ):
                full_response += chunk
                size += len(chunk)
                last_response = chunk
                placeholder.markdown(last_response + "▌")
                time.sleep(3)
        placeholder.markdown(last_response)

    # 播放语音
    _play_audio(last_response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": last_response
    })
    time.sleep(2 * size / 8)
    st.rerun()