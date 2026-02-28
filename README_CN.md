# Textream 中文化完成说明

## 已完成的工作

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

## 本地化特性

应用会自动检测系统语言：
- 如果系统语言是中文，显示中文界面
- 否则显示英文界面

检测代码：`Locale.current.language.languageCode?.identifier == "zh"`

## 如何编译

由于您的系统只安装了命令行工具，需要完整的Xcode才能编译。

### 方法1：从App Store安装Xcode（推荐）

1. 打开App Store
2. 搜索"Xcode"
3. 点击"获取"下载安装（约15GB）
4. 安装完成后，打开终端运行：

```bash
cd ~/textream/Textream
./build.sh
```

编译完成后会生成：
- `~/textream/Textream/build/release/universal/Textream.app` - 通用二进制应用
- `~/textream/Textream/build/release/Textream.dmg` - DMG安装包

### 方法2：仅使用命令行（受限）

如果您已安装Xcode但只是命令行工具路径不对：

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

然后重新运行 `./build.sh`

## 安装新编译的应用

```bash
# 卸载旧版本
brew uninstall --cask textream

# 安装新版本
cp -R ~/textream/Textream/build/release/universal/Textream.app /Applications/

# 如果应用被隔离，运行：
xattr -cr /Applications/Textream.app
```

## 文件位置

- 源代码：`~/textream/`
- 本地化文件：`~/textream/Textream/Textream/Localizable.swift`
- 构建脚本：`~/textream/Textream/build.sh`

## 备注

- 所有字符串翻译存储在 `LocalizedStrings` 结构体中
- 翻译方法：根据 `LocalizedStrings.isChinese` 返回对应语言字符串
- 如需修改翻译，直接编辑 `Localizable.swift` 文件
