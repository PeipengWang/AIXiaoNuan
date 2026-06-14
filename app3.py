from agent.react_agent import ReactAgent
import streamlit as st
from mcp.ttl_paly import speak_final_text
# 标题
st.title("AI心理陪伴系统")
st.divider()

# 初始化 session_state
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

# 1. 渲染历史消息
for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 2. 用户输入
prompt = st.chat_input()

if prompt:
    # 2.1 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 2.2 准备收集完整回复的列表
    response_messages = []

    # 2.3 显示思考动画，并调用 Agent
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt)

        # 2.4 定义捕获器：既给前端显示，又收集到列表
        def capture(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)  # 收集到列表
                yield chunk  # 同时流式显示


        # 2.5 显示流式消息，并将完整内容收集到 response_messages
        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

        # # 2.6 【关键修正】拼接完整回复，并存入历史
        # # 注意：这里不能用 response_messages[-1]，要用 join 拼接所有 chunk
        # full_response = "".join(response_messages)

        st.session_state["message"].append({
            "role": "assistant",
            "content": response_messages[-1]
        })
        speak_final_text(response_messages[-1])
        # 2.7 强制重绘页面（确保最新的消息显示出来）
        st.rerun()

