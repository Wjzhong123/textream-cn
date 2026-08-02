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

        // 捕获输出用于调试
        let pipe = Pipe()
        process?.standardOutput = pipe
        process?.standardError = pipe

        do {
            try process?.run()
            print("[AgentCore] ✅ 启动进程 (PID: \(process?.processIdentifier ?? 0))")

            // 等待后端就绪（轮询 /api/health）
            startReadinessCheck()
        } catch {
            print("[AgentCore] ❌ 启动失败: \(error.localizedDescription)")
            process = nil
        }
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
}