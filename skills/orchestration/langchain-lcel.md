---
name: langchain
version: 0.3.x
category: orchestration
trigger: 'when the user needs to chain LLM calls, build RAG pipelines, use structured output, or compose prompt-model-parser workflows'
updated: 2026-03-11
confidence: tested
eval_issue: 1
---

# LangChain v0.3.x — LCEL Patterns

## When to Use

- You need to chain prompts, LLMs, and output parsers into composable pipelines
- You want structured output (JSON/Pydantic) from LLM calls
- You're building RAG pipelines with retrieval + generation
- You need parallel execution of multiple LLM calls
- You want streaming support with minimal code
- You need to integrate multiple LLM providers with a unified interface

## When NOT to Use

- You need autonomous agents with loops/branching -> use LangGraph instead
- You want a simple one-shot API call -> use the provider SDK directly (openai, anthropic)
- You need fine-grained control over every HTTP request -> use provider SDKs
- You're building a conversational agent with state -> use LangGraph instead
- You want minimal dependencies -> use raw API calls or LiteLLM

IMPORTANT: LLMChain, ConversationChain, and other legacy chains are DEPRECATED in v0.3. Use LCEL (LangChain Expression Language) pipe syntax instead.

## Quick Start

```bash
# Install core + provider packages separately
pip install langchain==0.3.* langchain-openai langchain-anthropic langchain-community

# Note: LangChain v0.3 requires Pydantic v2 only. Pydantic v1 is NOT supported.
```

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# The LCEL pipe pattern: prompt | model | parser
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}"),
])

llm = ChatOpenAI(model="gpt-4o", temperature=0)
parser = StrOutputParser()

chain = prompt | llm | parser

# Invoke
answer = chain.invoke({"question": "What is LCEL?"})
print(answer)
```

## Common Patterns

### Basic chain with prompt | llm | parser

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in {style} style, in under 100 words."
)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

chain = prompt | llm | StrOutputParser()

result = chain.invoke({"topic": "quantum computing", "style": "pirate"})
```

### Structured output with Pydantic

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class MovieReview(BaseModel):
    title: str = Field(description="Movie title")
    rating: float = Field(description="Rating from 0 to 10")
    summary: str = Field(description="One-sentence summary")
    recommended: bool = Field(description="Would you recommend it?")

llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(MovieReview)

review = structured_llm.invoke("Review the movie Inception")
print(review.title)      # "Inception"
print(review.rating)     # 9.2
print(review.recommended) # True
```

### RAG pattern with RunnablePassthrough

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Assume `retriever` is a vector store retriever (e.g., from Qdrant)
# retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

prompt = ChatPromptTemplate.from_template("""
Answer the question based only on the following context:

{context}

Question: {question}
""")

rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | ChatOpenAI(model="gpt-4o")
    | StrOutputParser()
)

answer = rag_chain.invoke("How does PagedAttention work?")
```

### Parallel execution with RunnableParallel

```python
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o-mini")

summary_chain = (
    ChatPromptTemplate.from_template("Summarize this text: {text}")
    | llm
    | StrOutputParser()
)

keywords_chain = (
    ChatPromptTemplate.from_template("Extract 5 keywords from: {text}")
    | llm
    | StrOutputParser()
)

sentiment_chain = (
    ChatPromptTemplate.from_template("What is the sentiment of: {text}")
    | llm
    | StrOutputParser()
)

# Run all three in parallel
combined = RunnableParallel(
    summary=summary_chain,
    keywords=keywords_chain,
    sentiment=sentiment_chain,
)

result = combined.invoke({"text": "LangChain v0.3 is a major release..."})
print(result["summary"])
print(result["keywords"])
print(result["sentiment"])
```

### Streaming

```python
chain = prompt | llm | StrOutputParser()

for chunk in chain.stream({"question": "Tell me a story"}):
    print(chunk, end="", flush=True)
```

### Async support

```python
import asyncio

async def main():
    result = await chain.ainvoke({"question": "What is LCEL?"})
    print(result)

    # Async streaming
    async for chunk in chain.astream({"question": "Tell me a story"}):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### Using with Anthropic

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)

# Same LCEL chain works — just swap the model
chain = prompt | llm | StrOutputParser()
```

