//
//  SettingsView.swift
//  Textream
//
//  Created by Fatih Kadir Akın on 8.02.2026.
//

import SwiftUI
import AppKit
import Speech

// MARK: - Preview Panel Controller

class NotchPreviewController {
    private var panel: NSPanel?
    private var hostingView: NSHostingView<NotchPreviewContent>?

    func show(settings: NotchSettings) {
        guard let screen = NSScreen.main else { return }
        let screenFrame = screen.frame
        let visibleFrame = screen.visibleFrame
        let menuBarHeight = screenFrame.maxY - visibleFrame.maxY

        let maxWidth = NotchSettings.maxWidth
        let maxHeight = menuBarHeight + NotchSettings.maxHeight

        let xPosition = screenFrame.midX - maxWidth / 2
        let yPosition = screenFrame.maxY - maxHeight

        let content = NotchPreviewContent(settings: settings, menuBarHeight: menuBarHeight)
        let hostingView = NSHostingView(rootView: content)
        self.hostingView = hostingView

        let panel = NSPanel(
            contentRect: NSRect(x: xPosition, y: yPosition, width: maxWidth, height: maxHeight),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.level = .statusBar
        panel.ignoresMouseEvents = true
        panel.contentView = hostingView
        panel.orderFront(nil)
        self.panel = panel
    }

    func dismiss() {
        panel?.orderOut(nil)
        panel = nil
        hostingView = nil
    }
}

struct NotchPreviewContent: View {
    @Bindable var settings: NotchSettings
    let menuBarHeight: CGFloat

    private static let loremWords = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua Ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur Excepteur sint occaecat cupidatat non proident sunt in culpa qui officia deserunt mollit anim id est laborum Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium totam rem aperiam eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt".split(separator: " ").map(String.init)

    private let highlightedCount = 42

    var body: some View {
        GeometryReader { geo in
            let targetHeight = menuBarHeight + settings.textAreaHeight
            let currentWidth = settings.notchWidth

            ZStack(alignment: .top) {
                DynamicIslandShape(
                    topInset: 16,
                    bottomRadius: 18
                )
                .fill(.black)
                .frame(width: currentWidth, height: targetHeight)

                VStack(spacing: 0) {
                    Spacer().frame(height: menuBarHeight)

                    SpeechScrollView(
                        words: Self.loremWords,
                        highlightedCharCount: highlightedCount,
                        font: .systemFont(ofSize: 18, weight: .semibold),
                        isListening: false
                    )
                    .padding(.horizontal, 12)
                    .padding(.top, 6)
                }
                .padding(.horizontal, 16)
                .frame(width: currentWidth, height: targetHeight)
            }
            .frame(width: currentWidth, height: targetHeight, alignment: .top)
            .frame(width: geo.size.width, height: geo.size.height, alignment: .top)
            .animation(.easeInOut(duration: 0.15), value: settings.notchWidth)
            .animation(.easeInOut(duration: 0.15), value: settings.textAreaHeight)
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @Bindable var settings: NotchSettings
    @Environment(\.dismiss) private var dismiss
    @State private var previewController = NotchPreviewController()

    var body: some View {
        VStack(spacing: 16) {
            Text("Notch Settings")
                .font(.system(size: 15, weight: .semibold))
                .padding(.top, 4)

            // Width slider
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Width")
                        .font(.system(size: 13, weight: .medium))
                    Spacer()
                    Text("\(Int(settings.notchWidth))px")
                        .font(.system(size: 12, weight: .regular, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                Slider(
                    value: $settings.notchWidth,
                    in: NotchSettings.minWidth...NotchSettings.maxWidth,
                    step: 10
                )
            }

            // Height slider
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Height")
                        .font(.system(size: 13, weight: .medium))
                    Spacer()
                    Text("\(Int(settings.textAreaHeight))px")
                        .font(.system(size: 12, weight: .regular, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                Slider(
                    value: $settings.textAreaHeight,
                    in: NotchSettings.minHeight...NotchSettings.maxHeight,
                    step: 10
                )
            }

            // Language picker
            VStack(alignment: .leading, spacing: 6) {
                Text("Speech Language")
                    .font(.system(size: 13, weight: .medium))
                Picker("", selection: $settings.speechLocale) {
                    ForEach(SFSpeechRecognizer.supportedLocales().sorted(by: { $0.identifier < $1.identifier }), id: \.identifier) { locale in
                        Text(Locale.current.localizedString(forIdentifier: locale.identifier) ?? locale.identifier)
                            .tag(locale.identifier)
                    }
                }
                .labelsHidden()
            }

            // Buttons
            HStack {
                Button("Reset to Defaults") {
                    withAnimation(.easeInOut(duration: 0.3)) {
                        settings.notchWidth = NotchSettings.defaultWidth
                        settings.textAreaHeight = NotchSettings.defaultHeight
                    }
                }
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
                .buttonStyle(.plain)

                Spacer()

                Button("Done") {
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
        }
        .padding(20)
        .frame(width: 320)
        .background(.ultraThinMaterial)
        .onAppear {
            previewController.show(settings: settings)
        }
        .onDisappear {
            previewController.dismiss()
        }
    }
}
