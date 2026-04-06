import json
import csv
import matplotlib.pyplot as plt
import os
import sys
from typing import Dict, List, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 设置Matplotlib中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

from src.simulation.environment import Environment
from src.core.task import Task


class ResultGenerator:
    """结果生成器类"""
    
    def __init__(self, environment: Environment):
        """初始化结果生成器
        
        Args:
            environment: 环境对象
        """
        self.environment = environment
        self.output_dir = "results"
        
        # 创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_metrics(self):
        """生成性能指标文件 metrics.json
        
        Returns:
            str: 生成的文件路径
        """
        metrics = self.environment.get_metrics()
        
        # 添加能量消耗统计
        energy_consumption = {
            "uav_energy": 0.0,
            "agv_energy": 0.0
        }
        
        for uav in self.environment.uavs:
            # 计算UAV能耗
            initial_battery = 100.0
            current_battery = uav.battery
            energy_consumption["uav_energy"] += initial_battery - current_battery
        
        # 简化计算AGV能耗
        for agv in self.environment.agvs:
            if agv.task:
                energy_consumption["agv_energy"] += 10.0  # 简化模型
        
        metrics.update(energy_consumption)
        
        # 计算任务延误率
        completed_tasks = [task for task in self.environment.tasks if task.status == "completed"]
        delayed_tasks = [task for task in completed_tasks if task.completion_time > task.time_window[1]]
        delay_rate = len(delayed_tasks) / len(completed_tasks) if completed_tasks else 0.0
        metrics["delay_rate"] = delay_rate
        
        # 计算资源利用率
        total_uav_time = len(self.environment.uavs) * self.environment.current_time
        busy_uav_time = sum(
            self.environment.current_time for uav in self.environment.uavs if not uav.is_idle()
        )
        uav_utilization = busy_uav_time / total_uav_time if total_uav_time > 0 else 0.0
        metrics["uav_utilization"] = uav_utilization
        
        total_agv_time = len(self.environment.agvs) * self.environment.current_time
        busy_agv_time = sum(
            self.environment.current_time for agv in self.environment.agvs if not agv.is_idle()
        )
        agv_utilization = busy_agv_time / total_agv_time if total_agv_time > 0 else 0.0
        metrics["agv_utilization"] = agv_utilization
        
        # 写入metrics.json文件
        file_path = os.path.join(self.output_dir, "metrics.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def generate_records(self):
        """生成详细任务执行记录文件 records.csv
        
        Returns:
            str: 生成的文件路径
        """
        file_path = os.path.join(self.output_dir, "records.csv")
        
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow([
                "task_id", "task_type", "start_time", "completion_time", 
                "execution_time", "assigned_to", "start_point", "end_point",
                "payload", "priority", "time_window", "status", "path_distance"
            ])
            
            # 写入任务记录
            for task in self.environment.tasks:
                assigned_to = "UAV" if task.assigned_uav else "AGV" if task.assigned_agv else "None"
                execution_time = task.completion_time - task.start_time if task.completion_time and task.start_time else "N/A"
                
                # 计算路径距离
                path_distance = 0.0
                if task.assigned_uav:
                    uav = task.assigned_uav
                    if uav.path:
                        for i in range(1, len(uav.path)):
                            x1, y1 = uav.path[i-1]
                            x2, y2 = uav.path[i]
                            path_distance += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                elif task.assigned_agv:
                    agv = task.assigned_agv
                    if agv.path:
                        for i in range(1, len(agv.path)):
                            x1, y1 = agv.path[i-1]
                            x2, y2 = agv.path[i]
                            path_distance += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                
                writer.writerow([
                    task.id,
                    task.task_type,
                    task.start_time or "N/A",
                    task.completion_time or "N/A",
                    execution_time,
                    assigned_to,
                    task.start_point,
                    task.end_point,
                    task.payload,
                    task.priority,
                    task.time_window,
                    task.status,
                    path_distance
                ])
        
        return file_path
    
    def generate_chart(self):
        """生成可视化图表文件 chart.png
        
        Returns:
            str: 生成的文件路径
        """
        file_path = os.path.join(self.output_dir, "chart.png")
        
        # 创建一个包含3个子图的图表，聚焦于坐标形式展示
        # 设计思路：使用3个子图分别展示任务状态分布、资源利用率和系统性能指标
        # 这样可以全面反映系统的运行状态，便于分析和决策
        # 调整子图间距，使用更紧凑的布局
        fig, axes = plt.subplots(3, 1, figsize=(10, 12), tight_layout=True)
        
        # 设置窗口主标题，清晰反映窗口的功能和用途
        fig.suptitle("智能配送系统仿真结果 - 坐标形式展示", fontsize=16, y=0.99)
        
        # 设置窗口标题，使其在窗口栏中显示
        fig.canvas.manager.set_window_title("智能配送系统仿真结果可视化")
        
        # 子图1：任务状态分布
        # 功能：展示不同状态任务的数量分布，以及已完成任务的执行时间
        ax1 = axes[0]
        completed_tasks = [task for task in self.environment.tasks if task.status == "completed" and task.completion_time and task.start_time]
        in_progress_tasks = [task for task in self.environment.tasks if task.status == "in_progress"]
        pending_tasks = [task for task in self.environment.tasks if task.status == "pending"]
        
        # 显示任务状态分布
        status_counts = {
            '已完成': len(completed_tasks),
            '进行中': len(in_progress_tasks),
            '待处理': len(pending_tasks)
        }
        
        status_names = list(status_counts.keys())
        status_values = list(status_counts.values())
        status_ids = list(range(1, len(status_names) + 1))
        
        # 绘制任务状态分布柱状图
        bars = ax1.bar(status_ids, status_values, color=['green', 'blue', 'orange'])
        ax1.set_title("任务状态分布表", fontsize=14, fontweight='bold')
        ax1.set_xlabel("任务状态", fontsize=12)
        ax1.set_ylabel("任务数量", fontsize=12)
        ax1.set_xticks(status_ids)
        ax1.set_xticklabels(status_names)
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 优化Y轴范围，确保即使有柱子高度为0也能合理显示
        max_value = max(status_values) if status_values else 10
        ax1.set_ylim(0, max_value * 1.1 if max_value > 0 else 10)
        
        # 在坐标点上方标注数据值，提高可读性
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=10)
        
        # 为柱状图添加图例和注释
        ax1.legend(['任务数量'], loc='upper left')
        ax1.annotate('总任务数: {}'.format(len(self.environment.tasks)), 
                    xy=(0.02, 0.95), xycoords='axes fraction', fontsize=10)
        
        # 如果有完成的任务，显示完成时间
        if completed_tasks:
            # 在右侧添加完成任务的时间信息，使用双Y轴设计
            ax1_right = ax1.twinx()
            
            # 按任务ID排序，确保数据展示的一致性
            completed_tasks.sort(key=lambda x: x.id)
            task_ids = [task.id for task in completed_tasks]
            execution_times = [task.completion_time - task.start_time for task in completed_tasks]
            
            # 绘制完成时间折线图
            line, = ax1_right.plot(task_ids, execution_times, 'o-', color='red', linewidth=2, markersize=8)
            ax1_right.set_ylabel("完成时间（分钟）")
            ax1_right.set_title("任务完成时间", pad=20)
            
            # 为折线图添加图例
            ax1_right.legend([line], ['完成时间'], loc='upper right')
            
            # 在坐标点下方标注数据值，确保数据的清晰展示
            for i, (task_id, time) in enumerate(zip(task_ids, execution_times)):
                ax1_right.text(task_id, time - 0.5, f"{time:.2f}", ha='center', va='top', fontsize=8)
        
        # 子图2：资源利用率坐标图
        # 功能：展示UAV和AGV的资源利用率，反映系统资源的使用情况
        ax2 = axes[1]
        metrics = self.environment.get_metrics()
        
        # 计算实际的资源利用率
        uav_utilization = metrics.get('uav_utilization', 0)
        agv_utilization = metrics.get('agv_utilization', 0)
        
        # 准备数据
        resources = ['UAV利用率', 'AGV利用率']
        utilization_values = [uav_utilization, agv_utilization]
        resource_ids = [1, 2]  # 坐标点ID
        
        # 绘制资源利用率坐标图
        line, = ax2.plot(resource_ids, utilization_values, 'o-', color='green', linewidth=2, markersize=8)
        ax2.set_title("资源利用率表", fontsize=14, fontweight='bold')
        ax2.set_xlabel("资源类型", fontsize=12)
        ax2.set_ylabel("利用率", fontsize=12)
        ax2.set_xticks(resource_ids)
        ax2.set_xticklabels(resources)
        ax2.set_ylim(0, 1)  # 设置合理的Y轴范围
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 为图表添加图例
        ax2.legend([line], ['利用率'], loc='upper left')
        
        # 在坐标点下方标注数据值
        for i, (res_id, value) in enumerate(zip(resource_ids, utilization_values)):
            ax2.text(res_id, value - 0.05, f"{value:.2f}", ha='center', va='top', fontsize=8)
        
        # 子图3：系统性能指标坐标图
        # 功能：展示系统的关键性能指标，包括任务完成率、平均完成时间等
        ax3 = axes[2]
        
        # 准备性能指标数据
        performance_metrics = [
            ('任务完成率', metrics.get('completed_tasks', 0) / metrics.get('total_tasks', 1)),
            ('平均完成时间', metrics.get('average_completion_time', 0)),
            ('UAV利用率', uav_utilization),
            ('AGV利用率', agv_utilization),
            ('准时率', metrics.get('on_time_rate', 0))
        ]
        
        # 提取数据
        metric_names = [item[0] for item in performance_metrics]
        metric_values = [item[1] for item in performance_metrics]
        metric_ids = list(range(1, len(performance_metrics) + 1))  # 坐标点ID
        
        # 绘制系统性能指标坐标图
        line, = ax3.plot(metric_ids, metric_values, 'o-', color='red', linewidth=2, markersize=8)
        ax3.set_title("系统性能指标表", fontsize=14, fontweight='bold')
        ax3.set_xlabel("性能指标", fontsize=12)
        ax3.set_ylabel("值", fontsize=12)
        ax3.set_xticks(metric_ids)
        ax3.set_xticklabels(metric_names, rotation=45, ha='right')  # 旋转标签以避免重叠
        ax3.grid(True, linestyle='--', alpha=0.7)
        
        # 为图表添加图例
        ax3.legend([line], ['性能指标值'], loc='upper left')
        
        # 在坐标点下方标注数据值
        for i, (metric_id, value) in enumerate(zip(metric_ids, metric_values)):
            # 调整标注位置，避免重叠
            offset = 0.05 if value > 0.5 else -0.05
            va = 'top' if value > 0.5 else 'bottom'
            ax3.text(metric_id, value + offset, f"{value:.2f}", ha='center', va=va, fontsize=8)
        
        # 不需要再次调用tight_layout，因为已经在subplots中设置了
        # plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # 保存图表到文件
        plt.savefig(file_path)
        
        # 显示图表窗口
        plt.show()
        
        # 关闭图表，释放资源
        plt.close()
        
        return file_path
    
    def generate_map_visualization(self, num_tasks=10, seed=42, map_size=(1000, 1000)):
        """生成任务点分布地图可视化
        
        Args:
            num_tasks: 任务数量（10/30/50个）
            seed: 随机种子，用于生成确定性任务
            map_size: 地图大小
            
        Returns:
            str: 生成的文件路径
        """
        file_path = os.path.join(self.output_dir, f"map_visualization_{num_tasks}_{seed}.png")
        
        # 创建环境实例
        env = Environment(map_size=map_size)
        
        # 生成任务
        env.generate_tasks(num_tasks, seed=seed)
        
        # 生成随机车辆位置
        import random
        rng = random.Random(seed)
        
        # 随机生成一辆UAV的位置
        uav_position = (rng.randint(0, map_size[0]), rng.randint(0, map_size[1]))
        
        # 提取任务点坐标
        start_points = [task.start_point for task in env.tasks]
        end_points = [task.end_point for task in env.tasks]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 设置标题
        fig.suptitle(f"任务点分布地图 - 任务数量: {num_tasks}, 种子: {seed}", fontsize=16)
        fig.canvas.manager.set_window_title(f"任务点分布地图 - {num_tasks}个任务")
        
        # 绘制地图边界
        ax.set_xlim(0, map_size[0])
        ax.set_ylim(0, map_size[1])
        ax.set_xlabel("X坐标")
        ax.set_ylabel("Y坐标")
        ax.set_title("任务起始点（蓝色）、结束点（红色）和随机车辆位置（绿色）分布")
        
        # 绘制任务点
        start_x = [p[0] for p in start_points]
        start_y = [p[1] for p in start_points]
        end_x = [p[0] for p in end_points]
        end_y = [p[1] for p in end_points]
        
        # 绘制起始点（蓝色）
        ax.scatter(start_x, start_y, color='blue', label='起始点', s=50, alpha=0.7)
        
        # 绘制结束点（红色）
        ax.scatter(end_x, end_y, color='red', label='结束点', s=50, alpha=0.7)
        
        # 绘制随机车辆位置（绿色）
        ax.scatter([uav_position[0]], [uav_position[1]], color='green', label='随机车辆位置', s=100, alpha=0.9, marker='^')
        
        # 绘制任务路径
        for i, (start, end) in enumerate(zip(start_points, end_points)):
            ax.plot([start[0], end[0]], [start[1], end[1]], 'gray', linestyle='--', alpha=0.3)
        
        # 添加图例
        ax.legend()
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.5)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        plt.savefig(file_path)
        
        # 显示图表
        plt.show()
        
        # 关闭图表
        plt.close()
        
        return file_path
    
    def generate_all(self):
        """生成所有结果文件
        
        Returns:
            Dict[str, str]: 生成的文件路径
        """
        metrics_path = self.generate_metrics()
        records_path = self.generate_records()
        chart_path = self.generate_chart()
        
        # 生成不同任务规模的地图可视化
        map_paths = []
        for num_tasks in [10, 30, 50]:
            map_path = self.generate_map_visualization(num_tasks=num_tasks, seed=42)
            map_paths.append(map_path)
        
        print(f"生成结果文件：")
        print(f"- 性能指标: {metrics_path}")
        print(f"- 任务记录: {records_path}")
        print(f"- 可视化图表: {chart_path}")
        for i, map_path in enumerate(map_paths):
            print(f"- 地图可视化 {i+1}: {map_path}")
        
        return {
            "metrics": metrics_path,
            "records": records_path,
            "chart": chart_path,
            "maps": map_paths
        }