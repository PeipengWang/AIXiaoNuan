

from agent.react_agent import ReactAgent
import streamlit as st

# 🔥 直接导入你写的语音函数
from mcp.ttl_paly import speak_sentences_stream

# 页面标题
st.title("AI心理陪伴系统")
st.divider()

# 初始化会话
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

# 渲染历史消息
for msg in st.session_state["message"]:
    st.chat_message(msg["role"]).write(msg["content"])

# 用户输入
prompt = st.chat_input("请输入你的问题...")

if prompt:
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []

    with st.spinner("思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        # 捕获流式内容
        def capture(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                # =======================
                # 🔥 核心：来一块，播一块
                # =======================
                speak_sentences_stream(chunk)
                yield chunk

        # 前端流式打字
        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

        # =======================
        # 🔥 结束后强制播放剩余句子
        # =======================
        speak_sentences_stream("", flush=True)

        # 拼接完整回答
        full_answer = "".join(response_messages)

        # 保存到历史
        st.session_state["message"].append({
            "role": "assistant",
            "content": full_answer
        })

    st.rerun()