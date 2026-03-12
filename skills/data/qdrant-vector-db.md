---
name: qdrant
version: 1.13.2
category: data
trigger: 'when the user needs vector similarity search, RAG retrieval, semantic search, hybrid search, or storing/querying embeddings'
updated: 2026-03-11
confidence: tested
eval_issue: 1
---

# Qdrant v1.13.x

## When to Use

- You need vector similarity search for RAG (Retrieval Augmented Generation)
- You want hybrid search combining dense vectors + sparse vectors or keyword filtering
- You need named vectors (multiple embedding types per document)
- You want payload-based filtering combined with vector search
- You need a self-hosted vector database with a clean Python API
- You want production-grade persistence with snapshot/backup support

## When NOT to Use

- You have <10K vectors and need simplicity -> use NumPy/FAISS in-memory instead
- You need full-text search primarily -> use Elasticsearch or Meilisearch instead
- You want a fully managed cloud-native DB -> consider Pinecone (simpler ops)
- You need graph-based retrieval -> use Neo4j with vector index instead
- You only need key-value storage -> use Redis instead

## Quick Start

```bash
# Install client
pip install qdrant-client==1.13.2

# Run Qdrant server (Docker)
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.13.2
```

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(url="http://localhost:6333")

# Create a collection
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# Insert vectors
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=[0.1, 0.2, ...],  # 1536-dim embedding
            payload={"text": "Python is great", "source": "docs", "page": 1},
        ),
        PointStruct(
            id=2,
            vector=[0.3, 0.4, ...],
            payload={"text": "Rust is fast", "source": "blog", "page": 5},
        ),
    ],
)

# Search
results = client.query_points(
    collection_name="documents",
    query=[0.1, 0.2, ...],  # query embedding
    limit=5,
)
for point in results.points:
    print(point.id, point.score, point.payload["text"])
```

## Common Patterns

### RAG retrieval with OpenAI embeddings

```python
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

openai = OpenAI()
qdrant = QdrantClient(url="http://localhost:6333")

COLLECTION = "knowledge_base"

# Create collection (once)
qdrant.create_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

def embed(text: str) -> list[float]:
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding

# Index documents
docs = [
    {"id": 1, "text": "vLLM uses PagedAttention for efficient serving."},
    {"id": 2, "text": "Qdrant supports hybrid search with prefetch."},
    {"id": 3, "text": "LangChain LCEL uses the pipe operator."},
]

points = [
    PointStruct(id=d["id"], vector=embed(d["text"]), payload={"text": d["text"]})
    for d in docs
]
qdrant.upsert(collection_name=COLLECTION, points=points)

# Query
query = "How does vLLM handle memory?"
results = qdrant.query_points(
    collection_name=COLLECTION,
    query=embed(query),
    limit=3,
)
context = "\n".join(p.payload["text"] for p in results.points)
```

### Filtered search with payload conditions

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

# Search only in "docs" source
results = qdrant.query_points(
    collection_name="documents",
    query=query_vector,
    query_filter=Filter(
        must=[
            FieldCondition(key="source", match=MatchValue(value="docs")),
        ]
    ),
    limit=10,
)

# Search with numeric range filter
results = qdrant.query_points(
    collection_name="documents",
    query=query_vector,
    query_filter=Filter(
        must=[
            FieldCondition(key="page", range=Range(gte=1, lte=100)),
        ]
    ),
    limit=10,
)
```

### Named vectors (multiple embeddings per point)

```python
from qdrant_client.models import VectorParams, Distance

# Collection with both dense and title vectors
qdrant.create_collection(
    collection_name="articles",
    vectors_config={
        "content": VectorParams(size=1536, distance=Distance.COSINE),
        "title": VectorParams(size=384, distance=Distance.COSINE),
    },
)

# Upsert with named vectors
qdrant.upsert(
    collection_name="articles",
    points=[
        PointStruct(
            id=1,
            vector={
                "content": content_embedding,  # 1536-dim
                "title": title_embedding,       # 384-dim
            },
            payload={"title": "My Article", "text": "Full content..."},
        ),
    ],
)

# Search on a specific named vector
results = qdrant.query_points(
    collection_name="articles",
    query=query_embedding,
    using="title",  # search the title vector space
    limit=5,
)
```

### Hybrid search with prefetch + fusion

