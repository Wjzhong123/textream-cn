#!/usr/bin/env python3
"""Textream 智能体后端 — REST API for memory + knowledge + LLM.
Runs as a standalone service on port 9123.
DirectorServer (port 7575) serves the unified UI, JS calls this API."""

import json, os, time, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".textream"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE = DATA_DIR / "memory.json"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Textream Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Models ───────────────────────────────────────────────────────────────────
class MemoryEntry(BaseModel):
    id: str = ""
    timestamp: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = []
    importance: int = 3

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

# ── Memory Storage ───────────────────────────────────────────────────────────
def load_memories() -> list[dict]:
    if MEMORY_FILE.exists():
        try: return json.loads(MEMORY_FILE.read_text())
        except: return []
    return []

def save_memories(memories: list[dict]):
    MEMORY_FILE.write_text(json.dumps(memories, ensure_ascii=False, indent=2))

# ── Knowledge Base ───────────────────────────────────────────────────────────
def load_knowledge_files() -> list[dict]:
    results = []
    if not KNOWLEDGE_DIR.exists(): return results
    for f in sorted(KNOWLEDGE_DIR.glob("*.txt")):
        try:
            content = f.read_text().strip()
            if content: results.append({"name": f.stem, "content": content, "path": str(f)})
        except: pass
    return results

def search_knowledge(query: str) -> list[dict]:
    q = query.lower()
    results = []
    for doc in load_knowledge_files():
        if q in doc["content"].lower():
            idx = doc["content"].lower().find(q)
            start = max(0, idx - 100)
            end = min(len(doc["content"]), idx + len(query) + 200)
            snippet = doc["content"][start:end]
            if start > 0: snippet = "..." + snippet
            if end < len(doc["content"]): snippet = snippet + "..."
            results.append({"name": doc["name"], "snippet": snippet})
    return results

# ── LLM ──────────────────────────────────────────────────────────────────────
def query_llm(prompt: str, system: str = "") -> str:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("OPENHARNESS_MODEL", "gpt-4o-mini"),
            messages=messages, max_tokens=1024, temperature=0.7,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"[LLM Error] {e}"

# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/status")
def status():
    memories = load_memories()
    knowledge = load_knowledge_files()
    return {
        "agent": "online",
        "memory_count": len(memories),
        "knowledge_count": len(knowledge),
        "llm_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "timestamp": datetime.now().isoformat(),
    }

# ── Memory CRUD ──────────────────────────────────────────────────────────────

@app.get("/api/memory/list")
def list_memories(limit: int = 50, offset: int = 0, user_id: str = "default"):
    memories = load_memories()
    user_memories = [m for m in memories if m.get("user_id", "default") == user_id]
    user_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(user_memories)
    page = user_memories[offset:offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "items": page}

@app.post("/api/memory/add")
def add_memory(entry: MemoryEntry):
    memories = load_memories()
    new_entry = {
        "id": entry.id or str(uuid.uuid4())[:8],
        "timestamp": entry.timestamp or datetime.now().isoformat(),
        "title": entry.title,
        "content": entry.content,
        "tags": entry.tags,
        "importance": entry.importance,
        "user_id": "default",
    }
    memories.append(new_entry)
    save_memories(memories)
    return {"status": "ok", "id": new_entry["id"]}

@app.delete("/api/memory/delete/{memory_id}")
def delete_memory(memory_id: str):
    memories = load_memories()
    before = len(memories)
    memories = [m for m in memories if m.get("id") != memory_id]
    if len(memories) == before:
        raise HTTPException(status_code=404, detail="Memory not found")
    save_memories(memories)
    return {"status": "deleted", "id": memory_id}

@app.get("/api/memory/search")
def search_memory(q: str = Query("", description="Search query")):
    if not q: return {"items": []}
    q_lower = q.lower()
    memories = load_memories()
    results = []
    for m in memories:
        if q_lower in m.get("title", "").lower() or q_lower in m.get("content", "").lower():
            results.append(m)
    results.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return {"items": results[:20]}

# ── Knowledge ────────────────────────────────────────────────────────────────

@app.get("/api/knowledge/list")
def list_knowledge():
    return {"items": load_knowledge_files()}

@app.get("/api/knowledge/search")
def knowledge_search(q: str = Query("", description="Search query")):
    if not q: return {"items": []}
    return {"items": search_knowledge(q)}

# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(req: ChatRequest):
    memories = load_memories()
    user_memories = [m for m in memories if m.get("user_id", "default") == req.user_id]
    # Build context from recent memories
    context_parts = []
    for m in user_memories[-10:]:
        context_parts.append(f"[{m.get('timestamp','')[:10]}] {m.get('title','')}: {m.get('content','')[:200]}")
    context = "\n".join(context_parts) if context_parts else "暂无记忆"

    system = f"你是一个提词器智能助手。以下是用户最近的记忆：\n{context}\n\n请基于记忆回答用户的问题。如果记忆中没有相关信息，如实说不知道。"
    reply = query_llm(req.message, system=system)
    return {"reply": reply, "sources": [m.get("title", "") for m in user_memories[-3:]]}

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("AGENT_PORT", "9123"))
    print(f"Textream Agent starting on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")