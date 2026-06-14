@echo off
chcp 65001 > nul
echo ========================================
echo  UAV-AGV协同配送优化系统 - 在线演示
echo ========================================
echo.
echo 启动Streamlit演示页面...
echo.
echo 启动后访问: http://localhost:8501
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

"C:\Users\31675\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run demo_app.py --server.port 8501 --server.headless true
