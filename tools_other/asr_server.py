import uuid
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

app = FastAPI(title="语音识别 ASR 服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# ✅ 模型初始化（只加载一次）
# ========================
MODEL_SIZE = "small"   # 推荐 small / medium
DEVICE = "cpu"         # 有显卡可改为 "cuda"
COMPUTE_TYPE = "int8"

model = WhisperModel(
    MODEL_SIZE,
    device=DEVICE,
    compute_type=COMPUTE_TYPE
)

# 临时目录
TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)


# ========================
# ✅ ASR 接口
# ========================
@app.post("/asr")
async def asr(file: UploadFile = File(...)):
    """
    语音识别接口
    - 支持 webm / wav / mp3
    - 返回中文识别文本
    """
    try:
        suffix = file.filename.split(".")[-1]
        file_id = uuid.uuid4().hex
        file_path = os.path.join(TMP_DIR, f"{file_id}.{suffix}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Whisper 推理
        segments, info = model.transcribe(
            file_path,
            language="zh",
            beam_size=5
        )

        text = "".join([segment.text for segment in segments]).strip()

        # 清理临时文件
        os.remove(file_path)

        return {
            "text": text,
            "language": info.language,
            "duration": info.duration
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# 启动命令
# uvicorn asr_server:app --host 0.0.0.0 --port 9001
# ========================