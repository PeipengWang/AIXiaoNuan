import os

from abc import ABC, abstractmethod
from typing import Optional

from langchain.chat_models import init_chat_model
# LangChain 核心组件
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from openai import BaseModel

load_dotenv()
# 假设的全局配置字典
rag_conf = {
    "chat_model_name": "deepseek-chat",
    "embedding_model_name": "text-embedding-v1"
}

if not os.path.exists("resources"):
    os.mkdir("resources")
connection = sqlite3.connect("resources/psychologist.db", check_same_thread=False)
checkpointer = SqliteSaver(connection)
checkpointer.setup()


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self):
        # 新版统一写法，完全替代 ChatDeepSeek
        return init_chat_model(
            # 配置从你的 rag_conf 读取（不变）
            model=rag_conf["chat_model_name"],
            # 固定：指定厂商
            model_provider="deepseek",
            # 温度参数不变
            temperature=0.7,
            # api_key 自动读环境变量，不用写
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])


class FinalOnlySqliteSaver(SqliteSaver, ABC):
    def put(self, config, checkpoint, metadata, new_versions=None):
        # metadata里source标识步骤类型
        source = metadata.get("source", "")
        # 只放行两种场景写入：
        # 1. source="input" 首轮初始输入
        # 2. 非loop循环的收尾终态；所有loop中间step全部跳过不存储
        if source == "loop":
            # 中间工具循环步骤，直接跳过写入，减少IO
            return
        # 其余终态/初始输入正常执行写入逻辑
        super().put(config, checkpoint, metadata, new_versions)


# 如果你一定要继承 BaseModelFactory
class MemorySaver(BaseModel):

    def create_memory(self) -> FinalOnlySqliteSaver:
        if not os.path.exists("resources"):
            os.mkdir("resources")
        connection = sqlite3.connect(
            "resources/psychologist.db",
            check_same_thread=False
        )
        # 替换：用自定义FinalOnlySqliteSaver，不再原生SqliteSaver
        # checkpointer = SqliteSaver(connection) #这个实现工具过程全量存储
        checkpointer = FinalOnlySqliteSaver(connection)
        checkpointer.setup()

        return checkpointer


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
checkpointer = MemorySaver().create_memory()

if __name__ == '__main__':
    """
      仅用于验证：
      1. chat_model 是否能成功初始化
      2. 是否能正常调用通义千问 API
      """

    test_prompt = "你好，请用一句话介绍你自己。"

    try:
        # ✅ 推荐方式（LangChain 标准写法）
        response = chat_model.invoke([HumanMessage(content=test_prompt)])

        print("✅ ChatModel 调用成功！")
        print("模型返回结果：")
        print(response.content)

    except Exception as e:
        print("❌ ChatModel 调用失败！")
        print("错误信息：", str(e))