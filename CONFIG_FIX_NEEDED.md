# 🔧 配置修复补丁 - SettingsModal.tsx

**问题**: LLM 和 One Memory 配置缺少必要的参数
**修复时间**: 2026-07-25
**状态**: ⏳ 待手动应用

---

## 📋 需要修复的问题

### 问题 1: LLM 配置缺少 Base URL

**当前配置**:
```typescript
interface ServerConfig {
  llmProvider: string;      // ✅ 提供商
  llmApiKey: string;        // ✅ API Key
  llmModel: string;         // ✅ 模型名称
  // ❌ 缺少: Base URL
}
```

**问题**: 不同的 LLM 提供商需要不同的 API 端点

**修复**: 添加 `llmBaseUrl` 字段

---

### 问题 2: One Memory 配置缺少 API Key

**当前配置**:
```typescript
interface ServerConfig {
  useOneMemory: boolean;    // ✅ 启用开关
  oneRoot: string;          // ✅ One OS 根目录
  // ❌ 缺少: One API Key
}
```

**问题**: One Memory 向量检索需要 API Key 才能连接 One OS

**修复**: 添加 `oneApiKey` 字段

---

## 🔧 修复方案

### 方案 A: 自动检测 Base URL（推荐）

**优点**: 用户体验更好，无需手动输入
**实现**: 根据选择的提供商自动填充 Base URL

```typescript
const LLM_BASE_URLS = {
  siliconflow: 'https://api.siliconflow.cn/v1',
  openai: 'https://api.openai.com/v1',
  deepseek: 'https://api.deepseek.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
};

// 当用户选择提供商时自动填充
const handleProviderChange = (provider: string) => {
  setFormData(prev => ({
    ...prev,
    llmProvider: provider,
    llmBaseUrl: LLM_BASE_URLS[provider] || '',
  }));
};
```

---

### 方案 B: 允许自定义 Base URL（灵活）

**优点**: 支持自定义 API 端点（如代理、私有部署）
**实现**: 添加 Base URL 输入框

```typescript
<div>
  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
    API 地址
  </label>
  <input
    type="text"
    value={formData.llmBaseUrl}
    onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
    placeholder="https://api.siliconflow.cn/v1"
    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
  />
</div>
```

---

### 方案 C: 混合方案（最佳实践）

**实现**: 自动填充 + 允许手动修改

```typescript
<div>
  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
    API 地址
  </label>
  <input
    type="text"
    value={formData.llmBaseUrl}
    onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
  />
  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
    已自动填充 {provider} 的默认地址，可以手动修改
  </p>
</div>
```

---

## 📝 One Memory API Key

### 需要添加的字段

```typescript
interface ServerConfig {
  useOneMemory: boolean;    // ✅ 已有
  oneRoot: string;          // ✅ 已有
  oneApiKey: string;        // ❌ 新增
}
```

### One Memory API Key 来源

**来源 1: One OS 设置**
- 打开 One OS 应用
- 进入设置 → API 密钥
- 复制 API Key

**来源 2: One Cloud 控制台**
- 访问 https://one.ai/
- 登录 → 账户设置 → API 密钥
- 生成新密钥

### 配置 UI

```typescript
{formData.useOneMemory && (
  <div>
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      One API Key
    </label>
    <input
      type="password"
      value={formData.oneApiKey}
      onChange={(e) => handleChange('oneApiKey', e.target.value)}
      placeholder="one_xxxxx"
      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
    />
    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
      从 One OS 设置或 One Cloud 控制台获取
    </p>
  </div>
)}
```

---

## 🎯 推荐修复步骤

### Step 1: 更新接口定义

在 `SettingsModal.tsx` 和 `App.tsx` 中更新 `ServerConfig`:

```typescript
interface ServerConfig {
  url: string;
  llmProvider: string;
  llmBaseUrl: string;      // 新增
  llmApiKey: string;
  llmModel: string;
  useOneMemory: boolean;
  oneRoot: string;
  oneApiKey: string;       // 新增
}
```

### Step 2: 添加默认值

```typescript
const defaultConfig: ServerConfig = {
  url: 'http://localhost:9123',
  llmProvider: 'siliconflow',
  llmBaseUrl: 'https://api.siliconflow.cn/v1',  // 新增
  llmApiKey: '',
  llmModel: 'Qwen/Qwen2.5-72B-Instruct',
  useOneMemory: false,
  oneRoot: '/Users/mac/Desktop/oh-agent-panel',
  oneApiKey: '',                                  // 新增
};
```

### Step 3: 添加 Base URL 输入框

在 LLM 配置部分添加：

