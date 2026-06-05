import csv
import json
import matplotlib
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.strategies.alns_unified import ALNSUnifiedStrategy
from src.utils.result_layout import REQUIRED_ARTIFACTS, create_result_layout, write_metadata
from src.communication.network_manager import NetworkManager
from src.communication.message_dispatch import MessageDispatcher
from src.communication.communication_logger import CommunicationLogger


class Simulator:
    """Main simulation runner for UAV-AGV charging experiments."""

    def __init__(self, environment, energy_model, path_planner, scheduler, strategy_type="baseline_direct", scenario_name="default", seed=42, strategy_kwargs=None):
        self.environment = environment
        self.energy_model = energy_model
        self.path_planner = path_planner
        self.scheduler = scheduler
        self.time_step = 0
        self.scenario_name = scenario_name
        self.seed = seed
        self.strategy_kwargs = strategy_kwargs or {}

        strategy_factory = {
            "baseline_direct": lambda: BaselineDirectStrategy(),
            "relay_coop": lambda: RelayCoopStrategy(),
            "energy_priority": lambda: EnergyPriorityStrategy(energy_model=self.energy_model),
            "alns_unified": lambda: ALNSUnifiedStrategy(
                energy_model=self.energy_model,
                path_planner=self.path_planner,
                seed=seed,
                **self.strategy_kwargs
            ),
        }
        self.strategy = strategy_factory.get(strategy_type, strategy_factory["baseline_direct"])()

        self.total_energy = 0.0
        self.completed_tasks = 0
        self.charging_count = 0
        self.initial_task_count = len(environment.tasks)
        self.total_distance = 0.0
        self.total_distance_agv = 0.0
        self.total_uav_energy = 0.0
        self.total_agv_energy = 0.0
        self.total_charge_loss_energy = 0.0
        
        # 充电配置参数
        self.charge_rate_per_step = 5.0  # 每步充电百分比
        self.charge_start_threshold = 20  # 低于该值开始充电
        self.charge_target_soc = 80  # 充到该值结束
        
        # 充电状态管理
        self.charging_uavs = {}  # 记录正在充电的UAV及其充电信息

        self.energy_history = []
        self.task_history = []
        self.battery_history = []
        self.events = []  # 记录真实事件
        self.task_completion_times = []  # 记录任务完成时间
        self.charging_history = []  # 记录每个步骤的充电次数
        self.distance_history = []  # 记录每个步骤的距离
        
        # 初始化通信模块
        self.network_manager = NetworkManager()
        self.message_dispatcher = MessageDispatcher(self.network_manager)
        self.uav_distance_history = []
        self.agv_distance_history = []
        self.uav_energy_history = []
        self.agv_energy_history = []
        self.charge_loss_energy_history = []
        
        # 初始化状态跟踪
        self.uav_states = {}
        self.agv_states = {}
        self.task_states = {}
        self.charging_states = {}
        
        # 初始化所有任务的状态
        for task in self.environment.tasks:
            self._ensure_task_stats(task)
            self.task_states[task.id] = "PENDING"
        
        # 初始化所有 UAV 的状态
        for uav in self.environment.uavs:
            self.uav_states[uav.id] = "IDLE"
            self.charging_states[uav.id] = False
        
        # 初始化所有 AGV 的状态
        for agv in self.environment.agvs:
            self.agv_states[agv.id] = "IDLE"
        
        # 追踪 ALNS 策略的累计统计（在 assign_tasks 被调用后更新）
        self._cumulative_direct_count = 0
        self._cumulative_relay_count = 0
        self._cumulative_fallback_count = 0
        self._cumulative_replan_count = 0
        
        self.communication_logger = None  # 稍后在 save_results 中初始化
    
    def _ensure_task_stats(self, task):
        """确保任务对象具有必要的统计属性"""
        if not hasattr(task, 'uav_distance'):
            task.uav_distance = 0.0
        if not hasattr(task, 'agv_move_distance'):
            task.agv_move_distance = 0.0
        if not hasattr(task, 'agv_distance'):
            task.agv_distance = 0.0
        if not hasattr(task, 'uav_energy'):
            task.uav_energy = 0.0
        if not hasattr(task, 'agv_energy'):
            task.agv_energy = 0.0
        if not hasattr(task, 'charge_loss_energy'):
            task.charge_loss_energy = 0.0
        if not hasattr(task, 'total_energy'):
            task.total_energy = 0.0
        if not hasattr(task, 'assigned_time'):
            task.assigned_time = None
        if not hasattr(task, 'start_time'):
            task.start_time = None
        if not hasattr(task, 'completion_time'):
            task.completion_time = None
        if not hasattr(task, 'wait_time_at_relay'):
            task.wait_time_at_relay = 0.0

    def _get_task_by_id(self, task_id):
        if task_id is None:
            return None
        return next((task for task in self.environment.tasks if task.id == task_id), None)

    def _resolve_task_deadline(self, task):
        deadline = getattr(task, "deadline", None)
        if deadline is not None:
            return deadline
        time_window = getattr(task, "time_window", None)
        if isinstance(time_window, (tuple, list)) and len(time_window) >= 2:
            return time_window[1]
        return None

    def _add_task_stat(self, task, key, delta):
        if task is None:
            return
        self._ensure_task_stats(task)
        current_value = float(getattr(task, key, 0.0))
        setattr(task, key, current_value + float(delta))
        task.total_energy = float(task.uav_energy) + float(task.agv_energy) + float(task.charge_loss_energy)

    def run(self, max_steps, experiment_name="default", result_type="runs", campaign_name=None):
        print(f"Starting simulation, max_steps={max_steps}, strategy={self.strategy.name}")
        
        # 连接所有设备到网络
        for uav in self.environment.uavs:
            self.network_manager.connect(f"UAV_{uav.id}", "UAV")
        for agv in self.environment.agvs:
            self.network_manager.connect(f"AGV_{agv.id}", "AGV")
        self.network_manager.connect("CONTROL_CENTER", "CONTROL")

        for _ in range(max_steps):
            self.total_energy += self.step()
            # Do not stop until all active charging sessions are closed.
            # Otherwise CHARGING_END may be missing from records.
            # Also check that no AGV is still moving to relay point.
            has_moving_agv = any(hasattr(agv, 'status') and agv.status == "moving_to_relay" for agv in self.environment.agvs)
            if self.completed_tasks >= self.initial_task_count and not self.charging_uavs and not has_moving_agv:
                print("All tasks completed and no active charging or AGV movement, stopping early.")
                break

        self.print_results()
        return self.save_results(experiment_name, result_type, campaign_name)

    def step(self):
        step_energy = 0.0
        step_uav_distance = 0.0
        step_agv_distance = 0.0
        step_uav_energy = 0.0
        step_agv_energy = 0.0
        step_charge_loss_energy = 0.0

        # 处理运行时事件
        if hasattr(self, 'runtime_events') and self.runtime_events:
            events_to_remove = []
            for event in self.runtime_events:
                if event.get('step') == self.time_step:
                    if event.get('type') == 'uav_removal':
                        uav_id = event.get('uav_id')
                        # 找到目标UAV
                        uav = next((u for u in self.environment.uavs if u.id == uav_id), None)
                        if uav:
                            # 标记UAV为不可用
                            uav.available = False
                            print(f"[EVENT] UAV {uav_id} removed at step {self.time_step}")
                            
                            # 检查UAV是否正在执行任务
                            if hasattr(uav, 'task') and uav.task:
                                task = uav.task
                                # 将任务状态回退为pending
                                task.status = "pending"
                                task.assigned_uav = None
                                uav.task = None
                                print(f"[EVENT] Task {task.id} returned to pending state")
                            
                            # 记录事件
                            self.events.append({
                                "step": self.time_step,
                                "type": "UAV_REMOVED",
                                "uav_id": uav_id,
                                "details": f"UAV {uav_id} removed due to failure"
                            })
                    events_to_remove.append(event)
            # 移除已处理的事件
            for event in events_to_remove:
                self.runtime_events.remove(event)

        # 分配任务并记录开始时间
        assignment_result = self.strategy.assign_tasks(self.environment)
        
        # 更新累计的 ALNS 统计（在 assign_tasks 内部被重置后累加）
        self._cumulative_direct_count += getattr(self.strategy, 'direct_count', 0)
        self._cumulative_relay_count += getattr(self.strategy, 'relay_count', 0)
        self._cumulative_fallback_count += getattr(self.strategy, 'fallback_count', 0)
        self._cumulative_replan_count += getattr(self.strategy, 'replan_count', 0)
        
        # 处理策略返回的行动意图
        if 'actions' in assignment_result:
            for action in assignment_result['actions']:
                if action['action'] == 'move_agv_to_relay':
                    agv_id = action['agv_id']
                    relay_point = action['relay_point']
                    task_id = action['task_id']
                    
                    # 找到对应的AGV
                    agv = next((a for a in self.environment.agvs if a.id == agv_id), None)
                    if agv:
                        # 检查状态变化
                        if self.agv_states[agv.id] != "moving_to_relay":
                            # 记录 AGV 开始移动事件
                            self.events.append({
                                "step": self.time_step,
                                "type": "AGV_MOVE_START",
                                "agv_id": agv.id,
                                "task_id": task_id,
                                "x": agv.position[0],
                                "y": agv.position[1],
                                "details": "AGV starts moving to relay point"
                            })
                            # 更新状态
                            self.agv_states[agv.id] = "moving_to_relay"
                        
                        # 设置AGV的移动状态和目标
                        agv.status = "moving_to_relay"
                        agv.destination = relay_point
                        agv.move_distance = ((agv.position[0] - relay_point[0]) ** 2 + (agv.position[1] - relay_point[1]) ** 2) ** 0.5
                        agv.move_progress = 0
                        agv.task_id = task_id
        
        # 记录任务分配事件
        for assignment in assignment_result.get("assignments", []):
            task_id = assignment.get("task_id")
            uav_id = assignment.get("uav_id")
            agv_id = assignment.get("agv_id")
            
            # 检查任务状态变化
            if self.task_states.get(task_id) == "PENDING":
                # 记录任务分配事件
                self.events.append({
                    "step": self.time_step,
                    "type": "TASK_ASSIGNED",
                    "uav_id": uav_id,
                    "task_id": task_id,
                    "agv_id": agv_id,
                    "relay_point": assignment.get("relay_point"),
                    "details": "Task assigned to UAV"
                })
                # 更新任务状态
                self.task_states[task_id] = "ASSIGNED"
                
                # 设置任务分配时间
                task = self._get_task_by_id(task_id)
                if task:
                    self._ensure_task_stats(task)
                    task.assigned_time = self.time_step
            
            # 发送任务分配消息
            self.network_manager.send_message(
                "CONTROL_CENTER",
                f"UAV_{uav_id}",
                "TASK_ASSIGNMENT",
                f"Task {task_id} assigned to UAV {uav_id}"
            )
            if agv_id:
                # 记录继电器请求事件
                self.events.append({
                    "step": self.time_step,
                    "type": "RELAY_REQUEST",
                    "agv_id": agv_id,
                    "task_id": task_id,
                    "details": "Relay support requested for task"
                })
                self.network_manager.send_message(
                    "CONTROL_CENTER",
                    f"AGV_{agv_id}",
                    "RELAY_REQUEST",
                    f"AGV {agv_id} requested for relay support for task {task_id}"
                )
        
        # 处理策略返回的事件（ALNS 等策略可返回自定义事件）
        if 'events' in assignment_result:
            for event in assignment_result['events']:
                self.events.append({
                    "step": self.time_step,
                    "type": event.get('type'),
                    "task_id": event.get('task_id'),
                    "details": event.get('details', '')
                })
        
        # 处理任务状态变化
        for task in self.environment.tasks:
            current_task_state = self.task_states.get(task.id, "PENDING")
            
            # 检查任务状态变化
            if task.status == "waiting_for_agv" and current_task_state != "WAITING_FOR_AGV":
                # 记录等待 AGV 开始事件
                uav_id = task.assigned_uav.id if (hasattr(task, 'assigned_uav') and task.assigned_uav) else None
                self.events.append({
                    "step": self.time_step,
                    "type": "WAIT_FOR_AGV_START",
                    "task_id": task.id,
                    "uav_id": uav_id,
                    "details": "Task starts waiting for AGV"
                })
                # 更新任务状态
                self.task_states[task.id] = "WAITING_FOR_AGV"
            elif task.status == "in_progress" and current_task_state == "WAITING_FOR_AGV":
                # 记录等待 AGV 结束事件
                uav_id = task.assigned_uav.id if (hasattr(task, 'assigned_uav') and task.assigned_uav) else None
                self.events.append({
                    "step": self.time_step,
                    "type": "WAIT_FOR_AGV_END",
                    "task_id": task.id,
                    "uav_id": uav_id,
                    "details": "Task stops waiting for AGV"
                })
                # 更新任务状态
                self.task_states[task.id] = "IN_PROGRESS"
                # 设置任务开始时间（仅首次）
                if task.start_time is None:
                    task.start_time = self.time_step
            elif task.status == "in_progress" and current_task_state != "IN_PROGRESS" and current_task_state != "WAITING_FOR_AGV":
                # 记录任务开始事件
                self.events.append({
                    "step": self.time_step,
                    "type": "TASK_START",
                    "task_id": task.id,
                    "uav_id": task.assigned_uav.id if hasattr(task, 'assigned_uav') else None,
                    "details": "Task starts execution"
                })
                # 更新任务状态
                self.task_states[task.id] = "IN_PROGRESS"
                # 设置任务开始时间（仅首次）
                if task.start_time is None:
                    task.start_time = self.time_step
            elif task.status == "completed" and current_task_state != "COMPLETED":
                # 更新任务状态（不再在这里记录事件，避免重复）
                self.task_states[task.id] = "COMPLETED"
            
            # 累计等待时间
            if task.status == "waiting_for_agv":
                if not hasattr(task, 'wait_time_at_relay'):
                    task.wait_time_at_relay = 0
                task.wait_time_at_relay += 1
        
        current_battery = [uav.battery for uav in self.environment.uavs]

        # 处理 AGV 移动
        for agv in self.environment.agvs:
            if hasattr(agv, 'status') and agv.status == "moving_to_relay" and hasattr(agv, 'destination'):
                # 计算 AGV 移动速度（假设 AGV 移动速度为 10 单位/步）
                agv_speed = 10.0
                if hasattr(agv, 'move_distance') and hasattr(agv, 'move_progress'):
                    if agv.move_distance > 0:
                        # 计算每步移动的距离
                        step_distance = max(0, min(agv_speed, agv.move_distance - agv.move_progress))
                        
                        # 计算移动方向
                        dx = agv.destination[0] - agv.position[0]
                        dy = agv.destination[1] - agv.position[1]
                        distance = (dx**2 + dy**2) ** 0.5
                        
                        # 检查是否已经到达目的地
                        if distance <= 1e-6:
                            # 已经到达目的地
                            agv.position = agv.destination
                            agv.status = "idle"
                            
                            # 记录 AGV 到达中继点事件
                            self.events.append({
                                "step": self.time_step,
                                "type": "AGV_ARRIVE_RELAY",
                                "agv_id": agv.id,
                                "task_id": getattr(agv, 'task_id', None),
                                "x": agv.position[0],
                                "y": agv.position[1],
                                "details": "AGV arrived at relay point"
                            })
                            # 更新 AGV 状态
                            self.agv_states[agv.id] = "READY_AT_RELAY"
                            
                            # 找到对应的任务并将其状态改为in_progress
                            task_id = getattr(agv, 'task_id', None)
                            if task_id:
                                task = next((t for t in self.environment.tasks if t.id == task_id), None)
                                if task and task.status == "waiting_for_agv":
                                    # 将 UAV 位置更新到 relay_point
                                    if hasattr(task, 'assigned_uav') and task.assigned_uav:
                                        uav = task.assigned_uav
                                        # 记录更新前的位置
                                        old_position = uav.position
                                        # 使用统一的位置更新逻辑
                                        uav.update_position(agv.position)
                                        # 记录 UAV 被部署到中继点的事件
                                        self.events.append({
                                            "step": self.time_step,
                                            "type": "UAV_DEPLOYED_AT_RELAY",
                                            "uav_id": uav.id,
                                            "task_id": task.id,
                                            "agv_id": agv.id,
                                            "old_x": old_position[0],
                                            "old_y": old_position[1],
                                            "new_x": agv.position[0],
                                            "new_y": agv.position[1],
                                            "details": "UAV position updated to relay point"
                                        })
                                    # 更新任务状态
                                    task.status = "in_progress"
                            
                            # 移除移动相关属性
                            if hasattr(agv, 'destination'):
                                delattr(agv, 'destination')
                            if hasattr(agv, 'move_distance'):
                                delattr(agv, 'move_distance')
                            if hasattr(agv, 'move_progress'):
                                delattr(agv, 'move_progress')
                            # 最后删除task_id属性
                            if hasattr(agv, 'task_id'):
                                delattr(agv, 'task_id')
                        else:
                            direction_x = dx / distance
                            direction_y = dy / distance
                            
                            # 更新 AGV 位置
                            new_x = agv.position[0] + direction_x * step_distance
                            new_y = agv.position[1] + direction_y * step_distance
                            agv.position = (new_x, new_y)
                            
                            # 更新 path_history
                            if not hasattr(agv, 'path_history'):
                                agv.path_history = []
                            agv.path_history.append(agv.position)
                            
                            # 更新移动进度
                            agv.move_progress += step_distance
                            
                            # 检查是否到达目的地
                            if agv.move_progress >= agv.move_distance:
                                agv.position = agv.destination
                                agv.status = "idle"
                                
                                # 记录 AGV 到达中继点事件
                                self.events.append({
                                    "step": self.time_step,
                                    "type": "AGV_ARRIVE_RELAY",
                                    "agv_id": agv.id,
                                    "task_id": getattr(agv, 'task_id', None),
                                    "x": agv.position[0],
                                    "y": agv.position[1],
                                    "details": "AGV arrived at relay point"
                                })
                                # 更新 AGV 状态
                                self.agv_states[agv.id] = "READY_AT_RELAY"
                                
                                # 找到对应的任务并将其状态改为in_progress
                                task_id = getattr(agv, 'task_id', None)
                                if task_id:
                                    task = next((t for t in self.environment.tasks if t.id == task_id), None)
                                    if task and task.status == "waiting_for_agv":
                                        # 将 UAV 位置更新到 relay_point
                                        if hasattr(task, 'assigned_uav') and task.assigned_uav:
                                            uav = task.assigned_uav
                                            old_position = uav.position
                                            uav.update_position(agv.position)
                                            self.events.append({
                                                "step": self.time_step,
                                                "type": "UAV_DEPLOYED_AT_RELAY",
                                                "uav_id": uav.id,
                                                "task_id": task.id,
                                                "agv_id": agv.id,
                                                "old_x": old_position[0],
                                                "old_y": old_position[1],
                                                "new_x": agv.position[0],
                                                "new_y": agv.position[1],
                                                "details": "UAV position updated to relay point"
                                            })
                                        task.status = "in_progress"
                                
                                # 移除移动相关属性
                                if hasattr(agv, 'destination'):
                                    delattr(agv, 'destination')
                                if hasattr(agv, 'move_distance'):
                                    delattr(agv, 'move_distance')
                                if hasattr(agv, 'move_progress'):
                                    delattr(agv, 'move_progress')
                                # 最后删除task_id属性
                                if hasattr(agv, 'task_id'):
                                    delattr(agv, 'task_id')
                        
                        # 计算 AGV 移动能耗
                        agv_energy = step_distance * 0.05
                        self.total_energy += agv_energy
                        self.total_agv_energy += agv_energy
                        self.total_distance_agv += step_distance
                        step_energy += agv_energy
                        step_agv_distance += step_distance
                        step_agv_energy += agv_energy
                    else:
                        # AGV 已经在中继点，直接完成移动
                        agv.status = "idle"
                        
                        # 记录 AGV 到达中继点事件
                        self.events.append({
                            "step": self.time_step,
                            "type": "AGV_ARRIVE_RELAY",
                            "agv_id": agv.id,
                            "task_id": getattr(agv, 'task_id', None),
                            "x": agv.position[0],
                            "y": agv.position[1],
                            "details": "AGV arrived at relay point"
                        })
                        # 更新 AGV 状态
                        self.agv_states[agv.id] = "READY_AT_RELAY"
                        
                        # 找到对应的任务并将其状态改为in_progress
                        task_id = getattr(agv, 'task_id', None)
                        if task_id:
                            task = next((t for t in self.environment.tasks if t.id == task_id), None)
                            if task and task.status == "waiting_for_agv":
                                # 将 UAV 位置更新到 relay_point
                                if hasattr(task, 'assigned_uav') and task.assigned_uav:
                                    uav = task.assigned_uav
                                    old_position = uav.position
                                    uav.update_position(agv.position)
                                    self.events.append({
                                        "step": self.time_step,
                                        "type": "UAV_DEPLOYED_AT_RELAY",
                                        "uav_id": uav.id,
                                        "task_id": task.id,
                                        "agv_id": agv.id,
                                        "old_x": old_position[0],
                                        "old_y": old_position[1],
                                        "new_x": agv.position[0],
                                        "new_y": agv.position[1],
                                        "details": "UAV position updated to relay point"
                                    })
                                task.status = "in_progress"
                        
                        # 移除移动相关属性
                        if hasattr(agv, 'destination'):
                            delattr(agv, 'destination')
                        if hasattr(agv, 'move_distance'):
                            delattr(agv, 'move_distance')
                        if hasattr(agv, 'move_progress'):
                            delattr(agv, 'move_progress')
                        if hasattr(agv, 'task_id'):
                            delattr(agv, 'task_id')

        # 处理正在充电的UAV
        for uav in self.environment.uavs:
            if uav.id in self.charging_uavs:
                # UAV正在充电中
                charging_info = self.charging_uavs[uav.id]
                agv = charging_info['agv']
                
                # 每步充电
                charge_amount = self.charge_rate_per_step
                uav.update_battery(charge_amount)
                
                # 计算充电能耗
                agv_energy = 2.0  # 每次充电的基础能耗
                self.total_energy += agv_energy
                self.total_charge_loss_energy += agv_energy
                step_energy += agv_energy
                step_charge_loss_energy += agv_energy
                
                # 检查是否达到目标电量
                if uav.battery >= self.charge_target_soc:
                    # 记录充电结束事件
                    self.events.append({
                        "step": self.time_step,
                        "type": "CHARGING_END",
                        "uav_id": uav.id,
                        "agv_id": agv.id,
                        "battery": uav.battery,
                        "x": uav.position[0],
                        "y": uav.position[1],
                        "details": "Charging ended"
                    })
                    # 移除充电状态
                    del self.charging_uavs[uav.id]
                    self.charging_states[uav.id] = False
        
        # 处理 UAV 任务和路径规划
        for uav in self.environment.uavs:
            # 正在充电的UAV不能执行任务
            if uav.id in self.charging_uavs:
                continue
                
            if uav.task and not uav.path:
                # 检查等待AGV的时间，如果超时则回退到直接配送
                if uav.task.status == "waiting_for_agv":
                    # 增加等待时间
                    if hasattr(uav.task, 'assigned_time'):
                        uav.task.assigned_time += 1
                    else:
                        uav.task.assigned_time = 1
                    
                    # 如果等待时间超过10步，回退到直接配送
                    if uav.task.assigned_time > 10:
                        uav.task.status = "in_progress"
                        # 记录回退事件
                        self.events.append({
                            "step": self.time_step,
                            "type": "RELAY_FALLBACK",
                            "task_id": uav.task.id,
                            "uav_id": uav.id,
                            "details": "AGV took too long, falling back to direct delivery"
                        })
                
                # 当任务状态为 in_progress 时规划路径
                if uav.task.status == "in_progress":
                    # 对于 relay 模式的任务（无论使用哪种策略），如果任务已 fallback 或 AGV 已到达，直接规划路径
                    if hasattr(uav.task, "relay_point") and hasattr(uav.task, "assigned_agv"):
                        agv = uav.task.assigned_agv
                        # 检查是否已经 fallback 或 AGV 已到达
                        fallback_triggered = hasattr(uav.task, 'assigned_time') and uav.task.assigned_time > 10
                        agv_ready = hasattr(agv, 'status') and agv.status == "idle"
                        
                        # 如果已 fallback 或 AGV 已到达，直接规划路径
                        if fallback_triggered or agv_ready:
                            # 转换障碍物为 (x, y, radius) 列表格式
                            obstacles = []
                            if hasattr(self.environment, 'obstacles'):
                                for obstacle in self.environment.obstacles:
                                    if hasattr(obstacle, 'position') and hasattr(obstacle, 'radius'):
                                        obstacles.append((obstacle.position[0], obstacle.position[1], obstacle.radius))
                                    elif isinstance(obstacle, (list, tuple)) and len(obstacle) >= 3:
                                        obstacles.append((obstacle[0], obstacle[1], obstacle[2]))
                            # 使用 A* 算法规划路径，确保时间步与距离成正比
                            uav.path = self.path_planner.plan_path(uav.position, uav.task.end_point, obstacles)
                            # 记录事件
                            if not hasattr(uav.task, "relay_event_recorded"):
                                event_type = "RELAY_FALLBACK_START" if fallback_triggered else "RELAY_COOP_START"
                                self.events.append({
                                    "step": self.time_step,
                                    "type": event_type,
                                    "task_id": uav.task.id,
                                    "uav_id": uav.id,
                                    "agv_id": agv.id if agv_ready else None,
                                    "relay_point": getattr(uav.task, "relay_point", None)
                                })
                                uav.task.relay_event_recorded = True
                    else:
                        # 其他策略或 AGV 已到达，直接规划到终点
                        # 转换障碍物为 (x, y, radius) 列表格式
                        obstacles = []
                        if hasattr(self.environment, 'obstacles'):
                            for obstacle in self.environment.obstacles:
                                if hasattr(obstacle, 'position') and hasattr(obstacle, 'radius'):
                                    obstacles.append((obstacle.position[0], obstacle.position[1], obstacle.radius))
                                elif isinstance(obstacle, (list, tuple)) and len(obstacle) >= 3:
                                    obstacles.append((obstacle[0], obstacle[1], obstacle[2]))
                        uav.path = self.path_planner.plan_path(uav.position, uav.task.end_point, obstacles)

            if uav.path:
                next_point = uav.path[0]
                distance = (
                    (uav.position[0] - next_point[0]) ** 2 + (uav.position[1] - next_point[1]) ** 2
                ) ** 0.5
                self.total_distance += distance
                step_uav_distance += distance
                
                # 更新任务的 UAV 移动距离
                if uav.task:
                    self._add_task_stat(uav.task, 'uav_distance', distance)

                uav.update_position(next_point)
                uav.path.pop(0)

                # 计算能耗，考虑策略差异
                if self.strategy.name == "energy_priority" and hasattr(uav.task, "estimated_energy"):
                    # 对于能量优先策略，使用预计算的能耗
                    # 这里简化处理，将总能耗分摊到路径的每一步
                    total_distance = sum(
                        ((uav.path[i][0] - uav.path[i+1][0])**2 + (uav.path[i][1] - uav.path[i+1][1])**2)**0.5
                        for i in range(len(uav.path)-1)
                    )
                    if total_distance > 0:
                        segment_distance = distance / total_distance
                        cost = uav.task.estimated_energy * segment_distance
                    else:
                        cost = 0
                else:
                    # 其他策略使用标准能耗模型
                    cost = float(self.energy_model.compute(uav))

                uav.update_battery(-cost)
                step_energy += cost
                step_uav_energy += cost
                self.total_uav_energy += cost
                
                # 更新任务的 UAV 能耗
                if uav.task:
                    self._add_task_stat(uav.task, 'uav_energy', cost)

                if not uav.path and uav.task:
                    task = uav.task
                    task.complete(self.time_step)
                    task_id = task.id
                    uav.complete_task()
                    self.completed_tasks += 1
                    self.task_completion_times.append(self.time_step)  # 记录任务完成时间
                    print(f"UAV {uav.id} completed task {task_id}")
                    self.events.append({
                        "step": self.time_step,
                        "type": "TASK_COMPLETE",
                        "task_id": task_id,
                        "uav_id": uav.id,
                        "completion_time": self.time_step
                    })
            # 记录低电量事件
            if uav.battery < 30 and uav.battery >= 20:
                self.events.append({
                    "step": self.time_step,
                    "type": "LOW_BATTERY",
                    "uav_id": uav.id,
                    "battery": uav.battery
                })
                # 发送低电量状态消息
                self.network_manager.send_message(
                    f"UAV_{uav.id}",
                    "CONTROL_CENTER",
                    "LOW_BATTERY",
                    f"UAV {uav.id} battery level: {uav.battery:.2f}%"
                )
            # 检查充电状态变化
            now_charging = uav.battery < self.charge_start_threshold
            was_charging = self.charging_states.get(uav.id, False)
            
            # 确保不会在连续步骤中重复触发充电请求
            if now_charging and not was_charging and uav.id not in self.charging_uavs:
                # 记录充电请求事件
                self.events.append({
                    "step": self.time_step,
                    "type": "CHARGING_REQUEST",
                    "uav_id": uav.id,
                    "battery": uav.battery,
                    "details": "UAV requests charging"
                })
                # 发送充电请求消息
                self.network_manager.send_message(
                    f"UAV_{uav.id}",
                    "CONTROL_CENTER",
                    "CHARGING_REQUEST",
                    f"UAV {uav.id} requests charging, battery: {uav.battery:.2f}%"
                )
                agv = self.strategy.select_charging_station(uav, self.environment)
                if agv:
                    # 发送充电分配消息
                    self.network_manager.send_message(
                        "CONTROL_CENTER",
                        f"AGV_{agv.id}",
                        "CHARGING_ASSIGNMENT",
                        f"AGV {agv.id} assigned to charge UAV {uav.id}"
                    )
                    # 记录充电开始事件
                    self.events.append({
                        "step": self.time_step,
                        "type": "CHARGING_START",
                        "uav_id": uav.id,
                        "agv_id": agv.id,
                        "battery": uav.battery,
                        "x": uav.position[0],
                        "y": uav.position[1],
                        "details": "Charging started"
                    })
                    # 更新充电状态
                    self.charging_states[uav.id] = True
                    self.charging_count += 1
                    # 记录充电信息
                    self.charging_uavs[uav.id] = {
                        'agv': agv,
                        'start_step': self.time_step,
                        'start_battery': uav.battery
                    }

        self.energy_history.append(step_energy)
        self.task_history.append(self.completed_tasks)
        self.battery_history.append(current_battery)
        self.charging_history.append(self.charging_count)
        # 记录当前步骤的距离增量
        self.distance_history.append(step_uav_distance + step_agv_distance)
        # 更新新的历史记录数组
        self.uav_distance_history.append(step_uav_distance)
        self.agv_distance_history.append(step_agv_distance)
        self.uav_energy_history.append(step_uav_energy)
        self.agv_energy_history.append(step_agv_energy)
        self.charge_loss_energy_history.append(step_charge_loss_energy)

        self.time_step += 1
        return step_energy



    def print_results(self):
        completion_rate = (
            self.completed_tasks / self.initial_task_count if self.initial_task_count > 0 else 0.0
        )

        print("\n=== Results ===")
        print(f"total_energy: {self.total_energy}")
        print(f"total_time: {self.time_step}")
        print(f"completion_rate: {completion_rate:.2%}")
        print(f"completed_tasks: {self.completed_tasks}/{self.initial_task_count}")
        print(f"charging_count: {self.charging_count}")

    def calculate_metrics(self):
        completion_rate = (
            self.completed_tasks / self.initial_task_count if self.initial_task_count > 0 else 0.0
        )
        total_distance = self.total_distance + self.total_distance_agv
        avg_energy_per_task = self.total_energy / self.completed_tasks if self.completed_tasks > 0 else None
        energy_per_km = self.total_energy / total_distance if total_distance > 0 else None

        execution_times = []
        wait_times = []
        on_time_tasks = 0

        for task in self.environment.tasks:
            self._ensure_task_stats(task)
            start_time = getattr(task, "start_time", None)
            completion_time = getattr(task, "completion_time", None)
            deadline = self._resolve_task_deadline(task)

            if completion_time is not None and deadline is not None and completion_time <= deadline:
                on_time_tasks += 1

            if start_time is not None and completion_time is not None:
                execution_times.append(completion_time - start_time)

            wait_time = float(getattr(task, "wait_time_at_relay", 0.0))
            if wait_time > 0:
                wait_times.append(wait_time)

        avg_delivery_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        avg_wait_time_at_relay = sum(wait_times) / len(wait_times) if wait_times else None
        max_delivery_time = max(execution_times) if execution_times else 0.0
        on_time_rate = on_time_tasks / self.initial_task_count if self.initial_task_count > 0 else 0.0
        on_time_rate_given_completed = on_time_tasks / self.completed_tasks if self.completed_tasks > 0 else 0.0
        carbon_emission = self.total_energy * 0.5

        return {
            "strategy_name": self.strategy.name,
            "scenario_name": self.scenario_name,
            "seed": self.seed,
            "total_tasks": self.initial_task_count,
            "completed_tasks": int(self.completed_tasks),
            "failed_tasks": self.initial_task_count - self.completed_tasks,
            "completion_rate": float(completion_rate),
            "on_time_tasks": int(on_time_tasks),
            "on_time_rate": float(on_time_rate),
            "on_time_rate_given_completed": float(on_time_rate_given_completed),
            "total_time": int(self.time_step),
            "avg_delivery_time": float(avg_delivery_time),
            "avg_wait_time_at_relay": avg_wait_time_at_relay,
            "max_delivery_time": float(max_delivery_time),
            "total_distance_uav": float(self.total_distance),
            "total_distance_agv": float(self.total_distance_agv),
            "total_distance": float(total_distance),
            "uav_energy": float(self.total_uav_energy),
            "agv_energy": float(self.total_agv_energy),
            "charge_loss_energy": float(self.total_charge_loss_energy),
            "total_energy": float(self.total_energy),
            "avg_energy_per_task": avg_energy_per_task,
            "energy_per_km": energy_per_km,
            "carbon_emission": float(carbon_emission),
            "charging_count": int(self.charging_count),
            "fallback_count": int(self._cumulative_fallback_count),
            "replan_count": int(self._cumulative_replan_count),
            "relay_count": int(self._cumulative_relay_count),
            "direct_count": int(self._cumulative_direct_count),
            "baseline_strategy_name": None,
            "baseline_run_dir": None,
            "baseline_total_energy": None,
            "baseline_carbon_emission": None,
            "energy_saving_rate_vs_baseline": None,
            "emission_reduction_rate_vs_baseline": None,
        }

    def save_results(self, experiment_name="default", result_type="runs", campaign_name=None):
        # 根据result_type选择不同的布局创建函数
        robustness_result_types = {"seed_stability", "scale", "capacity", "failure"}
        if campaign_name and (result_type.startswith("round") or result_type in robustness_result_types):
            # 使用鲁棒性实验布局
            from src.utils.result_layout import create_robustness_layout
            layout = create_robustness_layout(
                campaign_name=campaign_name,
                round_type=result_type
            )
        else:
            # 使用原来的布局
            layout = create_result_layout(experiment_name=experiment_name, result_type=result_type)
        output_dir = str(layout.run_dir)

        metrics = self.calculate_metrics()

        # 保存 metrics.json
        metrics_file = layout.artifact_path("metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        # 保存 steps.csv
        steps_file = layout.record_path("steps.csv")
        with open(steps_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "sim_time", "active_tasks", "completed_tasks_cumulative", "charging_count_cumulative", 
                          "uav_distance_cumulative", "agv_distance_cumulative", "total_distance_cumulative", 
                          "uav_energy_cumulative", "agv_energy_cumulative", "charge_loss_energy_cumulative", "total_energy_cumulative"])
            
            cumulative_energy = 0
            cumulative_uav_distance = 0
            cumulative_agv_distance = 0
            cumulative_uav_energy = 0
            cumulative_agv_energy = 0
            cumulative_charge_loss_energy = 0
            
            # 确保所有历史记录长度一致
            max_len = max(
                len(self.energy_history),
                len(self.task_history),
                len(self.charging_history),
                len(self.uav_distance_history),
                len(self.agv_distance_history),
                len(self.uav_energy_history),
                len(self.agv_energy_history),
                len(self.charge_loss_energy_history),
            )
            
            for i in range(max_len):
                # 获取当前步骤的能量消耗
                step_energy = self.energy_history[i] if i < len(self.energy_history) else 0.0
                # 获取当前步骤的完成任务数
                step_tasks = self.task_history[i] if i < len(self.task_history) else (self.task_history[-1] if self.task_history else 0)
                # 获取当前步骤的充电次数
                step_charging = self.charging_history[i] if i < len(self.charging_history) else (self.charging_history[-1] if self.charging_history else 0)
                # 获取当前步骤的UAV距离
                step_uav_distance = self.uav_distance_history[i] if i < len(self.uav_distance_history) else 0.0
                step_agv_distance = self.agv_distance_history[i] if i < len(self.agv_distance_history) else 0.0
                step_uav_energy = self.uav_energy_history[i] if i < len(self.uav_energy_history) else 0.0
                step_agv_energy = self.agv_energy_history[i] if i < len(self.agv_energy_history) else 0.0
                step_charge_loss = self.charge_loss_energy_history[i] if i < len(self.charge_loss_energy_history) else 0.0
                
                # 累计能量和距离
                cumulative_energy += step_energy
                cumulative_uav_distance += step_uav_distance
                cumulative_agv_distance += step_agv_distance
                cumulative_uav_energy += step_uav_energy
                cumulative_agv_energy += step_agv_energy
                cumulative_charge_loss_energy += step_charge_loss
                
                # 从实例属性获取累计的AGV距离和能量
                active_tasks = max(self.initial_task_count - step_tasks, 0)
                
                writer.writerow([i, i + 1, active_tasks, step_tasks, step_charging, 
                              cumulative_uav_distance, cumulative_agv_distance, 
                              cumulative_uav_distance + cumulative_agv_distance, 
                              cumulative_uav_energy, cumulative_agv_energy, 
                              cumulative_charge_loss_energy, cumulative_energy])
            
            # 确保最后一行与 metrics.json 一致
            if max_len > 0:
                if abs(cumulative_energy - float(metrics["total_energy"])) > 1e-6:
                    raise ValueError("steps.csv total_energy_cumulative does not match metrics.total_energy")
                final_total_distance = cumulative_uav_distance + cumulative_agv_distance
                if abs(final_total_distance - float(metrics["total_distance"])) > 1e-6:
                    raise ValueError("steps.csv total_distance_cumulative does not match metrics.total_distance")
                if abs(cumulative_agv_distance - float(metrics["total_distance_agv"])) > 1e-6:
                    raise ValueError("steps.csv agv_distance_cumulative does not match metrics.total_distance_agv")
                if int(step_charging) != int(metrics["charging_count"]):
                    raise ValueError("steps.csv charging_count_cumulative does not match metrics.charging_count")

        # 保存 tasks.csv
        tasks_file = layout.record_path("tasks.csv")
        with open(tasks_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["task_id", "strategy_name", "start_time", "assigned_time", "finish_time", 
                          "execution_time", "completed", "on_time", "deadline", "uav_distance", 
                          "agv_distance", "wait_time_at_relay", "uav_energy", "agv_energy", 
                          "charge_loss_energy", "total_energy"])
            
            for task in self.environment.tasks:
                self._ensure_task_stats(task)
                start_time = getattr(task, "start_time", None)
                assigned_time = getattr(task, "assigned_time", None)
                completion_time = getattr(task, "completion_time", None)
                # 确保 start_time=0 的任务也能计算 execution_time
                execution_time = (
                    completion_time - start_time
                    if start_time is not None and completion_time is not None
                    else None
                )
                
                # 计算 on_time 列
                on_time = False
                deadline = None
                # 处理 time_window 可能是元组的情况
                time_window = getattr(task, 'time_window', ())
                time_window_max = time_window[1] if isinstance(time_window, tuple) and len(time_window) > 1 else None
                
                if time_window_max is not None:
                    deadline = time_window_max
                
                completed = task.status == "completed"
                if completed and completion_time is not None and deadline is not None:
                    on_time = completion_time <= deadline
                
                deadline = self._resolve_task_deadline(task)
                completed = task.status == "completed" or completion_time is not None
                on_time = (
                    completed
                    and completion_time is not None
                    and deadline is not None
                    and completion_time <= deadline
                )
                wait_time_at_relay = float(getattr(task, "wait_time_at_relay", 0.0))
                
                # 计算任务的距离和能耗
                uav_distance = float(getattr(task, "uav_distance", 0.0))
                agv_distance = float(getattr(task, "agv_distance", 0.0))
                uav_energy = float(getattr(task, "uav_energy", 0.0))
                agv_energy = float(getattr(task, "agv_energy", 0.0))
                charge_loss_energy = float(getattr(task, "charge_loss_energy", 0.0))
                total_energy = float(
                    getattr(task, "total_energy", uav_energy + agv_energy + charge_loss_energy)
                )
                
                writer.writerow([
                    task.id,
                    self.strategy.name,
                    start_time,
                    assigned_time,
                    completion_time,  # finish_time
                    execution_time,
                    completed,
                    on_time,
                    deadline,
                    uav_distance,  # uav_distance
                    agv_distance,  # agv_distance
                    wait_time_at_relay,
                    uav_energy,  # uav_energy
                    agv_energy,  # agv_energy
                    charge_loss_energy,  # charge_loss_energy
                    total_energy   # total_energy
                ])

        # 保存 config_snapshot.yaml
        config_snapshot = {
            "experiment_name": experiment_name,
            "strategy": self.strategy.name,
            "initial_task_count": self.initial_task_count,
            "num_uavs": len(self.environment.uavs),
            "num_agvs": len(self.environment.agvs)
        }
        config_file = layout.artifact_path("config_snapshot.yaml")
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_snapshot, f, default_flow_style=False, allow_unicode=True)

        # 保存 run.log
        log_file = layout.log_path("run.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Experiment: {experiment_name}\n")
            f.write(f"Strategy: {self.strategy.name}\n")
            f.write(f"Initial tasks: {self.initial_task_count}\n")
            f.write(f"UAVs: {len(self.environment.uavs)}\n")
            f.write(f"AGVs: {len(self.environment.agvs)}\n")
            f.write(f"Completed tasks: {self.completed_tasks}\n")
            f.write(f"Total energy: {self.total_energy}\n")
            f.write(f"Total time steps: {self.time_step}\n")
            f.write(f"Charging count: {self.charging_count}\n")

        # 保存 communication_log.csv 到 records 文件夹
        communication_log_file = layout.record_path("communication_log.csv")
        with open(communication_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sender", "receiver", "message_type", "content"])
            
            # 基于真实事件生成通信日志
            for event in self.events:
                step = event["step"]
                event_type = event["type"]
                
                # 同时支持 TASK_ASSIGNED（内部事件名）和 TASK_ASSIGNMENT（消息名）
                if event_type == "TASK_ASSIGNED" or event_type == "TASK_ASSIGNMENT":
                    writer.writerow([step, f"Control Center", f"UAV {event['uav_id']}", "TASK_ASSIGNMENT", f"Assign task {event['task_id']}"])
                elif event_type == "TASK_START":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "TASK_START", f"Start task {event['task_id']}"])
                elif event_type == "TASK_COMPLETE":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "TASK_COMPLETE", f"Complete task {event['task_id']}"])
                elif event_type == "LOW_BATTERY":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "LOW_BATTERY", f"Battery level: {event['battery']:.1f}%"])
                elif event_type == "CHARGING_REQUEST":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "CHARGING_REQUEST", f"Request charging, battery: {event['battery']:.1f}%"])
                elif event_type == "CHARGING_START":
                    writer.writerow([step, f"Control Center", f"AGV {event['agv_id']}", "CHARGING_COMMAND", f"Charge UAV {event['uav_id']}"])
                    writer.writerow([step, f"AGV {event['agv_id']}", f"UAV {event['uav_id']}", "CHARGING_START", "Start charging"])
                elif event_type == "AGV_ARRIVE_RELAY":
                    writer.writerow([step, f"AGV {event['agv_id']}", "Control Center", "AGV_ARRIVE_RELAY", f"AGV {event['agv_id']} arrived at relay point for task {event.get('task_id', 'N/A')}"])
                elif event_type == "RELAY_REQUEST":
                    writer.writerow([step, f"Control Center", f"AGV {event.get('agv_id', 'N/A')}", "RELAY_REQUEST", f"Request relay support for task {event.get('task_id', 'N/A')}"])

        # 保存 event_timeline.txt 到 records 文件夹
        event_timeline_file = layout.record_path("event_timeline.txt")
        with open(event_timeline_file, "w", encoding="utf-8") as f:
            f.write("Event Timeline\n")
            f.write("================\n")
            
            # 按步骤组织事件
            events_by_step = {}
            for event in self.events:
                step = event["step"]
                if step not in events_by_step:
                    events_by_step[step] = []
                events_by_step[step].append(event)
            
            # 按步骤输出事件
            for step in sorted(events_by_step.keys()):
                f.write(f"Step {step}:\n")
                for event in events_by_step[step]:
                    event_type = event["type"]
                    # 同时支持 TASK_ASSIGNED 和 TASK_ASSIGNMENT
                    if event_type == "TASK_ASSIGNED" or event_type == "TASK_ASSIGNMENT":
                        f.write(f"  - Task assignment: UAV {event['uav_id']} assigned task {event['task_id']}")
                        if "agv_id" in event and event["agv_id"]:
                            f.write(f" with AGV {event['agv_id']}")
                        f.write("\n")
                    elif event_type == "TASK_START":
                        f.write(f"  - Task start: UAV {event['uav_id']} started task {event['task_id']}\n")
                    elif event_type == "TASK_COMPLETE":
                        f.write(f"  - Task complete: UAV {event['uav_id']} completed task {event['task_id']}\n")
                    elif event_type == "LOW_BATTERY":
                        f.write(f"  - Low battery alert: UAV {event['uav_id']} battery at {event['battery']:.1f}%\n")
                    elif event_type == "CHARGING_REQUEST":
                        f.write(f"  - Charging request: UAV {event['uav_id']} requests charging (battery: {event['battery']:.1f}%)\n")
                    elif event_type == "CHARGING_START":
                        f.write(f"  - Charging start: AGV {event['agv_id']} starts charging UAV {event['uav_id']}\n")
                    elif event_type == "CHARGING_END":
                        f.write(f"  - Charging end: UAV {event['uav_id']} finished charging\n")
                    elif event_type == "AGV_MOVE_START":
                        f.write(f"  - AGV move start: AGV {event['agv_id']} starts moving to relay point for task {event['task_id']}\n")
                    elif event_type == "AGV_ARRIVE_RELAY":
                        f.write(f"  - AGV arrive relay: AGV {event['agv_id']} arrived at relay point for task {event['task_id']}\n")
                    elif event_type == "WAIT_FOR_AGV_START":
                        f.write(f"  - Wait for AGV start: Task {event['task_id']} starts waiting for AGV\n")
                    elif event_type == "WAIT_FOR_AGV_END":
                        f.write(f"  - Wait for AGV end: Task {event['task_id']} stops waiting for AGV\n")
                    elif event_type == "RELAY_REQUEST":
                        f.write(f"  - Relay request: Relay support requested for task {event.get('task_id', 'N/A')} with AGV {event.get('agv_id', 'N/A')}\n")
                    elif event_type == "RELAY_FALLBACK" or event_type == "RELAY_FALLBACK_START":
                        f.write(f"  - Relay fallback: Task {event['task_id']} falling back to direct delivery\n")
                    elif event_type == "UAV_REMOVED":
                        f.write(f"  - UAV removed: UAV {event['uav_id']} removed due to failure\n")
            
            # 输出最终统计信息
            f.write("\nFinal Statistics:\n")
            f.write(f"- Total tasks completed: {self.completed_tasks}/{self.initial_task_count}\n")


        
        # 保存 coordination_events.csv 到 records 文件夹
        coordination_events_file = layout.record_path("coordination_events.csv")
        with open(coordination_events_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "sim_time", "event_type", "task_id", "uav_id", "agv_id", "x", "y", "details"])
            
            for event in self.events:
                step = event.get("step", 0)
                sim_time = step  # 假设 sim_time 等于 step
                event_type = event.get("type", "")
                task_id = event.get("task_id", "")
                uav_id = event.get("uav_id", "")
                agv_id = event.get("agv_id", "")
                x = event.get("x", "")
                y = event.get("y", "")
                details = event.get("details", "")
                
                writer.writerow([step, sim_time, event_type, task_id, uav_id, agv_id, x, y, details])

        # 生成图表
        plot_files = self._generate_plots(layout)
        write_metadata(
            layout,
            {
                "experiment_name": experiment_name,
                "timestamp": layout.run_dir.name,
                "strategy": self.strategy.name,
                "records_granularity": "step",
                "required_artifacts": list(REQUIRED_ARTIFACTS),
                "plots": [str(path.relative_to(layout.run_dir)) for path in plot_files],
                "summary": {
                    "initial_task_count": self.initial_task_count,
                    "completed_tasks": self.completed_tasks,
                    "time_steps": self.time_step,
                },
            },
        )
        return output_dir

    def _generate_plots(self, layout):
        plot_files = []

        # 1. task_progress.png - 任务完成曲线
        plt.figure(figsize=(10, 6))
        plt.plot(self.task_history, label="Completed Tasks", drawstyle='steps-post')
        plt.xlabel("Step")
        plt.ylabel("Completed Tasks")
        plt.title("Task Progress Over Time")
        plt.legend()
        plt.grid(True)
        # 校验：最终值必须等于 metrics.completed_tasks
        metrics = self.calculate_metrics()
        plt.axhline(y=metrics['completed_tasks'], color='r', linestyle='--', label=f'Final: {metrics["completed_tasks"]}')
        plt.legend()
        task_progress_path = layout.plot_path("task_progress.png")
        plt.savefig(task_progress_path)
        plt.close()
        plot_files.append(task_progress_path)

        # 2. battery_status.png - 电池状态
        if not self.battery_history:
            raise ValueError("battery_status.png: Battery history is empty")
        battery_data = np.array(self.battery_history)
        plt.figure(figsize=(10, 6))
        for i in range(battery_data.shape[1]):
            plt.plot(battery_data[:, i], label=f"UAV {i + 1}")
        plt.xlabel("Step")
        plt.ylabel("Battery")
        plt.title("Battery Status Over Time")
        plt.legend()
        plt.grid(True)
        battery_status_path = layout.plot_path("battery_status.png")
        plt.savefig(battery_status_path)
        plt.close()
        plot_files.append(battery_status_path)

        # 3. energy_curve.png - 能耗曲线
        plt.figure(figsize=(10, 6))
        # 计算累计能耗
        cumulative_energy = np.cumsum(self.energy_history)
        plt.plot(self.energy_history, label="Step Energy")
        plt.plot(cumulative_energy, label="Cumulative Energy")
        plt.xlabel("Step")
        plt.ylabel("Energy")
        plt.title("Energy Consumption Over Time")
        plt.legend()
        plt.grid(True)
        # 校验：cumulative_energy 必须单调不减
        if not all(cumulative_energy[i] >= cumulative_energy[i-1] for i in range(1, len(cumulative_energy))):
            raise ValueError("energy_curve.png: Cumulative energy is not monotonically increasing")
        energy_curve_path = layout.plot_path("energy_curve.png")
        plt.savefig(energy_curve_path)
        plt.close()
        plot_files.append(energy_curve_path)

        # 4. trajectory_map.png - 轨迹图
        plt.figure(figsize=(10, 8))
        # 绘制任务起点和终点
        for task in self.environment.tasks:
            plt.scatter(task.start_point[0], task.start_point[1], color="blue", label="Task Start" if task.id == 1 else "")
            plt.scatter(task.end_point[0], task.end_point[1], color="red", label="Task End" if task.id == 1 else "")
        # 绘制 UAV 轨迹
        uav_trajectory_count = 0
        for uav in self.environment.uavs:
            if hasattr(uav, 'path_history') and uav.path_history:
                uav_trajectory_count += 1
                path = uav.path_history
                x, y = zip(*path)
                plt.plot(x, y, label=f"UAV {uav.id} Trajectory")
                # 绘制终态位置
                plt.scatter(uav.position[0], uav.position[1], color="green", marker="^", label=f"UAV {uav.id} End" if uav.id == 1 else "")
        # 绘制 AGV 轨迹
        for agv in self.environment.agvs:
            if hasattr(agv, 'path_history') and agv.path_history:
                path = agv.path_history
                x, y = zip(*path)
                plt.plot(x, y, linestyle="--", label=f"AGV {agv.id} Trajectory")
                # 绘制终态位置
                plt.scatter(agv.position[0], agv.position[1], color="orange", marker="s", label=f"AGV {agv.id} End" if agv.id == 1 else "")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Trajectory Map")
        plt.legend()
        plt.grid(True)
        # 校验：至少 1 条 UAV 轨迹
        if uav_trajectory_count == 0:
            raise ValueError("trajectory_map.png: No UAV trajectory found")
        # 校验：relay_coop 下 AGV 轨迹应非空
        if self.strategy.name == "relay_coop":
            agv_trajectory_count = 0
            for agv in self.environment.agvs:
                if hasattr(agv, 'path_history') and agv.path_history:
                    agv_trajectory_count += 1
            if agv_trajectory_count == 0:
                raise ValueError("trajectory_map.png: No AGV trajectory found for relay_coop strategy")
        trajectory_path = layout.plot_path("trajectory_map.png")
        plt.savefig(trajectory_path)
        plt.close()
        plot_files.append(trajectory_path)

        # 5. environment_state.png - 环境状态
        plt.figure(figsize=(10, 8))
        # 绘制任务起点和终点
        task_count = 0
        for task in self.environment.tasks:
            task_count += 1
            plt.scatter(task.start_point[0], task.start_point[1], color="blue", label="Task Start" if task.id == 1 else "")
            plt.scatter(task.end_point[0], task.end_point[1], color="red", label="Task End" if task.id == 1 else "")
        # 绘制 UAV
        for uav in self.environment.uavs:
            plt.scatter(uav.position[0], uav.position[1], color="green", marker="^", label="UAV" if uav.id == 1 else "")
        # 绘制 AGV
        for agv in self.environment.agvs:
            plt.scatter(agv.position[0], agv.position[1], color="orange", marker="s", label="AGV" if agv.id == 1 else "")
        # 绘制障碍物
        for obstacle in getattr(self.environment, 'obstacles', []):
            if hasattr(obstacle, 'position'):
                plt.scatter(obstacle.position[0], obstacle.position[1], color="gray", marker="x", label="Obstacle" if obstacle == getattr(self.environment, 'obstacles', [])[0] else "")
        # 绘制禁飞区
        for no_fly_zone in getattr(self.environment, 'no_fly_zones', []):
            if hasattr(no_fly_zone, 'center') and hasattr(no_fly_zone, 'radius'):
                circle = plt.Circle(no_fly_zone.center, no_fly_zone.radius, color="purple", alpha=0.3, label="No Fly Zone" if no_fly_zone == getattr(self.environment, 'no_fly_zones', [])[0] else "")
                plt.gca().add_patch(circle)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Environment State")
        plt.legend()
        plt.grid(True)
        # 校验：任务点数量与 total_tasks 一致
        if task_count != metrics['total_tasks']:
            raise ValueError(f"environment_state.png: Task count {task_count} does not match total_tasks {metrics['total_tasks']}")
        environment_state_path = layout.plot_path("environment_state.png")
        plt.savefig(environment_state_path)
        plt.close()
        plot_files.append(environment_state_path)

        # 6. coordination_events.png - 协调事件
        plt.figure(figsize=(12, 8))
        # 按步骤组织事件
        events_by_step = {}
        for event in self.events:
            step = event["step"]
            if step not in events_by_step:
                events_by_step[step] = []
            events_by_step[step].append(event)
        
        # 准备事件数据
        steps = sorted(events_by_step.keys())
        event_types = []
        event_steps = []
        
        for step in steps:
            for event in events_by_step[step]:
                event_type = event["type"]
                # 关注所有相关事件类型，接受 AGV_ARRIVE_RELAY（代替 AGV_REACHED_RELAY）
                if event_type in ["TASK_ASSIGNED", "RELAY_REQUEST", "AGV_MOVE_START", "AGV_ARRIVE_RELAY", "RELAY_COOP_START",
                                "WAIT_FOR_AGV_START", "WAIT_FOR_AGV_END", "CHARGING_START", "CHARGING_END", "RELAY_FALLBACK",
                                "RELAY_FALLBACK_START", "UAV_REMOVED"]:
                    event_types.append(event_type)
                    event_steps.append(step)
        
        # 绘制事件时间轴
        plt.scatter(event_steps, event_types, s=100, alpha=0.7)
        plt.xlabel("Step")
        plt.ylabel("Event Type")
        plt.title("Coordination Events Timeline")
        plt.grid(True, axis='x')
        # 旋转 x 轴标签
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # relay_coop 策略没有中继事件时不再抛错，改为警告并正常生成图表
        if self.strategy.name == "relay_coop":
            has_relay_event = any(et in ["RELAY_REQUEST", "AGV_ARRIVE_RELAY", "AGV_MOVE_START", "RELAY_COOP_START", "RELAY_FALLBACK"] for et in event_types)
            if not has_relay_event:
                print("Warning: No relay events found for relay_coop strategy, but continuing to generate coordination_events.png")
        
        coordination_events_path = layout.plot_path("coordination_events.png")
        plt.savefig(coordination_events_path)
        plt.close()
        plot_files.append(coordination_events_path)

        # 7. kpi_summary.png - KPI摘要
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('off')
        
        # 9 核心指标
        core_metrics = [
            'completion_rate',
            'on_time_rate',
            'avg_delivery_time',
            'total_energy',
            'avg_energy_per_task',
            'energy_per_km',
            'total_distance_agv',
            'avg_wait_time_at_relay',
            'charging_count'
        ]
        
        # 构建 KPI 文本
        kpi_text = "9 Core Metrics\n"
        kpi_text += "================\n"
        for metric in core_metrics:
            value = metrics.get(metric)
            if metric in ['completion_rate', 'on_time_rate']:
                kpi_text += f"{metric}: {value * 100:.2f}%\n"
            else:
                kpi_text += f"{metric}: {value if value is not None else 'N/A'}\n"
        
        ax.text(0.1, 0.5, kpi_text, fontsize=14, va="center")
        plt.title("KPI Summary")
        
        kpi_summary_path = layout.plot_path("kpi_summary.png")
        plt.savefig(kpi_summary_path)
        plt.close()
        plot_files.append(kpi_summary_path)

        return plot_files
