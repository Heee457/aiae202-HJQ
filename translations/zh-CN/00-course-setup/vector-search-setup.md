> 本文档由 AI 翻译自英文原文，可能存在疏漏。以准确性为准时请参阅[英文原版](../../../00-course-setup/vector-search-setup.md)。

# 用 Chroma 做向量检索

有几课（05、11、16、17）让智能体按语义而不是按关键词来检索文档，用的是 [Chroma](https://docs.trychroma.com/) —— 一个在你的 Python 进程内运行的开源向量数据库。它不需要启动服务端，也不需要为嵌入向量 API 付费：Chroma 自带一个小型本地嵌入模型，会在你第一次添加文档时下载。

## 两分钟上手

```python
import chromadb

client = chromadb.Client()                       # in-memory; use PersistentClient(path=...) to keep data
collection = client.create_collection("travel-docs")

collection.add(
    ids=["1", "2", "3"],
    documents=[
        "Our return policy allows refunds within 30 days of purchase.",
        "Standard shipping takes 3-5 business days.",
        "The Eiffel Tower is open daily from 9:30 to 23:45.",
    ],
)

results = collection.query(query_texts=["How long do I have to send something back?"], n_results=1)
print(results["documents"][0][0])
# -> Our return policy allows refunds within 30 days of purchase.
```

## 把检索能力开放给智能体

在 LangChain 里，把这次查询包装成一个工具，再传给 `create_agent`：

```python
from langchain.tools import tool

@tool
def search_docs(query: str) -> str:
    """Search the knowledge base for passages relevant to the query."""
    hits = collection.query(query_texts=[query], n_results=3)
    return "\n".join(hits["documents"][0])
```

第 05 课就是在这个模式之上，构建出一整套智能体式 RAG 循环。

## 持久化数据

```python
client = chromadb.PersistentClient(path="./chroma-data")
```

该目录会在首次使用时创建。仓库的 `.gitignore` 已经忽略了 `chroma-data/`。

## 换用其他嵌入模型

Chroma 接受任意嵌入函数。若想用 OpenAI 兼容的嵌入接口来替代自带模型：

```python
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

ef = OpenAIEmbeddingFunction(api_key="...", api_base="https://api.openai.com/v1", model_name="text-embedding-3-small")
collection = client.create_collection("travel-docs", embedding_function=ef)
```

课程 notebook 一律使用自带模型，这样在不提供嵌入向量 API 的服务商上也能正常运行。
