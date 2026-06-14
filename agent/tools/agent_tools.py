import os
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import json
from utils.logger_handler import logger
from model.factory import chat_model

# 初始化 RAG 服务实例
rag = RagSummarizeService()


@tool(description="从向量存储中检索参考资料并总结")
def rag_summarize(query: str) -> str:
    """
      从心理医学知识库检索内容并总结
      入参：query 用户问题
      出参：整理后的心理学专业知识文本（可直接用于疏导话术生成）
    """

    return rag.rag_summarize(query)


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    """
    触发上下文注入的工具
    """
    return "fill_context_for_report已调用"


@tool
def emotion_analysis(text: str) -> str:
    """
    调用大模型分析用户情绪类型与强度
    """
    prompt = f"""
你是一个临床心理助理。请根据用户输入判断：
1. 情绪类型（焦虑 / 抑郁 / 愤怒 / 恐惧 / 平静）
2. 情绪强度（轻度 / 中度 / 重度）

用户原话：
{text}

只返回 JSON，不要有任何额外说明：
{{"emotion": "...", "intensity": "..."}}
"""

    try:
        response = chat_model.invoke(prompt)
        content = getattr(response, "content", None)

        # ✅ 内容为空保护
        if not content or not isinstance(content, str):
            logger.warning("emotion_analysis: LLM 返回空内容")
            return '{"emotion": "平静", "intensity": "轻度"}'

        # ✅ JSON 解析保护
        result = json.loads(content)

        if "emotion" not in result or "intensity" not in result:
            raise ValueError("缺少 emotion 或 intensity 字段")

        return content

    except json.JSONDecodeError as e:
        logger.error(f"emotion_analysis JSON 解析失败: {e}, raw={content}")
        return '{"emotion": "平静", "intensity": "轻度"}'

    except Exception as e:
        logger.exception(f"emotion_analysis 调用失败: {e}")
        return '{"emotion": "平静", "intensity": "轻度"}'


@tool
def psychological_knowledge(query: str) -> str:
    """
    从心理学知识库检索专业概念与疗法说明，输出标准化科普内容；非心理学词条返回指定提示
    """
    prompt = f"""
你是专业心理学知识库顾问，针对检索关键词【{query}】按固定四段格式作答：
1.定义：专业简明释义
2.核心原理：底层理论逻辑
3.适用范围：适用心理问题/人群/场景
4.补充备注：疗法疗程、循证等级、注意事项

若该词汇不属于心理学范畴，直接只返回：该关键词不属于心理学范畴，无法检索相关知识
禁止多余闲聊、诊疗建议、心理疏导内容，只输出整理后的正文。
"""
    try:
        print(prompt)
        response = chat_model.invoke(prompt)
        content = getattr(response, "content", None)

        # 空返回兜底
        if not content or not isinstance(content, str):
            logger.warning("psychological_knowledge: LLM返回空内容")
            return "查询异常，暂时无法获取该心理学知识"

        return content.strip()

    except Exception as e:
        logger.exception(f"psychological_knowledge调用异常: {e}")
        return "查询异常，暂时无法获取该心理学知识"


@tool
def soothing_dialogue(emotion: str, intensity: str) -> str:
    """
    生成共情式、非评判性的心理疏导话术

    参数：
    - emotion: 情绪类型（如：焦虑、难过、愤怒、内疚、孤独、恐惧）
    - intensity: 强度等级（轻度 / 中度 / 重度）

    适用场景：
    - 用户情绪强烈、明显痛苦
    - 需要被看见、被接纳，而非被指导

    规则：
    - 禁止评价、指责、说教
    - 禁止出现“你应该”“你就是”等表述
    - 不提供建议、不解释原理、不诊断
    """
    prompt = (
        f"你正在面对一位正处于「{emotion}（{intensity}）」状态的人。"
        "你的任务只有一个：提供一段安全、温暖、可被依靠的情绪回应。\n\n"
        "严格遵守以下规则：\n"
        "1. 语气温和、稳定、缓慢\n"
        "2. 不评价、不指责、不说教\n"
        "3. 禁止出现以下表述：\n"
        "   - 你应该……\n"
        "   - 你就是……\n"
        "   - 这没什么\n"
        "   - 想开点\n"
        "   - 你要坚强\n"
        "4. 不提供建议、不分析问题、不解释原因\n\n"
        "结构建议（不强制模板）：\n"
        "- 第一步：确认并接纳情绪\n"
        "- 第二步：让对方感到被允许这样感受\n"
        "- 第三步：轻柔停留或极简提问\n\n"
        "输出要求：\n"
        "- 不输出推理过程\n"
        "- 生成共情式、非评判性的心理疏导话术"
    )

    try:
        # print("回复模板" + "*"*20)
        # print(prompt)
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", "")

        if not content or not isinstance(content, str):
            logger.warning("soothing_dialogue: LLM 返回空内容")
            return "我在这里，你可以慢慢说。"
        return content.strip()
    except Exception as e:
        logger.exception(f"soothing_dialogue 调用异常: {e}")
        return "我在这里，你可以慢慢说。"


