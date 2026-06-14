import os

import requests

from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import json
from utils.music_utils import scan_music_dir
from utils.path_tool import get_abs_path
from utils.config_handler import rag_conf

MUSIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "music")
# 初始化 RAG 服务实例
rag = RagSummarizeService()

#注意放到配置文件
BACKEND_URL = rag_conf["MUSIC_URL"]
# 请求公共头
REQUEST_HEADERS = {
    "Content-Type": "application/json; charset=utf-8"
}



@tool
def query_music_library(keyword: str = "") -> str:
    """
    查询本地音乐库，可获取全部歌曲或按关键词筛选疗愈音乐
    Args:
        keyword: 搜索关键词，如"心灵疗愈""轻音乐"；为空则返回全部歌曲列表
    """
    res = get_music_library(keyword)
    return json.dumps(res, ensure_ascii=False, indent=2)


def get_music_library(keyword: str = "") -> dict:
    """
    供给心理Agent调用的音乐查询工具
    :param keyword: 空=返回全部歌单；有文字=模糊匹配文件名
    :return: 结构化字典，方便LLM解析
    """
    full_list = scan_music_dir(get_abs_path("music"))
    if not full_list:
        return {
            "code": 0,
            "msg": "音乐目录无可用音频文件",
            "song_list": []
        }
    # 关键词过滤
    if keyword.strip():
        filter_list = [s for s in full_list if keyword.strip() in s["name"]]
        return {
            "code": 1,
            "msg": f"匹配关键词「{keyword}」共{len(filter_list)}首",
            "song_list": filter_list
        }
    # 无关键词，返回全库
    return {
        "code": 1,
        "msg": f"音乐库总计{len(full_list)}首歌曲",
        "song_list": full_list
    }


@tool
def play_selected_music(song_full_path: str) -> str:
    """
    ## 2. play_selected_music
      - 能力：向后端服务发送请求，通过 WebSocket 推送指定歌曲至所有前端播放器自动播放
      - 入参：`song_full_path`（音乐文件完整物理路径，取自 query_music_library 返回的 path 字段）
      - 出参：调用结果 JSON 字符串，标记成功 / 失败状态与提示文案
      - 适用场景：
        - Agent 匹配情绪后自动推送适配疗愈音乐
        - 用户指定某一首歌曲，指令播放器切换播放
        - 心理疏导过程中一键启动背景音乐
      - 规则：
        - 路径必须完全复用 query_music_library 输出的 path 值，禁止手动拼接修改路径
        - 仅执行播放推送动作，不二次扫描、筛选音乐文件
        - 异常错误完整写入返回 JSON，便于 Agent 判断重试
    """
    try:
        resp = requests.post(
            url=f"{BACKEND_URL}/api/play_song_by_path",
            params={"song_path": song_full_path},
            headers=REQUEST_HEADERS,
            timeout=5
        )
        resp_data = resp.json()
        return json.dumps(resp_data, ensure_ascii=False, indent=2)
    except Exception as e:
        err_result = {
            "status": "error",
            "msg": f"推送播放请求失败：{str(e)}"
        }
        return json.dumps(err_result, ensure_ascii=False, indent=2)


# ===================== 工具3：stop_all_music =====================
@tool
def stop_all_music() -> str:
    """
    ## 3. stop_all_music
      - 能力：发送接口指令，全局暂停所有前端正在播放的音乐
      - 入参：无入参
      - 出参：操作状态 JSON 字符串，标记停止指令下发结果
      - 适用场景：
        - 用户情绪平复、谈话结束需要关闭背景音乐
        - 切换疏导方案前清空播放状态
        - 用户主动要求停止音乐
      - 规则：
        - 无入参调用，直接下发全局停止信号
        - 停止后保留播放激活开关，可随时重新启动播放
    """
    try:
        resp = requests.post(
            url=f"{BACKEND_URL}/api/stop",
            headers=REQUEST_HEADERS,
            timeout=5
        )
        resp.raise_for_status()
        resp_data = resp.json()
        return json.dumps(resp_data, ensure_ascii=False, indent=2)
    except requests.exceptions.HTTPError as he:
        err_result = {
            "status": "error",
            "message": f"HTTP异常：{str(he)}"
        }
    except requests.exceptions.ConnectionError:
        err_result = {
            "status": "error",
            "message": "未连接音乐后端服务"
        }
    except Exception as e:
        err_result = {
            "status": "error",
            "message": f"停止音乐请求失败：{str(e)}"
        }
        return json.dumps(err_result, ensure_ascii=False, indent=2)


# ===================== 工具4：resume_first_music =====================
@tool
def resume_first_music() -> str:
    """
    ## 4. resume_first_music
      - 能力：发送接口指令，恢复播放音乐库第一首歌曲，推送至全部前端
      - 入参：无入参
      - 出参：操作状态 JSON 字符串，标记启动推送结果与歌曲名称
      - 适用场景：
        - 暂停后重新开启基础背景音乐
        - 对话初始化时自动启动默认疗愈曲目
      - 规则：
        - 固定读取扫描结果列表第一首作为默认播放源
        - 自动恢复全局播放激活状态
    """
    try:
        resp = requests.post(
            url=f"{BACKEND_URL}/api/start",
            headers=REQUEST_HEADERS,
            timeout=5
        )
        resp.raise_for_status()
        resp_data = resp.json()
        return json.dumps(resp_data, ensure_ascii=False, indent=2)
    except requests.exceptions.HTTPError as he:
        err_result = {
            "status": "error",
            "message": f"HTTP异常：{str(he)}"
        }
    except requests.exceptions.ConnectionError:
        err_result = {
            "status": "error",
            "message": "未连接音乐后端服务"
        }
    except Exception as e:
        err_result = {
            "status": "error",
            "message": f"恢复默认音乐请求失败：{str(e)}"
        }
        return json.dumps(err_result, ensure_ascii=False, indent=2)

# 导出工具列表给Agent加载
music_tool_list = [
    query_music_library,
    play_selected_music,
    stop_all_music,
    resume_first_music
]