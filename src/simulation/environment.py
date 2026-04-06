import random
import math
import sys
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

from src.core.task import Task
from src.core.uav import UAV
from src.core.agv import AGV


# ==================== 数据类定义 ====================

@dataclass
class Obstacle:
    """障碍物类
    
    属性：
        id: 障碍物唯一标识符
        position: 障碍物位置 (x, y)
        radius: 障碍物半径 (m)
        obstacle_type: 障碍物类型
    """
    id: int
    position: Tuple[float, float]
    radius: float
    obstacle_type: str  # wall, tree, building, etc.


@dataclass
class NoFlyZone:
    """禁飞区类
    
    属性：
        id: 禁飞区唯一标识符
        center: 禁飞区中心 (x, y)
        radius: 禁飞区半径 (m)
    """
    id: int
    center: Tuple[float, float]
    radius: float


@dataclass
class ConstraintViolation:
    """约束违反类
    
    属性：
        type: 约束类型
        severity: 严重程度（1-5）
        message: 违反信息
        affected_task: 受影响的任务
        affected_uav: 受影响的无人机
        affected_agv: 受影响的AGV
    """
    type: str
    severity: int
    message: str
    affected_task: Optional[Task] = None
    affected_uav: Optional[UAV] = None
    affected_agv: Optional[AGV] = None


@dataclass
class CoordinationEvent:
    """协同事件类
    
    属性：
        event_type: 事件类型
        timestamp: 事件时间戳
        source: 事件源
        target: 事件目标
        data: 事件数据
    """
    event_type: str  # task_start, task_complete, battery_low, etc.
    timestamp: float
    source: Optional[object] = None
    target: Optional[object] = None
    data: Optional[Dict] = None


# ==================== 约束管理器类 ====================

class ConstraintManager:
    """约束管理器类"""
    
    def __init__(self, environment):
        """初始化约束管理器
        
        Args:
            environment: 环境对象
        """
        self.environment = environment
        self.violations: List[ConstraintViolation] = []
    
    def check_all_constraints(self):
        """检查所有约束
        
        Returns:
            List[ConstraintViolation]: 约束违反列表
        """
        self.violations = []
        
        # 检查任务约束
        self._check_task_constraints()
        
        # 检查UAV约束
        self._check_uav_constraints()
        
        # 检查AGV约束
        self._check_agv_constraints()
        
        # 检查路径约束
        self._check_path_constraints()
        
        return self.violations
    
    def _check_task_constraints(self):
        """检查任务约束"""
        for task in self.environment.tasks:
            # 检查时间窗口约束
            if task.completion_time:
                if task.completion_time > task.time_window[1]:
                    violation = ConstraintViolation(
                        type="time_window",
                        severity=4,
                        message=f"任务 {task.id} 超出时间窗口",
                        affected_task=task
                    )
                    self.violations.append(violation)
            
            # 检查任务依赖关系（如果有）
            # 这里可以扩展为检查任务间的依赖关系
    
    def _check_uav_constraints(self):
        """检查UAV约束"""
        for uav in self.environment.uavs:
            # 检查电量约束
            if uav.battery < 10:
                violation = ConstraintViolation(
                    type="battery",
                    severity=5,
                    message=f"无人机 {uav.id} 电量过低",
                    affected_uav=uav
                )
                self.violations.append(violation)
            
            # 检查负载约束
            if uav.task:
                if not uav.can_carry(uav.task.payload, uav.task.volume):
                    violation = ConstraintViolation(
                        type="payload",
                        severity=4,
                        message=f"无人机 {uav.id} 无法携带任务 {uav.task.id} 的负载",
                        affected_uav=uav,
                        affected_task=uav.task
                    )
                    self.violations.append(violation)
            
            # 检查续航里程约束
            if uav.task:
                distance = ((uav.position[0] - uav.task.end_point[0]) ** 2 +
                           (uav.position[1] - uav.task.end_point[1]) ** 2) ** 0.5
                if distance > uav.get_remaining_range():
                    violation = ConstraintViolation(
                        type="range",
                        severity=4,
                        message=f"无人机 {uav.id} 续航里程不足",
                        affected_uav=uav,
                        affected_task=uav.task
                    )
                    self.violations.append(violation)
    
    def _check_agv_constraints(self):
        """检查AGV约束"""
        for agv in self.environment.agvs:
            # 检查负载约束
            if agv.task:
                if not agv.can_carry(agv.task.payload, agv.task.volume):
                    violation = ConstraintViolation(
                        type="payload",
                        severity=4,
                        message=f"AGV {agv.id} 无法携带任务 {agv.task.id} 的负载",
                        affected_agv=agv,
                        affected_task=agv.task
                    )
                    self.violations.append(violation)
    
    def _check_path_constraints(self):
        """检查路径约束"""
        # 检查UAV路径
        for uav in self.environment.uavs:
            if uav.path:
                for position in uav.path:
                    if not self.environment.is_valid_flight_position(position):
                        violation = ConstraintViolation(
                            type="path",
                            severity=3,
                            message=f"无人机 {uav.id} 路径经过无效位置",
                            affected_uav=uav
                        )
                        self.violations.append(violation)
                        break
        
        # 检查AGV路径
        for agv in self.environment.agvs:
            if agv.path:
                for position in agv.path:
                    if not self.environment.is_valid_position(position):
                        violation = ConstraintViolation(
                            type="path",
                            severity=3,
                            message=f"AGV {agv.id} 路径经过无效位置",
                            affected_agv=agv
                        )
                        self.violations.append(violation)
                        break
    
    def resolve_violations(self):
        """解决约束违反
        
        Returns:
            Dict: 解决结果
        """
        resolutions = {
            "battery": 0,
            "payload": 0,
            "time_window": 0,
            "range": 0,
            "path": 0
        }
        
        # 按严重程度排序违反
        self.violations.sort(key=lambda v: v.severity, reverse=True)
        
        for violation in self.violations:
            if violation.type == "battery" and violation.affected_uav:
                # 寻找空闲的AGV进行充电
                idle_agvs = self.environment.get_idle_agvs()
                if idle_agvs:
                    # 选择最近的AGV
                    best_agv = None
                    best_distance = float('inf')
                    
                    for agv in idle_agvs:
                        distance = ((agv.position[0] - violation.affected_uav.position[0]) ** 2 +
                                   (agv.position[1] - violation.affected_uav.position[1]) ** 2) ** 0.5
                        if distance < best_distance:
                            best_distance = distance
                            best_agv = agv
                    
                    if best_agv:
                        # 分配AGV进行充电
                        best_agv.status = "charging"
                        best_agv.move_to(violation.affected_uav.position)
                        best_agv.charge(violation.affected_uav)
                        resolutions["battery"] += 1
            
            elif violation.type == "payload" and violation.affected_task:
                # 重新分配任务
                if violation.affected_uav:
                    # 释放当前UAV的任务
                    violation.affected_uav.complete_task()
                elif violation.affected_agv:
                    # 释放当前AGV的任务
                    violation.affected_agv.complete_task()
                
                # 重新分配任务
                self.environment.assign_tasks()
                resolutions["payload"] += 1
            
            elif violation.type == "time_window" and violation.affected_task:
                # 调整任务优先级，重新分配
                violation.affected_task.priority = 5  # 提高优先级
                self.environment.assign_tasks()
                resolutions["time_window"] += 1
            
            elif violation.type == "range" and violation.affected_uav and violation.affected_task:
                # 重新分配任务
                violation.affected_uav.complete_task()
                self.environment.assign_tasks()
                resolutions["range"] += 1
            
            elif violation.type == "path":
                # 重新规划路径
                if violation.affected_uav and violation.affected_uav.task:
                    # 简单的路径重规划，这里可以扩展为更复杂的算法
                    violation.affected_uav.path = []
                elif violation.affected_agv and violation.affected_agv.task:
                    # 简单的路径重规划
                    violation.affected_agv.path = []
                resolutions["path"] += 1
        
        return resolutions
    
    def get_violation_summary(self):
        """获取违反摘要
        
        Returns:
            Dict: 违反摘要
        """
        summary = {}
        for violation in self.violations:
            if violation.type not in summary:
                summary[violation.type] = 0
            summary[violation.type] += 1
        return summary
    
    def check_task_feasibility(self, task: Task) -> bool:
        """检查任务是否可行
        
        Args:
            task: 任务对象
        
        Returns:
            bool: 任务是否可行
        """
        # 检查是否有可用的UAV或AGV
        idle_uavs = self.environment.get_idle_uavs()
        idle_agvs = self.environment.get_idle_agvs()
        
        if not idle_uavs and not idle_agvs:
            return False
        
        # 检查UAV是否能执行任务
        for uav in idle_uavs:
            if uav.can_carry(task.payload, task.volume):
                distance = ((uav.position[0] - task.start_point[0]) ** 2 +
                           (uav.position[1] - task.start_point[1]) ** 2) ** 0.5
                energy_consumption = uav.calculate_energy_consumption(distance, task.payload)
                if uav.battery >= energy_consumption * 1.5:
                    return True
        
        # 检查AGV是否能执行任务
        for agv in idle_agvs:
            if agv.can_carry(task.payload, task.volume):
                return True
        
        return False


