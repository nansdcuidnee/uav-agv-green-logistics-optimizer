import yaml
import os
import sys
import glob
import shutil
import numpy as np
import matplotlib.pyplot as plt

# 尝试导入 imageio 用于生成视频
try:
    import imageio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False
    print("警告: 未安装 imageio，将无法自动生成视频。请运行: pip install imageio")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.simulation.environment import Environment
from src.utils.result_generator import ResultGenerator
from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy


# 策略列表
STRATEGIES = ["baseline_direct", "relay_coop", "energy_priority"]


def run_simulation_for_strategy(config, strategy_type):
    """为指定策略运行仿真并生成帧图片

    Args:
        config: 场景配置
        strategy_type: 策略类型

    Returns:
        dict: 仿真结果统计
    """
    map_size = (config['map_size']['width'], config['map_size']['height'])

    # 每次都创建新的环境，确保策略独立运行
    env = Environment(map_size=map_size)

    env.generate_scenario({
        'num_tasks': config['num_tasks'],
        'num_uavs': config['num_uavs'],
        'num_agvs': config['num_agvs'],
        'num_obstacles': config['obstacles']['num'],
        'num_no_fly_zones': config.get('num_no_fly_zones', 0),
        'seed': config.get('seed')  # 使用相同的seed保证任务位置相同
    })

# 创建策略
    strategy_map = {
        "baseline_direct": BaselineDirectStrategy(),
        "relay_coop": RelayCoopStrategy(),
        "energy_priority": EnergyPriorityStrategy()
    }
    strategy = strategy_map.get(strategy_type, BaselineDirectStrategy())

    simulation_time = 300  # 增加仿真时间，让更多任务能完成
    time_step = 0.5

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 8))

    save_interval = 3  # 减少保存间隔，让视频更流畅
    frame_count = 0
    strategy_frames_dir = f'frames_{strategy_type}'
    os.makedirs(strategy_frames_dir, exist_ok=True)

    # 统计变量
    total_distance = 0.0
    total_energy = 0.0
    completed_tasks = 0

    # 记录每一步的移动距离用于后续统计
    step_distances = []

    for step in range(int(simulation_time / time_step)):
        # 执行策略分配
        strategy.assign_tasks(env)

        # 更新环境前记录UAV位置
        uav_positions_before = {uav.id: uav.position for uav in env.uavs}

        # 更新环境
        env.update(time_step)
        current_time = step * time_step

        # 计算UAV在这次更新中移动的距离
        for uav in env.uavs:
            if uav.id in uav_positions_before:
                old_pos = uav_positions_before[uav.id]
                new_pos = uav.position
                move_dist = ((new_pos[0] - old_pos[0])**2 + (new_pos[1] - old_pos[1])**2)**0.5
                if move_dist > 0.1:  # 忽略微小移动
                    total_distance += move_dist
                    # 能耗 = 距离 * 能耗系数(0.5 J/m)
                    total_energy += move_dist * 0.5

# 统计已完成的任务数量
        completed_tasks = len([t for t in env.tasks if t.status == "completed"])

        if step % save_interval == 0:
            ax.clear()

            ax.set_xlim(0, map_size[0])
            ax.set_ylim(0, map_size[1])
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.set_title(f'{strategy_type.replace("_", " ").title()} - Time: {current_time:.1f} min')

            # 绘制障碍物
            for obstacle in env.obstacles:
                circle = plt.Circle(obstacle.position, obstacle.radius, color='gray', alpha=0.5)
                ax.add_patch(circle)

