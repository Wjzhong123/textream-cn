/**
 * Textream — 预加载脚本
 * 安全地暴露 IPC 接口到渲染进程
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('textream', {
  getAgentUrl: () => ipcRenderer.invoke('get-agent-url'),
  getAgentStatus: () => ipcRenderer.invoke('get-agent-status'),
  onClickThroughMode: (callback) => {
    ipcRenderer.on('click-through-mode', (_, enabled) => callback(enabled));
  },
});