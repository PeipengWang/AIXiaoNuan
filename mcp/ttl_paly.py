import requests
import re

TTS_URL = "http://localhost:9000/tts-stream"


def clean_tts_text(text: str) -> str:
    """清洗文本，去掉 Markdown / 特殊符号"""
    if not text:
        return ""

    # 去掉加粗
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)

    # 去掉标题
    text = re.sub(r'#+\s?', '', text)

    # 去掉分割线
    text = re.sub(r'---+', '', text)

    # 去掉链接
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)

    # 去掉多余空格 / 换行
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def get_tts_audio_bytes(text: str) -> bytes | None:
    """
    调用 TTS 服务，返回音频二进制
    （供 FastAPI / 后端播放 / 转发）
    """
    text = clean_tts_text(text)
    if not text:
        return None

    try:
        url = f"{TTS_URL}?text={requests.utils.quote(text)}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return None


def play_tts_via_api(text: str) -> str:
    """
    仅返回 TTS 播放地址（供前端 Audio 使用）
    """
    text = clean_tts_text(text)
    if not text:
        return ""
    return f"{TTS_URL}?text={requests.utils.quote(text)}"