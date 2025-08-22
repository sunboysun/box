# WSGI 配置檔案 for PythonAnywhere
import sys
import os

# 添加專案路徑
path = '/home/yourusername/mysite'  # 記得替換 yourusername
if path not in sys.path:
    sys.path.append(path)

from app import app as application

if __name__ == "__main__":
    application.run()
