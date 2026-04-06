#!/usr/bin/env python3
"""
验证模块脚本

用于验证各个模块的功能，包括环境检查、依赖检查、模块测试、冒烟测试和集成检查
"""

import os
import sys
import subprocess
import datetime


def write_log(log_file, message, level="INFO"):
    """写入日志
    
    Args:
        log_file: 日志文件路径
        message: 日志消息
        level: 日志级别
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def run_command(command, log_file):
    """运行命令并记录日志
    
    Args:
        command: 要运行的命令
        log_file: 日志文件路径
    
    Returns:
        int: 命令的退出码
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True,
            text=False
        )
        with open(log_file, "a", encoding="utf-8", errors="replace") as f:
            if result.stdout:
                try:
                    f.write(result.stdout.decode("utf-8"))
                except UnicodeDecodeError:
                    f.write(result.stdout.decode("gbk", errors="replace"))
            if result.stderr:
                try:
                    f.write(result.stderr.decode("utf-8"))
                except UnicodeDecodeError:
                    f.write(result.stderr.decode("gbk", errors="replace"))
        return result.returncode
    except Exception as e:
        write_log(log_file, f"命令执行失败: {e}", "ERROR")
        return 1


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python verify_module.py [模块名]")
        print("模块名: energy_model, path_planner, scheduler, strategies, visualizer, simulation_framework, all")
        sys.exit(1)
    
    module = sys.argv[1]
    
    # 检查模块名是否有效
    valid_modules = ["energy_model", "path_planner", "scheduler", "strategies", "visualizer", "simulation_framework", "all"]
    if module not in valid_modules:
        print(f"无效的模块名: {module}")
        print(f"有效模块名: {', '.join(valid_modules)}")
        sys.exit(1)
    
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"verify_{timestamp}.log")
    
    write_log(log_file, f"开始验证模块: {module}")
    
    # 环境检查
    write_log(log_file, "开始环境检查")
    write_log(log_file, "检查 Python 版本")
    ret = run_command("python --version", log_file)
    if ret != 0:
        write_log(log_file, "Python 未安装或不在 PATH 中", "ERROR")
        sys.exit(1)
    
    write_log(log_file, "检查 pytest 版本")
    ret = run_command("python -m pytest --version", log_file)
    if ret != 0:
        write_log(log_file, "pytest 未安装", "ERROR")
        sys.exit(1)
    
    write_log(log_file, "环境检查通过", "SUCCESS")
    
    # 依赖检查
    write_log(log_file, "开始依赖检查")
    requirements_file = os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
    if os.path.exists(requirements_file):
        write_log(log_file, "发现 requirements.txt 文件")
        ret = run_command("python -m pip check", log_file)
        if ret != 0:
            write_log(log_file, "依赖检查失败，尝试安装依赖", "WARNING")
            ret = run_command(f"python -m pip install -r {requirements_file}", log_file)
            if ret != 0:
                write_log(log_file, "依赖安装失败", "ERROR")
                sys.exit(1)
            write_log(log_file, "依赖安装成功", "SUCCESS")
        else:
            write_log(log_file, "依赖检查通过", "SUCCESS")
    else:
        write_log(log_file, "未找到 requirements.txt 文件", "WARNING")
    
    # 模块测试
    write_log(log_file, "开始模块测试")
    all_tests_passed = True
    
    if module == "all":
        modules = ["energy_model", "path_planner", "scheduler", "strategies", "visualizer", "simulation_framework"]
    else:
        modules = [module]
    
    for m in modules:
        test_file = os.path.join(os.path.dirname(__file__), "..", "tests", f"test_{m}.py")
        if os.path.exists(test_file):
            write_log(log_file, f"测试模块: {m}")
            ret = run_command(f"python -m pytest {test_file} -v", log_file)
            if ret != 0:
                write_log(log_file, f"模块 {m} 测试失败", "ERROR")
                all_tests_passed = False
            else:
                write_log(log_file, f"模块 {m} 测试通过", "SUCCESS")
        else:
            write_log(log_file, f"测试文件 {test_file} 不存在，跳过模块测试", "WARNING")
    
    # 冒烟测试
    write_log(log_file, "开始冒烟测试")
    smoke_test_file = os.path.join(os.path.dirname(__file__), "..", "tests", "test_smoke.py")
    if os.path.exists(smoke_test_file):
        ret = run_command(f"python -m pytest {smoke_test_file} -v", log_file)
        if ret != 0:
            write_log(log_file, "冒烟测试失败", "ERROR")
            all_tests_passed = False
        else:
            write_log(log_file, "冒烟测试通过", "SUCCESS")
    else:
        write_log(log_file, "冒烟测试文件不存在，跳过冒烟测试", "WARNING")
    
    # 集成检查
    write_log(log_file, "开始集成检查")
    self_check_script = os.path.join(os.path.dirname(__file__), "self_check.py")
    if os.path.exists(self_check_script):
        if module == "all":
            strategies = ["baseline_direct", "relay_coop", "energy_priority"]
        else:
            strategies = ["baseline_direct"]
        
        for strategy in strategies:
            write_log(log_file, f"集成检查 (策略: {strategy})")
            ret = run_command(f"python {self_check_script} --strategy {strategy} --seed 42", log_file)
            if ret != 0:
                write_log(log_file, f"集成检查 (策略: {strategy}) 失败", "ERROR")
                all_tests_passed = False
            else:
                write_log(log_file, f"集成检查 (策略: {strategy}) 通过", "SUCCESS")
    else:
        write_log(log_file, "集成检查脚本不存在，跳过集成检查", "WARNING")
    
    # 汇总结果
    print("========================================")
    print("验证结果汇总")
    print("========================================")
    write_log(log_file, "验证结果汇总")
    
    if all_tests_passed:
        write_log(log_file, "验证成功: 所有测试通过", "SUCCESS")
        print("验证成功: 所有测试通过")
        print(f"日志文件: {log_file}")
        sys.exit(0)
    else:
        write_log(log_file, "验证失败: 部分测试未通过", "ERROR")
        print("验证失败: 部分测试未通过")
        print(f"日志文件: {log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()