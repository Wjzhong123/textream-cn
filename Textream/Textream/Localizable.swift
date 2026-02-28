//
//  Localizable.swift
//  Textream
//
//  Chinese localization support
//

import Foundation
import SwiftUI

struct LocalizedStrings {
    static var isChinese: Bool {
        Locale.current.language.languageCode?.identifier == "zh"
    }
    
    // MARK: - App
    static var appName: String { isChinese ? "Textream 提词器" : "Textream" }
    static var untitled: String { isChinese ? "未命名" : "Untitled" }
    
    // MARK: - Welcome Text
    static var welcomeText: String {
        isChinese ? """
        欢迎使用 Textream 提词器！这是您的个人提词器，位于 MacBook 刘海下方。[微笑]
        
        当您朗读时，文字会实时高亮显示，语音识别会匹配您的话并跟踪您的进度。您可以随时暂停，往回重新阅读部分内容，高亮显示会跟随。当您阅读完所有文字后，提词器会自动关闭。
        
        朗读这段文字来查看高亮效果。底部的波形显示您的语音活动，您最近说的几个字会显示在旁边。
        
        祝您演讲顺利！[挥手]
        """ : """
        Welcome to Textream! This is your personal teleprompter that sits right below your MacBook's notch. [smile]
        
        As you read aloud, the text will highlight in real-time, following your voice. The speech recognition matches your words and keeps track of your progress. You can pause at any time, go back and re-read sections, and the highlighting will follow along. When you finish reading all the text, the overlay will automatically close with a smooth animation. [nod]
        
        Try reading this passage out loud to see how the highlighting works. The waveform at the bottom shows your voice activity, and you'll see the last few words you spoke displayed next to it.
        
        Happy presenting! [wave]
        """
    }
    
    // MARK: - ContentView
    static var dropPowerPointFile: String { isChinese ? "拖放 PowerPoint (.pptx) 文件" : "Drop PowerPoint (.pptx) file" }
    static var exportAsPPTX: String { isChinese ? "如果是 Keynote 或 Google Slides，\n请先导出为 PPTX。" : "For Keynote or Google Slides,\nexport as PPTX first." }
    static var directorMode: String { isChinese ? "导演模式" : "Director Mode" }
    static var readingFromDirector: String { isChinese ? "正在接收导演的文字..." : "Reading from director…" }
    static var waitingForDirector: String { isChinese ? "等待导演发送脚本..." : "Waiting for director to send script…" }
    static var openSettings: String { isChinese ? "打开设置" : "Open Settings" }
    static var page: String { isChinese ? "页面" : "Page" }
    static var empty: String { isChinese ? "空白" : "Empty" }
    
    // MARK: - About View
    static var version: String { isChinese ? "版本" : "Version" }
    static var aboutDescription: String { isChinese ? "一款免费的开源提词器，会在您朗读时实时高亮显示脚本。" : "A free, open-source teleprompter that highlights your script in real-time as you speak." }
    static var github: String { isChinese ? "GitHub" : "GitHub" }
    static var donate: String { isChinese ? "捐赠" : "Donate" }
    static var madeBy: String { isChinese ? "由 Fatih Kadir Akin 开发" : "Made by Fatih Kadir Akin" }
    static var originalIdeaBy: String { isChinese ? "原始创意来自 Semih Kışlar" : "Original idea by Semih Kışlar" }
    static var ok: String { isChinese ? "确定" : "OK" }
    
    // MARK: - Settings
    static var settings: String { isChinese ? "设置" : "Settings" }
    static var resetAll: String { isChinese ? "重置全部" : "Reset All" }
    static var done: String { isChinese ? "完成" : "Done" }
    static var resetAllSettings: String { isChinese ? "重置所有设置？" : "Reset All Settings?" }
    static var resetWarning: String { isChinese ? "这将恢复所有设置到默认值。" : "This will restore all settings to their defaults." }
    static var cancel: String { isChinese ? "取消" : "Cancel" }
    static var reset: String { isChinese ? "重置" : "Reset" }
    
    // MARK: - Settings Tabs
    static var appearance: String { isChinese ? "外观" : "Appearance" }
    static var guidance: String { isChinese ? "引导" : "Guidance" }
    static var teleprompter: String { isChinese ? "提词器" : "Teleprompter" }
    static var external: String { isChinese ? "外部" : "External" }
    static var remote: String { isChinese ? "远程" : "Remote" }
    static var director: String { isChinese ? "导演" : "Director" }
    
