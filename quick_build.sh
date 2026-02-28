#!/bin/bash
# Textream 中文版快速编译脚本
# 使用方法: sudo ./quick_build.sh

set -e

echo "🔍 检查Xcode安装..."

if ! command -v xcodebuild &> /dev/null; then
    echo "❌ 未找到Xcode"
    echo ""
    echo "请先安装Xcode："
    echo "1. 打开App Store"
    echo "2. 搜索 'Xcode'"
    echo "3. 点击 '获取' 下载安装（约15GB）"
    echo "4. 安装完成后重新运行此脚本"
    exit 1
fi

echo "✅ 找到Xcode: $(xcodebuild -version | head -1)"
echo ""
cd /Users/mac/textream/Textream

echo "🧹 清理旧文件..."
rm -rf build
mkdir -p build/release

echo "🔨 开始编译（Apple Silicon）..."
xcodebuild archive \
  -project Textream.xcodeproj \
  -scheme Textream \
  -configuration Release \
  -archivePath ../build/release/Textream-arm64.xcarchive \
  -destination "generic/platform=macOS" \
  ARCHS=arm64 \
  ONLY_ACTIVE_ARCH=NO \
  SKIP_INSTALL=NO \
  -quiet || {
    echo "❌ Apple Silicon编译失败，尝试Intel模式..."
    xcodebuild archive \
      -project Textream.xcodeproj \
      -scheme Textream \
      -configuration Release \
      -archivePath ../build/release/Textream-arm64.xcarchive \
      -destination "generic/platform=macOS" \
      ARCHS=x86_64 \
      ONLY_ACTIVE_ARCH=NO \
      SKIP_INSTALL=NO \
      -quiet
}

echo "🔨 开始编译（Intel）..."
xcodebuild archive \
  -project Textream.xcodeproj \
  -scheme Textream \
  -configuration Release \
  -archivePath ../build/release/Textream-x86_64.xcarchive \
  -destination "generic/platform=macOS" \
  ARCHS=x86_64 \
  ONLY_ACTIVE_ARCH=NO \
  SKIP_INSTALL=NO \
  -quiet

echo "🧬 创建通用二进制..."
ARM_APP="build/release/Textream-arm64.xcarchive/Products/Applications/Textream.app"
X86_APP="build/release/Textream-x86_64.xcarchive/Products/Applications/Textream.app"
OUTPUT_APP="build/release/universal/Textream.app"

mkdir -p build/release/universal
cp -R "$ARM_APP" "$OUTPUT_APP"

find "$ARM_APP" -type f | while read -r arm_file; do
  rel="${arm_file#$ARM_APP}"
  x86_file="$X86_APP$rel"
  out_file="$OUTPUT_APP$rel"

  if [ -f "$x86_file" ] && file "$arm_file" | grep -q "Mach-O"; then
    lipo -create "$arm_file" "$x86_file" -output "$out_file" 2>/dev/null || true
  fi
done

echo "📦 创建DMG..."
DMG_STAGING="build/release/dmg_staging"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R build/release/universal/Textream.app "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

hdiutil create \
  -volname "Textream中文版" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  build/release/Textream-CN.dmg \
  -quiet

rm -rf "$DMG_STAGING"

echo ""
echo "✅ 编译完成！"
echo ""
echo "📍 文件位置："
echo "   应用: build/release/universal/Textream.app"
echo "   DMG:  build/release/Textream-CN.dmg"
echo ""
echo "📊 二进制信息："
lipo -info build/release/universal/Textream.app/Contents/MacOS/Textream
echo ""
echo "💡 安装方法："
echo "   方法1 - 打开DMG: open build/release/Textream-CN.dmg"
echo "   方法2 - 直接复制: cp -R build/release/universal/Textream.app /Applications/"
echo "   然后运行: xattr -cr /Applications/Textream.app"
echo ""
