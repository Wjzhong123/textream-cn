//
//  AgentCoreManager.swift
//  Textream
//
//  Created by One-Prime on 2.08.2026.
//
//  🆕 启动/停止 Python Agent Core 子进程（双击 App 自动拉起后端）

import Foundation
import AppKit

/// 管理 Python Agent Core 子进程的生命周期
class AgentCoreManager {
    static let shared = AgentCoreManager()

    private var process: Process?
    private var readinessCheckTimer: Timer?
    private let agentPort = 9123

    private var agentDir: URL? {
        // 开发时：../agent/（相对于 Textream.xcodeproj）
        // 打包后：Bundle.main.resourceURL!/agent/
        let devPath = URL(fileURLWithPath: #file)
            .deletingLastPathComponent() // 当前文件目录
            .deletingLastPathComponent() // Textream/ 目录
            .deletingLastPathComponent() // Textream/ 项目目录
            .appendingPathComponent("agent")

        if FileManager.default.fileExists(atPath: devPath.appendingPathComponent("run_agent_v2.py").path) {
            return devPath
        }

        // 打包后路径
        if let bundlePath = Bundle.main.resourceURL?
            .appendingPathComponent("agent") {
            if FileManager.default.fileExists(atPath: bundlePath.appendingPathComponent("run_agent_v2.py").path) {
                return bundlePath
            }
        }

        // 桌面项目路径（开发/发布通用）
        let desktopPaths = [
            URL(fileURLWithPath: NSHomeDirectory() + "/Desktop/textream-cn-master/agent"),
            URL(fileURLWithPath: NSHomeDirectory() + "/Desktop/直播AI军师/agent"),
        ]
        for path in desktopPaths {
            if FileManager.default.fileExists(atPath: path.appendingPathComponent("run_agent_v2.py").path) {
                return path
            }
        }

        // 环境变量覆盖
        if let envPath = ProcessInfo.processInfo.environment["TEXTREAM_AGENT_DIR"] {
            let envURL = URL(fileURLWithPath: envPath)
            if FileManager.default.fileExists(atPath: envURL.appendingPathComponent("run_agent_v2.py").path) {
                return envURL
            }
        }

        return nil
    }

    var isRunning: Bool {
        guard let process else { return false }
        return process.isRunning
    }

    func start() {
        guard !isRunning else {
            print("[AgentCore] 已在运行")
            return
        }

        // 异步检查后端是否已就绪，不阻塞主线程
        let healthCheck = URL(string: "http://127.0.0.1:\(agentPort)/api/health")!
        URLSession.shared.dataTask(with: healthCheck) { [weak self] data, response, error in
            guard let self = self else { return }
            DispatchQueue.main.async {
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    print("[AgentCore] ✅ 检测到已有后端运行中")
                    return
                }
                // 后端未就绪，启动它
                self._launchBackend()
            }
        }.resume()
    }