# 绘制任务点
            for task in env.tasks:
                if task.status == "pending":
                    ax.plot(task.start_point[0], task.start_point[1], 'bo', markersize=6)
                    ax.plot(task.end_point[0], task.end_point[1], 'bx', markersize=6)
                elif task.status == "in_progress":
                    ax.plot(task.start_point[0], task.start_point[1], 'go', markersize=6)
                    ax.plot(task.end_point[0], task.end_point[1], 'gx', markersize=6)
                elif task.status == "completed":
                    ax.plot(task.start_point[0], task.start_point[1], 'co', markersize=4, alpha=0.3)
                    ax.plot(task.end_point[0], task.end_point[1], 'cx', markersize=4, alpha=0.3)

            # 绘制AGV
            for agv in env.agvs:
                color = 'blue' if agv.status == "idle" else 'purple'
                ax.plot(agv.position[0], agv.position[1], 's', color=color, markersize=10)
                ax.annotate(f'AGV{agv.id}', (agv.position[0], agv.position[1]), textcoords="offset points", xytext=(5, 5), fontsize=8)

                # 绘制AGV移动轨迹
                if hasattr(agv, 'path') and agv.path and len(agv.path) > 1:
                    path_x = [p[0] for p in agv.path]
                    path_y = [p[1] for p in agv.path]
                    ax.plot(path_x, path_y, 'b-', alpha=0.3, linewidth=1.5)

            # 绘制UAV
            for uav in env.uavs:
                color = 'green' if uav.status == "idle" else 'orange' if uav.status == "busy" else 'red'
                ax.plot(uav.position[0], uav.position[1], 'o', color=color, markersize=8)
                ax.annotate(f'UAV{uav.id}\n{uav.battery:.0f}%', (uav.position[0], uav.position[1]), textcoords="offset points", xytext=(5, 5), fontsize=8)

                # 绘制UAV实际飞行轨迹（从起点到当前位置）
                if uav.path and len(uav.path) > 1:
                    path_x = [p[0] for p in uav.path]
                    path_y = [p[1] for p in uav.path]
                    ax.plot(path_x, path_y, 'r-', alpha=0.5, linewidth=2, label=f'UAV{uav.id}轨迹')

            # 添加图例
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(loc='upper right', fontsize=8)

            # 绘制任务连接线（起点到终点）
            for task in env.tasks:
                if task.status == "in_progress":
                    # 绘制任务路线
                    ax.annotate('', xy=task.end_point, xytext=task.start_point,
                               arrowprops=dict(arrowstyle='->', color='green', lw=1.5, alpha=0.7))

                    # 如果使用中继，绘制中继路线
                    if getattr(task, 'use_relay', False) and task.relay_point:
                        ax.plot(task.relay_point[0], task.relay_point[1], 'r*', markersize=15)
                        ax.annotate('', xy=task.start_point, xytext=task.relay_point,
                                   arrowprops=dict(arrowstyle='->', color='red', lw=1, alpha=0.5, linestyle=':'))

            ax.grid(True, linestyle='--', alpha=0.3)

            # 在图表上显示能耗统计信息
            info_text = f"飞行距离: {total_distance:.1f}m\n能耗: {total_energy:.1f}J\n完成任务: {completed_tasks}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            fig.canvas.draw()
            fig.canvas.flush_events()

            plt.savefig(f'{strategy_frames_dir}/frame_{frame_count:04d}.png', dpi=100)
            frame_count += 1

    plt.ioff()
    plt.close()

    return {
        "strategy": strategy_type,
        "total_distance": total_distance,
        "total_energy": total_energy,
        "completed_tasks": completed_tasks,
        "frames_dir": strategy_frames_dir
    }


def generate_comparison_video(results):
    """生成三种策略的对比视频

    Args:
        results: 各策略的仿真结果
    """
    if not IMAGEIO_AVAILABLE:
        print("无法生成视频：缺少 imageio 库")
        return

    # 获取每个策略的帧数
    min_frames = float('inf')
    for result in results:
        frames = sorted(glob.glob(f"{result['frames_dir']}/frame_*.png"))
        if len(frames) < min_frames:
            min_frames = len(frames)

    if min_frames == 0:
        print("没有找到帧图片")
        return

    # 创建并排展示的视频
    all_images = []
    labels = []

    for result in results:
        frames = sorted(glob.glob(f"{result['frames_dir']}/frame_*.png"))[:min_frames]
        strategy_name = result['strategy']

        # 读取帧并添加策略名称标签
        for frame_file in frames:
            img = imageio.imread(frame_file)
            all_images.append(img)

    # 生成视频
    video_path = 'frames/comparison_video.mp4'
    imageio.mimwrite(video_path, all_images, fps=10, quality=8)

    print(f"对比视频已生成: {video_path}")


