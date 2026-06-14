import requests
import streamlit as st
import re
TTS_URL = "http://localhost:9000/tts-stream"

TTS_URL = "http://localhost:9000/tts-stream"
_sentence_buffer = ""

def speak_sentences_stream(text: str, min_len: int = 3, flush: bool = False):
    """
    句子级流式 TTS 播放（通用组件，有状态 buffer）
    :param text: 增量文本块
    :param min_len: 最小触发长度（防止碎句）
    :param flush: 是否强制清空 buffer（流式结束时调用）
    """
    global _sentence_buffer
    punctuation = {"。", "！", "？", ".", "!", "?"}

    # 如果是结束刷新，播放剩余内容
    if flush:
        if _sentence_buffer.strip():
            _play_audio(_sentence_buffer.strip())
        _sentence_buffer = ""
        return

    # 把新块加入缓存
    _sentence_buffer += text

    # ========================
    # ✅ 核心：循环切割句子（你原来缺失了这一段！）
    # ========================
    while True:
        punct_idx = -1
        # 查找第一个标点
        for i, char in enumerate(_sentence_buffer):
            if char in punctuation:
                punct_idx = i
                break

        # 没找到标点就退出
        if punct_idx == -1:
            break

        # 截取句子
        sentence = _sentence_buffer[:punct_idx + 1].strip()
        # 剩下的放回缓存
        _sentence_buffer = _sentence_buffer[punct_idx + 1:]
        # 达到最小长度才播放
        if len(sentence) >= min_len:
            _play_audio(sentence)


    # 超长无标点强制播放
    if len(_sentence_buffer) > 200:
        _play_audio(_sentence_buffer.strip())
        _sentence_buffer = ""


def _play_audio(text: str):
    text = clean_tts_text(text)
    if not text:
        return
    url = f"{TTS_URL}?text={requests.utils.quote(text)}"
    audio_html = f"""
    <audio autoplay style="display:none">
        <source src="{url}" type="audio/mpeg">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


# 🔥 清洗文本：去掉 Markdown 符号、特殊格式，只保留纯文字
def clean_tts_text(text: str) -> str:
    # 1. 去掉 ** **
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # 2. 去掉 * *
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # 3. 去掉 # 标题
    text = re.sub(r'#+\s?', '', text)
    # 4. 去掉 --- 分割线
    text = re.sub(r'---+', '', text)
    # 5. 去掉多余空格、换行
    text = re.sub(r'\s+', ' ', text)
    # 6. 去掉 [ ] ( ) 链接
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    return text.strip()

def render_tts_button(text: str, key: str):
    if st.button("🔊 播放语音", key=key):
        url = f"{TTS_URL}?text={requests.utils.quote(text)}"
        st.audio(url, format="audio/mpeg")

