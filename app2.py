import streamlit as st
from agent.react_agent import ReactAgent

# ===================== 全局页面配置（必须放在最顶部）=====================
st.set_page_config(
    page_title="AI心理陪伴系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS美化样式
st.markdown("""
<style>
/* 整体页面背景 */
.main {
    background-color: #f8fafc;
}
/* 聊天气泡样式 */
.stChatMessage {
    border-radius: 14px !important;
    padding:8px 12px !important;
}
/* 输入框美化 */
.stChatInput > div {
    border-radius:20px !important;
}
/* 侧边栏样式 */
[data-testid="stSidebar"]{
    background-color:#eff6ff;
}
/* 分割线 */
hr{
    border:1px solid #cbd5e1;
}
</style>
""", unsafe_allow_html=True)

# ===================== 侧边栏配置区 =====================
with st.sidebar:
    st.header("🧩 系统设置")
    st.divider()
    st.subheader("关于本系统")
    st.markdown("""
    ✅ AI智能心理陪伴对话
    ✅ 内置心理学知识库查询
    ✅ 实时情绪识别分析
    ✅ 流式打字回复体验
    """)
    st.divider()
    # 清空聊天历史按钮
    if st.button("🗑️ 清空全部聊天记录", use_container_width=True, type="secondary"):
        st.session_state["message"] = []
        st.rerun()

# ===================== 主页面头部 =====================
col1, col2 = st.columns([5, 1])
with col1:
    st.title("🧠 AI心理陪伴系统")
    st.caption("温柔倾听 · 科学陪伴 · 舒缓情绪")
with col2:
    st.metric(label="当前对话条数", value=len(st.session_state.get("message", []))//2)

st.divider()

# ===================== 初始化会话变量 =====================
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

# ===================== 渲染历史聊天记录（区分头像） =====================
for message in st.session_state["message"]:
    avatar = "👤" if message["role"] == "user" else "🤖"
    st.chat_message(message["role"], avatar=avatar).write(message["content"])

# ===================== 用户聊天输入 =====================
prompt = st.chat_input("💬 在这里倾诉你的心情、疑问...")

if prompt:
    # 用户消息入历史+渲染
    st.chat_message("user", avatar="👤").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []

    # 流式数据捕获函数
    def capture(generator, cache_list):
        for chunk in generator:
            cache_list.append(chunk)
            yield chunk

    # AI回复流式输出
    with st.spinner("🤖 AI正在耐心思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)
        full_resp = st.chat_message("assistant", avatar="🤖").write_stream(capture(res_stream, response_messages))

    # 拼接完整回答存入历史
    full_content = "".join(response_messages)
    st.session_state["message"].append({"role": "assistant", "content": full_content})

    st.rerun()