```typescript
<div>
  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
    API 地址
  </label>
  <input
    type="text"
    value={formData.llmBaseUrl}
    onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
    placeholder="https://api.siliconflow.cn/v1"
    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
  />
  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
    {getProviderHint(formData.llmProvider)}
  </p>
</div>
```

### Step 4: 添加 One API Key 输入框

在 One Memory 配置部分添加：

```typescript
{formData.useOneMemory && (
  <>
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        One API Key
      </label>
      <input
        type="password"
        value={formData.oneApiKey}
        onChange={(e) => handleChange('oneApiKey', e.target.value)}
        placeholder="one_xxxxx"
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
      />
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        One Root
      </label>
      <input
        type="text"
        value={formData.oneRoot}
        onChange={(e) => handleChange('oneRoot', e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg..."
      />
    </div>
  </>
)}
```

### Step 5: 后端支持

确保后端可以读取这些配置：

在 `agent/agent_core/server.py` 或 `agent/run_agent_v2.py` 中添加环境变量支持：

```python
# 从环境变量读取配置
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
ONE_API_KEY = os.getenv("ONE_API_KEY", "")

# 初始化 LLM Router 时传入 base_url
llm_router = LLMRouter(base_url=LLM_BASE_URL)

# 初始化 One Memory 时传入 api_key
if USE_ONE_MEMORY and ONE_API_KEY:
    one_memory_mgr = MemoryManager(api_key=ONE_API_KEY)
```

---

## 📊 各提供商 Base URL 参考

| 提供商 | Base URL | 说明 |
|--------|---------|------|
| **SiliconFlow** | `https://api.siliconflow.cn/v1` | 国内推荐 |
| **OpenAI** | `https://api.openai.com/v1` | 国际标准 |
| **DeepSeek** | `https://api.deepseek.com/v1` | 国产替代 |
| **Anthropic** | `https://api.anthropic.com/v1` | Claude 官方 |
| **Azure OpenAI** | `https://{resource}.openai.azure.com` | 企业版 |
| **自定义代理** | `http://localhost:8000/v1` | 本地代理 |

---

## ✅ 验证清单

修复后需要验证：

- [ ] LLM Base URL 自动填充正确
- [ ] 可以手动修改 Base URL
- [ ] One API Key 可以输入
- [ ] 配置保存到 localStorage
- [ ] 后端可以读取这些配置
- [ ] LLM 请求成功发送到正确的地址
- [ ] One Memory 可以连接（配置 API Key 后）

---

## 🚀 快速修复代码

由于文件系统权限问题，请手动将以下代码应用到 `SettingsModal.tsx`：

### 1. 更新接口定义

```typescript
interface ServerConfig {
  url: string;
  llmProvider: string;
  llmBaseUrl: string;      // 新增
  llmApiKey: string;
  llmModel: string;
  useOneMemory: boolean;
  oneRoot: string;
  oneApiKey: string;       // 新增
}
```

### 2. 更新默认配置

```typescript
const defaultConfig: ServerConfig = {
  url: 'http://localhost:9123',
  llmProvider: 'siliconflow',
  llmBaseUrl: 'https://api.siliconflow.cn/v1',
  llmApiKey: '',
  llmModel: 'Qwen/Qwen2.5-72B-Instruct',
  useOneMemory: false,
  oneRoot: '/Users/mac/Desktop/oh-agent-panel',
  oneApiKey: '',
};
```

### 3. 添加 Base URL 输入框

在 LLM 配置部分，API Key 输入框之前添加：

```typescript
<div>
  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
    API 地址
  </label>
  <input
    type="text"
    value={formData.llmBaseUrl}
    onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
    placeholder="https://api.siliconflow.cn/v1"
    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
  />
</div>
```

### 4. 添加 One API Key 输入框

在 One Memory 配置部分，启用开关之后添加：

```typescript
{formData.useOneMemory && (
  <>
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        One API Key
      </label>
      <input
        type="password"
        value={formData.oneApiKey}
        onChange={(e) => handleChange('oneApiKey', e.target.value)}
        placeholder="one_xxxxx"
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      />
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
        从 One OS 设置或 One Cloud 控制台获取
      </p>
    </div>
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        One Root
      </label>
      <input
        type="text"
        value={formData.oneRoot}
        onChange={(e) => handleChange('oneRoot', e.target.value)}
        placeholder="/Users/mac/Desktop/oh-agent-panel"
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      />
    </div>
  </>
)}
```

---

**创建时间**: 2026-07-25 06:15
**待手动应用**: 由于文件系统权限限制，请手动应用上述修复