# ==================== 协同管理器类 ====================

class CoordinationManager:
    """协同管理器类"""
    
    def __init__(self, environment):
        """初始化协同管理器
        
        Args:
            environment: 环境对象
        """
        self.environment = environment
        self.events: List[CoordinationEvent] = []
        self.pending_transfers: List[Dict] = []  # 待交接的载荷
    
    def process_events(self):
        """处理所有事件
        
        Returns:
            List[CoordinationEvent]: 处理后的事件列表
        """
        processed_events = []
        
        for event in self.events:
            if event.event_type == "task_start":
                self._handle_task_start(event)
            elif event.event_type == "task_complete":
                self._handle_task_complete(event)
            elif event.event_type == "battery_low":
                self._handle_battery_low(event)
            elif event.event_type == "payload_transfer":
                self._handle_payload_transfer(event)
            elif event.event_type == "emergency":
                self._handle_emergency(event)
            
            processed_events.append(event)
        
        # 清空事件列表
        self.events = []
        return processed_events
    
    def _handle_task_start(self, event: CoordinationEvent):
        """处理任务开始事件
        
        Args:
            event: 任务开始事件
        """
        task = event.source
        if isinstance(task, Task):
            print(f"任务 {task.id} 开始执行")
    
    def _handle_task_complete(self, event: CoordinationEvent):
        """处理任务完成事件
        
        Args:
            event: 任务完成事件
        """
        task = event.source
        if isinstance(task, Task):
            print(f"任务 {task.id} 完成")
            # 检查是否有后续任务需要执行
            self._check_follow_up_tasks(task)
    
    def _handle_battery_low(self, event: CoordinationEvent):
        """处理电量低事件
        
        Args:
            event: 电量低事件
        """
        uav = event.source
        if isinstance(uav, UAV):
            print(f"无人机 {uav.id} 电量低，需要充电")
            # 寻找附近的AGV进行充电
            self._find_agv_for_charging(uav)
    
    def _handle_payload_transfer(self, event: CoordinationEvent):
        """处理载荷交接事件
        
        Args:
            event: 载荷交接事件
        """
        transfer_data = event.data
        if transfer_data:
            uav = transfer_data.get("uav")
            agv = transfer_data.get("agv")
            task = transfer_data.get("task")
            
            if uav and agv and task:
                print(f"无人机 {uav.id} 与 AGV {agv.id} 交接任务 {task.id}")
                # 执行载荷交接
                self._perform_payload_transfer(uav, agv, task)
    
    def _handle_emergency(self, event: CoordinationEvent):
        """处理紧急事件
        
        Args:
            event: 紧急事件
        """
        print(f"紧急事件：{event.data.get('message', '未知紧急情况')}")
        # 执行应急处理流程
        self._execute_emergency_procedure(event)
    
    def add_event(self, event: CoordinationEvent):
        """添加事件
        
        Args:
            event: 协同事件
        """
        self.events.append(event)
    
    def _check_follow_up_tasks(self, completed_task: Task):
        """检查是否有后续任务需要执行
        
        Args:
            completed_task: 已完成的任务
        """
        # 这里可以实现任务链的处理逻辑
        pass
    
    def _find_agv_for_charging(self, uav: UAV):
        """寻找AGV为无人机充电
        
        Args:
            uav: 需要充电的无人机
        """
        idle_agvs = self.environment.get_idle_agvs()
        if idle_agvs:
            # 选择最近的AGV
            best_agv = None
            best_distance = float('inf')
            
            for agv in idle_agvs:
                distance = math.sqrt(
                    (agv.position[0] - uav.position[0]) ** 2 +
                    (agv.position[1] - uav.position[1]) ** 2
                )
                if distance < best_distance:
                    best_distance = distance
                    best_agv = agv
            
            if best_agv:
                # 分配AGV进行充电
                best_agv.status = "charging"
                best_agv.move_to(uav.position)
                best_agv.charge(uav)
                
                # 添加充电事件
                event = CoordinationEvent(
                    event_type="battery_charging",
                    timestamp=self.environment.current_time,
                    source=best_agv,
                    target=uav,
                    data={"uav_id": uav.id, "agv_id": best_agv.id}
                )
                self.add_event(event)
    
    def _perform_payload_transfer(self, uav: UAV, agv: AGV, task: Task):
        """执行载荷交接
        
        Args:
            uav: 无人机
            agv: AGV
            task: 任务
        """
        # 无人机降落到AGV
        uav.position = agv.position
        
        # 交接载荷
        if uav.task == task:
            uav.complete_task()
            agv.assign_task(task)
        elif agv.task == task:
            agv.complete_task()
            uav.assign_task(task)
        
        # 添加交接完成事件
        event = CoordinationEvent(
            event_type="payload_transfer_complete",
            timestamp=self.environment.current_time,
            source=uav,
            target=agv,
            data={"task_id": task.id}
        )
        self.add_event(event)
    
    def _execute_emergency_procedure(self, event: CoordinationEvent):
        """执行应急处理流程
        
        Args:
            event: 紧急事件
        """
        emergency_type = event.data.get("type", "unknown")
        
        if emergency_type == "uav_failure":
            # 无人机故障处理
            uav = event.source
            if uav and uav.task:
                # 寻找AGV接管任务
                idle_agvs = self.environment.get_idle_agvs()
                if idle_agvs:
                    best_agv = None
                    best_distance = float('inf')
                    
                    for agv in idle_agvs:
                        distance = math.sqrt(
                            (agv.position[0] - uav.position[0]) ** 2 +
                            (agv.position[1] - uav.position[1]) ** 2
                        )
                        if distance < best_distance:
                            best_distance = distance
                            best_agv = agv
                    
                    if best_agv:
                        best_agv.move_to(uav.position)
                        best_agv.assign_task(uav.task)
                        uav.complete_task()
        
        elif emergency_type == "agv_failure":
            # AGV故障处理
            agv = event.source
            if agv and agv.task:
                # 寻找UAV接管任务
                idle_uavs = self.environment.get_idle_uavs()
                if idle_uavs:
                    best_uav = None
                    best_score = float('inf')
                    
                    for uav in idle_uavs:
                        if uav.can_carry(agv.task.payload, agv.task.volume):
                            distance = math.sqrt(
                                (uav.position[0] - agv.position[0]) ** 2 +
                                (uav.position[1] - agv.position[1]) ** 2
                            )
                            if distance < best_score:
                                best_score = distance
                                best_uav = uav
                    
                    if best_uav:
                        best_uav.assign_task(agv.task)
                        agv.complete_task()
    
    def coordinate_task_execution(self):
        """协同任务执行
        
        Returns:
            Dict: 协同执行结果
        """
        # 检查是否有需要协同的任务
        pending_tasks = [task for task in self.environment.tasks if task.status == "pending"]
        idle_uavs = self.environment.get_idle_uavs()
        idle_agvs = self.environment.get_idle_agvs()
        
        coordination_results = {
            "uav_assignments": [],
            "agv_assignments": [],
            "transfers": []
        }
        
        # 协同任务分配
        for task in pending_tasks:
            # 优先考虑UAV执行任务
            if idle_uavs:
                best_uav = None
                best_score = float('inf')
                
                for uav in idle_uavs:
                    if uav.can_carry(task.payload, task.volume):
                        distance = math.sqrt(
                            (uav.position[0] - task.start_point[0]) ** 2 +
                            (uav.position[1] - task.start_point[1]) ** 2
                        )
                        energy_consumption = uav.calculate_energy_consumption(distance, task.payload)
                        
                        if uav.battery >= energy_consumption * 1.5:
                            score = distance + energy_consumption
                            if score < best_score:
                                best_score = score
                                best_uav = uav
                
                if best_uav:
                    best_uav.assign_task(task)
                    task.assign_to_uav(best_uav)
                    task.start(self.environment.current_time)
                    idle_uavs.remove(best_uav)
                    coordination_results["uav_assignments"].append((best_uav.id, task.id))
                    
                    # 添加任务开始事件
                    event = CoordinationEvent(
                        event_type="task_start",
                        timestamp=self.environment.current_time,
                        source=task,
                        target=best_uav
                    )
                    self.add_event(event)
            
            # 如果没有合适的UAV，考虑AGV
            elif idle_agvs:
                best_agv = None
                best_score = float('inf')
                
                for agv in idle_agvs:
                    if agv.can_carry(task.payload, task.volume):
                        distance = math.sqrt(
                            (agv.position[0] - task.start_point[0]) ** 2 +
                            (agv.position[1] - task.start_point[1]) ** 2
                        )
                        if distance < best_score:
                            best_score = distance
                            best_agv = agv
                
                if best_agv:
                    best_agv.assign_task(task)
                    task.assign_to_agv(best_agv)
                    task.start(self.environment.current_time)
                    idle_agvs.remove(best_agv)
                    coordination_results["agv_assignments"].append((best_agv.id, task.id))
                    
                    # 添加任务开始事件
                    event = CoordinationEvent(
                        event_type="task_start",
                        timestamp=self.environment.current_time,
                        source=task,
                        target=best_agv
                    )
                    self.add_event(event)
            
            # 考虑协同执行（UAV和AGV配合）
            elif idle_uavs and idle_agvs:
                # 这里可以实现更复杂的协同执行逻辑
                pass
        
        # 处理待交接的载荷
        for transfer in self.pending_transfers:
            uav = transfer.get("uav")
            agv = transfer.get("agv")
            task = transfer.get("task")
            
            if uav and agv and task:
                # 执行载荷交接
                self._perform_payload_transfer(uav, agv, task)
                coordination_results["transfers"].append((uav.id, agv.id, task.id))
        
        # 处理事件
        self.process_events()
        
        return coordination_results
    
    def add_payload_transfer(self, uav: UAV, agv: AGV, task: Task):
        """添加载荷交接
        
        Args:
            uav: 无人机
            agv: AGV
            task: 任务
        """
        self.pending_transfers.append({"uav": uav, "agv": agv, "task": task})
        
        # 添加载荷交接事件
        event = CoordinationEvent(
            event_type="payload_transfer",
            timestamp=self.environment.current_time,
            source=uav,
            target=agv,
            data={"uav": uav, "agv": agv, "task": task}
        )
        self.add_event(event)


