import json
import os
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio

# 复用你原有音乐扫描函数
from utils.music_utils import scan_music_dir
from utils.path_tool import get_abs_path

app = FastAPI(title="音乐播放推送后端")

# 跨域放行
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: Set[WebSocket] = set()

class PlayMessage(BaseModel):
    action: str
    song_path: str = ""
    song_name: str = ""
    msg: str = ""

# 修复WS阻塞：不再死等前端发消息，循环sleep保活
@app.websocket("/ws/music")
async def websocket_music(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        active_connections.discard(websocket)
    except Exception:
        active_connections.discard(websocket)

async def broadcast_message(msg: PlayMessage):
    data = json.dumps(msg.model_dump(), ensure_ascii=False)
    conn_list = list(active_connections)
    for conn in conn_list:
        try:
            await conn.send_text(data)
        except Exception:
            active_connections.discard(conn)

# ========== 新增关键音频流接口，解决404 ==========
@app.get("/api/music_stream")
async def stream_music_file(path: str = Query(...)):
    if not os.path.exists(path):
        return {"status":"fail","msg":"文件不存在"}
    return FileResponse(path, media_type="audio/mpeg")

# 播放指定歌曲
@app.post("/api/play_song_by_path")
async def play_song_by_path(song_path: str = Query(...)):
    if not os.path.exists(song_path):
        return {"status": "fail", "msg": f"文件路径不存在：{song_path}"}
    song_name = os.path.basename(song_path)
    await broadcast_message(PlayMessage(
        action="play",
        song_path=song_path,
        song_name=song_name,
        msg=f"开始播放：{song_name}"
    ))
    return {
        "status": "success",
        "msg": f"已向{len(active_connections)}个前端推送播放指令",
        "song_name": song_name,
        "song_path": song_path
    }

# 全局停止
@app.post("/api/stop")
async def stop_music():
    await broadcast_message(PlayMessage(action="stop", msg="全局停止所有音乐"))
    return {
        "status": "success",
        "msg": f"停止指令已推送至{len(active_connections)}个前端"
    }

# 播放第一首
@app.post("/api/start")
async def start_first_music():
    music_full = scan_music_dir(get_abs_path("music"))
    if not music_full:
        return {"status": "fail", "msg": "音乐库无歌曲"}
    first_song = music_full[0]
    path = first_song["path"]
    name = first_song["name"]
    await broadcast_message(PlayMessage(
        action="play",
        song_path=path,
        song_name=name,
        msg=f"启动默认曲目：{name}"
    ))
    return {
        "status": "success",
        "msg": f"默认曲目推送至{len(active_connections)}前端",
        "song_name": name,
        "song_path": path
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)