def generate_combined_video(results):
    """生成合并的对比视频（3个策略并排显示）

    Args:
        results: 各策略的仿真结果
    """
    if not IMAGEIO_AVAILABLE:
        print("无法生成视频：缺少 imageio 库")
        return

    # 获取每个策略的帧数
    min_frames = float('inf')
    for result in results:
        frames = sorted(glob.glob(f"{result['frames_dir']}/frame_*.png"))
        if len(frames) < min_frames:
            min_frames = len(frames)

    if min_frames == 0:
        print("没有找到帧图片")
        return

    print(f"正在生成合并视频，每个策略 {min_frames} 帧...")

    # 创建合并视频
    combined_images = []

    # 读取所有策略的帧
    strategy_frames = {}
    for result in results:
        frames = sorted(glob.glob(f"{result['frames_dir']}/frame_*.png"))[:min_frames]
        strategy_frames[result['strategy']] = frames

    # 合并每帧
    try:
        from PIL import Image
        for i in range(min_frames):
            images = []
            for strategy in STRATEGIES:
                if strategy in strategy_frames and i < len(strategy_frames[strategy]):
                    img = Image.open(strategy_frames[strategy][i])
                    images.append(img)

            if len(images) == 3:
                # 并排拼接
                widths, heights = zip(*(img.size for img in images))
                total_width = sum(widths)
                max_height = max(heights)

                combined = Image.new('RGB', (total_width, max_height))
                x_offset = 0
                for img in images:
                    combined.paste(img, (x_offset, 0))
                    x_offset += img.width

                combined_images.append(np.array(combined))

        # 生成视频
        video_path = 'frames/comparison_video.mp4'
        imageio.mimwrite(video_path, combined_images, fps=10, quality=8)
        print(f"对比视频已生成: {video_path}")

    except ImportError:
        # 如果没有PIL，直接串联
        all_images = []
        for i in range(min_frames):
            for strategy in STRATEGIES:
                if strategy in strategy_frames and i < len(strategy_frames[strategy]):
                    img = imageio.imread(strategy_frames[strategy][i])
                    all_images.append(img)

        video_path = 'frames/comparison_video.mp4'
        imageio.mimwrite(video_path, all_images, fps=10, quality=8)
        print(f"对比视频已生成: {video_path}")