    // MARK: - Appearance Tab
    static var font: String { isChinese ? "字体" : "Font" }
    static var size: String { isChinese ? "大小" : "Size" }
    static var highlightColor: String { isChinese ? "高亮颜色" : "Highlight Color" }
    static var dimensions: String { isChinese ? "尺寸" : "Dimensions" }
    static var width: String { isChinese ? "宽度" : "Width" }
    static var height: String { isChinese ? "高度" : "Height" }
    
    // MARK: - Guidance Tab
    static var speechLanguage: String { isChinese ? "语音语言" : "Speech Language" }
    static var microphone: String { isChinese ? "麦克风" : "Microphone" }
    static var systemDefault: String { isChinese ? "系统默认" : "System Default" }
    static var scrollSpeed: String { isChinese ? "滚动速度" : "Scroll Speed" }
    static var slower: String { isChinese ? "较慢" : "Slower" }
    static var faster: String { isChinese ? "较快" : "Faster" }
    
    // MARK: - Teleprompter Tab
    static var display: String { isChinese ? "显示" : "Display" }
    static var followCursor: String { isChinese ? "跟随光标" : "Follow Cursor" }
    static var followCursorDesc: String { isChinese ? "窗口会跟随您的光标并吸附在右下角。" : "The window follows your cursor and sticks to its bottom-right." }
    static var glassEffect: String { isChinese ? "毛玻璃效果" : "Glass Effect" }
    static var opacity: String { isChinese ? "不透明度" : "Opacity" }
    static var elapsedTime: String { isChinese ? "已用时间" : "Elapsed Time" }
    static var elapsedTimeDesc: String { isChinese ? "提词器运行时显示计时器。" : "Display a running timer while the teleprompter is active." }
    static var hideFromScreenSharing: String { isChinese ? "屏幕共享时隐藏" : "Hide from Screen Sharing" }
    static var hideFromScreenSharingDesc: String { isChinese ? "在屏幕录制和视频通话中隐藏提词器。" : "Hide the overlay from screen recordings and video calls." }
    static var pagination: String { isChinese ? "分页" : "Pagination" }
    static var autoNextPage: String { isChinese ? "自动下一页" : "Auto Next Page" }
    static var autoNextPageDesc: String { isChinese ? "倒计时后自动进入下一页。" : "Automatically advance to the next page after a countdown." }
    static var countdown: String { isChinese ? "倒计时" : "Countdown" }
    static var seconds3: String { isChinese ? "3 秒" : "3 seconds" }
    static var seconds5: String { isChinese ? "5 秒" : "5 seconds" }
    static var pressEscToStop: String { isChinese ? "按 Esc 键停止提词器。" : "Press Esc to stop the teleprompter." }
    
    // MARK: - External Tab
    static var externalDisplayDesc: String { isChinese ? "在外部显示器或 Sidecar iPad 上显示提词器。" : "Show the teleprompter on an external display or Sidecar iPad." }
    static var mirrorAxis: String { isChinese ? "镜像轴" : "Mirror Axis" }
    static var targetDisplay: String { isChinese ? "目标显示器" : "Target Display" }
    static var noExternalDisplays: String { isChinese ? "未检测到外部显示器。请连接显示器或启用 Sidecar。" : "No external displays detected. Connect a display or enable Sidecar." }
    static var refresh: String { isChinese ? "刷新" : "Refresh" }
    
    // MARK: - Remote Tab
    static var remoteDesc: String { isChinese ? "扫描二维码或在同一 Wi-Fi 网络上使用 iPhone、Android 或电视浏览器打开网址。" : "Scan the QR code or open the URL with your iPhone, Android or TV browser on the same Wi-Fi network." }
    static var enableRemoteConnection: String { isChinese ? "启用远程连接" : "Enable Remote Connection" }
    static var port: String { isChinese ? "端口" : "Port" }
    static var restartRequired: String { isChinese ? "更改后需要重启" : "Restart required after change" }
    static var portUsage: String { isChinese ? "使用端口 %d (HTTP) 和 %d (WebSocket)。" : "Uses ports %d (HTTP) and %d (WebSocket)." }
    
