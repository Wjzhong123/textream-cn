#!/usr/bin/env python3
"""
Phase 2 完整测试脚本

测试内容：
1. One Memory MCP 连接
2. 记忆读写查询
3. 知识库 RAG 检索
4. 弹幕模块导入
"""

import asyncio
import sys
import requests
import json
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:9123"
TEST_USER = "phase2_test_user"

def test_endpoint(name, method, path, **kwargs):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{method} {url}")

    try:
        if method == "GET":
            resp = requests.get(url, **kwargs)
        elif method == "POST":
            resp = requests.post(url, **kwargs)
        elif method == "DELETE":
            resp = requests.delete(url, **kwargs)

        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

async def test_one_memory_mcp():
    """测试 One Memory MCP 连接"""
    print("\n\n🧪 测试 One Memory MCP 连接")
    print("="*60)

    try:
        from agent.one_memory_adapter import MemoryManager

        async with MemoryManager(user_id=TEST_USER) as manager:
            # 1. 写入记忆
            print("\n1. 写入测试记忆...")
            memory_id = await manager.write(
                title="Phase 2 测试记忆",
                summary="这是 Phase 2 的 MCP 连接测试",
                tags=["phase2", "test", "mcp"],
                importance=5,
            )
            print(f"✅ 记忆 ID: {memory_id}")

            if not memory_id:
                print("⚠️  写入返回空 ID（可能是 Mock 模式）")
                return False

            # 2. 查询记忆
            print("\n2. 查询记忆...")
            results = await manager.query("Phase 2", limit=5)
            print(f"✅ 找到 {len(results)} 条记忆")
            for m in results:
                print(f"  - [{m.importance}] {m.title}")

            # 3. 删除记忆
            print(f"\n3. 删除记忆 {memory_id}...")
            deleted = await manager.delete(memory_id)
            print(f"✅ 删除{'成功' if deleted else '失败'}")

        print("\n✅ One Memory MCP 测试通过")
        return True

    except Exception as e:
        print(f"\n❌ One Memory MCP 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_knowledge_rag():
    """测试知识库 RAG 检索"""
    print("\n\n🧪 测试知识库 RAG 检索")
    print("="*60)

    try:
        from agent.agent_core.knowledge.manager import KnowledgeManager

        manager = KnowledgeManager()

        # 1. 添加知识库文件
        print("\n1. 添加知识库文件...")
        result = await manager.add_file(
            name="Phase2测试",
            content="Textream 智能提词器是一个专为直播和演讲打造的 AI 军师工具。",
            tags=["测试", "知识库"],
            importance=3,
        )
        print(f"✅ 添加成功: {result}")

        # 2. 搜索知识库
        print("\n2. 搜索知识库...")
        results = await manager.search("Textream", limit=5)
        print(f"✅ 找到 {len(results)} 条结果")
        for r in results:
            print(f"  - {r.get('name', 'Unknown')}: {r.get('summary', r.get('snippet', ''))[:100]}")

        # 3. 删除知识库文件
        print("\n3. 删除知识库文件...")
        deleted = await manager.delete_file("Phase2测试")
        print(f"✅ 删除{'成功' if deleted else '失败'}")

        print("\n✅ 知识库 RAG 测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 知识库 RAG 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_danmaku_modules():
    """测试弹幕模块"""
    print("\n\n🧪 测试弹幕模块")
    print("="*60)

    try:
        # 1. 测试导入
        print("\n1. 测试模块导入...")
        from agent.agent_core.danmaku import DanmakuCapture, DanmakuResponder, DanmakuProcessor
        print("✅ 模块导入成功")

        # 2. 测试 DanmakuCapture
        print("\n2. 测试 DanmakuCapture...")
        capture = DanmakuCapture()
        print(f"✅ 平台检测: {capture.platform}")
        capture.set_region(x=100, y=100, width=800, height=600)
        print(f"✅ 截图区域设置成功: {capture.region}")

        # 3. 测试 DanmakuResponder
        print("\n3. 测试 DanmakuResponder...")
        responder = DanmakuResponder()
        print("✅ Responder 初始化成功")

        # 4. 测试意图分类
        print("\n4. 测试意图分类...")
        test_cases = [
            ("怎么使用这个功能？", "question"),
            ("太棒了！", "praise"),
            ("建议增加这个功能", "suggestion"),
            ("随机弹幕", "default"),
        ]

        for text, expected_intent in test_cases:
            intent = responder._classify_intent(text)
            status = "✅" if intent == expected_intent else "❌"
            print(f"{status} 「{text}」→ {intent} (期望: {expected_intent})")

        # 5. 测试模板生成
        print("\n5. 测试模板话术生成...")
        for style in ["simple", "detailed", "humor"]:
            response = responder._generate_with_template("怎么使用？", style)
            print(f"✅ [{style}] {response[:80]}...")

        print("\n✅ 弹幕模块测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 弹幕模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoints():
    """测试 API 端点"""
    print("\n\n🧪 测试 API 端点")
    print("="*60)

    results = []

    # 1. 健康检查
    results.append(("健康检查", test_endpoint("健康检查", "GET", "/api/health")))

    # 2. 服务状态
    results.append(("服务状态", test_endpoint("服务状态", "GET", "/api/status")))

    # 3. 记忆列表
    results.append(("记忆列表", test_endpoint("记忆列表", "GET", "/api/memory/list")))

    # 4. 添加记忆
    print(f"\n{'='*60}")
    print("测试: 添加记忆（Phase 2 测试）")
    print("POST /api/memory/add")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/memory/add",
            json={
                "title": "Phase 2 测试",
                "content": "这是一个 Phase 2 的测试记忆",
                "tags": ["phase2", "test"],
                "importance": 5,
                "user_id": TEST_USER
            }
        )
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        results.append(("添加记忆", resp.status_code == 200))
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(("添加记忆", False))

    # 5. 记忆搜索
    results.append(("记忆搜索", test_endpoint("记忆搜索", "GET", "/api/memory/search?q=Phase2")))

    # 6. 用户画像
    results.append(("用户画像", test_endpoint("用户画像", "GET", "/api/memory/persona")))

    # 7. 错题本
    results.append(("错题本", test_endpoint("错题本", "GET", "/api/memory/error-book")))

    # 8. 知识库列表
    results.append(("知识库列表", test_endpoint("知识库列表", "GET", "/api/knowledge/list")))

    # 9. 知识库搜索
    results.append(("知识库搜索", test_endpoint("知识库搜索", "GET", "/api/knowledge/search?q=textream")))

    return results

async def main():
    """主测试函数"""
    print("🤖 Textream Agent Core v2.0 - Phase 2 完整测试")
    print("="*60)
    print(f"测试用户: {TEST_USER}")
    print(f"API 地址: {BASE_URL}")
    print()

    # 检查服务是否运行
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if resp.status_code != 200:
            print(f"❌ 服务未运行或响应异常（状态码: {resp.status_code}）")
            print("请先启动服务:")
            print("  cd /Users/mac/Desktop/textream-cn-master/agent")
            print("  source venv/bin/activate")
            print("  ONE_ROOT=/Users/mac/Desktop/oh-agent-panel python run_agent_v2.py")
            return False
    except Exception as e:
        print(f"❌ 服务未运行: {e}")
        print("请先启动服务:")
        print("  cd /Users/mac/Desktop/textream-cn-master/agent")
        print("  source venv/bin/activate")
        print("  ONE_ROOT=/Users/mac/Desktop/oh-agent-panel python run_agent_v2.py")
        return False

    print("✅ 服务运行正常")
    print()

    # 运行测试
    results = []

    # Phase 1 测试
    print("\n" + "="*60)
    print("📦 Phase 1 基础功能测试")
    print("="*60)
    phase1_results = await test_api_endpoints()
    results.extend(phase1_results)

    # Phase 2 测试
    print("\n\n" + "="*60)
    print("🚀 Phase 2 新功能测试")
    print("="*60)

    # One Memory MCP 测试
    one_memory_pass = await test_one_memory_mcp()
    results.append(("One Memory MCP", one_memory_pass))

    # 知识库 RAG 测试
    rag_pass = await test_knowledge_rag()
    results.append(("知识库 RAG", rag_pass))

    # 弹幕模块测试
    danmaku_pass = await test_danmaku_modules()
    results.append(("弹幕模块", danmaku_pass))

    # 汇总
    print(f"\n\n{'='*60}")
    print("📊 Phase 2 测试结果汇总")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}  {name}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有 Phase 2 测试通过！服务运行正常")
        return True
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
