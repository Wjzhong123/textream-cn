# Textream 中文版

Textream 提词器应用的中文本地化版本

> 📦 **GitHub仓库：** https://github.com/Wjzhong123/textream-cn
> 🌍 **原项目：** https://github.com/f/textream

## ✨ 特性

- ✅ 完整的中文界面翻译
- ✅ 自动检测系统语言（中文/英文）
- ✅ 100+ UI字符串本地化
- ✅ 支持所有原始功能

## 🎯 已完成的工作

1. ✅ 创建了完整的中文本地化系统 `Localizable.swift`
2. ✅ 修改了所有Swift文件以使用本地化字符串：
   - ContentView.swift - 主界面
   - SettingsView.swift - 设置界面
   - NotchOverlayController.swift - 提词器覆盖层
   - ExternalDisplayController.swift - 外部显示
   - TextreamService.swift - 服务层
   - UpdateChecker.swift - 更新检查器
   - TextreamApp.swift - 应用程序入口和菜单

3. ✅ 添加了100+中文字符串翻译

## 🚀 快速开始

### 方式1：下载预编译版本（推荐）

如果有预编译的DMG文件：
```bash
# 下载后打开DMG，将Textream.app拖到Applications文件夹
open ~/Downloads/Textream.dmg
```

### 方式2：从源码编译

需要安装Xcode（从App Store获取）：

```bash
# 克隆仓库
git clone https://github.com/Wjzhong123/textream-cn.git
cd textream-cn/Textream

# 编译应用
./build.sh

# 安装应用
cp -R build/release/universal/Textream.app /Applications/
xattr -cr /Applications/Textream.app
```

## 📝 本地化特性

应用会自动检测系统语言：
- 如果系统语言是中文，显示中文界面
- 否则显示英文界面

检测代码：`Locale.current.language.languageCode?.identifier == "zh"`

## 🌐 语言支持

应用会自动检测系统语言：
- **中文（简体）**：当系统语言设置为中文时显示
- **English**：其他语言时显示英文

检测代码：`Locale.current.language.languageCode?.identifier == "zh"`

## 📂 文件结构

```
textream-cn/
├── Textream/               # 主项目
│   ├── Textream/          # 源代码
│   │   ├── Localizable.swift      # 本地化系统
│   │   ├── ContentView.swift      # 主界面
│   │   ├── SettingsView.swift     # 设置界面
│   │   └── ...
│   └── build.sh           # 编译脚本
├── README_CN.md           # 本文件
└── .github/               # GitHub配置
```

## 🔧 如何编译

### 前置要求

- macOS 15.0 或更高版本
- Xcode（从 [App Store](https://apps.apple.com/app/xcode/id497799835) 下载）

### 编译步骤

1. **安装Xcode**
   ```bash
   # 从App Store安装Xcode（约15GB）
   # 安装后打开Xcode完成初始设置
   ```

2. **编译应用**
   ```bash
   cd ~/textream/Textream
   ./build.sh
   ```

编译完成后会生成：
- `build/release/universal/Textream.app` - 通用二进制应用（支持Intel和Apple Silicon）
- `build/release/Textream.dmg` - DMG安装包

3. **安装应用**
   ```bash
   # 卸载旧版本（如果已安装）
   brew uninstall --cask textream 2>/dev/null || true

   # 安装新版本
   cp -R build/release/universal/Textream.app /Applications/

   # 移除隔离属性
   xattr -cr /Applications/Textream.app
   ```

### 方法2：仅使用命令行（受限）

如果您已安装Xcode但命令行工具路径不对：

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

然后重新运行 `./build.sh`

### 方法2：仅使用命令行（受限）

如果您已安装Xcode但只是命令行工具路径不对：

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

然后重新运行 `./build.sh`

## 📦 安装新编译的应用

```bash
# 卸载旧版本
brew uninstall --cask textream

# 安装新版本
cp -R ~/textream/Textream/build/release/universal/Textream.app /Applications/

# 如果应用被隔离，运行：
xattr -cr /Applications/Textream.app
```

## 🎮 使用说明

1. **启动应用**：打开 `/Applications/Textream.app`
2. **设置语言**：系统设置为中文即可看到中文界面
   - 系统设置 → 通用 → 语言与地区 → 中文（简体）
3. **开始使用**：
   - 输入或粘贴您的脚本
   - 点击播放按钮开始提词
   - 语音识别会高亮显示您朗读的内容

## 🤝 贡献

欢迎提交Issue和Pull Request！

如果您想：
- **修复翻译**：编辑 `Localizable.swift` 文件
- **添加新功能**：创建Pull Request
- **报告Bug**：在GitHub Issues中提交

## 📄 许可证

本项目基于原项目的MIT许可证。

- **原项目**：https://github.com/f/textream
- **许可证文件**：[LICENSE](https://github.com/f/textream/blob/master/LICENSE)

## 🙏 致谢

- [Fatih Kadir Akın](https://github.com/f) - 原项目作者
- 所有贡献者

## 📮 联系方式

- GitHub Issues: https://github.com/Wjzhong123/textream-cn/issues
- 基于原项目：https://github.com/f/textream

---

**注意**：这是Textream的中文本地化版本。如需使用最新版本，请访问原项目仓库。

- 所有字符串翻译存储在 `LocalizedStrings` 结构体中
- 翻译方法：根据 `LocalizedStrings.isChinese` 返回对应语言字符串
- 如需修改翻译，直接编辑 `Localizable.swift` 文件
