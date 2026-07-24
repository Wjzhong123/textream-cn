"""
适配器测试脚本
"""

import asyncio


async def test_memory_manager():
    """测试记忆管理器"""
    print("🧪 测试 MemoryManager")
    print("=" * 60)

    from one_memory_adapter import MemoryManager

    async with MemoryManager(user_id="test_user") as manager:
        # 写入记忆
        print("\n1. 写入记忆...")
        memory_id = await manager.write(
            title="测试记忆",
            summary="这是一个测试记忆",
            tags=["测试"],
            importance=3,
        )
        print(f"✅ 记忆 ID: {memory_id}")

        # 查询记忆
        print("\n2. 查询记忆...")
        results = await manager.query("测试", limit=5)
        print(f"✅ 找到 {len(results)} 条记忆")
        for m in results:
            print(f"  - [{m.importance}] {m.title}")

        # 统计
        print("\n3. 记忆统计...")
        stats = await manager.stats()
        print(f"✅ 总记忆数: {stats['total']}")
        print(f"✅ 今日新增: {stats['today']}")

        # 删除
        print(f"\n4. 删除记忆 {memory_id}...")
        deleted = await manager.delete(memory_id)
        print(f"✅ 删除{'成功' if deleted else '失败'}")


async def test_vector_store():
    """测试向量存储"""
    print("\n\n🧪 测试 VectorStore")
    print("=" * 60)

    from one_memory_adapter import VectorStore

    async with VectorStore(collection_name="test") as store:
        # 添加文档
        print("\n1. 添加文档...")
        doc_id = await store.add(
            document_id="test_doc",
            content="Textream 是一个智能提词器",
            metadata={"type": "测试"},
        )
        print(f"✅ 文档 ID: {doc_id}")

        # 搜索
        print("\n2. 语义搜索...")
        results = await store.search("提词器", top_k=3)
        print(f"✅ 找到 {len(results)} 个结果")
        for doc in results:
            print(f"  - [{doc.score:.3f}] {doc.content[:50]}")


async def main():
    """主测试函数"""
    print("🤖 One Memory Python 适配器 - 测试套件")
    print("=" * 60)
    print("⚠️  注意：当前为 Mock 模式（未连接真实的 One Memory 服务）\n")

    try:
        await test_memory_manager()
        await test_vector_store()
        print("\n\n✅ 所有测试通过！")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
