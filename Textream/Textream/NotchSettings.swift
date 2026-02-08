//
//  NotchSettings.swift
//  Textream
//
//  Created by Fatih Kadir Akın on 8.02.2026.
//

import SwiftUI

@Observable
class NotchSettings {
    static let shared = NotchSettings()

    var notchWidth: CGFloat {
        didSet { UserDefaults.standard.set(Double(notchWidth), forKey: "notchWidth") }
    }
    var textAreaHeight: CGFloat {
        didSet { UserDefaults.standard.set(Double(textAreaHeight), forKey: "textAreaHeight") }
    }

    var speechLocale: String {
        didSet { UserDefaults.standard.set(speechLocale, forKey: "speechLocale") }
    }

    static let defaultWidth: CGFloat = 340
    static let defaultHeight: CGFloat = 150
    static let defaultLocale: String = Locale.current.identifier

    static let minWidth: CGFloat = 280
    static let maxWidth: CGFloat = 500
    static let minHeight: CGFloat = 100
    static let maxHeight: CGFloat = 400

    init() {
        let savedWidth = UserDefaults.standard.double(forKey: "notchWidth")
        let savedHeight = UserDefaults.standard.double(forKey: "textAreaHeight")
        self.notchWidth = savedWidth > 0 ? CGFloat(savedWidth) : Self.defaultWidth
        self.textAreaHeight = savedHeight > 0 ? CGFloat(savedHeight) : Self.defaultHeight
        self.speechLocale = UserDefaults.standard.string(forKey: "speechLocale") ?? Self.defaultLocale
    }
}