# ==================== 任务协调器类 ====================

class TaskCoordinator:
    """任务协调器
    
    负责地面车辆与无人机协同工作的标准化流程
    包括任务分配策略、载荷交接机制、路径规划协同和应急处理流程
    """
    
    def __init__(self, environment):
        """初始化任务协调器
        
        Args:
            environment: 环境对象
        """
        self.environment = environment
        self.task_assignments = {}  # 任务分配记录
        self.state_transitions = []  # 状态转换记录
    
    def assign_tasks(self):
        """分配任务
        
        基于负载、距离、优先级等因素分配任务给UAV和AGV
        优化策略：优先考虑UAV，提高UAV利用率
        
        Returns:
            dict: 任务分配结果
        """
        # 获取待分配的任务
        pending_tasks = [task for task in self.environment.tasks if task.status == "pending"]
        
        # 按优先级排序任务
        pending_tasks.sort(key=lambda x: x.priority, reverse=True)
        
        # 获取可用的UAV和AGV
        available_uavs = [uav for uav in self.environment.uavs if uav.is_idle()]
        available_agvs = [agv for agv in self.environment.agvs if agv.is_idle()]
        
        # 分配任务
        assignments = {}
        
        for task in pending_tasks:
            # 尝试分配给UAV（优先考虑UAV）
            assigned = False
            if available_uavs:
                # 选择最合适的UAV
                best_uav = self._select_best_uav(task, available_uavs)
                if best_uav:
                    # 检查约束（适当放宽UAV约束，提高利用率）
                    constraint_result = self.environment.check_task_constraints(task, uav=best_uav)
                    if constraint_result['satisfied']:
                        # 分配任务
                        best_uav.assign_task(task)
                        task.assign_to_uav(best_uav)
                        assignments[task.id] = {'type': 'uav', 'id': best_uav.id}
                        self.task_assignments[task.id] = {'type': 'uav', 'id': best_uav.id, 'time': datetime.now()}
                        available_uavs.remove(best_uav)
                        assigned = True
                    else:
                        # 尝试放宽约束，提高UAV利用率
                        if best_uav.battery > 20 and task.payload < best_uav.max_payload * 1.1:
                            # 允许一定程度的电池和负载超限
                            best_uav.assign_task(task)
                            task.assign_to_uav(best_uav)
                            assignments[task.id] = {'type': 'uav', 'id': best_uav.id}
                            self.task_assignments[task.id] = {'type': 'uav', 'id': best_uav.id, 'time': datetime.now()}
                            available_uavs.remove(best_uav)
                            assigned = True
            
            # 如果没有合适的UAV，尝试分配给AGV
            # 监控AGV饱和状态，当AGV接近饱和时，优先将任务保留给UAV
            agv_utilization = len(self.environment.agvs) - len(available_agvs) / len(self.environment.agvs) if self.environment.agvs else 0
            if not assigned and available_agvs and agv_utilization < 0.8:  # 当AGV利用率低于80%时才分配
                # 选择最合适的AGV
                best_agv = self._select_best_agv(task, available_agvs)
                if best_agv:
                    # 检查约束
                    constraint_result = self.environment.check_task_constraints(task, agv=best_agv)
                    if constraint_result['satisfied']:
                        # 分配任务
                        best_agv.assign_task(task)
                        task.assign_to_agv(best_agv)
                        assignments[task.id] = {'type': 'agv', 'id': best_agv.id}
                        self.task_assignments[task.id] = {'type': 'agv', 'id': best_agv.id, 'time': datetime.now()}
                        available_agvs.remove(best_agv)
                        assigned = True
            
            # 如果无法分配，记录为未分配
            if not assigned:
                assignments[task.id] = {'type': 'unassigned'}
        
        return assignments
    
    def _select_best_uav(self, task, uavs):
        """选择最合适的UAV
        
        Args:
            task: 任务对象
            uavs: UAV列表
        
        Returns:
            UAV: 最合适的UAV
        """
        best_uav = None
        best_score = float('inf')
        
        for uav in uavs:
            # 检查UAV是否能执行任务
            if not uav.can_perform_task(task):
                continue
            
            # 计算评分（距离 + 负载影响 + 电量影响）
            distance = self._calculate_distance(uav.position, task.start_point)
            payload_factor = task.payload / uav.max_payload * 100
            battery_factor = (100 - uav.battery) * 0.5
            
            score = distance + payload_factor + battery_factor
            
            if score < best_score:
                best_score = score
                best_uav = uav
        
        return best_uav
    
    def _select_best_agv(self, task, agvs):
        """选择最合适的AGV
        
        Args:
            task: 任务对象
            agvs: AGV列表
        
        Returns:
            AGV: 最合适的AGV
        """
        best_agv = None
        best_score = float('inf')
        
        for agv in agvs:
            # 检查AGV是否能执行任务
            if not agv.can_perform_task(task):
                continue
            
            # 计算评分（距离 + 负载影响 + 电量影响）
            distance = self._calculate_distance(agv.position, task.start_point)
            payload_factor = task.payload / agv.max_payload * 50
            battery_factor = (100 - agv.battery) * 0.3
            
            score = distance + payload_factor + battery_factor
            
            if score < best_score:
                best_score = score
                best_agv = agv
        
        return best_agv
    
    def coordinate_payload_transfer(self, uav, agv, location):
        """协调载荷交接
        
        Args:
            uav: 无人机对象
            agv: AGV对象
            location: 交接位置 (x, y)
        
        Returns:
            bool: 交接是否成功
        """
        # 检查UAV和AGV是否空闲
        if not uav.is_idle() or not agv.is_idle():
            return False
        
        # 移动到交接位置
        uav.update_position(location)
        agv.move_to(location)
        
        # 执行交接（这里简化处理）
        print(f"Payload transfer between UAV {uav.id} and AGV {agv.id} at {location}")
        
        # 记录状态转换
        self._record_state_transition('payload_transfer', {
            'uav_id': uav.id,
            'agv_id': agv.id,
            'location': location,
            'time': datetime.now()
        })
        
        return True
    
    def coordinate_path_planning(self, tasks):
        """协调路径规划
        
        Args:
            tasks: 任务列表
        
        Returns:
            dict: 路径规划结果
        """
        # 简化实现：为每个任务生成路径
        paths = {}
        
        for task in tasks:
            if task.assigned_uav:
                # UAV路径
                path = [task.assigned_uav.position, task.start_point, task.end_point]
                task.assigned_uav.path = path
                paths[task.id] = path
            elif task.assigned_agv:
                # AGV路径
                path = [task.assigned_agv.position, task.start_point, task.end_point]
                paths[task.id] = path
        
        return paths
    
    def handle_emergency(self, emergency_type, entity, task=None):
        """处理应急情况
        
        Args:
            emergency_type: 应急类型（如 'battery_low', 'equipment_failure', 'task_change'）
            entity: 相关实体（UAV或AGV）
            task: 相关任务（可选）
        
        Returns:
            dict: 应急处理结果
        """
        response = {'type': emergency_type, 'handled': False}
        
        if emergency_type == 'battery_low':
            # 处理电量不足
            if hasattr(entity, 'needs_charging') and entity.needs_charging():
                # 寻找最近的AGV进行充电
                if self.environment.agvs:
                    nearest_agv = self._find_nearest_agv(entity.position)
                    if nearest_agv and nearest_agv.is_idle():
                        # 移动到充电位置
                        charging_location = entity.position
                        nearest_agv.move_to(charging_location)
                        # 充电
                        nearest_agv.charge(entity, duration=300)  # 充电5分钟
                        response['handled'] = True
                        response['action'] = f"AGV {nearest_agv.id} charged {type(entity).__name__} {entity.id}"
        
        elif emergency_type == 'equipment_failure':
            # 处理设备故障
            if entity.task:
                # 重新分配任务
                entity.task.status = 'pending'
                entity.task = None
                # 重新分配
                self.assign_tasks()
                response['handled'] = True
                response['action'] = f"Reassigned task from failed {type(entity).__name__} {entity.id}"
        
        elif emergency_type == 'task_change':
            # 处理任务变更
            if task:
                task.status = 'pending'
                # 重新分配
                self.assign_tasks()
                response['handled'] = True
                response['action'] = f"Reassigned changed task {task.id}"
        
        # 记录状态转换
        self._record_state_transition('emergency', {
            'type': emergency_type,
            'entity_type': type(entity).__name__,
            'entity_id': entity.id,
            'task_id': task.id if task else None,
            'handled': response['handled'],
            'time': datetime.now()
        })
        
        return response
    
    def _find_nearest_agv(self, position):
        """寻找最近的AGV
        
        Args:
            position: 位置 (x, y)
        
        Returns:
            AGV: 最近的AGV
        """
        nearest_agv = None
        min_distance = float('inf')
        
        for agv in self.environment.agvs:
            distance = self._calculate_distance(position, agv.position)
            if distance < min_distance:
                min_distance = distance
                nearest_agv = agv
        
        return nearest_agv
    
    def _calculate_distance(self, point1, point2):
        """计算两点之间的距离
        
        Args:
            point1: 第一个点 (x, y)
            point2: 第二个点 (x, y)
        
        Returns:
            float: 距离
        """
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def _record_state_transition(self, event_type, details):
        """记录状态转换
        
        Args:
            event_type: 事件类型
            details: 事件详情
        """
        self.state_transitions.append({
            'type': event_type,
            'details': details,
            'timestamp': datetime.now()
        })
    
    def get_state_transitions(self):
        """获取状态转换记录
        
        Returns:
            list: 状态转换记录
        """
        return self.state_transitions
    
    def get_task_assignments(self):
        """获取任务分配记录
        
        Returns:
            dict: 任务分配记录
        """
        return self.task_assignments


