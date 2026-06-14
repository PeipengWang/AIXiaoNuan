import time

from agent.react_agent import ReactAgent
import streamlit as st
from mcp.ttl_paly import _play_audio
from mcp.asr_get import asr_from_bytes
import uuid

# ===========================
# 页面配置（更现代）
# ===========================
st.set_page_config(
    page_title="AI心理陪伴",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================
# 🔥 全局样式美化（灵动UI）
# ===========================
st.markdown("""
<style>
/* 主背景 */
.main {
    background: linear-gradient(135deg, #fdfbfb 0%, #eef6fc 100%);
}

/* 标题 */
h1 {
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 10px;
}

/* 消息气泡 */
.stChatMessage {
    border-radius: 18px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

/* 用户消息 */
.stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #e1f5fe;
}

/* AI 消息 */
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: #f6f8fa;
}

/* 输入框 */
.stChatInput {
    border-radius: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

/* 侧边栏 */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #eee;
}

/* 按钮 */
.stButton button {
    border-radius: 10px;
    background: #4a90e2;
    color: white;
    border: none;
    transition: all 0.2s;
}
.stButton button:hover {
    background: #357abd;
    transform: translateY(-1px);
}

/* 输入框 */
.stTextInput input {
    border-radius: 10px;
}

/* 选择框 */
.stSelectbox {
    border-radius: 10px;
}

/* 平滑滚动 */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-thumb {
    background: #ddd;
    border-radius: 3px;
}
# /* 麦克风按钮容器 */
# div[data-testid="stAudioInput"] {
#     display: flex;
#     align-items: center;
#     justify-content: center;
#     height: 44px !important;
#     width: 44px !important;
#     border-radius: 50% !important;
#     background: #e8f0fe !important;
#     box-shadow: 0 2px 6px rgba(0,0,0,0.08);
#     padding: 0 !important;
#     cursor: pointer;
# }
""", unsafe_allow_html=True)

# ===========================
# 标题区域（更精致）
# ===========================
st.title("💖 小暖心事屋")
st.caption("🌿 温柔陪伴 | 安心倾诉 | 永久记忆")
st.divider()

# ===========================
# 会话管理（不变）
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
    st.markdown("<div style='height:1px;background:#eee;margin:10px 0'></div>", unsafe_allow_html=True)

    # 1. 新建会话
    new_session = st.text_input("新建会话名称")
    if st.button("➕ 创建会话") and new_session:
        if new_session not in st.session_state.sessions:
            st.session_state.sessions[new_session] = str(uuid.uuid4())
            st.session_state.current_session_name = new_session
            st.rerun()

    st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)

    # 2. 切换会话
    session_names = list(st.session_state.sessions.keys())
    selected = st.selectbox(
        "切换会话",
        session_names,
        index=session_names.index(st.session_state.current_session_name)
    )
    st.session_state.current_session_name = selected

    st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)

    # 3. 重命名当前会话
    rename = st.text_input("重命名当前会话")
    if st.button("✏️ 重命名") and rename and rename != selected:
        th_id = st.session_state.sessions[selected]
        del st.session_state.sessions[selected]
        st.session_state.sessions[rename] = th_id
        st.session_state.current_session_name = rename
        st.rerun()

    st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)

    # 4. 当前会话 ID
    current_thread_id = st.session_state.sessions[st.session_state.current_session_name]
    st.caption(f"✅ 当前会话：{current_thread_id[:8]}...")

# ===========================
# 消息历史（不变）
# ===========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = ReactAgent()

# 渲染消息
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

voice_input_text = None

# ===========================
# 聊天逻辑（完全不变）
# ===========================

# 语音录音模块
# st.markdown("### 🎤 语音输入")
# audio_rec = st.audio_input("点击麦克风录制语音消息", key="voice_rec")

# ===========================
# 🎤 原生麦克风 + 输入框 同行布局
# ===========================
col1, col2 = st.columns([8, 2], vertical_alignment="bottom")

# with col1:
text_prompt = st.chat_input("输入消息...")

# with col2:
audio_rec = st.audio_input(
    label="🎤",
    key="voice",
    label_visibility="hidden",
    width=50,
)
#     # 原生麦克风（右侧）

# with col1:

# 检测到录音文件
if audio_rec:
    with st.spinner("小暖正在听你说话，转文字中..."):
        # 读取二进制流
        audio_byte_data = audio_rec.read()
        # 调用你的ASR服务
        voice_input_text = asr_from_bytes(audio_byte_data)
    st.success(f"识别内容：{voice_input_text}")

# 优先级：语音识别文字 > 手动打字
# 2. 如果语音有内容 → 用语音；没有 → 为空
prompt = voice_input_text if voice_input_text else None
voice_input_text = None
# 3. 如果用户打字了 → 覆盖使用文字
if text_prompt:
    prompt = text_prompt
    text_prompt = None

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