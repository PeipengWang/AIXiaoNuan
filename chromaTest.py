import chromadb
from chromadb.utils import embedding_functions

# ===================== 核心：禁用自动下载模型 =====================
chromadb.api.client.SharedSystemClient.clear_system_cache()



# 使用默认嵌入函数，不下载 79M 模型
embedding = embedding_functions.DefaultEmbeddingFunction()


def getCollection():
    # 获取所有Collection
    collections = client.list_collections()

    print("现有Collections:")
    for collection in collections:
        print(f"- {collection.name}: {collection.metadata}")

def checkCollection():
    # 获取所有Collection
    # 获取所有Collection
    collections = client.list_collections()
    print("现有Collections:")
    for collection in collections:
        print(f"- {collection.name}: {collection.metadata}")
        # 获取Collection统计信息
        count = collection.count()
        print(f"文档数量: {count}")

        # 查看Collection详情
        print(f"Collection名称: {collection.name}")
        print(f"Collection ID: {collection.id}")
        print(f"元数据: {collection.metadata}")


# 创建客户端

# 本地持久化，不联网
client = chromadb.PersistentClient(path="./chroma_db")
# 创建Collection
collection = client.create_collection(
    name="my_collection",
    metadata={"description": "我的第一个Collection"}
)
# 单个文档
collection.add(
    documents="这是一个文档",
    ids="doc_1",
    metadatas={"source": "manual"}
)

# 批量添加
collection.add(
    documents=[
        "第一个文档内容",
        "第二个文档内容",
        "第三个文档内容"
    ],
    ids=["doc_1", "doc_2", "doc_3"],
    metadatas=[
        {"category": "A", "priority": 1},
        {"category": "B", "priority": 2},
        {"category": "A", "priority": 3}
    ]
)

print(f"Collection创建成功: {collection.name}")
collection = client.get_collection(name="my_collection")

# 获取或创建
collection = client.get_or_create_collection(
    name="my_collection",
    metadata={"updated": "2024-01-01"}
)

checkCollection()
# 删除Collection
client.delete_collection(name="my_collection")
print("Collection已删除")
getCollection()