def load_config(config_path):
    """加载场景配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        dict: 配置信息
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def run_simulation(config):
    """运行仿真

    Args:
        config: 场景配置

    Returns:
        Environment: 环境对象
    """
    # 初始化环境
    map_size = (config['map_size']['width'], config['map_size']['height'])
    env = Environment(map_size=map_size)

    # 生成场景
    env.generate_scenario({
        'num_tasks': config['num_tasks'],
        'num_uavs': config['num_uavs'],
        'num_agvs': config['num_agvs'],
        'num_obstacles': config['obstacles']['num'],
        'num_no_fly_zones': config.get('num_no_fly_zones', 0),
        'seed': config.get('seed')
    })

    # 运行仿真
    simulation_time = 600  # 10小时，延长仿真时间以观察任务完成情况
    time_step = 0.5  # 1分钟

    # 创建图形窗口
    plt.ion()  # 开启交互模式
    fig, ax = plt.subplots(figsize=(10, 8))

    # 每隔多少帧保存一次图像
    save_interval = 5
    frame_count = 0
    os.makedirs('frames', exist_ok=True)

    for step in range(int(simulation_time / time_step)):
        env.update(time_step)
        current_time = step * time_step

        # 每隔save_interval帧绘制一次
        if step % save_interval == 0:
            ax.clear()

            # 绘制地图边界
            ax.set_xlim(0, map_size[0])
            ax.set_ylim(0, map_size[1])
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.set_title(f'Simulation Time: {current_time:.1f} min')

            # 绘制障碍物
            for obstacle in env.obstacles:
                circle = plt.Circle(obstacle.position, obstacle.radius, color='gray', alpha=0.5)
                ax.add_patch(circle)

            # 绘制禁飞区
            for nfz in env.no_fly_zones:
                circle = plt.Circle(nfz.center, nfz.radius, color='red', alpha=0.2)
                ax.add_patch(circle)

            # 绘制任务点
            for task in env.tasks:
                if task.status == "pending":
                    ax.plot(task.start_point[0], task.start_point[1], 'bo', markersize=6, label='Pending Task' if task == env.tasks[0] else "")
                    ax.plot(task.end_point[0], task.end_point[1], 'bx', markersize=6)
                elif task.status == "in_progress":
                    ax.plot(task.start_point[0], task.start_point[1], 'go', markersize=6, label='In Progress' if task == next((t for t in env.tasks if t.status == "in_progress"), None) else "")
                    ax.plot(task.end_point[0], task.end_point[1], 'gx', markersize=6)
                    # 绘制任务路径
                    if task.assigned_uav and task.assigned_uav.path:
                        path_x = [p[0] for p in task.assigned_uav.path]
                        path_y = [p[1] for p in task.assigned_uav.path]
                        ax.plot(path_x, path_y, 'g--', alpha=0.5)
                elif task.status == "completed":
                    ax.plot(task.start_point[0], task.start_point[1], 'co', markersize=4, alpha=0.3)
                    ax.plot(task.end_point[0], task.end_point[1], 'cx', markersize=4, alpha=0.3)

            # 绘制AGV位置
            for agv in env.agvs:
                color = 'blue' if agv.status == "idle" else 'purple'
                ax.plot(agv.position[0], agv.position[1], 's', color=color, markersize=10, label='AGV' if agv == env.agvs[0] else "")
                ax.annotate(f'AGV{agv.id}', (agv.position[0], agv.position[1]), textcoords="offset points", xytext=(5, 5), fontsize=8)

            # 绘制UAV位置
            for uav in env.uavs:
                color = 'green' if uav.status == "idle" else 'orange' if uav.status == "busy" else 'red'
                ax.plot(uav.position[0], uav.position[1], 'o', color=color, markersize=8, label='UAV' if uav == env.uavs[0] else "")
                ax.annotate(f'UAV{uav.id}\n{uav.battery:.0f}%', (uav.position[0], uav.position[1]), textcoords="offset points", xytext=(5, 5), fontsize=8)

                # 绘制UAV路径
                if uav.path and len(uav.path) > 1:
                    path_x = [p[0] for p in uav.path]
                    path_y = [p[1] for p in uav.path]
                    ax.plot(path_x, path_y, 'orange', linestyle='--', alpha=0.7, linewidth=1)

            # 添加图例（避免重复）
            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            if by_label:
                ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=8)

            # 添加网格
            ax.grid(True, linestyle='--', alpha=0.3)

            # 更新图形
            fig.canvas.draw()
            fig.canvas.flush_events()

            # 保存帧
            plt.savefig(f'frames/frame_{frame_count:04d}.png', dpi=100)
            frame_count += 1

    plt.ioff()  # 关闭交互模式
    plt.close()

    return env


def generate_video(frames_dir='frames', video_name='simulation_video.mp4', fps=10):
    """将帧图片合成视频

    Args:
        frames_dir: 帧图片所在目录
        video_name: 输出视频文件名
        fps: 视频帧率

    Returns:
        str: 视频文件路径，如果失败返回None
    """
    if not IMAGEIO_AVAILABLE:
        print("无法生成视频：缺少 imageio 库")
        return None

    # 查找所有帧图片
    frame_pattern = os.path.join(frames_dir, 'frame_*.png')
    frame_files = sorted(glob.glob(frame_pattern))

    if not frame_files:
        print(f"未找到帧图片: {frame_pattern}")
        return None

    print(f"找到 {len(frame_files)} 帧图片，正在生成视频...")

    # 读取所有帧
    images = []
    for frame_file in frame_files:
        images.append(imageio.imread(frame_file))

    # 生成视频
    video_path = os.path.join(frames_dir, video_name)
    imageio.mimwrite(video_path, images, fps=fps, quality=8)

    print(f"视频已生成: {video_path}")
    return video_path


def main():
    """主函数 - 运行三种策略对比仿真"""
    config_file = 'configs/scene_large.yaml'

    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        return

    # 加载配置
    config = load_config(config_file)
    print(f"加载配置: {config_file}")
    print(f"  任务数: {config['num_tasks']}, UAV: {config['num_uavs']}, AGV: {config['num_agvs']}")

    # 清理旧的帧目录
    if os.path.exists('frames'):
        shutil.rmtree('frames')
    os.makedirs('frames', exist_ok=True)

    # 清理各策略的帧目录
    for strategy in STRATEGIES:
        strategy_dir = f'frames_{strategy}'
        if os.path.exists(strategy_dir):
            shutil.rmtree(strategy_dir)

    # 运行三种策略的仿真
    results = []
    for strategy_type in STRATEGIES:
        print(f"\n{'='*50}")
        print(f"运行策略: {strategy_type}")
        print('='*50)

        result = run_simulation_for_strategy(config, strategy_type)
        results.append(result)

        print(f"  总飞行距离: {result['total_distance']:.2f} m")
        print(f"  总能耗: {result['total_energy']:.2f} J")
        print(f"  完成任务: {result['completed_tasks']}")

    # 打印对比结果
    print("\n" + "="*60)
    print("三种策略对比结果")
    print("="*60)
    print(f"{'策略':<20} {'飞行距离(m)':<15} {'能耗(J)':<15} {'完成任务数':<10}")
    print("-"*60)
    for result in results:
        print(f"{result['strategy']:<20} {result['total_distance']:<15.2f} {result['total_energy']:<15.2f} {result['completed_tasks']:<10}")
    print("="*60)

    # 生成对比视频
    print("\n正在生成对比视频...")
    generate_combined_video(results)

    print("\n完成！")


if __name__ == "__main__":
    main()