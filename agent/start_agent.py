"""Textream Agent Core 启动脚本"""
import sys
import os

# 添加路径
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)
sys.path.insert(0, os.path.join(agent_dir, 'vendor/captiocr'))
sys.path.insert(0, os.path.join(agent_dir, 'captiocr_adapter'))

# 解析端口
port = 9123
if '--port' in sys.argv:
    idx = sys.argv.index('--port')
    if idx + 1 < len(sys.argv):
        port = int(sys.argv[idx + 1])

from agent_core.server import create_app
import uvicorn

app = create_app()
print(f"🤖 启动 Textream Agent Core on port {port}")
uvicorn.run(app, host='127.0.0.1', port=port, log_level='info')