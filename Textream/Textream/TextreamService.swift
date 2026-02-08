//
//  TextreamService.swift
//  Textream
//
//  Created by Fatih Kadir Akın on 8.02.2026.
//

import AppKit
import SwiftUI

class TextreamService: NSObject {
    static let shared = TextreamService()
    let overlayController = NotchOverlayController()
    var onOverlayDismissed: (() -> Void)?
    var launchedExternally = false

    func readText(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        launchedExternally = true
        hideMainWindow()

        overlayController.show(text: trimmed) { [weak self] in
            self?.onOverlayDismissed?()
        }
    }

    func hideMainWindow() {
        DispatchQueue.main.async {
            for window in NSApp.windows where !(window is NSPanel) {
                window.orderOut(nil)
            }
        }
    }

    // macOS Services handler
    @objc func readInTextream(_ pboard: NSPasteboard, userData: String, error: AutoreleasingUnsafeMutablePointer<NSString?>) {
        guard let text = pboard.string(forType: .string) else {
            error.pointee = "No text found on pasteboard" as NSString
            return
        }
        readText(text)
    }

    // URL scheme handler: textream://read?text=Hello%20World
    func handleURL(_ url: URL) {
        guard url.scheme == "textream" else { return }

        if url.host == "read" || url.path == "/read" {
            if let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
               let textParam = components.queryItems?.first(where: { $0.name == "text" })?.value {
                readText(textParam)
            }
        }
    }
}
