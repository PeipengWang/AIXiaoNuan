import json
import sqlite3
import uuid
import re
import time
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite import SqliteSaver
from starlette.middleware.cors import CORSMiddleware
import requests
# ========== 对齐你原有项目依赖 & 模块导入（和Streamlit版本完全一致） ==========
from agent.react_agent import ReactAgent
from mcp.ttl_paly import clean_tts_text
from mcp.asr_get import asr_from_bytes
from fastapi import  WebSocket, WebSocketDisconnect
from typing import Dict

from utils.config_handler import rag_conf
# ===========================
# 服务实例初始化（和原Streamlit逻辑保持一致：全局单例Agent）
# ===========================
app = FastAPI(title="AI心理陪伴 API")

# 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== TTS / ASR 下游服务地址（保留原有配置） ==========
TTS_URL = rag_conf["TTS_URL"]
ASR_API_URL = rag_conf["ASR_API_URL"]

# ========== 全局会话 & 智能体（完全沿用你原会话结构） ==========
sessions: dict[str, str] = {"默认对话": "default_user"}
# 全局初始化Agent（只初始化一次，同Streamlit全局实例）
agent = ReactAgent()


# ===========================
# 文本清洗函数（用于TTS，沿用原有逻辑）
# ===========================
def clean_tts_text(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#+\s?', '', text)
    text = re.sub(r'---+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)

    # 新增：过滤所有emoji表情符号
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"
                               u"\U0001F300-\U0001F5FF"
                               u"\U0001F680-\U0001F6FF"
                               u"\U0001F1E0-\U0001F1FF"
                               u"\U00002700-\U000027BF"
                               u"\U0000FE00-\U0000FE0F"
                               u"\U0001F900-\U0001F9FF"
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    return text.strip()


# ===========================
# 会话管理接口（原有逻辑不变）
# ===========================
@app.get("/api/sessions")
async def list_sessions():
    return {
        "sessions": sessions,
        "current_count": len(sessions),
    }


@app.post("/api/sessions")
async def create_session(name: str = Form(...)):
    if name in sessions:
        return JSONResponse({"error": "会话名称已存在"}, status_code=400)
    sessions[name] = str(uuid.uuid4())
    return {"name": name, "thread_id": sessions[name]}


@app.put("/api/sessions/rename")
async def rename_session(old_name: str = Form(...), new_name: str = Form(...)):
    if old_name not in sessions:
        return JSONResponse({"error": "原会话不存在"}, status_code=404)
    if new_name in sessions:
        return JSONResponse({"error": "新名称已存在"}, status_code=400)
    thread_id = sessions.pop(old_name)
    sessions[new_name] = thread_id
    return {"name": new_name, "thread_id": thread_id}


# ===========================
# 聊天接口（对齐原Streamlit执行逻辑）
# ===========================
@app.post("/api/chat/send")
async def chat_send(request: Request):
    """普通接口：一次性返回完整回复"""
    body = await request.json()
    prompt = body.get("message", "")
    session_name = body.get("session_name", "默认对话")
    thread_id = sessions.get(session_name, "default_user")

    if not prompt:
        return JSONResponse({"error": "消息不能为空"}, status_code=400)

    full_response = ""
    # 沿用原有 agent.execute_stream 逻辑
    for chunk in agent.execute_stream(prompt, thread_id=thread_id):
        full_response += chunk
        time.sleep(0.05)  # 模拟原有流式间隔，对齐体验

    full_response = full_response.strip()
    return {"response": full_response, "thread_id": thread_id}


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """SSE 流式聊天接口，和前端流式展示对齐"""
    body = await request.json()
    prompt = body.get("message", "")
    session_name = body.get("session_name", "默认对话")
    thread_id = sessions.get(session_name, "default_user")

    if not prompt:
        return JSONResponse({"error": "消息不能为空"}, status_code=400)

    async def event_generator():
        last_chunk = ""
        try:
            # 遍历流式输出，和原逻辑一致
            for chunk in agent.execute_stream(prompt, thread_id=thread_id):
                last_chunk = chunk
                time.sleep(0.05)
            # 收尾：清洗文本用于TTS
            if last_chunk != "":
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            tts_text = clean_tts_text(last_chunk.strip())
            yield f"data: {json.dumps({'done': True, 'tts_text': tts_text, 'full_response': last_chunk}, ensure_ascii=False)}\n\n"

            # ========== 一轮问答完全结束，后置判断压缩:
            # 当前已完成基于SummarizationMiddleware进行摘要提问压缩，后续需要改成库原始压缩==========
            # current_step = get_current_step(checkpointer, thread_id)
            # if current_step >= STEP_TRIM_THRESHOLD:
            #     trim_round_chat(checkpointer, thread_id, chat_model)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
# ---------------------- 改造后的流式接口 ----------------------
# @app.post("/api/chat/stream")
# async def chat_stream(request: Request):
#     """SSE 流式聊天接口，和前端流式展示对齐"""
#     body = await request.json()
#     prompt = body.get("message", "")
#     session_name = body.get("session_name", "默认对话")
#     thread_id = sessions.get(session_name, "default_user")
#
#     if not prompt:
#         return JSONResponse({"error": "消息不能为空"}, status_code=400)
#
#     async def event_generator():
#         last_chunk = ""
#         try:
#             # 遍历流式输出，和原逻辑一致
#             for chunk in agent.execute_stream(prompt, thread_id=thread_id):
#                 last_chunk = chunk
#
#                 time.sleep(0.05)
#             yield f"data: {json.dumps({'chunk': last_chunk}, ensure_ascii=False)}\n\n"
#             # ========== 一轮问答完全结束，后置判断压缩 ==========
#             current_step = get_current_step(checkpointer, thread_id)
#             if current_step >= STEP_TRIM_THRESHOLD:
#                 trim_round_chat(checkpointer, thread_id, chat_model)
#             # ==================================================
#
#             # 收尾清洗文本用于TTS
#             tts_text = clean_tts_text(last_chunk.strip())
#             yield f"data: {json.dumps({'done': True, 'tts_text': tts_text, 'full_response': last_chunk}, ensure_ascii=False)}\n\n"
#         except Exception as e:
#             yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
#
#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no",
#         },
#     )
@app.get("/api/memory/list_threads")
async def memory_list_threads():
    try:
        conn = sqlite3.connect("resources/psychologist.db", check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT thread_id FROM checkpoints;")
        rows = cur.fetchall()
        conn.close()
        thread_list = [row[0] for row in rows if row[0]]
        return {"code":0, "threads": thread_list}
    except Exception as e:
        return {"code":-1, "msg": str(e)}

# 查看单个会话记忆详情
@app.get("/api/memory/detail")
async def memory_detail(thread_id: str):
    try:
        conn = sqlite3.connect("resources/psychologist.db", check_same_thread=False)
        saver = SqliteSaver(conn)
        cfg = {"configurable":{"thread_id":thread_id}}
        cp = saver.get(cfg)
        conn.close()
        return {"code":0, "checkpoint": cp}
    except Exception as e:
        return {"code":-1, "msg": str(e)}
# ===========================
# TTS 语音合成代理接口（不变）
# ===========================
# @app.get("/api/tts")
# async def proxy_tts(text: str):
#     text = clean_tts_text(text)
#     if not text:
#         raise HTTPException(status_code=400, detail="文本为空")
#
#     url = f"{TTS_URL}?text={requests.utils.quote(text)}"
#     try:
#         # 修正：httpx 异步响应使用 iter_content，而非 aiter_bytes
#         async with httpx.AsyncClient(timeout=45) as client:
#             r = await client.get(url)
#             r.raise_for_status()  # 捕获 4xx/5xx 状态码
#             return StreamingResponse(
#                 r.iter_content(chunk_size=4096),
#                 media_type="audio/mpeg",
#                 headers={"Accept-Ranges": "bytes"}
#             )
#     except httpx.ConnectError:
#         raise HTTPException(status_code=503, detail="TTS服务连接失败，请检查9000端口服务")
#     except httpx.TimeoutException:
#         raise HTTPException(status_code=504, detail="TTS请求超时")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"TTS服务异常：{str(e)}")


# ===========================
# ASR 语音转文字代理（重点对齐：复用你原有 asr_from_bytes 逻辑）
# ===========================
@app.post("/api/asr")
async def proxy_asr(file: UploadFile = File(...)):
    """
    复用原有 mcp.asr_get.asr_from_bytes 逻辑，
    同时保留代理转发能力，双兼容
    """
    try:
        audio_bytes = await file.read()
        # 方式1：优先使用你原有项目的 asr_from_bytes（和Streamlit完全一致）
        voice_text = asr_from_bytes(audio_bytes)
        if voice_text:
            return {"text": voice_text, "error": ""}

        # 方式2：原有代理转发兜底（防止本地函数异常）
        upload_file = {
            "file": (file.filename or "voice.wav", audio_bytes, file.content_type or "audio/wav")
        }
        res = requests.post(ASR_API_URL, files=upload_file, timeout=25)
        data = res.json()
        return {"text": data.get("text", "无识别内容"), "error": ""}

    except Exception as e:
        return {"text": "", "error": f"识别失败：{str(e)}"}


# ===========================
# 前端静态页面 & 静态资源挂载
# ===========================
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


# 音乐播放


connected_clients: Dict[str, WebSocket] = {}
playback_active = True


# 挂载静态目录
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass

# ===========================
# 服务入口（启动配置不变）
# ===========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
