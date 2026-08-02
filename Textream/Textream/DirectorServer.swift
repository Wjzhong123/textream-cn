//
//  DirectorServer.swift
//  Textream
//
//  Created by Fatih Kadir Akın on 8.02.2026.
//

import Foundation
import Network
import AppKit
import OSLog

// MARK: - Director State (App → Web)

struct DirectorState: Codable {
    let words: [String]
    let highlightedCharCount: Int
    let totalCharCount: Int
    let isActive: Bool
    let isDone: Bool
    let isListening: Bool
    let fontColor: String
    let cueColor: String
    let lastSpokenText: String
    let audioLevels: [Double]
}

// MARK: - Director Command (Web → App)

struct DirectorCommand: Codable {
    let type: String          // "setText", "updateText", "stop"
    let text: String?
    let readCharCount: Int?
}

// MARK: - Director Server

class DirectorServer {
    private var httpListener: NWListener?
    private var wsListener: NWListener?
    private var wsConnections: [NWConnection] = []
    private var authenticatedConnections: Set<ObjectIdentifier> = []
    private var broadcastTimer: Timer?

    private static let logger = Logger(subsystem: "com.textream.director", category: "Screenshot")

    // Connection limit to prevent resource exhaustion (CWE-400)
    private let maxConnections = 5

    // Dedicated queue for broadcasting to avoid blocking the main/UI thread
    private let broadcastQueue = DispatchQueue(label: "com.textream.director.broadcast")
    // Security: shared secret token for WebSocket authentication
    private var authToken: String = ""

    // Content state
    private var words: [String] = []
    private var totalCharCount: Int = 0
    private weak var speechRecognizer: SpeechRecognizer?
    private var contentActive: Bool = false
    private var lastBroadcastState: Data?

    // Callbacks
    var onSetText: ((String) -> Void)?
    var onUpdateText: ((String, Int) -> Void)?
    var onStop: (() -> Void)?

    var httpPort: UInt16 { NotchSettings.shared.directorServerPort }
    var wsPort: UInt16 { httpPort + 1 }
    var isRunning: Bool { httpListener != nil }
    var connectedClients: Int { wsConnections.count }

    // MARK: - Lifecycle

    func start() {
        stop()
        authToken = Self.generateToken()
        startHTTPListener()
        startWSListener()
    }

    func startScreenshotAPIOnly() {
        // 仅启动 HTTP 截图 API（不启动 WebSocket 广播）
        // 用于用户未启用 DirectorServer 但需要截图功能的场景
        guard httpListener == nil else { return }
        guard let port = NWEndpoint.Port(rawValue: httpPort) else { return }
        do {
            httpListener = try NWListener(using: .tcp, on: port)
        } catch { return }
        httpListener?.stateUpdateHandler = { [weak self] state in
            if case .failed = state { self?.httpListener = nil }
        }
        httpListener?.newConnectionHandler = { [weak self] conn in
            self?.handleHTTPConnection(conn)
        }
        httpListener?.start(queue: .main)
        Self.logger.info("Screenshot API started on port \(self.httpPort)")
    }

    func stop() {
        broadcastTimer?.invalidate()
        broadcastTimer = nil

        httpListener?.cancel()
        httpListener = nil
        wsListener?.cancel()
        wsListener = nil

        for conn in wsConnections { conn.cancel() }
        wsConnections.removeAll()
        authenticatedConnections.removeAll()
        contentActive = false
    }

    // MARK: - Content Management

    func showContent(speechRecognizer: SpeechRecognizer, words: [String], totalCharCount: Int) {
        self.speechRecognizer = speechRecognizer
        self.words = words
        self.totalCharCount = totalCharCount
        self.contentActive = true
        startBroadcasting()
    }

    func updateContent(words: [String], totalCharCount: Int) {
        self.words = words
        self.totalCharCount = totalCharCount
    }

    func hideContent() {
        contentActive = false
        broadcastTimer?.invalidate()
        broadcastTimer = nil
        broadcastInactive()
    }

    // MARK: - HTTP Server

    private func startHTTPListener() {
        guard let port = NWEndpoint.Port(rawValue: httpPort) else { return }
        do {
            httpListener = try NWListener(using: .tcp, on: port)
        } catch { return }

        httpListener?.stateUpdateHandler = { [weak self] state in
            if case .failed = state { self?.httpListener = nil }
        }
        httpListener?.newConnectionHandler = { [weak self] conn in
            self?.handleHTTPConnection(conn)
        }
        httpListener?.start(queue: .main)
    }

