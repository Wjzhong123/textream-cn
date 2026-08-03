# textream-cn-master 架构蓝图（北极星指标）

> **蓝图版本**: v1.0.0-20260803
> **生成时间**: 2026-08-03T10:13:45.855383
> **确认时间**: 2026-08-03T10:13:57.418261
> **项目语言**: python

## 📋 目录职责映射

| 目录 | 职责类型 | 描述 | 文件数 | 代码行数 |
|------|---------|------|--------|---------|
| . | root | 项目根目录 | 115 | 31773 |
| Textream | unknown | 自动识别: unknown | 1 | 87 |
| Textream/Textream | unknown | 自动识别: unknown | 20 | 10479 |
| Textream/Textream.xcodeproj | unknown | 自动识别: unknown | 0 | 0 |
| Textream/Textream.xcodeproj/project.xcworkspace | unknown | 自动识别: unknown | 0 | 0 |
| Textream/Textream.xcodeproj/project.xcworkspace/xcshareddata | unknown | 自动识别: unknown | 0 | 0 |
| Textream/Textream.xcodeproj/project.xcworkspace/xcshareddata/swiftpm | unknown | 自动识别: unknown | 0 | 0 |
| Textream/Textream.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/configuration | unknown | 自动识别: unknown | 0 | 0 |
| Textream/Textream/Assets.xcassets | unknown | 自动识别: unknown | 1 | 6 |
| Textream/Textream/Assets.xcassets/AccentColor.colorset | unknown | 自动识别: unknown | 1 | 11 |
| Textream/Textream/Assets.xcassets/AppIcon.appiconset | unknown | 自动识别: unknown | 1 | 68 |
| Textream/Textream/Fonts | unknown | 自动识别: unknown | 0 | 0 |
| agent | unknown | 自动识别: unknown | 5 | 584 |
| agent/TextreamAgent.app | unknown | 自动识别: unknown | 0 | 0 |
| agent/TextreamAgent.app/Contents | unknown | 自动识别: unknown | 0 | 0 |
| agent/TextreamAgent.app/Contents/MacOS | unknown | 自动识别: unknown | 0 | 0 |
| agent/TextreamAgent.app/Contents/Resources | unknown | 自动识别: unknown | 0 | 0 |
| agent/TextreamAgent.app/Contents/_CodeSignature | unknown | 自动识别: unknown | 0 | 0 |
| agent/agent_core | unknown | 自动识别: unknown | 4 | 782 |
| agent/agent_core/danmaku | unknown | 自动识别: unknown | 4 | 1011 |
| agent/agent_core/danmaku/ocr_scripts | unknown | 自动识别: unknown | 1 | 77 |
| agent/agent_core/knowledge | unknown | 自动识别: unknown | 2 | 284 |
| agent/agent_core/llm | unknown | 自动识别: unknown | 3 | 233 |
| agent/agent_core/memory | unknown | 自动识别: unknown | 4 | 955 |
| agent/captiocr_adapter | unknown | 自动识别: unknown | 3 | 276 |
| agent/one_memory_adapter | unknown | 自动识别: unknown | 8 | 1169 |
| agent/scripts | unknown | 自动识别: unknown | 1 | 44 |
| agent/web-console-dist | unknown | 自动识别: unknown | 1 | 17 |
| agent/web-console-dist/assets | unknown | 自动识别: unknown | 2 | 5702 |
| docs | docs | 文档目录 | 1 | 2208 |
| docs/learnings | docs | 文档目录 | 1 | 23 |
| tests | test | 测试层 | 0 | 0 |
| tests/moat | test | 测试层 | 2 | 146 |
| textream-windows | unknown | 自动识别: unknown | 5 | 607 |
| textream-windows/assets | unknown | 自动识别: unknown | 0 | 0 |
| web-console | unknown | 自动识别: unknown | 10 | 367 |
| web-console/public | unknown | 自动识别: unknown | 0 | 0 |
| web-console/src | unknown | 自动识别: unknown | 3 | 259 |
| web-console/src/assets | unknown | 自动识别: unknown | 0 | 0 |
| web-console/src/components | unknown | 自动识别: unknown | 11 | 1769 |
| web-console/src/hooks | unknown | 自动识别: unknown | 2 | 211 |
| web-console/src/stores | unknown | 自动识别: unknown | 1 | 80 |
| web-console/src/types | utility | 通用工具（Helpers、Utils） | 1 | 59 |
| web-console/src/utils | utility | 通用工具（Helpers、Utils） | 1 | 107 |

## 🏗️ 分层规则

| 规则 ID | 来源层 | 目标层 | 是否允许 | 描述 |
|---------|--------|--------|---------|------|


## 🎯 北极星指标目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 架构合规率 | ≥ 95% | 遵循分层规则的调用占比 |
| 依赖枢纽数（高危） | ≤ 5 | 被 ≥10 个模块依赖的文件 |
| 依赖枢纽数（中危） | ≤ 10 | 被 5-9 个模块依赖的文件 |
| 技术债务增速 | ≤ 0 | TODO/FIXME 净变化率 |

## 📊 当前健康度

- **架构合规率**: 0.0% (目标: ≥ 95%) ❌
- **高危依赖枢纽**: 0 (目标: ≤ 5) ✅
- **中危依赖枢纽**: 0 (目标: ≤ 10) ✅

## 🧭 架构约束（写入代码时）

1. **必须遵守**目录职责边界
2. **禁止**跨层调用（如 entry 直接调 data）
3. **禁止**新增未备案的依赖
4. **谨慎修改**依赖枢纽文件

---

**注意**: 如需修改此蓝图，请运行 `moat north_star edit` 或重新运行 `moat north_star init`。
