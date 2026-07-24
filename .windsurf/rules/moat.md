# Moat — AI 编码护城河

## 铁律
- 改代码前跑 `moat check`，改代码后跑 `moat check`
- 不通过不允许提交
- 禁止使用 `git commit --no-verify` 绕过

## 项目记忆
改代码前先查看:
- `moat memory list redlines` — 项目红线
- `moat memory list lessons` — 踩坑记录
- `moat memory list templates` — 经验模版
- `.moat/ai_context.md` — 自动同步的记忆快照

## 命令
```bash
moat check           # 改代码前/后检查
moat dashboard       # Web 看板
moat memory list     # 查看项目记忆
```
