# GitHub Actions 工作流设置指南

由于GitHub对workflow文件有特殊权限要求，需要在网页上手动创建。

## 步骤1：在GitHub创建工作流文件

1. 访问：https://github.com/Wjzhong123/textream-cn/new/master
2. 在文件名框中输入：`.github/workflows/build.yml`
3. 复制以下内容粘贴进去：

```yaml
name: Build Textream Chinese Edition

on:
  push:
    branches: [ master ]
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag (e.g., v1.5.1-cn)'
        required: false
        default: 'v1.5.1-cn'

jobs:
  build:
    runs-on: macos-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Select Xcode version
      run: |
        sudo xcode-select -s /Applications/Xcode_16.1.app/Contents/Developer

    - name: Build for Apple Silicon
      run: |
        cd Textream
        xcodebuild archive \
          -project Textream.xcodeproj \
          -scheme Textream \
          -configuration Release \
          -archivePath ../build/Textream-arm64.xcarchive \
          -destination "generic/platform=macOS" \
          ARCHS=arm64 \
          ONLY_ACTIVE_ARCH=NO \
          SKIP_INSTALL=NO

    - name: Build for Intel
      run: |
        cd Textream
        xcodebuild archive \
          -project Textream.xcodeproj \
          -scheme Textream \
          -configuration Release \
          -archivePath ../build/Textream-x86_64.xcarchive \
          -destination "generic/platform=macOS" \
          ARCHS=x86_64 \
          ONLY_ACTIVE_ARCH=NO \
          SKIP_INSTALL=NO

    - name: Create Universal Binary
      run: |
        ARM_APP="build/Textream-arm64.xcarchive/Products/Applications/Textream.app"
        X86_APP="build/Textream-x86_64.xcarchive/Products/Applications/Textream.app"
        OUTPUT_APP="build/universal/Textream.app"

        mkdir -p build/universal
        cp -R "$ARM_APP" "$OUTPUT_APP"

        find "$ARM_APP" -type f | while read -r arm_file; do
          rel="${arm_file#$ARM_APP}"
          x86_file="$X86_APP$rel"
          out_file="$OUTPUT_APP$rel"

          if [ -f "$x86_file" ] && file "$arm_file" | grep -q "Mach-O"; then
            lipo -create "$arm_file" "$x86_file" -output "$out_file" 2>/dev/null || true
          fi
        done

    - name: Create DMG
      run: |
        DMG_STAGING="build/dmg_staging"
        mkdir -p "$DMG_STAGING"
        cp -R build/universal/Textream.app "$DMG_STAGING/"
        ln -s /Applications "$DMG_STAGING/Applications"

        hdiutil create \
          -volname "Textream中文版" \
          -srcfolder "$DMG_STAGING" \
          -ov \
          -format UDZO \
          -imagekey zlib-level=9 \
          build/Textream-CN.dmg

    - name: Upload DMG as artifact
      uses: actions/upload-artifact@v4
      with:
        name: Textream-CN-macOS
        path: build/Textream-CN.dmg
        retention-days: 90

    - name: Create Release
      if: github.event_name == 'workflow_dispatch'
      uses: softprops/action-gh-release@v1
      with:
        tag_name: ${{ github.event.inputs.version }}
        name: Textream中文版 ${{ github.event.inputs.version }}
        body: |
          ## Textream 中文版
          
          这是Textream提词器的中文本地化版本。
          
          ### 安装方法
          1. 下载 `Textream-CN.dmg`
          2. 打开DMG文件
          3. 将 Textream.app 拖到 Applications 文件夹
          4. 在终端运行: `xattr -cr /Applications/Textream.app`
          
          ### 系统要求
          - macOS 15.0 或更高版本
        files: build/Textream-CN.dmg
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

4. 点击页面底部的 **"Commit changes"**
5. 提交信息填写：`Add CI/CD workflow`

## 步骤2：触发自动编译

创建文件后，访问：
https://github.com/Wjzhong123/textream-cn/actions

点击 **"Build Textream Chinese Edition"** → **"Run workflow"** → **"Run workflow"**

等待大约10-15分钟，编译完成后会自动上传DMG文件。

## 步骤3：下载编译好的应用

编译完成后，有两种方式下载：

**方式A：从Artifacts下载（临时）**
- 访问：https://github.com/Wjzhong123/textream-cn/actions
- 点击最新的workflow run
- 在 "Artifacts" 部分下载 `Textream-CN-macOS`

**方式B：从Releases下载（永久）**
- 重新运行workflow并输入版本号（如 `v1.5.1-cn`）
- 访问：https://github.com/Wjzhong123/textream-cn/releases
- 下载对应版本的DMG

## 步骤4：安装中文版应用

```bash
# 打开下载的DMG
open ~/Downloads/Textream-CN.dmg

# 或者在终端中
hdiutil attach ~/Downloads/Textream-CN.dmg

# 复制应用（替换旧版本）
sudo rm -rf /Applications/Textream.app
sudo cp -R /Volumes/Textream中文版/Textream.app /Applications/

# 卸载DMG
hdiutil detach /Volumes/Textream中文版

# 移除隔离属性
xattr -cr /Applications/Textream.app
```

完成！🎉
