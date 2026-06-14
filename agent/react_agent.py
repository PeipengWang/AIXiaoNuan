from langchain.agents import create_agent, AgentState


from model.factory import chat_model,checkpointer
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, fill_context_for_report, emotion_analysis, psychological_knowledge,
                                     soothing_dialogue, crisis_intervention, relaxation_guidance)
from agent.tools.music_tools import query_music_library, play_selected_music, stop_all_music, resume_first_music
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch, summary_middleware

class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
                rag_summarize,
                fill_context_for_report,
                emotion_analysis,
                psychological_knowledge,
                soothing_dialogue,
                crisis_intervention,
                relaxation_guidance,
                query_music_library,
                play_selected_music,
                stop_all_music,
                resume_first_music
            ],
            middleware=[
                summary_middleware,
                monitor_tool,
                log_before_model,
                report_prompt_switch,
            ],
            checkpointer=checkpointer,
        )


    def execute_stream(self, query: str, thread_id: str = "default_user"):
        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }
        config = {"configurable": {"thread_id": thread_id}}
        # 下方的代码应该是调用 self.agent.stream(input_dict) 之类的逻辑
        # 图片在此处截断
        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(input_dict,
                                       stream_mode="values",
                                       context={"report": False},
                                       config=config):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("我一直被排斥"):
        print(chunk, end="", flush=True)