class Simulator:
    """模拟器类
    
    负责整个系统的模拟运行，串联所有模块
    """
    
    def __init__(self, environment, uavs, agvs, tasks, scheduler, charging_strategy, energy_model, path_planner):
        """初始化模拟器
        
        Args:
            environment: 环境对象
            uavs: 无人机列表
            agvs: AGV列表
            tasks: 任务列表
            scheduler: 调度器对象
            charging_strategy: 充电策略对象
            energy_model: 能耗模型对象
            path_planner: 路径规划对象
        """
        self.environment = environment
        self.uavs = uavs
        self.agvs = agvs
        self.tasks = tasks
        self.scheduler = scheduler
        self.charging_strategy = charging_strategy
        self.energy_model = energy_model
        self.path_planner = path_planner
        self.time_step = 0
    
    def run(self, max_steps=1000):
        """运行模拟
        
        Args:
            max_steps: 最大模拟步数
        """
        # 实现模拟运行逻辑
        for step in range(max_steps):
            self.step()
    
    def step(self):
        """单步模拟
        
        执行一个时间步的模拟，包括：
        1. 更新环境
        2. 分配任务
        3. 执行任务
        4. 充电调度
        5. 更新状态
        
        Returns:
            float: 本步消耗的总能耗
        """
        total_energy = 0
        
        for uav in self.uavs:
            
            # 移动
            if uav.path:
                next_point = uav.path[0]
                uav.update_position(next_point)
                uav.path.pop(0)
                
                # 能耗
                cost = self.energy_model.compute(uav)
                uav.update_battery(-cost)
                total_energy += cost
                
                # 打印电量
                print(f"UAV {uav.id} 电量: {uav.battery}")
            
            # 充电判断
            if uav.needs_charging():
                print(f"UAV {uav.id} 触发充电！")
                agv = self.scheduler.select_agv(uav, self.agvs)
                self.charging_strategy.charge(uav, agv)
                print(f"UAV {uav.id} 充电后电量: {uav.battery}")
        
        self.time_step += 1
        return total_energy