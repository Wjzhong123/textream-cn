## Moat 护城河

Moat 是 AI 编码护城河，防止 AI 改代码时搞坏系统。

### 铁律
1. 改代码**前**跑一次 `moat check`，改代码**后**再跑一次。两次都通过才能提交。
2. 任何 AI 工具接手项目，第一件事就是跑 `moat check`。
3. 如果 `moat check` 报错，修到通过为止，不许跳过。
4. **禁止使用 `git commit --no-verify` 绕过检查**。会被拦截。

### 项目记忆（moat-memory）
这个项目积累了一些记忆，改代码前先查看：
```bash
# 查看项目红线（架构规则、编码边界）
moat memory list redlines

# 查看踩坑记录（以前 MOAT 检查失败的地方）
moat memory list lessons

# 查看经验模版
moat memory list templates
```

**自动同步的文件**: `.moat/ai_context.md` 包含上述全部记忆，AI 工具可自动读取。

### 命令
```bash
# 改代码前/后检查（12秒）
moat check

# 实时监控日志错误
moat watch --log logs/backend.log

# Web 错误看板
moat dashboard

# 更新基线（允许的改动后）
moat baseline save
```

### 四层防线
| 层级 | 作用 |
|------|------|
| L1 存活 | 骨架完整、API 存活 |
| L2 结构 | API 返回字段符合契约 |
| L3 关联 | 改了 A B 还能用 |
| L4 基线 | 文件数/路由数不退化 |