    // MARK: - Director Tab
    static var directorDesc: String { isChinese ? "导演模式允许远程人员通过网页浏览器实时控制您的提词器脚本。激活时编辑器将不可用。" : "Director Mode lets a remote person control your teleprompter script in real-time via a web browser. The editor will be disabled while active." }
    static var enableDirectorMode: String { isChinese ? "启用导演模式" : "Enable Director Mode" }
    static var directorWordTrackingForced: String { isChinese ? "导演开始朗读时将强制使用文字跟踪。" : "Word tracking is forced when the director starts reading." }
    
    // MARK: - Overlay
    static var jumpToPage: String { isChinese ? "跳转到页面" : "Jump to page" }
    static var tapToJump: String { isChinese ? "点击页面跳转" : "Tap a page to jump" }
    static var nextPage: String { isChinese ? "下一页" : "Next Page" }
    static var doneButton: String { isChinese ? "完成！" : "Done!" }
    static var pageN: String { isChinese ? "第 %d 页" : "Page %d" }
    
    // MARK: - Alerts
    static var importError: String { isChinese ? "导入错误" : "Import Error" }
    static var conversionRequired: String { isChinese ? "需要转换" : "Conversion Required" }
    static var unsupportedFile: String { isChinese ? "不支持的文件格式。请拖放 PowerPoint (.pptx) 文件。" : "Unsupported file. Drop a PowerPoint (.pptx) file." }
    static var keynoteCannotImport: String { isChinese ? "Keynote 文件无法直接导入。请先将 Keynote 演示文稿导出为 PowerPoint (.pptx)。" : "Keynote files can't be imported directly. Please export your Keynote presentation as PowerPoint (.pptx) first." }
    static var keynoteExportHint: String { isChinese ? "在 Keynote 中：文件 → 导出为 → PowerPoint" : "In Keynote: File → Export To → PowerPoint" }
    static var unsavedChanges: String { isChinese ? "您有未保存的更改" : "You have unsaved changes" }
    static var saveChangesPrompt: String { isChinese ? "在打开另一个文件之前是否保存更改？" : "Do you want to save your changes before opening another file?" }
    static var save: String { isChinese ? "保存" : "Save" }
    static var discard: String { isChinese ? "放弃" : "Discard" }
    static var failedToSave: String { isChinese ? "保存文件失败" : "Failed to save file" }
    static var failedToOpen: String { isChinese ? "打开文件失败" : "Failed to open file" }
    
    // MARK: - Update Checker
    static var updateAvailable: String { isChinese ? "有可用更新" : "Update Available" }
    static var updateMessage: String { isChinese ? "Textream %@ 已发布。您当前使用的是 %@。" : "Textream %@ is available. You are currently running %@." }
    static var download: String { isChinese ? "下载" : "Download" }
    static var later: String { isChinese ? "稍后" : "Later" }
    static var upToDate: String { isChinese ? "已是最新版本" : "You're Up to Date" }
    static var upToDateMessage: String { isChinese ? "Textream %@ 是最新版本。" : "Textream %@ is the latest version." }
    static var updateCheckFailed: String { isChinese ? "检查更新失败" : "Update Check Failed" }
    static var couldNotCheckUpdates: String { isChinese ? "无法检查更新。\n%@" : "Could not check for updates.\n%@" }
    static var parseReleaseFailed: String { isChinese ? "无法解析发布信息。" : "Could not parse the release information." }
    
    // MARK: - Browser Server
    static var connecting: String { isChinese ? "连接中…" : "Connecting…" }
    static var typeOrPasteScript: String { isChinese ? "在此输入或粘贴脚本…" : "Type or paste your script here…" }
    static var go: String { isChinese ? "开始" : "Go" }
    static var newScript: String { isChinese ? "新脚本" : "New Script" }
    
    // MARK: - Menu Items
    static var aboutTextream: String { isChinese ? "关于 Textream" : "About Textream" }
    static var checkForUpdates: String { isChinese ? "检查更新…" : "Check for Updates…" }
    static var textreamHelp: String { isChinese ? "Textream 帮助" : "Textream Help" }
    static var openFileOrPresentation: String { isChinese ? "打开文件或演示文稿…" : "Open File or Presentation…" }
    static var saveAs: String { isChinese ? "另存为…" : "Save As…" }
}

// Helper view modifier for localization
struct LocalizedText: ViewModifier {
    let key: String
    
    func body(content: Content) -> some View {
        content
    }
}

extension View {
    func localized(_ key: String) -> some View {
        self
    }
}
