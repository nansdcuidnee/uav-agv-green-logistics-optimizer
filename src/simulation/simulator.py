class Simulator:
    """模拟器类
    
    负责整个系统的模拟运行，串联所有模块
    """
    
    def __init__(self, environment, energy_model, path_planner, scheduler, charging_strategy):
        """初始化模拟器
        
        Args:
            environment: 环境对象
            energy_model: 能耗模型对象
            path_planner: 路径规划对象
            scheduler: 调度器对象
            charging_strategy: 充电策略对象
        """
        self.environment = environment
        self.energy_model = energy_model
        self.path_planner = path_planner
        self.scheduler = scheduler
        self.charging_strategy = charging_strategy
        self.time_step = 0
        
        # 统计数据
        self.total_energy = 0
        self.completed_tasks = 0
        self.charging_count = 0
        self.initial_task_count = len(environment.tasks)
    
    def run(self, max_steps):
        """运行模拟
        
        Args:
            max_steps: 最大模拟步数
        """
        print(f"开始模拟，总步数: {max_steps}")
        
        # 运行模拟
        for step in range(max_steps):
            energy = self.step()
            self.total_energy += energy
            
            # 检查是否所有任务都已完成
            if self.completed_tasks == self.initial_task_count:
                print(f"所有任务已完成，提前结束模拟")
                break
        
        # 输出实验结果
        self.print_results()
    
    def step(self):
        """单步模拟
        
        执行一个时间步的模拟，包括：
        1. 获取任务
        2. 调用 path_planner 生成路径
        3. UAV 按路径移动
        4. 调用 energy_model 计算能耗
        5. 判断电量是否低于阈值
        6. 如果需要充电调用 scheduler 选择 AGV
        7. 调用 charging_strategy 执行充电
        8. 更新时间步
        
        Returns:
            float: 本步消耗的总能耗
        """
        total_energy = 0
        
        # 1. 获取任务
        tasks = self.environment.tasks
        
        # 2. 为每个UAV分配任务并规划路径
        self._assign_tasks(tasks)
        
        # 3. 处理每个UAV
        for uav in self.environment.uavs:
            
            # 4. 如果有任务且没有路径，规划路径
            if uav.task and not uav.path:
                # 调用路径规划模块
                uav.path = self.path_planner.plan_path(uav.position, uav.task['end'])
                print(f"为 UAV {uav.id} 规划路径")
            
            # 5. UAV按路径移动
            if uav.path:
                next_point = uav.path[0]
                uav.update_position(next_point)
                uav.path.pop(0)
                
                # 6. 调用能耗模型计算能耗
                cost = self.energy_model.compute(uav)
                uav.update_battery(-cost)
                total_energy += cost
                
                # 打印电量
                print(f"UAV {uav.id} 电量: {uav.battery}")
                
                # 7. 检查任务是否完成
                if not uav.path and uav.task:
                    task_id = uav.task['id']
                    uav.complete_task()
                    self.completed_tasks += 1
                    print(f"UAV {uav.id} 完成任务 {task_id}")
                    uav.task = None
            
            # 8. 判断电量是否低于阈值
            if uav.needs_charging():
                print(f"UAV {uav.id} 触发充电！")
                # 9. 调用调度器选择AGV
                agv = self.scheduler.select_agv(uav, self.environment.agvs)
                # 10. 调用充电策略执行充电
                self.charging_strategy.charge(uav, agv)
                self.charging_count += 1
                print(f"UAV {uav.id} 充电后电量: {uav.battery}")
        
        # 11. 更新时间步
        self.time_step += 1
        return total_energy
    
    def _assign_tasks(self, tasks):
        """分配任务给无人机
        
        Args:
            tasks: 任务列表
        """
        # 找出未分配的任务
        pending_tasks = [task for task in tasks if task['status'] == 'pending']
        
        # 找出空闲的无人机
        idle_uavs = [uav for uav in self.environment.uavs if not uav.task]
        
        # 分配任务
        for task in pending_tasks:
            if idle_uavs:
                # 简单的任务分配策略：按顺序分配
                uav = idle_uavs.pop(0)
                uav.assign_task(task)
                task['status'] = 'in_progress'
                print(f"分配任务 {task['id']} 给 UAV {uav.id}")
    
    def print_results(self):
        """输出实验结果"""
        task_completion_rate = (self.completed_tasks / self.initial_task_count) * 100 if self.initial_task_count > 0 else 0
        
        print("\n=== 实验结果 ===")
        print(f"总能耗: {self.total_energy}")
        print(f"总时间: {self.time_step}")
        print(f"任务完成率: {task_completion_rate:.2f}%")
        print(f"完成任务数: {self.completed_tasks}/{self.initial_task_count}")
        print(f"充电次数: {self.charging_count}")
        print("================")