@tool
def relaxation_guidance(method: str) -> str:
    """
    生成可执行的心理调节指导语

    参数：
    - method: 调节方法（如：呼吸训练、正念、渐进式肌肉放松、身体扫描）

    适用场景：
    - 用户焦虑、紧张、心慌、失眠

    规则：
    - 语言温和、稳定、适合口头引导
    - 节奏清晰，每一步都可执行
    - 不解释原理、不诊断、不建议用药
    """
    prompt = (
        f"你正在带领用户进行一次「{method}」练习。"
        "请生成一段适合语音或文字引导的执行脚本。\n\n"
        "要求：\n"
        "1. 语言温和、缓慢、稳定\n"
        "2. 每一步都是可执行动作（如：吸气、停住、放松）\n"
        "3. 步骤之间留出心理节奏，不要堆砌\n"
        "4. 总时长控制在 1～3 分钟当量\n"
        "5. 不解释原理、不分析情绪、不诊断\n\n"
        "输出格式：\n"
        "请直接输出引导语，不添加标题、不说明自己是 AI。"
    )
    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", "")
        if not content or not isinstance(content, str):
            logger.warning("relaxation_guidance: LLM 返回空内容")
            return "抱歉，暂时无法生成调节指导，请稍后再试。"

        return content.strip()

    except Exception as e:
        logger.exception(f"relaxation_guidance 调用异常: {e}")
        return "抱歉，暂时无法生成调节指导，请稍后再试。"


@tool
def crisis_intervention(risk_level: str) -> str:
    """
    识别高危心理状态并输出干预话术与求助资源

    参数：
    - risk_level: 风险等级（high / critical）

    适用场景：
    - 用户表达自伤、自杀、无望、无法继续生活
    强制规则：
    ✅ 必须调用
    ✅ 必须包含求助渠道
    ❌ 不得安慰性拖延
    ❌ 不得质疑真实性
    ❌ 不得诊断或建议就医方式以外的内容
    """

    hotline_block = (
        "📞 全国统一心理援助热线：400-161-9995\n"
        "📞 北京心理危机研究与干预中心：010-82951332\n"
        "📞 24小时希望热线：400-161-9995\n"
        "🏥 如有紧急危险，请立即前往最近医院急诊科或拨打 120"
    )

    prompt = (
        f"当前用户处于「{risk_level}」风险状态，可能存在自伤或自杀倾向。"
        "请生成一段**危机干预回应**，目标只有一个：保护生命、连接现实帮助。\n\n"
        "必须遵守：\n"
        "1. 不质疑、不否定、不反驳用户感受\n"
        "2. 不拖延，不试图“说服”对方放弃\n"
        "3. 不提供心理分析、不解释原因\n"
        "4. 先表达关心与确认，再**直接给出求助渠道**\n\n"
        "输出结构：\n"
        "第一段：简短、稳定、非评判的安抚（不超过 2 句）\n"
        "第二段：明确告知这不是对方需要独自承受的时刻\n"
        "第三段：求助电话与就医建议（必须包含以下内容）：\n"
        f"{hotline_block}\n\n"
        "只输出最终干预文本，不解释你的行为。"
    )

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", "")

        if not content or not isinstance(content, str):
            logger.critical("crisis_intervention: LLM 返回空内容")
            return (
                "你现在并不孤单，有人可以帮你。\n"
                "这不是你必须一个人扛着的事情。\n\n"
                f"{hotline_block}"
            )

        return content.strip()

    except Exception as e:
        logger.exception(f"crisis_intervention 调用异常: {e}")
        return (
            "你现在并不孤单，有人可以帮你。\n"
            "这不是你必须一个人扛着的事情。\n\n"
            f"{hotline_block}"
        )
