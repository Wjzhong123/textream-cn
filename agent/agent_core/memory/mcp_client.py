"""
MCP Client — 通过子进程调用 AI-memory (One Memory) MCP 服务器

本模块启动 memory-mcp 的 Node.js MCP 服务器作为子进程，
通过 JSON-RPC over stdio 与其通信，暴露 clean Python API。
"""

import asyncio
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger("mcp_client")

# ── 路径常量 ──

TEXTREAM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_MCP_DIR = TEXTREAM_ROOT / "third_party" / ".codegraph"
DEFAULT_MCP_ROOT = TEXTREAM_ROOT / "third_party" / "AI-memory"


class MCPTimeoutError(Exception):
    """MCP 子进程响应超时"""


class MCPError(Exception):
    """MCP 返回 error 响应"""


class MCPClient:
    """
    管理 memory-mcp 子进程，封装 JSON-RPC 通信。

    用法:
        async with MCPClient() as mcp:
            await mcp.write(title="测试", summary="hello", user_id="default")
            results = await mcp.query("测试", user_id="default")
    """

    def __init__(
        self,
        codegraph_dir: str | os.PathLike | None = None,
        mcp_root: str | os.PathLike | None = None,
        embedder: str = "simple",
    ):
        self.codegraph_dir = pathlib.Path(codegraph_dir or DEFAULT_MCP_DIR)
        self.mcp_root = pathlib.Path(mcp_root or DEFAULT_MCP_ROOT)
        self.embedder = embedder
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_db(self) -> None:
        """确保 codegraph.db 存在（创建空文件，首次启动时 schema 自动迁移）"""
        db_path = self.codegraph_dir / "codegraph.db"
        if not db_path.exists():
            self.codegraph_dir.mkdir(parents=True, exist_ok=True)
            db_path.touch()
            logger.info("已创建空 codegraph.db: %s", db_path)

    async def _start_process(self) -> None:
        """启动 MCP 子进程"""
        await self._ensure_db()

        index_ts = self.mcp_root / "packages" / "memory-mcp" / "src" / "index.ts"
        if not index_ts.exists():
            raise FileNotFoundError(f"MCP server source not found: {index_ts}")

        # 用 npx tsx 运行 TypeScript 源码
        tsx_path = self.mcp_root / "node_modules" / ".bin" / "tsx"
        if not tsx_path.exists():
            # fallback 到系统 npx
            tsx_cmd = ["npx", "tsx", str(index_ts)]
        else:
            tsx_cmd = [str(tsx_path), str(index_ts)]

        cmd = [
            *tsx_cmd,
            "--codegraph-dir", str(self.codegraph_dir),
            "--embedder", self.embedder,
        ]

        logger.info("启动 MCP server: %s", " ".join(cmd))

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.mcp_root),
        )

        # 同时启动 stderr 读取（不会阻塞）
        self._stderr_task = asyncio.create_task(self._read_stderr())

        # 稍等初始化
        await asyncio.sleep(2)

        # 检查进程是否还活着
        if self._process.returncode is not None:
            stderr_out = await self._read_stderr_all()
            raise RuntimeError(
                f"MCP server exited early (code={self._process.returncode}): {stderr_out}"
            )

    async def _read_stderr(self) -> None:
        """持续读取 stderr 日志"""
        assert self._process is not None
        assert self._process.stderr is not None
        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug("[MCP stderr] %s", text)
        except Exception:
            pass

    async def _read_stderr_all(self) -> str:
        """读取全部 stderr（进程已退出时使用）"""
        assert self._process is not None
        assert self._process.stderr is not None
        try:
            remaining = await asyncio.wait_for(
                self._process.stderr.read(), timeout=2
            )
            return remaining.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            return "(stderr read timeout)"

    async def initialize(self) -> None:
        """发送 initialize 请求，等待服务器就绪"""
        result = await self._call("initialize", {})
        self._initialized = True
        logger.info(
            "MCP server initialized: %s v%s",
            result.get("serverInfo", {}).get("name", "?"),
            result.get("serverInfo", {}).get("version", "?"),
        )

    async def _call(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float = 30.0,
    ) -> Any:
        """发送 JSON-RPC 请求并等待响应"""
        assert self._process is not None
        assert self._process.stdin is not None
        assert self._process.stdout is not None

        request_id = str(uuid.uuid4())[:8]
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        payload = json.dumps(request, ensure_ascii=False) + "\n"

        async with self._lock:
            self._process.stdin.write(payload.encode("utf-8"))
            await self._process.stdin.drain()

            # 读取响应（逐行读取直到找到我们的 id）
            start = time.monotonic()
            while True:
                elapsed = time.monotonic() - start
                if elapsed > timeout:
                    raise MCPTimeoutError(
                        f"MCP 调用 {method} 超时 ({timeout}s)"
                    )

                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=timeout - elapsed,
                )
                if not line:
                    raise MCPError("MCP server 已关闭连接")

                try:
                    response = json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    logger.warning("MCP 收到非 JSON 输出（忽略）: %s", line[:200])
                    continue

                if response.get("id") != request_id:
                    # 不是我们的响应，可能是之前的请求还在返回
                    continue

                if "error" in response:
                    err = response["error"]
                    raise MCPError(
                        f"MCP 调用 {method} 失败: [{err.get('code')}] {err.get('message')}"
                    )

                return response.get("result")

    async def ping(self) -> bool:
        """Ping 服务器"""
        try:
            await self._call("ping", {}, timeout=5)
            return True
        except Exception:
            return False

    # ── 工具封装 ──

    async def write(
        self,
        title: str,
        summary: str = "",
        body: str = "",
        importance: int = 5,
        tags: Optional[list[str]] = None,
        node_type: str = "memory_entry",
        user_id: str = "default",
        ttl_days: Optional[int] = None,
    ) -> dict[str, Any]:
        """写入一条记忆"""
        params = {
            "title": title,
            "summary": summary,
            "body": body,
            "importance": importance,
            "tags": tags or [],
            "type": node_type,
            "user_id": user_id,
        }
        if ttl_days is not None:
            params["ttl_days"] = ttl_days
        result = await self._call("tools/call", {
            "name": "memory_write",
            "arguments": params,
        })
        # 解析 MCP 响应：{content: [{type: "text", text: '{"id":"...","title":"..."}'}]}
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "{}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return {"id": "?", "title": title, "status": "stored"}

    @staticmethod
    def _parse_query_response(text: str) -> list[dict[str, Any]]:
        """
        解析 MCP memory_query 返回的格式化文本为结构化列表。

        MCP 服务器返回格式：
            [1] 标题
                重要性: 3/10  |  评分: 0.40
                摘要: 摘要文本
                标签: #tag1 #tag2

            [2] 标题
                ...
        """
        if not text or text.strip() == "[]":
            return []

        # 先尝试 JSON 解析（兼容性）
        text = text.strip()
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        results = []
        # 按空行分割条目
        entries = re.split(r'\n\s*\n', text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            item: dict[str, Any] = {
                "id": "", "title": "", "summary": "",
                "importance": 3, "score": 0.0, "tags": [],
            }

            # 第一行: [N] Title
            lines = entry.split('\n')
            header = lines[0].strip()
            m = re.match(r'\[\d+\]\s*(.*)', header)
            if m:
                item["title"] = m.group(1).strip()

            # 后续行: 键: 值
            for line in lines[1:]:
                line = line.strip()
                if line.startswith("重要性:"):
                    m = re.search(r'(\d+)/10', line)
                    if m:
                        item["importance"] = int(m.group(1))
                    m = re.search(r'评分:\s*([\d.]+)', line)
                    if m:
                        item["score"] = float(m.group(1))
                elif line.startswith("摘要:"):
                    item["summary"] = line[len("摘要:"):].strip()
                elif line.startswith("标签:"):
                    tags_str = line[len("标签:"):].strip()
                    item["tags"] = [t.strip().lstrip("#") for t in tags_str.split() if t.strip()]

            # 如果只有标题没有摘要，用标题当摘要
            if not item["summary"] and item["title"]:
                item["summary"] = item["title"]

            results.append(item)

        return results

    async def query(
        self,
        query_text: str,
        limit: int = 5,
        min_importance: Optional[int] = None,
        user_id: str = "default",
    ) -> list[dict[str, Any]]:
        """语义搜索记忆"""
        params: dict[str, Any] = {
            "query": query_text,
            "limit": limit,
            "user_id": user_id,
        }
        if min_importance is not None:
            params["min_importance"] = min_importance
        result = await self._call("tools/call", {
            "name": "memory_query",
            "arguments": params,
        })
        # result.content[0].text 包含 MCP 格式化文本
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "[]")
            return self._parse_query_response(text)
        return []

    async def dream(self, dry_run: bool = False) -> dict[str, Any]:
        """触发梦境整理"""
        return await self._call("tools/call", {
            "name": "memory_dream",
            "arguments": {"dry_run": dry_run},
        })

    async def health(self) -> dict[str, Any]:
        """健康检查"""
        return await self._call("tools/call", {
            "name": "memory_health",
            "arguments": {"format": "json"},
        })

    async def close(self) -> None:
        """关闭 MCP 子进程"""
        if self._process and self._process.returncode is None:
            try:
                self._process.stdin.close()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                self._process.kill()
                await self._process.wait()
        self._initialized = False

    async def __aenter__(self) -> "MCPClient":
        await self._start_process()
        await self.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ── 兼容同步接口 ──