### Using with a local vLLM server

```python
from langchain_openai import ChatOpenAI

# Point to your vLLM server
llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
    model="meta-llama/Llama-3.1-8B-Instruct",
)

chain = prompt | llm | StrOutputParser()
```

### Adding message history (simple version)

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm | StrOutputParser()

history = []
while True:
    user_input = input("You: ")
    result = chain.invoke({"input": user_input, "history": history})
    history.append(HumanMessage(content=user_input))
    history.append(AIMessage(content=result))
    print(f"AI: {result}")
```

## Configuration Reference

### Provider packages (install separately)

| Package | Models |
|---------|--------|
| langchain-openai | GPT-4o, GPT-4o-mini, o1, embeddings |
| langchain-anthropic | Claude 3.5 Sonnet, Claude 3 Opus/Haiku |
| langchain-google-genai | Gemini 1.5 Pro/Flash |
| langchain-community | Ollama, HuggingFace, many others |

### Core imports

| Class | Import | Purpose |
|-------|--------|---------|
| ChatPromptTemplate | langchain_core.prompts | Build chat prompts |
| StrOutputParser | langchain_core.output_parsers | Parse LLM output to string |
| RunnablePassthrough | langchain_core.runnables | Pass input through unchanged |
| RunnableParallel | langchain_core.runnables | Run chains in parallel |
| MessagesPlaceholder | langchain_core.prompts | Inject message history |

### LCEL operators

| Operator | Meaning |
|----------|---------|
| `a \| b` | Pipe: output of a feeds into b |
| `chain.invoke(input)` | Run synchronously |
| `chain.ainvoke(input)` | Run async |
| `chain.stream(input)` | Stream output chunks |
| `chain.batch([inputs])` | Run on multiple inputs |

## Pitfalls & Gotchas

- **Pydantic v2 ONLY**: LangChain v0.3 dropped Pydantic v1 support entirely. If you see `PydanticUserError`, you have a Pydantic v1 model somewhere. Pin pydantic>=2.0.
- **LLMChain is DEAD**: Do NOT use `from langchain.chains import LLMChain`. It's deprecated. Use `prompt | llm | parser` instead.
- **ConversationChain is DEAD**: Use ChatPromptTemplate with MessagesPlaceholder + manual history, or use LangGraph for stateful agents.
- **Import paths changed**: Use `langchain_core` for base classes, `langchain_openai` for OpenAI (not `langchain.chat_models`). Old import paths are deprecated.
- **Partner packages**: Each provider is a separate pip install. `pip install langchain` alone doesn't give you OpenAI — you need `pip install langchain-openai`.
- **with_structured_output requires tool calling**: The model must support function/tool calling. Works with GPT-4o, Claude 3.5, Gemini. Does NOT work with older models or most local models.
- **RunnablePassthrough gotcha**: `RunnablePassthrough()` passes the entire input dict. `RunnablePassthrough.assign(key=chain)` adds a new key to the dict.
- **Streaming with parsers**: StrOutputParser streams fine. Pydantic structured output does NOT stream (it needs the complete JSON).
- **Agents**: For anything with loops, tool use, or decision-making, use LangGraph, not LCEL chains. LCEL is for linear/parallel pipelines.

## Compared To

| Feature | LangChain LCEL | LlamaIndex | Haystack | Raw SDKs |
|---------|----------------|------------|----------|----------|
| Composability | Excellent (pipe) | Good | Good | Manual |
| Streaming | Native | Native | Limited | Native |
| Provider support | 60+ via packages | 30+ | 20+ | 1 per SDK |
| Structured output | with_structured_output | Pydantic programs | N/A | Manual JSON |
| RAG built-in | Via retrievers | Primary focus | Pipeline-based | DIY |
| Agent support | LangGraph (separate) | Built-in | Built-in | DIY |
| Learning curve | Medium | Medium | Medium | Low |
| Overhead | Some abstraction cost | Some | Some | None |
