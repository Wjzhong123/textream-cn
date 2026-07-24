#!/usr/bin/env node
/**
 * 前端 API 调用测试脚本
 * 模拟前端对记忆和知识库 API 的调用
 */

const http = require('http');

const BASE_URL = 'http://localhost:9123';

// 颜色输出
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(type, message) {
  const prefix = {
    pass: `${colors.green}✅${colors.reset}`,
    fail: `${colors.red}❌${colors.reset}`,
    info: `${colors.blue}ℹ️${colors.reset}`,
    warn: `${colors.yellow}⚠️${colors.reset}`
  };
  console.log(`${prefix[type]} ${message}`);
}

function httpRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Content-Type': 'application/json',
      }
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          resolve({ status: res.statusCode, data: json });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

async function testMemoryAPI() {
  console.log('\n' + '='.repeat(60));
  console.log('🧠 记忆管理 API 测试');
  console.log('='.repeat(60));

  // 1. 获取记忆列表
  log('info', '测试 GET /api/memory/list');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/memory/list`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `记忆总数: ${res.data.total}`);
      log('info', `当前页: ${res.data.items.length} 条`);
      if (res.data.items.length > 0) {
        console.log('   示例:', JSON.stringify(res.data.items[0], null, 2).split('\n').join('\n   '));
      }
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 2. 搜索记忆
  log('info', '测试 GET /api/memory/search?q=API');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/memory/search?q=API`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `搜索结果: ${res.data.items.length} 条`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 3. 添加记忆
  log('info', '测试 POST /api/memory/add');
  try {
    const res = await httpRequest('POST', `${BASE_URL}/api/memory/add`, {
      title: '前端 API 测试记忆',
      content: '这是前端 API 测试创建的临时记忆',
      tags: ['test', 'frontend'],
      importance: 3,
      user_id: 'default'
    });
    if (res.status === 200 && res.data.status === 'ok') {
      log('pass', `状态码: ${res.status}`);
      log('info', `记忆 ID: ${res.data.id}`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 4. 获取用户画像
  log('info', '测试 GET /api/memory/persona');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/memory/persona`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `标签数: ${res.data.tag_count}`);
      log('info', `记忆数: ${res.data.memory_count}`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 5. 删除刚才添加的记忆
  log('info', '测试 DELETE /api/memory/delete/{id}');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/memory/list`);
    if (res.data.items.length > 0) {
      const lastId = res.data.items[0].id;
      const deleteRes = await httpRequest('DELETE', `${BASE_URL}/api/memory/delete/${lastId}`);
      if (deleteRes.status === 200) {
        log('pass', `状态码: ${deleteRes.status}`);
        log('info', `删除记忆: ${lastId}`);
      } else {
        log('fail', `状态码: ${deleteRes.status}`);
      }
    } else {
      log('warn', '没有记忆可删除');
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }
}

async function testKnowledgeAPI() {
  console.log('\n' + '='.repeat(60));
  console.log('📚 知识库 API 测试');
  console.log('='.repeat(60));

  // 1. 获取知识库列表
  log('info', '测试 GET /api/knowledge/list');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/knowledge/list`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `文档总数: ${res.data.items.length} 个`);
      res.data.items.forEach((item, idx) => {
        log('info', `  ${idx + 1}. ${item.name} (${item.size} bytes)`);
      });
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 2. 搜索知识库
  log('info', '测试 GET /api/knowledge/search?q=architecture');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/knowledge/search?q=architecture`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `搜索结果: ${res.data.items.length} 个`);
      if (res.data.items.length > 0) {
        console.log('   示例:', JSON.stringify(res.data.items[0], null, 2).split('\n').join('\n   '));
      }
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 3. 搜索知识库（另一个关键词）
  log('info', '测试 GET /api/knowledge/search?q=tips');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/knowledge/search?q=tips`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `搜索结果: ${res.data.items.length} 个`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 4. 添加知识库文档
  log('info', '测试 POST /api/knowledge/add');
  try {
    const res = await httpRequest('POST', `${BASE_URL}/api/knowledge/add`, {
      name: 'frontend_test',
      content: '这是一个前端 API 测试文档，用于验证知识库添加功能是否正常工作。'
    });
    if (res.status === 200 && res.data.status === 'ok') {
      log('pass', `状态码: ${res.status}`);
      log('info', `文档 ID: ${res.data.id}`);
      log('info', `来源: ${res.data.source}`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 5. 验证添加后的列表
  log('info', '验证添加后的知识库列表');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/knowledge/list`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `文档总数: ${res.data.items.length} 个`);

      // 查找我们刚添加的文档
      const addedDoc = res.data.items.find(item => item.name === 'frontend_test');
      if (addedDoc) {
        log('pass', '找到刚添加的文档');
      } else {
        log('warn', '未找到刚添加的文档');
      }
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  // 6. 删除测试文档
  log('info', '测试 DELETE /api/knowledge/delete/{name}');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/knowledge/list`);
    const testDoc = res.data.items.find(item => item.name === 'frontend_test');
    if (testDoc) {
      const deleteRes = await httpRequest('DELETE', `${BASE_URL}/api/knowledge/delete/frontend_test`);
      if (deleteRes.status === 200) {
        log('pass', `状态码: ${deleteRes.status}`);
        log('info', '删除文档成功');
      } else {
        log('fail', `状态码: ${deleteRes.status}`);
      }
    } else {
      log('warn', '没有找到测试文档');
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }
}

async function testHealthCheck() {
  console.log('\n' + '='.repeat(60));
  console.log('🏥 健康检查测试');
  console.log('='.repeat(60));

  log('info', '测试 GET /api/health');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/health`);
    if (res.status === 200 && res.data.status === 'ok') {
      log('pass', `状态码: ${res.status}`);
      log('info', `状态: ${res.data.status}`);
      log('info', `版本: ${res.data.version}`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }

  log('info', '测试 GET /api/status');
  try {
    const res = await httpRequest('GET', `${BASE_URL}/api/status`);
    if (res.status === 200) {
      log('pass', `状态码: ${res.status}`);
      log('info', `Agent: ${res.data.agent}`);
      log('info', `版本: ${res.data.version}`);
      log('info', `Memory: ${res.data.memory.enabled ? '启用' : '禁用'}`);
      log('info', `Knowledge: ${res.data.knowledge.enabled ? '启用' : '禁用'}`);
    } else {
      log('fail', `状态码: ${res.status}`);
    }
  } catch (e) {
    log('fail', `请求失败: ${e.message}`);
  }
}

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🚀 前端 API 测试（模拟前端调用）');
  console.log('='.repeat(60));
  console.log(`后端地址: ${BASE_URL}`);
  console.log(`测试时间: ${new Date().toLocaleString('zh-CN')}`);

  await testHealthCheck();
  await testMemoryAPI();
  await testKnowledgeAPI();

  console.log('\n' + '='.repeat(60));
  console.log('✅ 测试完成');
  console.log('='.repeat(60) + '\n');
}

main().catch(console.error);