    private func handleHTTPConnection(_ conn: NWConnection) {
        conn.start(queue: .main)
        conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, _, error in
            guard let self else { conn.cancel(); return }
            guard let data, error == nil else { conn.cancel(); return }

            let requestStr = String(decoding: data, as: UTF8.self)
            let (method, path, params) = Self.parseHTTPRequest(requestStr)
            let response: Data

            switch path {
            case "/api/screenshot":
                response = self.handleScreenshotRequest(params: params)
            case "/api/capture-status":
                response = self.handleCaptureStatus()
            case let p where p.hasPrefix("/api/"):
                response = self.proxyToAgentCore(method: method, path: p, requestStr: requestStr)
            default:
                response = self.buildHTMLResponse()
            }

            conn.send(content: response, completion: .contentProcessed { _ in
                conn.cancel()
            })
        }
    }

    /// Parse HTTP request line to extract method, path and query parameters.
    /// Example: "GET /api/screenshot?x=0&y=0&w=200&h=50 HTTP/1.1" → ("GET", "/api/screenshot", ["x":"0", ...])
    private static func parseHTTPRequest(_ request: String) -> (method: String, path: String, params: [String: String]) {
        let lines = request.components(separatedBy: "\r\n")
        guard let firstLine = lines.first else { return ("GET", "/", [:]) }
        let parts = firstLine.components(separatedBy: " ")
        guard parts.count >= 2 else { return ("GET", "/", [:]) }

        let method = parts[0]
        let uri = parts[1]
        let uriParts = uri.components(separatedBy: "?")
        let path = uriParts[0]

        var params: [String: String] = [:]
        if uriParts.count >= 2 {
            let query = uriParts[1]
            for pair in query.components(separatedBy: "&") {
                let kv = pair.components(separatedBy: "=")
                if kv.count == 2 {
                    let key = kv[0].removingPercentEncoding ?? kv[0]
                    let value = kv[1].removingPercentEncoding ?? kv[1]
                    params[key] = value
                }
            }
        }
        return (method, path, params)
    }

    /// Build a JSON HTTP response with CORS headers.
    private static func jsonResponse(statusCode: Int = 200, body: [String: Any]) -> Data {
        guard let jsonData = try? JSONSerialization.data(withJSONObject: body, options: []) else {
            return Self.errorResponse(statusCode: 500, message: "JSON serialization failed")
        }
        let header = "HTTP/1.1 \(statusCode) \(statusCode == 200 ? "OK" : "Error")\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: \(jsonData.count)\r\n" +
            "Access-Control-Allow-Origin: *\r\n" +
            "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n" +
            "Cache-Control: no-store\r\n" +
            "Connection: close\r\n\r\n"
        return Data(header.utf8) + jsonData
    }

    /// Build a plain error HTTP response.
    private static func errorResponse(statusCode: Int, message: String) -> Data {
        let body = Data(message.utf8)
        let header = "HTTP/1.1 \(statusCode) \(statusCode == 200 ? "OK" : "Error")\r\n" +
            "Content-Type: text/plain; charset=utf-8\r\n" +
            "Content-Length: \(body.count)\r\n" +
            "Access-Control-Allow-Origin: *\r\n" +
            "Cache-Control: no-store\r\n" +
            "Connection: close\r\n\r\n"
        return Data(header.utf8) + body
    }

    private func buildHTMLResponse() -> Data {
        let html = Self.generateHTML(wsPort: wsPort, authToken: authToken)
        let body = Data(html.utf8)
        let header = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: \(body.count)\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
        return Data(header.utf8) + body
    }

    // MARK: - Screenshot API

    /// Handle /api/screenshot: capture a region of the screen and return JPEG base64.
    /// Query params: x, y, w, h (integers, pixels). Defaults to full screen if omitted.
    private func handleScreenshotRequest(params: [String: String]) -> Data {
        let x = Int(params["x"] ?? "") ?? 0
        let y = Int(params["y"] ?? "") ?? 0
        let w = Int(params["w"] ?? "") ?? Int(NSScreen.main?.frame.width ?? 1440)
        let h = Int(params["h"] ?? "") ?? Int(NSScreen.main?.frame.height ?? 900)

        guard w > 0, h > 0 else {
            return Self.jsonResponse(statusCode: 400, body: ["error": "Invalid region dimensions"])
        }

        // Use /usr/sbin/screencapture (built-in macOS tool, not deprecated)
        // This avoids ScreenCaptureKit API unavailability in macOS 15+ SDK
        guard let jpegData = Self.captureScreenRegion(x: x, y: y, width: w, height: h) else {
            return Self.jsonResponse(statusCode: 500, body: [
                "error": "Failed to capture screen region",
                "hint": "The screencapture tool may need Screen Recording permission."
            ])
        }

        let base64 = jpegData.base64EncodedString()

        return Self.jsonResponse(body: [
            "status": "ok",
            "width": w,
            "height": h,
            "x": x,
            "y": y,
            "format": "jpeg",
            "data": base64,
            "size_bytes": jpegData.count,
        ])
    }

    /// Capture a screen region using /usr/sbin/screencapture (Process-based).
    /// Returns JPEG data, or nil on failure.
    private static func captureScreenRegion(x: Int, y: Int, width: Int, height: Int) -> Data? {
        let tempPath = "/tmp/textream_shot_\(UUID().uuidString).jpg"
        defer { try? FileManager.default.removeItem(atPath: tempPath) }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        process.arguments = ["-x", "-t", "jpg", "-R", "\(x),\(y),\(width),\(height)", tempPath]

        do {
            try process.run()
            process.waitUntilExit()
            guard process.terminationStatus == 0 else {
                Self.logger.error("screencapture exited with code \(process.terminationStatus)")
                return nil
            }
            return try? Data(contentsOf: URL(fileURLWithPath: tempPath))
        } catch {
            Self.logger.error("screencapture failed: \(error.localizedDescription)")
            return nil
        }
    }

    /// Handle /api/capture-status: return whether screen capture is available.
    private func handleCaptureStatus() -> Data {
        let canCapture = Self.captureScreenRegion(x: 0, y: 0, width: 1, height: 1) != nil
        return Self.jsonResponse(body: [
            "status": "ok",
            "can_capture": canCapture,
            "hint": canCapture
                ? "Screen capture is available"
                : "The screencapture tool may need Screen Recording permission.",
        ])
    }

    // MARK: - Agent Core Proxy

    /// 代理 /api/* 请求到 Agent Core (port 9123)
    /// 将 DirectorServer 收到的 HTTP 请求转发到 Python 后端，返回其结果。
    private func proxyToAgentCore(method: String, path: String, requestStr: String) -> Data {
        let agentPort = 9123
        guard let url = URL(string: "http://127.0.0.1:\(agentPort)\(path)") else {
            return Self.errorResponse(statusCode: 500, message: "Invalid proxy URL")
        }

        // 解析请求体（POST/PUT 时从请求字符串中提取）
        let lines = requestStr.components(separatedBy: "\r\n")
        var bodyData: Data?
        var contentLength = 0

        var inHeaders = true
        for line in lines.dropFirst() { // 跳过请求行
            if inHeaders {
                if line.isEmpty {
                    inHeaders = false
                    continue
                }
                let headerParts = line.components(separatedBy: ": ")
                if headerParts.count == 2, headerParts[0].lowercased() == "content-length" {
                    contentLength = Int(headerParts[1]) ?? 0
                }
            }
        }

        // 提取请求体（位于空行之后）
        if contentLength > 0, let bodyStart = requestStr.range(of: "\r\n\r\n") {
            let bodyString = String(requestStr[bodyStart.upperBound...])
            if let data = bodyString.data(using: .utf8), data.count >= contentLength {
                bodyData = data
            }
        }

        // 使用信号量同步等待 URLSession 结果
        var resultData: Data?
        let semaphore = DispatchSemaphore(value: 0)

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = bodyData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = 30

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse {
                // 构建代理响应（保留原始状态码和内容）
                let body = data ?? Data()
                let statusCode = httpResponse.statusCode
                let statusText = statusCode == 200 ? "OK" : (statusCode == 404 ? "Not Found" : "Error")
                let header = "HTTP/1.1 \(statusCode) \(statusText)\r\n" +
                    "Content-Type: \(httpResponse.mimeType ?? "application/json"); charset=utf-8\r\n" +
                    "Content-Length: \(body.count)\r\n" +
                    "Access-Control-Allow-Origin: *\r\n" +
                    "Cache-Control: no-store\r\n" +
                    "Connection: close\r\n\r\n"
                resultData = Data(header.utf8) + body
            } else {
                resultData = Self.errorResponse(statusCode: 502, message: "Agent Core proxy failed: \(error?.localizedDescription ?? "unknown")")
            }
            semaphore.signal()
        }
        task.resume()
        semaphore.wait()

        return resultData ?? Self.errorResponse(statusCode: 502, message: "Agent Core proxy failed")
    }

    // MARK: - WebSocket Server

    private func startWSListener() {
        guard let port = NWEndpoint.Port(rawValue: wsPort) else { return }
        let params = NWParameters.tcp
        let wsOptions = NWProtocolWebSocket.Options()
        params.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)

        do {
            wsListener = try NWListener(using: params, on: port)
        } catch { return }

        wsListener?.stateUpdateHandler = { [weak self] state in
            if case .failed = state { self?.wsListener = nil }
        }
        wsListener?.newConnectionHandler = { [weak self] conn in
            self?.handleWSConnection(conn)
        }
        wsListener?.start(queue: .main)
    }

    private func handleWSConnection(_ conn: NWConnection) {
        guard wsConnections.count < maxConnections else {
            conn.cancel()
            return
        }
        conn.start(queue: .main)
        wsConnections.append(conn)
        receiveWSMessage(conn)

        // Auto-disconnect unauthenticated connections after 5 seconds
        let connId = ObjectIdentifier(conn)
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
            guard let self else { return }
            if !self.authenticatedConnections.contains(connId) {
                conn.cancel()
            }
        }

        conn.stateUpdateHandler = { [weak self] state in
            switch state {
            case .failed, .cancelled:
                self?.wsConnections.removeAll { $0 === conn }
                self?.authenticatedConnections.remove(ObjectIdentifier(conn))
            default: break
            }
        }
    }

    private func receiveWSMessage(_ conn: NWConnection) {
        conn.receiveMessage { [weak self] data, _, _, error in
            if error != nil { conn.cancel(); return }
            if let data {
                self?.handleIncomingMessage(data, from: conn)
            }
            self?.receiveWSMessage(conn)
        }
    }

    private func handleIncomingMessage(_ data: Data, from conn: NWConnection) {
        guard let command = try? JSONDecoder().decode(DirectorCommand.self, from: data) else { return }
        let connId = ObjectIdentifier(conn)

        DispatchQueue.main.async { [weak self] in
            guard let self else { return }

            // First message must be authentication
            if !self.authenticatedConnections.contains(connId) {
                if command.type == "auth", command.text == self.authToken {
                    self.authenticatedConnections.insert(connId)
                } else {
                    conn.cancel()
                }
                return
            }

            switch command.type {
            case "setText":
                if let text = command.text {
                    self.onSetText?(text)
                }
            case "updateText":
                if let text = command.text, let readCharCount = command.readCharCount {
                    self.onUpdateText?(text, readCharCount)
                }
            case "stop":
                self.onStop?()
            default:
                break
            }
        }
    }

    // MARK: - Token Generation

    private static func generateToken() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return bytes.map { String(format: "%02x", $0) }.joined()
    }

    // MARK: - Broadcasting

    private func startBroadcasting() {
        broadcastTimer?.invalidate()
        broadcastTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.broadcastCurrentState()
        }
    }

    private func broadcastCurrentState() {
        guard contentActive, !wsConnections.isEmpty else { return }

        let charCount = speechRecognizer?.recognizedCharCount ?? 0
        let effective = min(charCount, totalCharCount)
        let isDone = totalCharCount > 0 && effective >= totalCharCount

        let state = DirectorState(
            words: words,
            highlightedCharCount: effective,
            totalCharCount: totalCharCount,
            isActive: true,
            isDone: isDone,
            isListening: speechRecognizer?.isListening ?? false,
            fontColor: NotchSettings.shared.fontColorPreset.cssColor,
            cueColor: NotchSettings.shared.cueColorPreset.cssColor,
            lastSpokenText: speechRecognizer?.lastSpokenText ?? "",
            audioLevels: (speechRecognizer?.audioLevels ?? []).map { Double($0) }
        )
        broadcast(state)
    }

    private func broadcastInactive() {
        let state = DirectorState(
            words: [], highlightedCharCount: 0, totalCharCount: 0,
            isActive: false, isDone: false, isListening: false,
            fontColor: "#ffffff", cueColor: "#ffffff", lastSpokenText: "",
            audioLevels: []
        )
        broadcast(state)
    }

    private func broadcast(_ state: DirectorState) {
        guard !wsConnections.isEmpty, let data = try? JSONEncoder().encode(state) else { return }

        // Skip broadcast if state hasn't changed
        if let last = lastBroadcastState, last == data { return }
        lastBroadcastState = data

        let connections = wsConnections.filter { authenticatedConnections.contains(ObjectIdentifier($0)) }
        guard !connections.isEmpty else { return }
        let meta = NWProtocolWebSocket.Metadata(opcode: .text)
        let ctx = NWConnection.ContentContext(identifier: "ws", metadata: [meta])

        broadcastQueue.async {
            for conn in connections {
                conn.send(content: data, contentContext: ctx, completion: .idempotent)
            }
        }
    }

    // MARK: - HTML Template

    static func generateHTML(wsPort: UInt16, authToken: String) -> String {
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
        <title>Textream</title>
        <style>
        *{margin:0;padding:0;box-sizing:border-box}
        html,body{height:100%;overflow:hidden;background:#0a0a0a;color:#e0e0e0;
          font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Helvetica Neue',monospace,sans-serif}
        body{display:flex;flex-direction:column}

        /* ── Tab bar ── */
        #tab-bar{flex-shrink:0;display:flex;background:rgba(0,0,0,0.6);
          border-bottom:1px solid rgba(255,255,255,0.06)}
        .tab-btn{flex:1;padding:10px 0;font-size:12px;font-weight:600;letter-spacing:0.5px;
          text-transform:uppercase;border:none;background:transparent;color:rgba(255,255,255,0.3);
          cursor:pointer;transition:all .15s;position:relative}
        .tab-btn:hover{color:rgba(255,255,255,0.6)}
        .tab-btn.active{color:#fff}
        .tab-btn.active::after{content:'';position:absolute;bottom:0;left:20%;right:20%;
          height:2px;background:#fff;border-radius:1px}

        /* ── Tab panels ── */
        .tab-panel{display:none;flex:1;overflow:hidden;flex-direction:column}
        .tab-panel.active{display:flex}

        /* ── Director tab (existing) ── */
        #status-bar{flex-shrink:0;padding:10px 16px;display:flex;align-items:center;gap:10px;
          border-bottom:1px solid rgba(255,255,255,0.06)}
        #status-dot{width:7px;height:7px;border-radius:50%;background:#555;flex-shrink:0}
        #status-dot.connected{background:#4ade80}
        #status-dot.active{background:#facc15;animation:pulse-dot 1.5s ease-in-out infinite}
        @keyframes pulse-dot{0%,100%{opacity:1}50%{opacity:0.4}}
        #status-text{font-size:12px;color:rgba(255,255,255,0.4);flex:1}
        #progress-text{font-size:12px;font-weight:600;color:rgba(255,255,255,0.3);
          font-variant-numeric:tabular-nums}

        #editor-wrap{flex:1;overflow:hidden;position:relative}
        #editor-container{height:100%;overflow-y:auto;padding:16px}
        #editor-container::-webkit-scrollbar{display:none}
        #read-text{color:rgba(255,255,255,0.25);font-size:16px;line-height:1.6;
          font-weight:500;white-space:pre-wrap;word-wrap:break-word;
          pointer-events:none;user-select:none}
        #read-text:empty{display:none}
        #edit-text{color:#e0e0e0;font-size:16px;line-height:1.6;font-weight:500;
          white-space:pre-wrap;word-wrap:break-word;outline:none;
          min-height:50vh;caret-color:#facc15}
        #edit-text:empty::before{content:attr(data-placeholder);color:rgba(255,255,255,0.15)}
        #read-divider{height:2px;background:linear-gradient(to right,#facc15,transparent);
          margin:6px 0;border-radius:1px;display:none}
        #read-divider.visible{display:block}

        #controls{flex-shrink:0;padding:12px 16px;
          border-top:1px solid rgba(255,255,255,0.06);
          display:flex;align-items:center;gap:10px}
        .ctrl-btn{border:none;border-radius:8px;padding:10px 20px;font-size:13px;
          font-weight:600;cursor:pointer;transition:all .15s ease;
          display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.08);color:#e0e0e0}
        .ctrl-btn:hover{background:rgba(255,255,255,0.14)}
        .ctrl-btn:active{transform:scale(0.97)}
        #go-btn{background:#22c55e;color:#fff}
        #go-btn:hover{background:#16a34a}
        #go-btn.running{background:#ef4444}
        #go-btn.running:hover{background:#dc2626}
        #go-btn:disabled{opacity:0.4;cursor:not-allowed}
        #waveform{display:flex;align-items:center;gap:1.5px;height:24px;flex:1;justify-content:flex-end}
        .wf-bar{width:2px;background:rgba(255,255,255,.08);border-radius:1px;min-height:2px;transition:height .08s ease;align-self:center}
        #mic-indicator{width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:12px}
        #mic-indicator.on{background:rgba(250,204,21,0.15)}

        #done-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);
          flex-direction:column;align-items:center;justify-content:center;gap:12px;z-index:100}
        #done-overlay.show{display:flex}
        #done-overlay .check{width:48px;height:48px;border-radius:50%;background:#22c55e;
          display:flex;align-items:center;justify-content:center;font-size:24px;color:#fff}
        #done-overlay .label{font-size:22px;font-weight:700}
        #done-overlay .reset-btn{margin-top:8px;background:rgba(255,255,255,0.1);color:#fff;
          border:none;border-radius:8px;padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer}

        /* ── Agent tab ── */
        #agent-panel{flex:1;overflow-y:auto;padding:16px;-webkit-overflow-scrolling:touch}
        #agent-panel::-webkit-scrollbar{display:none}
        .ag-section{margin-bottom:20px}
        .ag-section-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;
          color:rgba(255,255,255,0.25);margin-bottom:10px}
        .ag-stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
        .ag-stat-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);
          border-radius:8px;padding:12px}
        .ag-stat-value{font-size:20px;font-weight:700;color:#fff}
        .ag-stat-label{font-size:10px;color:rgba(255,255,255,0.3);text-transform:uppercase;letter-spacing:0.5px;margin-top:2px}
        .ag-btn{border:none;border-radius:6px;padding:8px 14px;font-size:12px;font-weight:600;
          cursor:pointer;transition:all .12s;background:rgba(255,255,255,0.08);color:#e0e0e0}
        .ag-btn:hover{background:rgba(255,255,255,0.14)}
        .ag-btn:active{transform:scale(0.97)}
        .ag-input{width:100%;padding:8px 10px;border:1px solid rgba(255,255,255,0.1);
          border-radius:6px;background:rgba(0,0,0,0.3);color:#e0e0e0;font-size:13px;outline:none}
        .ag-input:focus{border-color:rgba(255,255,255,0.2)}
        .ag-input::placeholder{color:rgba(255,255,255,0.2)}
        .ag-search-row{display:flex;gap:6px;margin-bottom:10px}
        .ag-search-row .ag-input{flex:1}
        .ag-memory-item{padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)}
        .ag-memory-item:last-child{border-bottom:none}
        .ag-mem-title{font-size:13px;font-weight:600;color:#e0e0e0}
        .ag-mem-meta{font-size:10px;color:rgba(255,255,255,0.25);margin-top:2px}
        .ag-mem-content{font-size:12px;color:rgba(255,255,255,0.45);margin-top:4px;line-height:1.4}
        .ag-empty{color:rgba(255,255,255,0.2);font-size:12px;text-align:center;padding:20px 0}
        .ag-chat-box{background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.06);
          border-radius:8px;padding:12px;min-height:80px;margin-bottom:8px;
          font-size:12px;line-height:1.5;color:rgba(255,255,255,0.6);white-space:pre-wrap;overflow-y:auto;max-height:200px}
        .ag-chat-row{display:flex;gap:6px}
        .ag-chat-row .ag-input{flex:1}
        .ag-kb-item{padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04)}
        .ag-kb-item:last-child{border-bottom:none}
        .ag-kb-name{font-size:12px;font-weight:600;color:#e0e0e0}
        .ag-kb-snippet{font-size:11px;color:rgba(255,255,255,0.35);margin-top:2px;line-height:1.3}
        .ag-online{color:#4ade80}
        .ag-offline{color:#ef4444}

        /* Persona tags */
        #persona-tags{display:flex;flex-wrap:wrap;gap:6px;min-height:20px}
        .ag-tag{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;
          border:1px solid rgba(255,255,255,0.12);border-radius:12px;font-size:11px;
          font-weight:500;color:rgba(255,255,255,0.7);background:rgba(255,255,255,0.04);
          cursor:pointer;transition:all .12s}
        .ag-tag:hover{background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.2)}
        .ag-tag .del{font-size:10px;color:rgba(255,255,255,0.3);margin-left:2px}
        .ag-tag .del:hover{color:#ef4444}

        /* Error book cards */
        .ag-error-card{border:1px solid rgba(239,68,68,0.15);background:rgba(239,68,68,0.04);
          border-radius:8px;padding:10px 12px;margin-bottom:8px}
        .ag-error-title{font-size:13px;font-weight:600;color:#e0e0e0}
        .ag-error-scene{font-size:10px;color:rgba(255,255,255,0.3);margin-top:2px}
        .ag-error-lesson{font-size:11px;color:rgba(255,255,255,0.5);margin-top:4px;line-height:1.4;
          padding:4px 8px;background:rgba(255,255,255,0.03);border-radius:4px}
        </style>
        </head>
        <body>

        <!-- Tab bar -->
        <div id="tab-bar">
          <button class="tab-btn active" data-tab="director">提词器</button>
          <button class="tab-btn" data-tab="agent">智能体</button>
        </div>

        <!-- ════════════════ Director Tab ════════════════ -->
        <div id="tab-director" class="tab-panel active">
          <div id="status-bar">
            <div id="status-dot"></div>
            <div id="status-text">\(LocalizedStrings.connecting)</div>
            <div id="progress-text"></div>
          </div>
          <div id="editor-wrap">
            <div id="editor-container">
              <div id="read-text"></div>
              <div id="read-divider"></div>
              <div id="edit-text" contenteditable="true" data-placeholder="\(LocalizedStrings.typeOrPasteScript)" spellcheck="false"></div>
            </div>
          </div>
          <div id="controls">
            <button id="go-btn" class="ctrl-btn" onclick="toggleGo()">\(LocalizedStrings.go)</button>
            <div id="waveform"></div>
            <div id="mic-indicator">🎤</div>
          </div>
          <div id="done-overlay">
            <div class="check">✓</div>
            <div class="label">\(LocalizedStrings.doneLabel)</div>
            <button class="reset-btn" onclick="resetAll()">\(LocalizedStrings.newScript)</button>
          </div>
        </div>

        <!-- ════════════════ Agent Tab ════════════════ -->
        <div id="tab-agent" class="tab-panel">
          <div id="agent-panel">

            <!-- 状态概览 -->
            <div class="ag-section">
              <div class="ag-section-title">状态</div>
              <div class="ag-stat-grid">
                <div class="ag-stat-card">
                  <div class="ag-stat-value" id="agent-status">--</div>
                  <div class="ag-stat-label">智能体</div>
                </div>
                <div class="ag-stat-card">
                  <div class="ag-stat-value" id="memory-count">--</div>
                  <div class="ag-stat-label">记忆</div>
                </div>
                <div class="ag-stat-card">
                  <div class="ag-stat-value" id="knowledge-count">--</div>
                  <div class="ag-stat-label">知识库</div>
                </div>
                <div class="ag-stat-card">
                  <div class="ag-stat-value" id="llm-status">--</div>
                  <div class="ag-stat-label">大模型</div>
                </div>
              </div>
            </div>

            <!-- 人格画像 -->
            <div class="ag-section">
              <div class="ag-section-title">人格画像</div>
              <div id="persona-tags"></div>
            </div>

            <!-- 错题本 -->
            <div class="ag-section">
              <div class="ag-section-title">错题本</div>
              <div id="error-book"></div>
            </div>

            <!-- 记忆 -->
            <div class="ag-section">
              <div class="ag-section-title">记忆</div>
              <div class="ag-search-row">
                <input class="ag-input" id="mem-search-input" placeholder="搜索记忆..." />
                <button class="ag-btn" id="mem-search-btn">搜索</button>
                <button class="ag-btn" id="mem-refresh-btn">全部</button>
              </div>
              <div id="memory-list"></div>
            </div>

            <!-- 知识库 -->
            <div class="ag-section">
              <div class="ag-section-title">知识库</div>
              <div class="ag-search-row">
                <input class="ag-input" id="kb-search-input" placeholder="搜索知识库..." />
                <button class="ag-btn" id="kb-search-btn">搜索</button>
                <button class="ag-btn" id="kb-refresh-btn">全部</button>
              </div>
              <div id="kb-list"></div>
            </div>

            <!-- AI 对话 -->
            <div class="ag-section">
              <div class="ag-section-title">AI 对话</div>
              <div class="ag-chat-box" id="chat-output">向智能体提问...</div>
              <div class="ag-chat-row">
                <input class="ag-input" id="chat-input" placeholder="输入问题..." />
                <button class="ag-btn" id="chat-send-btn">发送</button>
              </div>
            </div>

          </div>
        </div>

        <script>
        const WSP=\(wsPort),host=location.hostname,AUTH_TOKEN='\(authToken)';
        const AGENT_URL = 'http://localhost:9123';
        let ws,rt,isActive=false,isRunning=false,lastReadCount=0;

        /* ════════════════ Tab Switching ════════════════ */
        document.querySelectorAll('.tab-btn').forEach(btn => {
          btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');
            if (this.dataset.tab === 'agent') refreshAgent();
          });
        });

        /* ════════════════ Director (existing) ════════════════ */
        function connect(){
          ws=new WebSocket('ws://'+host+':'+WSP);
          ws.onopen=()=>{clearTimeout(rt);
            ws.send(JSON.stringify({type:'auth',text:AUTH_TOKEN}));
            document.getElementById('status-dot').className='connected';
            document.getElementById('status-text').textContent='\(LocalizedStrings.connected)';};
          ws.onmessage=e=>{try{handleState(JSON.parse(e.data))}catch(x){console.error(x)}};
          ws.onclose=()=>{
            document.getElementById('status-dot').className='';
            document.getElementById('status-text').textContent='\(LocalizedStrings.reconnecting)';
            rt=setTimeout(connect,1500);};
          ws.onerror=()=>{ws.close()};
        }
        function send(obj){if(ws&&ws.readyState===1)ws.send(JSON.stringify(obj));}
        function handleState(s){
          const doneEl=document.getElementById('done-overlay');
          if(!s.isActive){isActive=false;isRunning=false;updateGoButton();
            document.getElementById('status-dot').className='connected';
            document.getElementById('progress-text').textContent='';return;}
          if(s.isDone){doneEl.classList.add('show');isRunning=false;updateGoButton();return;}
          doneEl.classList.remove('show');
          isActive=true;isRunning=true;updateGoButton();
          document.getElementById('status-dot').className='active';
          const pct=s.totalCharCount>0?Math.round(s.highlightedCharCount/s.totalCharCount*100):0;
          document.getElementById('progress-text').textContent=pct+'%';
          lastReadCount=s.highlightedCharCount;updateReadBoundary(s.highlightedCharCount);
          const wf=document.getElementById('waveform'),lv=s.audioLevels||[];
          while(wf.children.length<lv.length){const b=document.createElement('div');b.className='wf-bar';wf.appendChild(b)}
          for(let i=0;i<wf.children.length;i++){
            const l=i<lv.length?lv[i]:0;
            wf.children[i].style.height=Math.max(2,l*24)+'px';
            wf.children[i].style.background=l>0.05?'rgba(250,204,21,0.6)':'rgba(255,255,255,0.08)';
          }
          document.getElementById('mic-indicator').className=s.isListening?'on':'';
        }
        function getText(el){return (el.innerText||el.textContent||'').replace(/\\n/g,' ');}
        function getFullText(){return getText(document.getElementById('read-text'))+getText(document.getElementById('edit-text'));}
        function updateReadBoundary(charCount){
          if(charCount<=0)return;
          const fullText=getFullText();if(charCount>fullText.length)charCount=fullText.length;
          const readPart=fullText.substring(0,charCount),editPart=fullText.substring(charCount);
          const readEl=document.getElementById('read-text'),editEl=document.getElementById('edit-text');
          const divider=document.getElementById('read-divider');
          readEl.textContent=readPart;divider.classList.toggle('visible',readPart.length>0);
          if(editEl.textContent!==editPart)editEl.textContent=editPart;
        }
        function toggleGo(){
          if(isRunning){send({type:'stop'});isRunning=false;updateGoButton();}
          else{const fullText=getFullText();if(!fullText.trim())return;
            send({type:'setText',text:fullText});isRunning=true;updateGoButton();}
        }
        function updateGoButton(){
          const btn=document.getElementById('go-btn');
          if(isRunning){btn.textContent='\(LocalizedStrings.stop)';btn.classList.add('running');}
          else{btn.textContent='\(LocalizedStrings.go)';btn.classList.remove('running');}
        }
        let editDebounce=null;
        document.getElementById('edit-text').addEventListener('input',function(){
          if(!isRunning)return;clearTimeout(editDebounce);
          editDebounce=setTimeout(()=>{send({type:'updateText',text:getFullText(),readCharCount:lastReadCount});},300);
        });
        function resetAll(){
          document.getElementById('done-overlay').classList.remove('show');
          document.getElementById('read-text').textContent='';
          document.getElementById('edit-text').textContent='';
          document.getElementById('read-divider').classList.remove('visible');
          document.getElementById('progress-text').textContent='';
          isRunning=false;isActive=false;lastReadCount=0;updateGoButton();
        }
        const wfInit=document.getElementById('waveform');
        for(let i=0;i<20;i++){const b=document.createElement('div');b.className='wf-bar';b.style.height='2px';wfInit.appendChild(b)}

        /* ════════════════ Agent ════════════════ */
        async function api(path) {
          try {
            const r = await fetch(AGENT_URL + path);
            return await r.json();
          } catch(e) {
            return {error: true, message: e.message};
          }
        }

        async function refreshAgent() {
          const s = await api('/api/status');
          if (s.error) {
            document.getElementById('agent-status').textContent = '离线';
            document.getElementById('agent-status').className = 'ag-stat-value ag-offline';
            document.getElementById('memory-count').textContent = '-';
            document.getElementById('knowledge-count').textContent = '-';
            document.getElementById('llm-status').textContent = '-';
            return;
          }
          document.getElementById('agent-status').textContent = '在线';
          document.getElementById('agent-status').className = 'ag-stat-value ag-online';
          document.getElementById('memory-count').textContent = s.memory_count ?? 0;
          document.getElementById('knowledge-count').textContent = s.knowledge_count ?? 0;
          document.getElementById('llm-status').textContent = s.llm_configured ? '就绪' : '未配置';
          document.getElementById('llm-status').className = 'ag-stat-value ' + (s.llm_configured ? 'ag-online' : 'ag-offline');

          refreshMemoryList();
          refreshKBList();
          refreshPersona();
          refreshErrorBook();
        }

        async function refreshPersona() {
          const data = await api('/api/memory/list?limit=100');
          const el = document.getElementById('persona-tags');
          if (data.error || !data.items || data.items.length === 0) {
            el.innerHTML = '<div class="ag-empty">暂无画像数据</div>';
            return;
          }
          // Collect all unique tags from memories
          const tagSet = new Set();
          data.items.forEach(m => (m.tags || []).forEach(t => tagSet.add(t)));
          const tags = Array.from(tagSet);
          if (tags.length === 0) {
            el.innerHTML = '<div class="ag-empty">暂无标签</div>';
            return;
          }
          el.innerHTML = tags.map(t => '<span class="ag-tag">#' + t + '<span class="del">&times;</span></span>').join('');
        }

        async function refreshErrorBook() {
          const data = await api('/api/memory/list?limit=100');
          const el = document.getElementById('error-book');
          if (data.error || !data.items || data.items.length === 0) {
            el.innerHTML = '<div class="ag-empty">暂无错题记录</div>';
            return;
          }
          const errors = data.items.filter(m => (m.importance || 0) >= 5);
          if (errors.length === 0) {
            el.innerHTML = '<div class="ag-empty">暂无严重错误，表现不错！</div>';
            return;
          }
          el.innerHTML = errors.map(m => {
            const ts = (m.timestamp || '').substring(0, 10);
            return '<div class="ag-error-card">' +
              '<div class="ag-error-title">' + (m.title || '未知') + '</div>' +
              '<div class="ag-error-scene">' + ts + ' · 重要度 ' + (m.importance || 0) + '</div>' +
              '<div class="ag-error-lesson">' + (m.content || '').substring(0, 200) + '</div>' +
              '</div>';
          }).join('');
        }

        async function refreshMemoryList(query) {
          const el = document.getElementById('memory-list');
          let url = '/api/memory/list?limit=30';
          if (query) url = '/api/memory/search?q=' + encodeURIComponent(query);
          const data = await api(url);
          if (data.error || !data.items || data.items.length === 0) {
            el.innerHTML = '<div class="ag-empty">' + (query ? '无匹配记忆' : '暂无记忆') + '</div>';
            return;
          }
          el.innerHTML = data.items.map(m => {
            const ts = (m.timestamp || '').substring(0, 10);
            const tags = (m.tags || []).map(t => '<span style="font-size:10px;color:rgba(255,255,255,0.3);margin-right:4px">#' + t + '</span>').join('');
            return '<div class="ag-memory-item">' +
              '<div class="ag-mem-title">' + m.title + '</div>' +
              '<div class="ag-mem-meta">' + ts + ' · 重要度 ' + (m.importance || 3) + ' · ' + tags + '</div>' +
              '<div class="ag-mem-content">' + (m.content || '').substring(0, 150) + '</div>' +
              '</div>';
          }).join('');
        }

        async function refreshKBList(query) {
          const el = document.getElementById('kb-list');
          let url = '/api/knowledge/list';
          if (query) url = '/api/knowledge/search?q=' + encodeURIComponent(query);
          const data = await api(url);
          if (data.error || !data.items || data.items.length === 0) {
            el.innerHTML = '<div class="ag-empty">' + (query ? '无匹配知识库' : '暂无知识库') + '</div>';
            return;
          }
          el.innerHTML = data.items.map(k => {
            const snippet = k.snippet || (k.content || '').substring(0, 200);
            return '<div class="ag-kb-item">' +
              '<div class="ag-kb-name">' + k.name + '</div>' +
              '<div class="ag-kb-snippet">' + snippet + '</div>' +
              '</div>';
          }).join('');
        }

        // Memory search
        document.getElementById('mem-search-btn').addEventListener('click', function() {
          const q = document.getElementById('mem-search-input').value.trim();
          refreshMemoryList(q || undefined);
        });
        document.getElementById('mem-search-input').addEventListener('keydown', function(e) {
          if (e.key === 'Enter') document.getElementById('mem-search-btn').click();
        });
        document.getElementById('mem-refresh-btn').addEventListener('click', function() {
          document.getElementById('mem-search-input').value = '';
          refreshMemoryList();
        });

        // Knowledge search
        document.getElementById('kb-search-btn').addEventListener('click', function() {
          const q = document.getElementById('kb-search-input').value.trim();
          refreshKBList(q || undefined);
        });
        document.getElementById('kb-search-input').addEventListener('keydown', function(e) {
          if (e.key === 'Enter') document.getElementById('kb-search-btn').click();
        });
        document.getElementById('kb-refresh-btn').addEventListener('click', function() {
          document.getElementById('kb-search-input').value = '';
          refreshKBList();
        });

        // Chat
        document.getElementById('chat-send-btn').addEventListener('click', async function() {
          const input = document.getElementById('chat-input');
          const msg = input.value.trim();
          if (!msg) return;
          const output = document.getElementById('chat-output');
          output.textContent = '> ' + msg + '\\n\\n思考中...';
          input.value = '';
          try {
            const r = await fetch(AGENT_URL + '/api/chat', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({message: msg, user_id: 'default'})
            });
            const data = await r.json();
            output.textContent = '> ' + msg + '\\n\\n' + (data.reply || '[无回复]');
          } catch(e) {
            output.textContent = '> ' + msg + '\\n\\n[错误] ' + e.message;
          }
        });
        document.getElementById('chat-input').addEventListener('keydown', function(e) {
          if (e.key === 'Enter') document.getElementById('chat-send-btn').click();
        });

        connect();
        </script>
        </body>
        </html>
        """
    }
}
