import json
import os
from datetime import datetime

class Logger:
    """日志记录类
    
    用于记录仿真过程中的实验数据
    """
    
    def __init__(self, log_dir="logs"):
        """初始化日志记录器
        
        Args:
            log_dir: 日志保存目录
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志数据
        self.log_data = {
            "experiment_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "energy": [],
            "tasks": [],
            "charging": [],
            "time": [],
            "summary": {
                "total_energy": 0,
                "completed_tasks": 0,
                "charging_count": 0,
                "total_time": 0
            }
        }
    
    def log_energy(self, step, energy):
        """记录能耗数据
        
        Args:
            step: 时间步
            energy: 能耗值
        """
        self.log_data["energy"].append({
            "step": step,
            "energy": energy
        })
        self.log_data["summary"]["total_energy"] += energy
    
    def log_task(self, step, task_id, status):
        """记录任务数据
        
        Args:
            step: 时间步
            task_id: 任务ID
            status: 任务状态
        """
        self.log_data["tasks"].append({
            "step": step,
            "task_id": task_id,
            "status": status
        })
        if status == "completed":
            self.log_data["summary"]["completed_tasks"] += 1
    
    def log_charging(self, step, uav_id, agv_id, before_battery, after_battery):
        """记录充电数据
        
        Args:
            step: 时间步
            uav_id: 无人机ID
            agv_id: AGV ID
            before_battery: 充电前电量
            after_battery: 充电后电量
        """
        self.log_data["charging"].append({
            "step": step,
            "uav_id": uav_id,
            "agv_id": agv_id,
            "before_battery": before_battery,
            "after_battery": after_battery
        })
        self.log_data["summary"]["charging_count"] += 1
    
    def log_time(self, step, current_time):
        """记录时间数据
        
        Args:
            step: 时间步
            current_time: 当前时间
        """
        self.log_data["time"].append({
            "step": step,
            "current_time": current_time
        })
        self.log_data["summary"]["total_time"] = current_time
    
    def save(self):
        """保存日志数据到文件"""
        # 更新结束时间
        self.log_data["end_time"] = datetime.now().isoformat()
        
        # 保存到JSON文件
        log_file = os.path.join(self.log_dir, f"experiment_{self.log_data['experiment_id']}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        
        print(f"日志已保存到: {log_file}")
        return log_file
    
    def get_summary(self):
        """获取实验摘要
        
        Returns:
            dict: 实验摘要
        """
        return self.log_data["summary"]