# RAG 向量检索实现详解

## 从 Dict Lookup 到 RAG 的演进

### 原始方案（已替换）
```python
# ai/rag_retriever.py — 简单字典查找
from knowledge.pesticide_db import pesticide_db
def retrieve_pesticide(disease_key):
    return pesticide_db.get(disease_key, [])
```

**问题**: 只能精确匹配 disease_key，不支持模糊查询、语义搜索。

### 新方案: ChromaDB + 语义检索
- 将所有知识库数据转为文本块，嵌入 ChromaDB 向量数据库
- 支持自然语言查询，如"早疫病用什么药"、"高湿度下的防治方案"
- 通过 metadata 过滤实现精确 + 语义的混合检索

## 知识库数据源

| 数据源 | 文件 | 文档数 | 内容 |
|--------|------|--------|------|
| 病害信息 | `knowledge/disease_db.py` | 2 | 早疫病、晚疫病的详细信息 |
| 农药数据 | `knowledge/pesticide_db.py` | 6 | 每种病害 3 种推荐药剂 |
| SOP 流程 | `knowledge/sop_db.py` | 6 | 每种病害 × 3 个风险等级 |

## 向量化流程

### 1. 文档构建 (`rag/ingest.py`)

将 Python 字典转为 LangChain Document 对象：

```python
# 病害信息 → Document
for disease_id, info in disease_db.items():
    content = f"病害名称: {info['name']}\n类型: {info['type']}\n..."
    Document(
        page_content=content,
        metadata={"disease_id": disease_id, "type": "disease_info"}
    )

# 农药数据 → Document
for disease_id, pesticides in pesticide_db.items():
    for p in pesticides:
        content = f"药剂名称: {p['name']}\n有效成分: {p['ingredient']}\n..."
        Document(
            page_content=content,
            metadata={"disease_id": disease_id, "type": "pesticide", "name": p["name"]}
        )

# SOP 流程 → Document
for disease_id, risk_levels in sop_db.items():
    for risk_level, steps in risk_levels.items():
        content = f"病害: {disease_id}\n风险等级: {risk_level}\nSOP流程:\n..."
        Document(
            page_content=content,
            metadata={"disease_id": disease_id, "type": "sop", "risk_level": risk_level}
        )
```

### 2. Embedding 模型

使用 HuggingFace 的中文 sentence-transformer 模型：

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
```

**选择理由**:
- 中文优化，对农业术语支持好
- 本地运行，无需外部 API
- 模型体积小（~100MB），推理速度快

### 3. ChromaDB 存储

```python
from langchain_chroma import Chroma

vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db",  # 持久化到本地
    collection_name="potato_knowledge",
)
```

## 语义检索 (`rag/retriever.py`)

### 检索函数

```python
def search_knowledge_base(
    query: str,           # 自然语言查询
    doc_type: str = None, # metadata 过滤: disease_info/pesticide/sop
    disease_id: str = None,  # metadata 过滤: early_blight/late_blight
    top_k: int = 5,       # 返回前 k 个结果
):
    results = vs.similarity_search(
        query=query,
        k=top_k,
        filter={"type": doc_type, "disease_id": disease_id} if ... else None,
    )
    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
```

### 查询示例

| 查询 | 预期结果 |
|------|----------|
| `"早疫病用什么药"` | 代森锰锌、百菌清、嘧菌酯的详细信息 |
| `"late blight treatment"` | 晚疫病的防治策略和药剂 |
| `"高湿度下的防治方案"` | 高风险环境下的 SOP 步骤 |
| `"fungicide spray interval"` | 药剂施药间隔信息 |

## 与 Agent 的集成

Treatment Agent 通过 `search_knowledge_base` 工具调用 RAG 检索：

```python
@tool
def search_knowledge_base(query: str) -> list:
    """Search the potato disease knowledge base using semantic search."""
    from rag.retriever import search_knowledge_base as _search
    return _search(query, top_k=5)
```

Agent 的 LLM 根据上下文自主决定查询内容，例如：
- 知道是早疫病后，查询"早疫病推荐药剂"
- 知道是高风险后，查询"高风险防治方案"

## 运行方式

```bash
# 一次性初始化（构建 ChromaDB）
python rag/ingest.py

# 测试检索
python -c "from rag.retriever import search_knowledge_base; \
           print(search_knowledge_base('早疫病用药'))"
```