# ==================== 环境类 ====================

class Environment:
    """Simulation environment that stores entities and tasks."""

    def __init__(self, map_size=(1000, 1000)):
        """初始化环境
        
        Args:
            map_size: 地图大小，默认值为(1000, 1000)
        """
        self.map_size = map_size  # 地图大小
        self.tasks = []  # 配送任务列表
        self.uavs = []  # UAV列表
        self.agvs = []  # AGV列表
        self.delivery_points = []  # 配送点列表
        self.obstacles = []  # 障碍物列表
        self.no_fly_zones = []  # 禁飞区列表
        self.current_time = 0.0  # 当前时间（分钟）
        self.constraint_manager = ConstraintManager(self)  # 约束管理器
        self.coordination_manager = CoordinationManager(self)  # 协同管理器
        self.task_coordinator = TaskCoordinator(self)  # 任务协调器
    
    def generate_tasks(self, num_tasks, seed=None, task_density=None, time_window_range=None):
        """生成指定数量的配送任务
        
        Args:
            num_tasks: 任务数量
            seed: 随机种子，用于生成确定性任务
            task_density: 任务点分布密度（影响任务点的集中程度）
            time_window_range: 时间窗口范围配置
        """
        rng = random.Random(seed) if seed is not None else random

        self.tasks = []
        task_types = ["pickup", "delivery", "inspection"]
        
        # 计算地图面积
        map_area = self.map_size[0] * self.map_size[1]
        
        # 根据任务密度调整任务点分布
        if task_density:
            # 计算每个任务点的平均覆盖面积
            avg_area_per_task = map_area / (num_tasks * task_density)
            cluster_radius = int((avg_area_per_task ** 0.5) / 2)
        else:
            cluster_radius = 0
        
        # 生成聚类中心
        clusters = []
        if cluster_radius > 0:
            # 生成聚类中心
            num_clusters = min(num_tasks, 5)  # 最多5个聚类中心
            for _ in range(num_clusters):
                cluster_x = rng.randint(0, self.map_size[0])
                cluster_y = rng.randint(0, self.map_size[1])
                clusters.append((cluster_x, cluster_y))
        
        for i in range(num_tasks):
            # 根据聚类中心生成任务点
            if clusters:
                cluster = rng.choice(clusters)
                start_x = max(0, min(self.map_size[0], cluster[0] + rng.randint(-cluster_radius, cluster_radius)))
                start_y = max(0, min(self.map_size[1], cluster[1] + rng.randint(-cluster_radius, cluster_radius)))
                end_x = max(0, min(self.map_size[0], cluster[0] + rng.randint(-cluster_radius, cluster_radius)))
                end_y = max(0, min(self.map_size[1], cluster[1] + rng.randint(-cluster_radius, cluster_radius)))
            else:
                start_x = rng.randint(0, self.map_size[0])
                start_y = rng.randint(0, self.map_size[1])
                end_x = rng.randint(0, self.map_size[0])
                end_y = rng.randint(0, self.map_size[1])
            
            payload = rng.uniform(0.5, 5.0)
            volume = rng.uniform(0.1, 2.0)
            task_type = rng.choice(task_types)
            priority = rng.randint(1, 5)
            
            # 使用配置的时间窗口范围
            if time_window_range:
                min_window = time_window_range.get("min", 30)
                max_window = time_window_range.get("max", 120)
                earliest_start = rng.uniform(0.0, 720.0)
                latest_finish = earliest_start + rng.uniform(min_window, max_window)
            else:
                earliest_start = rng.uniform(0.0, 720.0)
                latest_finish = earliest_start + rng.uniform(30.0, 180.0)

            task = Task(
                id=i + 1,
                start_point=(start_x, start_y),
                end_point=(end_x, end_y),
                payload=payload,
                volume=volume,
                task_type=task_type,
                priority=priority,
                time_window=(earliest_start, latest_finish)
            )
            self.tasks.append(task)

        self.delivery_points = [task.end_point for task in self.tasks]
        return self.tasks
    
    def add_uav(self, uav):
        """添加无人机
        
        Args:
            uav: 无人机对象
        """
        self.uavs.append(uav)
    
    def add_agv(self, agv):
        """添加AGV
        
        Args:
            agv: AGV对象
        """
        self.agvs.append(agv)
    
    def add_obstacle(self, obstacle):
        """添加障碍物
        
        Args:
            obstacle: 障碍物对象
        """
        self.obstacles.append(obstacle)
    
    def add_no_fly_zone(self, no_fly_zone):
        """添加禁飞区
        
        Args:
            no_fly_zone: 禁飞区对象
        """
        self.no_fly_zones.append(no_fly_zone)
    
    def reset(self):
        """重置环境"""
        self.tasks = []
        self.uavs = []
        self.agvs = []
        self.delivery_points = []
        self.obstacles = []
        self.no_fly_zones = []
        self.current_time = 0.0

    def add_delivery_point(self, point):
        """添加配送点
        
        Args:
            point: 配送点位置 (x, y)
        """
        self.delivery_points.append(point)

    def is_valid_position(self, position):
        """判断位置是否有效
        
        Args:
            position: 位置 (x, y)
        
        Returns:
            bool: 位置是否有效
        """
        x, y = position
        if not (0 <= x <= self.map_size[0] and 0 <= y <= self.map_size[1]):
            return False
        
        # 检查是否与障碍物碰撞
        for obstacle in self.obstacles:
            distance = math.sqrt(
                (position[0] - obstacle.position[0]) ** 2 +
                (position[1] - obstacle.position[1]) ** 2
            )
            if distance < obstacle.radius:
                return False
        
        return True
    
    def is_valid_flight_position(self, position):
        """判断飞行位置是否有效
        
        Args:
            position: 位置 (x, y)
        
        Returns:
            bool: 位置是否有效
        """
        if not self.is_valid_position(position):
            return False
        
        # 检查是否在禁飞区内
        for no_fly_zone in self.no_fly_zones:
            distance = math.sqrt(
                (position[0] - no_fly_zone.center[0]) ** 2 +
                (position[1] - no_fly_zone.center[1]) ** 2
            )
            if distance < no_fly_zone.radius:
                return False
        
        return True
    
    def get_idle_uavs(self):
        """获取空闲的无人机
        
        Returns:
            List[UAV]: 空闲无人机列表
        """
        return [uav for uav in self.uavs if uav.is_idle()]
    
    def get_idle_agvs(self):
        """获取空闲的AGV
        
        Returns:
            List[AGV]: 空闲AGV列表
        """
        return [agv for agv in self.agvs if agv.is_idle()]
    
    def assign_tasks(self):
        """分配任务给空闲的UAV和AGV
        
        Returns:
            Dict: 分配结果
        """
        idle_uavs = self.get_idle_uavs()
        idle_agvs = self.get_idle_agvs()
        pending_tasks = [task for task in self.tasks if task.status == "pending"]
        
        # 按优先级排序任务
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        assignments = {
            "uav_assignments": [],
            "agv_assignments": []
        }
        
        # 分配任务给UAV
        for task in pending_tasks:
            if not idle_uavs:
                break
            
            # 选择最合适的UAV
            best_uav = None
            best_score = float('inf')
            
            for uav in idle_uavs:
                # 计算距离
                distance = math.sqrt(
                    (uav.position[0] - task.start_point[0]) ** 2 +
                    (uav.position[1] - task.start_point[1]) ** 2
                )
                
                # 检查是否能携带负载
                if not uav.can_carry(task.payload, task.volume):
                    continue
                
                # 计算能耗
                energy_consumption = uav.calculate_energy_consumption(
                    distance, task.payload
                )
                
                # 检查电量是否足够
                if uav.battery < energy_consumption * 1.5:  # 留有余量
                    continue
                
                # 计算评分（距离 + 能耗）
                score = distance + energy_consumption
                
                if score < best_score:
                    best_score = score
                    best_uav = uav
            
            if best_uav:
                best_uav.assign_task(task)
                task.assign_to_uav(best_uav)
                task.start(self.current_time)
                idle_uavs.remove(best_uav)
                assignments["uav_assignments"].append((best_uav.id, task.id))
        
        # 分配任务给AGV
        for task in pending_tasks:
            if task.status != "pending":
                continue
            if not idle_agvs:
                break
            
            # 选择最合适的AGV
            best_agv = None
            best_score = float('inf')
            
            for agv in idle_agvs:
                # 计算距离
                distance = math.sqrt(
                    (agv.position[0] - task.start_point[0]) ** 2 +
                    (agv.position[1] - task.start_point[1]) ** 2
                )
                
                # 检查是否能携带负载
                if not agv.can_carry(task.payload, task.volume):
                    continue
                
                # 计算评分（距离）
                score = distance
                
                if score < best_score:
                    best_score = score
                    best_agv = agv
            
            if best_agv:
                best_agv.assign_task(task)
                task.assign_to_agv(best_agv)
                task.start(self.current_time)
                idle_agvs.remove(best_agv)
                assignments["agv_assignments"].append((best_agv.id, task.id))
        
        return assignments
    
    def check_task_constraints(self, task, uav=None, agv=None):
        """检查任务约束
        
        Args:
            task: 任务对象
            uav: UAV对象（可选）
            agv: AGV对象（可选）
        
        Returns:
            Dict: 约束检查结果
        """
        result = {'satisfied': True, 'violations': []}
        
        # 检查UAV约束
        if uav:
            # 检查负载约束
            if not uav.can_carry(task.payload, task.volume):
                result['satisfied'] = False
                result['violations'].append('payload_exceeded')
            
            # 检查电量约束
            distance = math.sqrt(
                (uav.position[0] - task.start_point[0]) ** 2 +
                (uav.position[1] - task.start_point[1]) ** 2
            )
            energy_consumption = uav.calculate_energy_consumption(distance, task.payload)
            if uav.battery < energy_consumption * 1.5:
                result['satisfied'] = False
                result['violations'].append('insufficient_battery')
        
        # 检查AGV约束
        if agv:
            # 检查负载约束
            if not agv.can_carry(task.payload, task.volume):
                result['satisfied'] = False
                result['violations'].append('payload_exceeded')
        
        return result
    
    def update(self, time_step=1.0):
        """更新环境状态
        
        Args:
            time_step: 时间步长（分钟）
        """
        self.current_time += time_step
        
        # 更新UAV状态
        for uav in self.uavs:
            if uav.task and uav.task.status == "in_progress":
                # 计算任务完成情况
                task = uav.task
                distance = math.sqrt(
                    (uav.position[0] - task.end_point[0]) ** 2 +
                    (uav.position[1] - task.end_point[1]) ** 2
                )
                
                if distance < 10:  # 到达目标位置
                    task.complete(self.current_time)
                    uav.complete_task()
                else:
                    # 向目标位置移动
                    direction_x = (task.end_point[0] - uav.position[0]) / distance
                    direction_y = (task.end_point[1] - uav.position[1]) / distance
                    step_distance = uav.max_speed * time_step * 60  # 转换为米
                    new_x = uav.position[0] + direction_x * step_distance
                    new_y = uav.position[1] + direction_y * step_distance
                    
                    # 检查新位置是否有效
                    if self.is_valid_flight_position((new_x, new_y)):
                        uav.update_position((new_x, new_y))
                    
                    # 消耗电量
                    energy_consumption = uav.calculate_energy_consumption(
                        step_distance, task.payload
                    )
                    uav.update_battery(-energy_consumption / (time_step * 60))
        
        # 更新AGV状态
        for agv in self.agvs:
            if agv.task and agv.task.status == "in_progress":
                # 计算任务完成情况
                task = agv.task
                distance = math.sqrt(
                    (agv.position[0] - task.end_point[0]) ** 2 +
                    (agv.position[1] - task.end_point[1]) ** 2
                )
                
                if distance < 5:  # 到达目标位置
                    task.complete(self.current_time)
                    agv.complete_task()
                else:
                    # 向目标位置移动
                    direction_x = (task.end_point[0] - agv.position[0]) / distance
                    direction_y = (task.end_point[1] - agv.position[1]) / distance
                    step_distance = agv.max_speed * time_step * 60  # 转换为米
                    new_x = agv.position[0] + direction_x * step_distance
                    new_y = agv.position[1] + direction_y * step_distance
                    
                    # 检查新位置是否有效
                    if self.is_valid_position((new_x, new_y)):
                        agv.move_to((new_x, new_y))
        
        # 检查约束
        violations = self.constraint_manager.check_all_constraints()
        if violations:
            # 解决约束违反
            self.constraint_manager.resolve_violations()
        
        # 协同任务执行
        self.coordination_manager.coordinate_task_execution()
    
    def get_metrics(self):
        """获取性能指标
        
        Returns:
            Dict: 性能指标
        """
        completed_tasks = [task for task in self.tasks if task.status == "completed"]
        total_tasks = len(self.tasks)
        
        if completed_tasks:
            avg_completion_time = sum(
                task.completion_time - task.start_time
                for task in completed_tasks
            ) / len(completed_tasks)
        else:
            avg_completion_time = 0.0
        
        on_time_tasks = [
            task for task in completed_tasks
            if task.completion_time <= task.time_window[1]
        ]
        on_time_rate = len(on_time_tasks) / total_tasks if total_tasks > 0 else 0.0
        
        # 计算资源利用率
        uav_utilization = sum(
            0 if uav.is_idle() else 1 for uav in self.uavs
        ) / len(self.uavs) if self.uavs else 0.0
        
        agv_utilization = sum(
            0 if agv.is_idle() else 1 for agv in self.agvs
        ) / len(self.agvs) if self.agvs else 0.0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks),
            "average_completion_time": avg_completion_time,
            "on_time_rate": on_time_rate,
            "uav_utilization": uav_utilization,
            "agv_utilization": agv_utilization,
            "current_time": self.current_time
        }
    
    def generate_scenario(self, config):
        """根据配置生成场景
        
        Args:
            config: 场景配置
        """
        # 设置随机种子，确保可复现性
        seed = config.get("seed")
        if seed is not None:
            random.seed(seed)
        
        # 生成任务
        self.generate_tasks(
            config["num_tasks"], 
            seed=seed,
            task_density=config.get("task_density"),
            time_window_range=config.get("time_window")
        )
        
        # 生成UAV
        for i in range(config["num_uavs"]):
            position = (random.randint(0, self.map_size[0]), random.randint(0, self.map_size[1]))
            uav = UAV(
                id=i + 1,
                position=position
            )
            self.add_uav(uav)
        
        # 生成AGV
        for i in range(config["num_agvs"]):
            position = (random.randint(0, self.map_size[0]), random.randint(0, self.map_size[1]))
            agv = AGV(
                id=i + 1,
                position=position
            )
            self.add_agv(agv)
        
        # 生成障碍物
        for i in range(config.get("obstacles", {}).get("num", 0)):
            position = (random.randint(0, self.map_size[0]), random.randint(0, self.map_size[1]))
            radius = random.uniform(5, 20)
            obstacle_types = config.get("obstacles", {}).get("types", ["building"])
            obstacle_type = random.choice(obstacle_types)
            obstacle = Obstacle(
                id=i + 1,
                position=position,
                radius=radius,
                obstacle_type=obstacle_type
            )
            self.add_obstacle(obstacle)
        
        # 生成禁飞区
        for i in range(config.get("num_no_fly_zones", 0)):
            center = (random.randint(0, self.map_size[0]), random.randint(0, self.map_size[1]))
            radius = random.uniform(50, 200)
            no_fly_zone = NoFlyZone(
                id=i + 1,
                center=center,
                radius=radius
            )
            self.add_no_fly_zone(no_fly_zone)
