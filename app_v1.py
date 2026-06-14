from agent.react_agent import ReactAgent
import streamlit as st
import time

# 导入你的语音函数
from mcp.ttl_paly import speak_sentences_stream, _play_audio

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
voice_text = ""
# 用户输入
prompt = st.chat_input("请输入你的问题...")

if prompt:
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    full_response = ""
    last_response = ""
    size = 0
    with st.chat_message("assistant"):
        placeholder = st.empty()

        with st.spinner("思考中..."):
            # 🔥 只在这里流式输出文字，不播放语音
            for chunk in st.session_state["agent"].execute_stream(prompt):
                full_response += chunk
                placeholder.markdown(full_response + "▌")
                size += len(chunk)
                last_response = chunk

        placeholder.markdown(full_response)

    # ==============================================
    # ✅ 【唯一播放点】只播放最终完整回答，绝对不乱播
    # ==============================================
    # speak_sentences_stream(full_response)
    voice_text = last_response
    # 保存对话
    st.session_state["message"].append({
        "role": "assistant",
        "content": last_response
    })
    # _play_audio(voice_text)
    time.sleep(2 * size / 8)
    st.rerun()
