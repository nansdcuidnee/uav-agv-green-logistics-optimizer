"""测试demo_app的辅助函数"""

from pathlib import Path
import sys


def find_latest_run_dir():
    """查找最新的单次运行目录"""
    runs_root = Path("results/runs")
    if not runs_root.exists():
        return None
    all_runs = []
    for scene_dir in runs_root.iterdir():
        if scene_dir.is_dir():
            for run_dir in scene_dir.iterdir():
                if run_dir.is_dir() and run_dir.name.startswith("202"):
                    all_runs.append(run_dir)
    if not all_runs:
        return None
    return sorted(all_runs, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def find_latest_ablation_dir():
    """查找最新的消融实验目录"""
    ablation_root = Path("results/ablation")
    if not ablation_root.exists():
        return None
    all_dirs = []
    for d in ablation_root.iterdir():
        if d.is_dir() and d.name.startswith("alns_ablation_"):
            all_dirs.append(d)
    if not all_dirs:
        return None
    return sorted(all_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[0]


if __name__ == "__main__":
    print("测试 demo_app 辅助函数...")
    print()
    run_dir = find_latest_run_dir()
    print(f"最新运行目录: {run_dir}")
    ab_dir = find_latest_ablation_dir()
    print(f"最新消融目录: {ab_dir}")
    print()
    if run_dir and ab_dir:
        print("测试通过!")
    else:
        print("测试失败!")
