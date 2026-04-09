@echo off

rem 验证模块脚本
if "%1"=="" goto usage

set MODULE=%1
set LOG_DIR=..\logs
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set LOG_FILE=%LOG_DIR%\verify_%TIMESTAMP%.log

rem 创建日志目录
if not exist %LOG_DIR% mkdir %LOG_DIR%

echo ========================================
echo 开始验证模块: %MODULE%
echo ========================================
echo [%date% %time%] [INFO] 开始验证模块: %MODULE% >> %LOG_FILE%

rem 环境检查
echo [%date% %time%] [INFO] 开始环境检查 >> %LOG_FILE%
echo 开始环境检查
python --version 2>> %LOG_FILE%
if %errorlevel% neq 0 (
    echo [%date% %time%] [ERROR] Python 未安装或不在 PATH 中 >> %LOG_FILE%
    echo Python 未安装或不在 PATH 中
    exit /b 1
)

python -m pytest --version 2>> %LOG_FILE%
if %errorlevel% neq 0 (
    echo [%date% %time%] [ERROR] pytest 未安装 >> %LOG_FILE%
    echo pytest 未安装
    exit /b 1
)

echo [%date% %time%] [SUCCESS] 环境检查通过 >> %LOG_FILE%
echo 环境检查通过

rem 依赖检查
echo [%date% %time%] [INFO] 开始依赖检查 >> %LOG_FILE%
echo 开始依赖检查
if exist ..\requirements.txt (
    echo [%date% %time%] [INFO] 发现 requirements.txt 文件 >> %LOG_FILE%
    echo 发现 requirements.txt 文件
    python -m pip check >> %LOG_FILE% 2>&1
    if %errorlevel% neq 0 (
        echo [%date% %time%] [WARNING] 依赖检查失败，尝试安装依赖 >> %LOG_FILE%
        echo 依赖检查失败，尝试安装依赖
        python -m pip install -r ..\requirements.txt >> %LOG_FILE% 2>&1
        if %errorlevel% neq 0 (
            echo [%date% %time%] [ERROR] 依赖安装失败 >> %LOG_FILE%
            echo 依赖安装失败
            exit /b 1
        )
        echo [%date% %time%] [SUCCESS] 依赖安装成功 >> %LOG_FILE%
        echo 依赖安装成功
    ) else (
        echo [%date% %time%] [SUCCESS] 依赖检查通过 >> %LOG_FILE%
        echo 依赖检查通过
    )
) else (
    echo [%date% %time%] [WARNING] 未找到 requirements.txt 文件 >> %LOG_FILE%
    echo 未找到 requirements.txt 文件
)

rem 模块测试
echo [%date% %time%] [INFO] 开始模块测试 >> %LOG_FILE%
echo 开始模块测试
set ALL_TESTS_PASSED=1

if "%MODULE%"=="all" (
    set MODULES=energy_model path_planner scheduler strategies visualizer simulation_framework
) else (
    set MODULES=%MODULE%
)

for %%m in (%MODULES%) do (
    if exist ..\tests\test_%%m.py (
        echo [%date% %time%] [INFO] 测试模块: %%m >> %LOG_FILE%
        echo 测试模块: %%m
        python -m pytest ..\tests\test_%%m.py -v >> %LOG_FILE% 2>&1
        if %errorlevel% neq 0 (
            echo [%date% %time%] [ERROR] 模块 %%m 测试失败 >> %LOG_FILE%
            echo 模块 %%m 测试失败
            set ALL_TESTS_PASSED=0
        ) else (
            echo [%date% %time%] [SUCCESS] 模块 %%m 测试通过 >> %LOG_FILE%
            echo 模块 %%m 测试通过
        )
    ) else (
        echo [%date% %time%] [WARNING] 测试文件 ..\tests\test_%%m.py 不存在，跳过模块测试 >> %LOG_FILE%
        echo 测试文件 ..\tests\test_%%m.py 不存在，跳过模块测试
    )
)

rem 冒烟测试
echo [%date% %time%] [INFO] 开始冒烟测试 >> %LOG_FILE%
echo 开始冒烟测试
if exist ..\tests\test_smoke.py (
    python -m pytest ..\tests\test_smoke.py -v >> %LOG_FILE% 2>&1
    if %errorlevel% neq 0 (
        echo [%date% %time%] [ERROR] 冒烟测试失败 >> %LOG_FILE%
        echo 冒烟测试失败
        set ALL_TESTS_PASSED=0
    ) else (
        echo [%date% %time%] [SUCCESS] 冒烟测试通过 >> %LOG_FILE%
        echo 冒烟测试通过
    )
) else (
    echo [%date% %time%] [WARNING] 冒烟测试文件 ..\tests\test_smoke.py 不存在，跳过冒烟测试 >> %LOG_FILE%
    echo 冒烟测试文件 ..\tests\test_smoke.py 不存在，跳过冒烟测试
)

rem 集成检查
echo [%date% %time%] [INFO] 开始集成检查 >> %LOG_FILE%
echo 开始集成检查
if exist self_check.py (
    if "%MODULE%"=="all" (
        set STRATEGIES=baseline_direct relay_coop energy_priority
    ) else (
        set STRATEGIES=baseline_direct
    )
    
    for %%s in (%STRATEGIES%) do (
        echo [%date% %time%] [INFO] 集成检查 (策略: %%s) >> %LOG_FILE%
        echo 集成检查 (策略: %%s)
        python self_check.py --strategy %%s --seed 42 >> %LOG_FILE% 2>&1
        if %errorlevel% neq 0 (
            echo [%date% %time%] [ERROR] 集成检查 (策略: %%s) 失败 >> %LOG_FILE%
            echo 集成检查 (策略: %%s) 失败
            set ALL_TESTS_PASSED=0
        ) else (
            echo [%date% %time%] [SUCCESS] 集成检查 (策略: %%s) 通过 >> %LOG_FILE%
            echo 集成检查 (策略: %%s) 通过
        )
    )
) else (
    echo [%date% %time%] [WARNING] 集成检查脚本 self_check.py 不存在，跳过集成检查 >> %LOG_FILE%
    echo 集成检查脚本 self_check.py 不存在，跳过集成检查
)

rem 汇总结果
echo ========================================
echo 验证结果汇总
echo ========================================
echo [%date% %time%] [INFO] 验证结果汇总 >> %LOG_FILE%

if %ALL_TESTS_PASSED% equ 1 (
    echo [%date% %time%] [SUCCESS] 验证成功: 所有测试通过 >> %LOG_FILE%
    echo 验证成功: 所有测试通过
    echo 日志文件: %LOG_FILE%
) else (
    echo [%date% %time%] [ERROR] 验证失败: 部分测试未通过 >> %LOG_FILE%
    echo 验证失败: 部分测试未通过
    echo 日志文件: %LOG_FILE%
    exit /b 1
)

goto end

:usage
echo 用法: verify_module.bat [模块名]
echo 模块名: energy_model, path_planner, scheduler, strategies, visualizer, simulation_framework, all
goto end

:end