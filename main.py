"""
Resume & Interview Analysis App - 入口文件

启动方式:
    python main.py
    或
    uvicorn Analyzer.main:app --host 0.0.0.0 --port 8000
"""
from Analyzer.main import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