    private func _launchBackend() {
        guard let agentDir else {
            print("[AgentCore] ❌ 找不到 agent 目录")
            return
        }

        let pythonBin = agentDir
            .appendingPathComponent(".venv")
            .appendingPathComponent("bin")
            .appendingPathComponent("python")

        // 如果 .venv 不存在，回退到系统 Python
        let executable = FileManager.default.fileExists(atPath: pythonBin.path) ? pythonBin : URL(fileURLWithPath: "/usr/local/bin/python3")

        process = Process()
        process?.executableURL = executable
        process?.arguments = ["run_agent_v2.py"]
        process?.currentDirectoryURL = agentDir

        // 捕获输出用于调试（异步读取，防止阻塞子进程）
        let pipe = Pipe()
        process?.standardOutput = pipe
        process?.standardError = pipe

        // 在后台线程读取管道数据，防止缓冲区满阻塞子进程
        let outHandle = pipe.fileHandleForReading
        outHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if data.isEmpty { return }
            if let text = String(data: data, encoding: .utf8), !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                // 打印所有输出，用于调试
                for line in text.components(separatedBy: "\n") {
                    let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !trimmed.isEmpty {
                        print("[AgentCore] \(trimmed)")
                    }
                }
            }
        }

        do {
            try process?.run()
            print("[AgentCore] ✅ 启动进程 (PID: \(process?.processIdentifier ?? 0))")

            // 捕获进程退出状态
            process?.terminationHandler = { [weak self] proc in
                let status = proc.terminationStatus
                print("[AgentCore] ⚠️ 后端进程退出 (PID: \(proc.processIdentifier), 状态: \(status))")
                self?.process = nil
            }

            // 等待后端就绪（轮询 /api/health）
            startReadinessCheck()
        } catch {
            print("[AgentCore] ❌ 启动失败: \(error.localizedDescription)")
            process = nil
        }
    }

    /// 检查端口是否已被占用
    private func isPortInUse(port: Int) -> Bool {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
        task.arguments = ["-i", ":\(port)", "-P", "-n", "-l"]

        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe

        do {
            try task.run()
            task.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8) ?? ""
            return output.contains("LISTEN")
        } catch {
            return false
        }
    }

    /// 检查后端健康状态
    private func checkBackendHealth(completion: @escaping (Bool) -> Void) {
        let url = URL(string: "http://127.0.0.1:\(agentPort)/api/health")!
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode == 200 {
                DispatchQueue.main.async { completion(true) }
            } else {
                DispatchQueue.main.async { completion(false) }
            }
        }
        task.resume()
    }

    func stop() {
        readinessCheckTimer?.invalidate()
        readinessCheckTimer = nil

        guard let process, process.isRunning else {
            print("[AgentCore] 未运行，无需停止")
            return
        }

        process.terminate()
        // 给进程 3 秒优雅退出，否则强制 kill
        DispatchQueue.global().asyncAfter(deadline: .now() + 3) { [weak self] in
            guard let self, let process = self.process, process.isRunning else { return }
            // POSIX kill -9
            kill(process.processIdentifier, SIGKILL)
            print("[AgentCore] ⚠️ 强制终止进程 (PID: \(process.processIdentifier))")
        }
        print("[AgentCore] ✅ 已停止")
    }

    private func startReadinessCheck() {
        readinessCheckTimer?.invalidate()

        let url = URL(string: "http://127.0.0.1:\(agentPort)/api/health")!
        var attempts = 0
        let maxAttempts = 30 // 最多等 30 秒

        readinessCheckTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] timer in
            attempts += 1

            if attempts >= maxAttempts {
                print("[AgentCore] ⏰ 后端启动超时")
                timer.invalidate()
                return
            }

            let task = URLSession.shared.dataTask(with: url) { data, response, error in
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    DispatchQueue.main.async {
                        print("[AgentCore] ✅ 后端就绪 (port \(self?.agentPort ?? 9123))")
                        timer.invalidate()
                    }
                }
            }
            task.resume()
        }
    }

    func restart() {
        print("[AgentCore] 🔄 正在重启后端...")
        stop()
        // 等 1 秒确保进程已清理
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.start()
        }
    }

    func showStatus() {
        let status: String
        if isRunning {
            // 检测后端是否就绪
            let url = URL(string: "http://127.0.0.1:\(agentPort)/api/health")!
            let semaphore = DispatchSemaphore(value: 0)
            var backendReady = false

            let task = URLSession.shared.dataTask(with: url) { data, response, error in
                if let httpResponse = response as? HTTPURLResponse,
                   httpResponse.statusCode == 200 {
                    backendReady = true
                }
                semaphore.signal()
            }
            task.resume()
            _ = semaphore.wait(timeout: .now() + 3.0)

            if backendReady {
                status = "✅ 后端运行中 (Port \(agentPort))"
            } else {
                status = "⚠️ 进程已启动，但后端未就绪 (Port \(agentPort))"
            }
        } else {
            status = "❌ 后端未运行"
        }

        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.messageText = "后端状态"
            alert.informativeText = status
            alert.alertStyle = .informational
            alert.addButton(withTitle: "确定")
            alert.runModal()
        }
    }
}