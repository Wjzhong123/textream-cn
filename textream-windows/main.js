/**
 * Textream — 直播 AI 军师（Windows 版）
 * Electron 主进程
 *
 * 职责：
 *   1. 管理 Agent Core Python 子进程生命周期
 *   2. 提词器悬浮覆盖层（透明、置顶、无边框）
 *   3. Web Console 调试面板（系统托盘切换）
 *   4. 系统托盘图标
 */

const { app, BrowserWindow, Tray, Menu, nativeImage, screen, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// ── 常量 ─────────────────────────────────────────────────────────────────
const AGENT_PORT = 9123;
const AGENT_URL = `http://127.0.0.1:${AGENT_PORT}`;
const isDev = !app.isPackaged;

// 开发时 agent 目录在项目根目录，打包后在 resources/agent/
const AGENT_DIR = isDev
  ? path.resolve(__dirname, '..', 'agent')
  : path.join(process.resourcesPath, 'agent');

// ── 全局状态 ──────────────────────────────────────────────────────────────
let overlayWindow = null;
let consoleWindow = null;
let tray = null;
let agentProcess = null;
let agentReady = false;

// ── Agent Core 管理 ──────────────────────────────────────────────────────

/** 启动 Python Agent Core 子进程 */
function startAgentCore() {
  if (agentProcess) return;

  const pythonBin = path.join(AGENT_DIR, '.venv', 'Scripts', 'python.exe');
  // 回退到系统 Python
  const executable = require('fs').existsSync(pythonBin) ? pythonBin : 'python';

  console.log(`[AgentCore] 启动: ${executable} run_agent_v2.py`);

  agentProcess = spawn(executable, ['run_agent_v2.py'], {
    cwd: AGENT_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  agentProcess.stdout.on('data', (data) => {
    const text = data.toString();
    console.log(`[AgentCore] ${text.trim()}`);
    if (text.includes('Uvicorn running')) {
      agentReady = true;
      console.log('[AgentCore] ✅ 后端就绪');
    }
  });

  agentProcess.stderr.on('data', (data) => {
    console.error(`[AgentCore] ${data.toString().trim()}`);
  });

  agentProcess.on('close', (code) => {
    console.log(`[AgentCore] 进程退出 (code: ${code})`);
    agentProcess = null;
    agentReady = false;
  });
}

/** 停止 Agent Core 子进程 */
function stopAgentCore() {
  if (!agentProcess) return;
  console.log('[AgentCore] 正在停止...');
  agentProcess.kill('SIGTERM');
  // 3 秒后强制 kill
  setTimeout(() => {
    if (agentProcess) {
      agentProcess.kill('SIGKILL');
      agentProcess = null;
    }
  }, 3000);
}

/** 等待 Agent Core 就绪（轮询 /api/health） */
function waitForAgentCore(maxAttempts = 30) {
  return new Promise((resolve) => {
    let attempts = 0;
    const check = () => {
      attempts++;
      if (attempts > maxAttempts) {
        console.log('[AgentCore] ⏰ 等待超时');
        resolve(false);
        return;
      }
      http.get(`${AGENT_URL}/api/health`, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            if (json.status === 'ok') {
              agentReady = true;
              console.log('[AgentCore] ✅ 后端就绪');
              resolve(true);
              return;
            }
          } catch {}
          setTimeout(check, 1000);
        });
      }).on('error', () => {
        setTimeout(check, 1000);
      });
    };
    check();
  });
}

// ── 窗口创建 ──────────────────────────────────────────────────────────────

/** 创建提词器悬浮覆盖层 */
function createOverlayWindow() {
  overlayWindow = new BrowserWindow({
    width: 400,
    height: 200,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  overlayWindow.loadFile('overlay.html');
  overlayWindow.setIgnoreMouseEvents(false);

  // 点击穿透模式切换（Alt+O）
  overlayWindow.webContents.on('before-input-event', (e, input) => {
    if (input.key === 'O' && input.alt) {
      const ignore = overlayWindow.isIgnoreMouseEvents();
      overlayWindow.setIgnoreMouseEvents(!ignore);
      overlayWindow.webContents.send('click-through-mode', !ignore);
    }
  });

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });
}

/** 创建 Web Console 调试面板 */
function createConsoleWindow() {
  if (consoleWindow) {
    consoleWindow.focus();
    return;
  }

  consoleWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'Textream — 调试面板',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 加载 Agent Core 内嵌的 Web Console
  consoleWindow.loadURL(`${AGENT_URL}/`);

  consoleWindow.on('closed', () => {
    consoleWindow = null;
  });
}

// ── 系统托盘 ──────────────────────────────────────────────────────────────

function createTray() {
  // 使用 16x16 的简单图标
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);

  tray.setToolTip('Textream — 直播 AI 军师');

  updateTrayMenu();
  tray.setPressedImage(icon);

  // 双击托盘打开调试面板
  tray.on('double-click', () => {
    createConsoleWindow();
  });
}

function updateTrayMenu() {
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '📺 显示提词器',
      click: () => {
        if (overlayWindow) overlayWindow.show();
      },
    },
    {
      label: '🛠 打开调试面板',
      click: () => createConsoleWindow(),
    },
    { type: 'separator' },
    {
      label: `🔌 后端: ${agentReady ? '已连接' : '启动中...'}`,
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(contextMenu);
}

// ── IPC 处理 ──────────────────────────────────────────────────────────────

ipcMain.handle('get-agent-url', () => AGENT_URL);
ipcMain.handle('get-agent-status', () => agentReady);

// ── 应用生命周期 ──────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // 1. 启动 Agent Core
  startAgentCore();

  // 2. 创建提词器覆盖层
  createOverlayWindow();

  // 3. 创建系统托盘
  createTray();

  // 4. 等待后端就绪
  const ready = await waitForAgentCore();
  if (ready) {
    updateTrayMenu();
    // 启动后自动打开调试面板（首次使用）
    createConsoleWindow();
  }

  // 定时更新托盘状态
  setInterval(updateTrayMenu, 5000);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Windows 上不退出，保持托盘运行
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  stopAgentCore();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createOverlayWindow();
  }
});