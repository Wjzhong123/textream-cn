"""
向量存储 - 知识库向量化

基于 One Memory 的向量能力
"""

from __future__ import annotations

from typing import Any

from .client import OneMemoryClient
from .exceptions import ValidationError


class Document:
    """文档对象"""

    def __init__(
        self,
        id: str,
        content: str,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<Document id={self.id} score={self.score:.3f}>"


class VectorStore:
    """
    向量存储

    用于知识库的向量化和语义检索
    """

    def __init__(
        self,
        collection_name: str = "default",
        embedder: str = "local",
        mcp_url: str = "http://localhost:3000",
    ):
        """
        初始化向量存储

        Args:
            collection_name: 集合名称
            embedder: 嵌入模型（"local" 或 "openai"）
            mcp_url: One Memory MCP 服务地址
        """
        self.collection_name = collection_name
        self.embedder = embedder
        self.client = OneMemoryClient(mcp_url=mcp_url)

    async def __aenter__(self):
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    async def add(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        添加文档

        Args:
            document_id: 文档 ID
            content: 文档内容
            metadata: 元数据

        Returns:
            文档 ID
        """
        arguments = {
            "id": document_id,
            "content": content,
            "collection": self.collection_name,
            "metadata": metadata or {},
        }

        result = await self.client.call_tool("vector_add", arguments)
        return result.get("id", document_id)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[Document]:
        """
        语义搜索

        Args:
            query: 搜索查询
            top_k: 返回结果数
            threshold: 相似度阈值

        Returns:
            文档列表（按相关度排序）
        """
        arguments = {
            "query": query,
            "collection": self.collection_name,
            "topK": top_k,
            "threshold": threshold,
        }

        result = await self.client.call_tool("vector_search", arguments)
        docs_data = result.get("documents", [])

        return [Document(**d) for d in docs_data]

    async def delete(self, document_id: str) -> bool:
        """
        删除文档

        Args:
            document_id: 文档 ID

        Returns:
            是否删除成功
        """
        result = await self.client.call_tool("vector_delete", {"id": document_id})
        return result.get("status") == "deleted"