```python
from qdrant_client.models import Prefetch, FusionQuery, Fusion

# Hybrid: combine results from two different vector spaces
results = qdrant.query_points(
    collection_name="articles",
    prefetch=[
        Prefetch(
            query=content_query_vector,
            using="content",
            limit=20,
        ),
        Prefetch(
            query=title_query_vector,
            using="title",
            limit=20,
        ),
    ],
    query=FusionQuery(fusion=Fusion.RRF),  # Reciprocal Rank Fusion
    limit=10,
)
```

### In-memory mode (no server needed)

```python
# Great for testing, prototyping, or small datasets
client = QdrantClient(":memory:")

# Or persist to disk without running a server
client = QdrantClient(path="./local_qdrant_data")
```

### Payload indexing for fast filtering

```python
from qdrant_client.models import PayloadSchemaType

# Create indexes on frequently filtered fields
qdrant.create_payload_index(
    collection_name="documents",
    field_name="source",
    field_schema=PayloadSchemaType.KEYWORD,
)

qdrant.create_payload_index(
    collection_name="documents",
    field_name="page",
    field_schema=PayloadSchemaType.INTEGER,
)
```

## Configuration Reference

### Collection creation

| Parameter | Description |
|-----------|-------------|
| vectors_config | VectorParams or dict of named VectorParams |
| VectorParams.size | Embedding dimension (must match your model) |
| VectorParams.distance | COSINE, EUCLID, DOT, MANHATTAN |
| shard_number | Number of shards (for distributed mode) |
| replication_factor | Number of replicas |
| on_disk_payload | Store payloads on disk (saves RAM) |

### Client connection

| Mode | Code |
|------|------|
| Remote server | QdrantClient(url="http://host:6333") |
| With API key | QdrantClient(url="http://host:6333", api_key="key") |
| In-memory | QdrantClient(":memory:") |
| Local disk | QdrantClient(path="./data") |
| Qdrant Cloud | QdrantClient(url="https://xyz.cloud.qdrant.io", api_key="key") |

### Docker ports

| Port | Protocol |
|------|----------|
| 6333 | HTTP REST API |
| 6334 | gRPC API (faster for bulk ops) |

## Pitfalls & Gotchas

- **Vector dimension mismatch**: The vector you upsert/query MUST match the `size` in VectorParams exactly. text-embedding-3-small = 1536, text-embedding-3-large = 3072, all-MiniLM-L6-v2 = 384.
- **ID types**: Point IDs can be integers or UUIDs (strings). Pick one and be consistent. Mixing causes confusion.
- **Payload not indexed**: Filtering on unindexed payload fields works but is slow at scale. Always create payload indexes for fields you filter on frequently.
- **Distance metric matters**: Use COSINE for normalized embeddings (OpenAI, most sentence-transformers). Use DOT if embeddings are not normalized and magnitude matters.
- **Upsert is idempotent**: Upserting with the same ID replaces the point. This is good for updates but can silently overwrite if you reuse IDs accidentally.
- **query_points vs search**: In v1.13.x, `query_points` is the unified API replacing older `search` method. Use `query_points` for new code.
- **Memory usage**: Each float32 vector dimension uses 4 bytes. 1M vectors * 1536 dims = ~6GB RAM. Use scalar quantization or on-disk vectors for large collections.
- **Batch size for upserts**: Upsert in batches of 100-500 points for best throughput instead of one-by-one.

## Compared To

| Feature | Qdrant | Pinecone | Weaviate | ChromaDB | FAISS |
|---------|--------|----------|----------|----------|-------|
| Self-hosted | Yes | No (cloud) | Yes | Yes | Yes (library) |
| Cloud managed | Yes | Yes | Yes | No | No |
| Hybrid search | Yes (prefetch+fusion) | Yes | Yes (BM25) | No | No |
| Named vectors | Yes | No | No | No | No |
| Payload filtering | Yes (indexed) | Yes (metadata) | Yes | Yes (metadata) | No |
| Persistence | Yes | Managed | Yes | Yes | Manual |
| Python client | Excellent | Good | Good | Good | C++/Python |
| Ease of setup | Easy (Docker) | Easiest (cloud) | Medium | Easiest (pip) | Hardest |
| Scale | Millions+ | Millions+ | Millions+ | Thousands | Billions |