class SyncMCPClient:
    """同步版本的 MCP 客户端（用于不支持 async 的代码路径）"""

    def __init__(
        self,
        codegraph_dir: str | os.PathLike | None = None,
        mcp_root: str | os.PathLike | None = None,
        embedder: str = "simple",
    ):
        self._codegraph_dir = pathlib.Path(codegraph_dir or DEFAULT_MCP_DIR)
        self._mcp_root = pathlib.Path(mcp_root or DEFAULT_MCP_ROOT)
        self._embedder = embedder
        self._process: Optional[subprocess.Popen] = None

    def _ensure_db(self) -> None:
        db_path = self._codegraph_dir / "codegraph.db"
        if not db_path.exists():
            self._codegraph_dir.mkdir(parents=True, exist_ok=True)
            db_path.touch()

    def _call(self, method: str, params: dict[str, Any]) -> Any:
        """同步调用 MCP（每次调用启动/关闭进程，用于低频率场景）"""
        self._ensure_db()
        index_ts = self._mcp_root / "packages" / "memory-mcp" / "src" / "index.ts"
        cmd = [
            "npx", "tsx", str(index_ts),
            "--codegraph-dir", str(self._codegraph_dir),
            "--embedder", self._embedder,
        ]

        request_id = str(uuid.uuid4())[:8]
        if method == "tools/call":
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {},
            }
            init_payload = json.dumps(request, ensure_ascii=False) + "\n"

            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
            call_payload = json.dumps(request, ensure_ascii=False) + "\n"
            full_input = init_payload + call_payload
        else:
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
            full_input = json.dumps(request, ensure_ascii=False) + "\n"

        try:
            result = subprocess.run(
                cmd,
                input=full_input,
                capture_output=True,
                text=True,
                cwd=str(self._mcp_root),
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise MCPTimeoutError(f"MCP 调用 {method} 超时")

        if result.returncode != 0:
            raise MCPError(f"MCP 进程退出 (code={result.returncode}): {result.stderr}")

        # 解析最后一行输出（可能有 stderr log 混在中间）
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            raise MCPError(f"MCP 无输出: stderr={result.stderr[:500]}")

        for line in reversed(lines):
            try:
                response = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise MCPError(f"MCP 无有效 JSON 输出: {result.stdout[:500]}")

        if "error" in response:
            err = response["error"]
            raise MCPError(
                f"MCP 调用 {method} 失败: [{err.get('code')}] {err.get('message')}"
            )
        return response.get("result")

    def write(
        self,
        title: str,
        summary: str = "",
        body: str = "",
        importance: int = 5,
        tags: Optional[list[str]] = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        return self._call("tools/call", {
            "name": "memory_write",
            "arguments": {
                "title": title,
                "summary": summary,
                "body": body,
                "importance": importance,
                "tags": tags or [],
                "user_id": user_id,
            },
        })

    def query(self, query_text: str, limit: int = 5, user_id: str = "default") -> list[dict[str, Any]]:
        result = self._call("tools/call", {
            "name": "memory_query",
            "arguments": {
                "query": query_text,
                "limit": limit,
                "user_id": user_id,
            },
        })
        content = result.get("content", [])
        if content:
            text = content[0].get("text", "[]")
            return MCPClient._parse_query_response(text)
        return []


# ── 快速测试 ──

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    async def test():
        try:
            async with MCPClient() as mcp:
                print("✅ MCP server initialized")

                # Test write
                result = await mcp.write(
                    title="测试记忆条目",
                    summary="这是从 Textream 写入的测试记忆",
                    body="详细内容：测试 AI-memory 集成",
                    importance=8,
                    tags=["测试", "集成"],
                    user_id="test_user",
                )
                print(f"✅ Write result: {result}")

                # Test query
                results = await mcp.query("测试记忆", user_id="test_user")
                print(f"✅ Query results ({len(results)}):")
                for r in results:
                    print(f"   - [{r.get('importance', 0)}] {r.get('title', '?')}: {r.get('summary', '')[:60]}")

                # Test health
                health = await mcp.health()
                print(f"✅ Health: {json.dumps(health, ensure_ascii=False, indent=2)[:300]}")

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(test())
