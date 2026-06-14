import json
from typing import List
from langchain_core.documents import Document
from rag.vector_store import VectorStoreService  # 你的向量库类
from utils.logger_handler import logger

# 1. 下载并加载 SoulChat 数据集
from modelscope.msdatasets import MsDataset
logger.info("正在加载 SoulChatCorpus 数据集...")
ds = MsDataset.load('YIRONGCHEN/SoulChatCorpus', subset_name='default', split='train')

# 2. 初始化你的向量库
vs = VectorStoreService()

# 3. 批量插入（只跑一次！）
def import_soulchat_to_chroma():
    documents: List[Document] = []

    # 遍历数据集（可限制数量，比如前 5000 条）
    for idx, item in enumerate(ds):
        try:
            # 数据格式
            conv_id = item["id"]
            topic = item["topic"]
            messages = item["messages"]

            # 把多轮对话拼接成一段文本
            dialogue_text = f"主题：{topic}\n"
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    dialogue_text += f"用户：{content}\n"
                else:
                    dialogue_text += f"助手：{content}\n"

            # 构建 Document
            doc = Document(
                page_content=dialogue_text.strip(),
                metadata={
                    "source": "SoulChatCorpus",
                    "topic": topic,
                    "id": conv_id,
                    "type": "empathy_dialogue"
                }
            )

            documents.append(doc)

            # 每 200 条批量入库（防止内存爆炸）
            if len(documents) >= 200:
                vs.vector_store.add_documents(documents)
                logger.info(f"已导入 {idx+1} 条对话...")
                documents = []

        except Exception as e:
            continue

    # 最后一批
    if documents:
        vs.vector_store.add_documents(documents)

    logger.info("✅ SoulChatCorpus 数据集全部导入完成！")

if __name__ == '__main__':
    import_soulchat_to_chroma()