#!/usr/bin/env python3
"""
运行三种策略对比的脚本
"""

import subprocess
import sys


def main():
    """运行三种策略对比"""
    print("=== 运行三种策略对比 ===")
    
    # 构建命令
    cmd = [
        sys.executable,
        "-m", "experiments.compare_strategies",
        "--config", "configs/qualification.yaml",
        "--max-steps", "200",
        "--baseline-strategy", "baseline_direct"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 运行命令
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print("\n=== 命令输出 ===")
        print(result.stdout)
        
        if result.stderr:
            print("\n=== 错误输出 ===")
            print(result.stderr)
        
        print("\n=== 对比完成 ===")
        print("结果保存到: results/comparisons/strategy_comparison/")
        
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print(f"错误输出: {e.stderr}")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    main()
