---
name: moat
description: Moat — AI 编码护城河。每次改代码前后必须运行的门禁检查。
---

# Moat — AI 编码护城河

## ⚠️ 重要：你必须遵守以下工作流

> 你是 AI 编码工具，**不是人类开发者**。人类可以靠经验判断，你需要靠工具检查。
> **不执行 moat check 就改代码，等于闭着眼睛开车。**

## 强制工作流

### 第 1 步：读项目记忆
```bash
cat .moat/ai_context.md
```

### 第 2 步：改代码前 — 跑 moat check
```bash
moat check
```
如果失败 → 先修，不要跳过。

### 第 3 步：改代码

### 第 4 步：改代码后 — 再跑 moat check
```bash
moat check
```
如果失败 → 修到通过。

### 第 5 步：提交
```bash
git add .
git commit -m "描述你的改动"
```

## 禁止
- ❌ 不要跳过 moat check
- ❌ 不要使用 `git commit --no-verify`（会被拦截）
- ❌ 不要"我以为没问题"——跑 moat check 确认

## 为什么？
moat check 会检查文件完整性、API 存活、跨系统关联、基线退化。
这些你靠"看代码"看不出来，必须跑工具。
