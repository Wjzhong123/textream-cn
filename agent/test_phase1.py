#!/usr/bin/env python3
"""
Phase 1 智能体内核服务 - 测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:9123"

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

def main():
    print("🤖 Textream Agent Core v2.0 - 测试套件")
    print("="*60)

    results = []

    # 1. 健康检查
    results.append(("健康检查", test_endpoint("健康检查", "GET", "/api/health")))

    # 2. 状态
    results.append(("服务状态", test_endpoint("服务状态", "GET", "/api/status")))

    # 3. 记忆列表
    results.append(("记忆列表", test_endpoint("记忆列表", "GET", "/api/memory/list")))

    # 4. 添加记忆（需要修复）
    print(f"\n{'='*60}")
    print("测试: 添加记忆")
    print("POST /api/memory/add")
    try:
        # 使用 JSON body
        resp = requests.post(
            f"{BASE_URL}/api/memory/add",
            json={  # 使用 json= 参数，而不是 data=
                "title": "Phase 1 完成",
                "content": "智能体内核 v2.0 重构完成，所有测试通过",
                "tags": ["测试", "Phase1", "里程碑"],
                "importance": 5,
                "user_id": "test_user"
            }
        )
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        results.append(("添加记忆", resp.status_code == 200))
    except Exception as e:
        print(f"❌ 错误: {e}")
        results.append(("添加记忆", False))

    # 5. 记忆搜索
    results.append(("记忆搜索", test_endpoint("记忆搜索", "GET", "/api/memory/search?q=Phase1")))

    # 6. 用户画像
    results.append(("用户画像", test_endpoint("用户画像", "GET", "/api/memory/persona?user_id=test_user")))

    # 7. 错题本
    results.append(("错题本", test_endpoint("错题本", "GET", "/api/memory/error-book?user_id=test_user")))

    # 8. 知识库列表
    results.append(("知识库列表", test_endpoint("知识库列表", "GET", "/api/knowledge/list")))

    # 9. 知识库搜索
    results.append(("知识库搜索", test_endpoint("知识库搜索", "GET", "/api/knowledge/search?q=architecture")))

    # 10. LLM 聊天（未配置 API Key，预期失败）
    results.append(("LLM 聊天（无 Key）", test_endpoint(
        "LLM 聊天（无 Key）",
        "POST",
        "/api/chat",
        json={"message": "你好", "user_id": "test_user"}
    )))

    # 汇总
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}  {name}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！Phase 1 服务运行正常")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
