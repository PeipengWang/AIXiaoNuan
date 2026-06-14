import requests

# 地址对应你的云服务器/本地ASR服务
ASR_API_URL = "http://152.136.246.11:9001/asr"

def asr_from_bytes(audio_binary):
    """接收st.audio_input读取的二进制，POST上传识别"""
    try:
        # 表单上传文件，wav格式
        upload_file = {
            "file": ("voice.wav", audio_binary, "audio/wav")
        }
        res = requests.post(ASR_API_URL, files=upload_file, timeout=25)
        data = res.json()
        # 取出识别文本
        return data.get("text", "无识别内容")
    except Exception as err:
        return f"识别失败：{str(err)}"