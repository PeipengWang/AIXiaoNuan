from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from utils.logger_handler import logger
from utils.prompt_loader import load_report_prompts, load_system_prompts
from langchain.agents.middleware import SummarizationMiddleware
from model.factory import chat_model, checkpointer


@wrap_tool_call
def monitor_tool(
    # 请求的数据封装
    request: ToolCallRequest,
    # 执行的函数本身
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    # 工具执行的监控
    logger.info(f"[tool monitor]执行工具: {request.tool_call['name']}")
    logger.info(f"[tool monitor]传入参数: {request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")
        if request.tool_call['name'] == "fill_context_for_report":
            request.runtime.context["report"] = True
        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败, 原因: {str(e)}")
        raise e


@before_model
def log_before_model(
    state: AgentState,
    runtime: Runtime,
) -> None:
    # 在模型执行前输出日志
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")

    # ===================== 打印所有传入模型的消息（万能解析） =====================
    for i, msg in enumerate(state["messages"]):
        try:
            # 优先获取 content（所有消息都有 content）
            content = msg.content

            # 获取类型/角色
            if hasattr(msg, "role"):
                role = msg.role
            elif hasattr(msg, "name"):
                role = f"Tool({msg.name})"
            elif "tool_call" in str(msg):
                role = "ToolCall"
            else:
                role = type(msg).__name__

            logger.info(f"[消息 {i+1}] {role}: {content}")
        except Exception:
            # 终极兜底：直接转字符串打印
            logger.info(f"[消息 {i+1}] 完整内容: {str(msg)[:300]}...")

    # 你原来的逻辑（保留）
    if state['messages']:
        last_message = state['messages'][-1]
        logger.debug(f"[log_before_model]{type(last_message).__name__} | {last_message.content}")
    else:
        logger.debug("[log_before_model]消息列表为空")

    return None


@dynamic_prompt  # 每一次在生成提示词之前，调用此函数
def report_prompt_switch(request: ModelRequest):  # 动态切换提示词
    is_report = request.runtime.context.get("report", False)
    if is_report:  # 是报告生成场景，返回报告生成提示词内容
        return load_report_prompts()

    return load_system_prompts()

# 摘要专用提示词
SUMMARY_PROMPT = """
你是心理咨询对话总结专家，将下面多轮医患对话浓缩成一段精简上下文摘要：
1. 完整保留用户核心心理情绪、原生困扰诉求、关键压力点；
2. 保留咨询师给出的疏导方案、安抚话术、干预手段；
3. 删除重复语气词、客套话、无效停顿语句；
4. 输出纯正文段落，不要标题、编号、多余符号。
"""

# 实例化摘要中间件
summary_middleware = SummarizationMiddleware(
    model=chat_model,  # 新版参数名：model，不再是 summary_model
    # 触发条件：消息数量 >20 就执行压缩
    trigger=("messages", 100),
    # 压缩后：只保留最新10条原始对话，前面全部合并成一条摘要
    keep=("messages", 10),
    summary_prompt=SUMMARY_PROMPT
)


from utils.compress_memory import get_current_step


def test_check_sqlite():
    thread_id = "default_user"
    step = get_current_step(checkpointer, thread_id)
    print(f"库内消息条数：{step}")


if __name__ == '__main__':
    test_check_sqlite()