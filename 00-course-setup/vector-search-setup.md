# Vector Search with Chroma

Several lessons (05, 11, 16, 17) let an agent retrieve documents by meaning
rather than by keyword. They use [Chroma](https://docs.trychroma.com/), an
open-source vector database that runs inside your Python process. There is no
server to start and no embedding API to pay for: Chroma ships with a small
local embedding model that it downloads the first time you add documents.

## Try it in two minutes

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

## Exposing retrieval to an agent

In LangChain, wrap the query in a tool and pass it to `create_agent`:

```python
from langchain.tools import tool

@tool
def search_docs(query: str) -> str:
    """Search the knowledge base for passages relevant to the query."""
    hits = collection.query(query_texts=[query], n_results=3)
    return "\n".join(hits["documents"][0])
```

Lesson 05 builds a complete Agentic RAG loop on this pattern.

## Persisting data

```python
client = chromadb.PersistentClient(path="./chroma-data")
```

The directory is created on first use. The repository's `.gitignore` already ignores `chroma-data/`.

## Using a different embedding model

Chroma accepts any embedding function. To use an OpenAI-compatible embeddings
endpoint instead of the bundled model:

```python
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

ef = OpenAIEmbeddingFunction(api_key="...", api_base="https://api.openai.com/v1", model_name="text-embedding-3-small")
collection = client.create_collection("travel-docs", embedding_function=ef)
```

The course notebooks stick with the bundled model so that they work with
providers that offer no embeddings API.
