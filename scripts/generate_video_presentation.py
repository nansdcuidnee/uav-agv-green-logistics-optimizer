"""生成 UAV-AGV 协同配送答辩演示视频 - 强调 AGV 支撑作用"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


def parse_args():
    parser = argparse.ArgumentParser(description="生成答辩演示视频（强调AGV支撑）")
    parser.add_argument("--run-dir", required=True, help="运行结果目录")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument("--fps", type=int, default=10, help="帧率")
    parser.add_argument("--width", type=int, default=1280, help="视频宽度")
    parser.add_argument("--height", type=int, default=720, help="视频高度")
    parser.add_argument("--map-size", type=int, default=1000, help="地图尺寸")
    return parser.parse_args()


def get_font(font_size):
    windows_fonts = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for font_path in windows_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                continue
    return ImageFont.load_default()


def put_text(img, text, position, font_size=32, color=(30, 30, 30)):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = get_font(font_size)
    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def put_text_with_bg(img, text, position, font_size=32, color=(30, 30, 30), bg_color=(255, 255, 255)):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = get_font(font_size)
    
    try:
        text_width, text_height = draw.textsize(text, font=font)
    except AttributeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    
    bg_padding = 6
    draw.rectangle(
        [position[0] - bg_padding, position[1] - bg_padding,
         position[0] + text_width + bg_padding, position[1] + text_height + bg_padding],
        fill=bg_color
    )
    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def add_bottom_subtitle(frame, text, width, height, font_size=24):
    """在视频底部添加固定位置字幕（半透明背景）"""
    if not text:
        return frame
    
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = get_font(font_size)
    
    try:
        text_width, text_height = draw.textsize(text, font=font)
    except AttributeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    
    x_pos = (width - text_width) // 2
    y_pos = height - 70
    
    bg_padding_x = 25
    bg_padding_y = 10
    bg_alpha = 200
    
    draw.rectangle(
        [x_pos - bg_padding_x, y_pos - bg_padding_y,
         x_pos + text_width + bg_padding_x, y_pos + text_height + bg_padding_y],
        fill=(30, 30, 30, bg_alpha)
    )
    
    draw.text((x_pos, y_pos), text, font=font, fill=(255, 255, 255))
    
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def load_data(run_dir):
    dense_df = pd.read_csv(Path(run_dir) / "records" / "entity_timeline_dense.csv")
    tasks_df = pd.read_csv(Path(run_dir) / "records" / "tasks.csv")
    events_df = pd.read_csv(Path(run_dir) / "records" / "coordination_events.csv")
    
    import json
    with open(Path(run_dir) / "metrics.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)
    
    task_coords = {}
    for _, row in dense_df.iterrows():
        task_id = row['current_task_id']
        if pd.isna(task_id):
            continue
        task_id = int(task_id)
        if task_id not in task_coords:
            task_coords[task_id] = {'start_x': None, 'start_y': None, 'end_x': None, 'end_y': None}
        if task_coords[task_id]['start_x'] is None:
            task_coords[task_id]['start_x'] = row['x']
            task_coords[task_id]['start_y'] = row['y']
        task_coords[task_id]['end_x'] = row['x']
        task_coords[task_id]['end_y'] = row['y']
    
    return dense_df, tasks_df, events_df, metrics, task_coords


def build_state_cache(dense_df):
    state_cache = {}
    current_states = {}
    max_frame = dense_df['frame_id'].max()
    
    for frame_id in range(1, max_frame + 1):
        frame_data = dense_df[dense_df['frame_id'] == frame_id]
        for _, row in frame_data.iterrows():
            current_states[row['entity_id']] = row.to_dict()
        state_cache[frame_id] = current_states.copy()
    
    return state_cache, list(current_states.keys())


def build_events_by_step(events_df):
    events_by_step = {}
    for _, row in events_df.iterrows():
        step = row['step']
        if step not in events_by_step:
            events_by_step[step] = []
        events_by_step[step].append(row.to_dict())
    return events_by_step


def get_charging_events(events_df):
    """提取充电事件时间范围"""
    charging_events = []
    active_charging = {}
    
    for _, row in events_df.iterrows():
        event_type = row['event_type']
        uav_id = row['uav_id']
        
        if 'CHARGING_START' in event_type and not pd.isna(uav_id):
            active_charging[uav_id] = {'start_step': row['step'], 'agv_id': row['agv_id']}
        elif 'CHARGING_END' in event_type and uav_id in active_charging:
            charging_events.append({
                'uav_id': uav_id,
                'agv_id': active_charging[uav_id]['agv_id'],
                'start_step': active_charging[uav_id]['start_step'],
                'end_step': row['step']
            })
            del active_charging[uav_id]
    
    return charging_events


def get_event_subtitle(step, events_by_step, charging_events):
    if step in events_by_step:
        events = events_by_step[step]
        for event in events:
            event_type = event['event_type']
            uav_id = event['uav_id']
            agv_id = event['agv_id']
            
            if 'CHARGING_START' in event_type:
                return f"AGV{int(agv_id)} provides charging support for UAV{int(uav_id)}", 'charging'
            elif 'CHARGING_END' in event_type:
                return f"UAV{int(uav_id)} resumes delivery after AGV charging", 'charging_end'
            elif 'RELAY_FALLBACK' in event_type:
                return f"Task T{int(event.get('task_id', 0))} falls back to direct delivery", 'fallback'
            elif 'RELAY_REQUEST' in event_type:
                return f"UAV{int(uav_id)} requests relay support from AGV{int(agv_id)}", 'relay'
            elif 'AGV_MOVE_START' in event_type:
                return f"AGV{int(agv_id)} moves to support position", 'moving'
            elif 'AGV_ARRIVE' in event_type:
                return f"AGV{int(agv_id)} arrived at relay position", 'arrived'
            elif 'TASK_COMPLETE' in event_type:
                return f"Task T{int(event['task_id'])} completed", 'complete'
    
    for ce in charging_events:
        if ce['start_step'] <= step <= ce['end_step']:
            return f"UAV{int(ce['uav_id'])} is charging on AGV{int(ce['agv_id'])}...", 'charging_active'
    
    return None, None


def create_intro_frame(width, height):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (245, 245, 248)
    
    frame = put_text(frame, "UAV-AGV 协同绿色配送优化", 
                    (width//2 - 220, height//2 - 80), 36, (30, 60, 100))
    frame = put_text(frame, "无人机配送 + 无人车充电支撑", 
                    (width//2 - 180, height//2 - 20), 24, (80, 100, 140))
    frame = put_text(frame, "AGV 为 UAV 提供能源保障与中继支持", 
                    (width//2 - 200, height//2 + 40), 20, (100, 100, 120))
    
    cv2.circle(frame, (width//2 - 200, height//2 + 100), 20, (50, 150, 255), -1)
    cv2.circle(frame, (width//2 - 200, height//2 + 100), 24, (255, 255, 255), 3)
    frame = put_text(frame, "UAV", (width//2 - 175, height//2 + 105), 18, (30, 60, 120))
    
    cv2.rectangle(frame, (width//2 + 180 - 15, height//2 + 100 - 15), 
                  (width//2 + 180 + 15, height//2 + 100 + 15), (255, 140, 50), -1)
    cv2.rectangle(frame, (width//2 + 180 - 18, height//2 + 100 - 18), 
                  (width//2 + 180 + 18, height//2 + 100 + 18), (255, 255, 255), 3)
    frame = put_text(frame, "AGV", (width//2 + 200, height//2 + 105), 18, (120, 60, 30))
    
    # 连接线表示协同
    cv2.line(frame, (width//2 - 180, height//2 + 100), 
             (width//2 + 162, height//2 + 100), (100, 180, 100), 3)
    frame = put_text(frame, "Charging Support", (width//2 - 35, height//2 + 95), 16, (60, 120, 80))
    
    return frame


def create_legend_frame(width, height):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (245, 245, 248)
    
    frame = put_text(frame, "角色说明与图例", (width//2 - 100, 40), 32, (30, 60, 100))
    cv2.line(frame, (100, 80), (width - 100, 80), (200, 200, 210), 2)
    
    map_w = width - 320
    
    cv2.rectangle(frame, (50, 100), (map_w - 50, height - 100), (200, 200, 210), -1)
    cv2.rectangle(frame, (50, 100), (map_w - 50, height - 100), (100, 100, 120), 3)
    
    y = 130
    
    cv2.circle(frame, (80, y + 10), 12, (100, 180, 100), -1)
    cv2.circle(frame, (80, y + 10), 15, (60, 120, 60), 2)
    frame = put_text(frame, "Depot (配送中心)", (110, y), 18, (60, 100, 60))
    y += 40
    
    cv2.circle(frame, (80, y + 10), 10, (255, 100, 100), -1)
    cv2.circle(frame, (80, y + 10), 13, (200, 50, 50), 2)
    frame = put_text(frame, "Task Pickup (取货点)", (110, y), 18, (150, 50, 50))
    y += 40
    
    cv2.circle(frame, (80, y + 10), 10, (100, 200, 255), -1)
    cv2.circle(frame, (80, y + 10), 13, (50, 150, 200), 2)
    frame = put_text(frame, "Task Delivery (送货点)", (110, y), 18, (50, 100, 150))
    y += 40
    
    cv2.circle(frame, (80, y + 10), 14, (255, 200, 100), -1)
    cv2.circle(frame, (80, y + 10), 17, (200, 150, 50), 2)
    frame = put_text(frame, "Charging Link (AGV充电连接)", (110, y), 18, (150, 100, 50))
    y += 40
    
    cv2.circle(frame, (80, y + 10), 12, (50, 150, 255), -1)
    cv2.circle(frame, (80, y + 10), 15, (255, 255, 255), 3)
    frame = put_text(frame, "UAV (无人机 - 空中配送)", (110, y), 18, (30, 60, 120))
    y += 40
    
    cv2.rectangle(frame, (70, y), (90, y + 20), (255, 140, 50), -1)
    cv2.rectangle(frame, (67, y - 3), (93, y + 23), (255, 255, 255), 3)
    frame = put_text(frame, "AGV (无人车 - 地面支撑)", (110, y), 18, (120, 60, 30))
    y += 40
    
    cv2.line(frame, (70, y + 10), (90, y + 10), (50, 150, 255), 4)
    frame = put_text(frame, "UAV Trajectory", (110, y), 18, (30, 60, 120))
    y += 40
    
    cv2.line(frame, (70, y + 10), (90, y + 10), (50, 180, 100), 4)
    frame = put_text(frame, "AGV Trajectory", (110, y), 18, (50, 120, 80))
    y += 40
    
    cv2.line(frame, (70, y + 10), (90, y + 10), (100, 180, 100), 4, cv2.LINE_AA)
    frame = put_text(frame, "Charging Link", (110, y), 18, (60, 120, 80))
    y += 40
    
    panel_x = map_w + 20
    panel_y = 120
    
    frame = put_text(frame, "AGV 的核心作用", (panel_x, panel_y), 22, (30, 60, 100))
    panel_y += 30
    
    frame = put_text(frame, "⚡ 充电支撑", (panel_x, panel_y), 18, (100, 150, 200))
    frame = put_text(frame, "   为低电量 UAV 提供能源补给", (panel_x + 15, panel_y + 20), 16, (100, 100, 120))
    panel_y += 45
    
    frame = put_text(frame, "🔄 中继接驳", (panel_x, panel_y), 18, (100, 180, 100))
    frame = put_text(frame, "   延长配送距离，接力完成任务", (panel_x + 15, panel_y + 20), 16, (100, 100, 120))
    panel_y += 45
    
    frame = put_text(frame, "📦 地面运输", (panel_x, panel_y), 18, (255, 140, 50))
    frame = put_text(frame, "   支持货物在地面的中转运输", (panel_x + 15, panel_y + 20), 16, (100, 100, 120))
    
    return frame


def create_summary_frame(width, height, metrics, charging_events):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (245, 245, 248)
    
    frame = put_text(frame, "仿真结果总结", (width//2 - 120, 60), 36, (30, 60, 100))
    
    y = 140
    
    completed = metrics.get('completed_tasks', 0)
    total = metrics.get('total_tasks', 0)
    frame = put_text(frame, f"任务完成: {completed} / {total} ({metrics.get('completion_rate', 0) * 100:.1f}%)", 
                    (width//2 - 150, y), 24, (80, 100, 140))
    y += 35
    
    energy = metrics.get('total_energy', 0)
    frame = put_text(frame, f"总能耗: {energy:.1f} Wh", 
                    (width//2 - 80, y), 24, (80, 100, 140))
    y += 35
    
    cv2.line(frame, (width//2 - 250, y), (width//2 + 250, y), (200, 200, 210), 2)
    y += 20
    
    frame = put_text(frame, "AGV 支撑贡献", (width//2 - 100, y), 28, (30, 60, 100))
    y += 30
    
    charging_count = len(charging_events)
    frame = put_text(frame, f"⚡ 充电支撑次数: {charging_count}", 
                    (width//2 - 150, y), 22, (100, 150, 200))
    y += 28
    
    supported_uavs = len(set([ce['uav_id'] for ce in charging_events]))
    frame = put_text(frame, f"🔋 支持 UAV 数量: {supported_uavs}", 
                    (width//2 - 150, y), 22, (100, 150, 200))
    y += 28
    
    avg_charging_time = np.mean([ce['end_step'] - ce['start_step'] for ce in charging_events]) if charging_events else 0
    frame = put_text(frame, f"⏱️ 平均充电时长: {avg_charging_time:.1f} steps", 
                    (width//2 - 150, y), 22, (100, 150, 200))
    y += 40
    
    cv2.line(frame, (width//2 - 250, y), (width//2 + 250, y), (200, 200, 210), 2)
    y += 20
    
    frame = put_text(frame, "AGV 在协同配送中起到关键的能源保障作用", 
                    (width//2 - 220, y), 22, (100, 100, 120))
    
    return frame


def create_main_frame(state_cache, frame_idx, all_entities, task_coords, events_by_step, 
                      charging_events, width, height, map_size):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (245, 245, 248)
    
    map_margin = 50
    map_w = width - 320
    map_h = height - 150
    
    scale_x = (map_w - 2 * map_margin) / map_size
    scale_y = (map_h - 2 * map_margin) / map_size
    
    def scale_coords(x, y):
        sx = int(map_margin + x * scale_x)
        sy = int(map_margin + y * scale_y)
        return sx, sy
    
    cv2.rectangle(frame, (map_margin, map_margin), 
                  (map_w - map_margin, map_h - map_margin), 
                  (200, 200, 210), -1)
    
    grid_size = 50
    for x in range(0, map_size, grid_size):
        sx = int(map_margin + x * scale_x)
        cv2.line(frame, (sx, map_margin), (sx, map_h - map_margin), (220, 220, 225), 1)
    for y in range(0, map_size, grid_size):
        sy = int(map_margin + y * scale_y)
        cv2.line(frame, (map_margin, sy), (map_w - map_margin, sy), (220, 220, 225), 1)
    
    cv2.rectangle(frame, (map_margin, map_margin), 
                  (map_w - map_margin, map_h - map_margin), 
                  (100, 100, 120), 3)
    
    for task_id, coords in task_coords.items():
        if coords['start_x'] is not None:
            sx, sy = scale_coords(coords['start_x'], coords['start_y'])
            cv2.circle(frame, (sx, sy), 10, (255, 100, 100), -1)
            cv2.circle(frame, (sx, sy), 13, (200, 50, 50), 2)
            frame = put_text(frame, f"T{task_id}", (sx - 12, sy - 25), 12, (150, 50, 50))
        
        if coords['end_x'] is not None:
            sx, sy = scale_coords(coords['end_x'], coords['end_y'])
            cv2.circle(frame, (sx, sy), 10, (100, 200, 255), -1)
            cv2.circle(frame, (sx, sy), 13, (50, 150, 200), 2)
    
    depot_x, depot_y = scale_coords(100, 100)
    cv2.circle(frame, (depot_x, depot_y), 15, (100, 180, 100), -1)
    cv2.circle(frame, (depot_x, depot_y), 18, (60, 120, 60), 2)
    frame = put_text(frame, "Depot", (depot_x - 25, depot_y + 25), 14, (60, 100, 60))
    
    current_states = state_cache.get(frame_idx, {})
    
    step = next(iter(current_states.values()))['step'] if current_states else 0
    current_task_ids = []
    active_uavs = []
    active_agvs = []
    charging_uavs = []
    
    for entity_id, state in current_states.items():
        if entity_id.startswith('UAV'):
            if state.get('status') == 'busy':
                active_uavs.append(entity_id)
            if state.get('status') == 'charging':
                charging_uavs.append(entity_id)
            task_id = state.get('current_task_id')
            if task_id and not pd.isna(task_id):
                current_task_ids.append(int(task_id))
        else:
            if state.get('status') == 'moving':
                active_agvs.append(entity_id)
    
    # 获取充电中的 UAV 和 AGV 配对
    charging_pairs = []
    for ce in charging_events:
        if ce['start_step'] <= step <= ce['end_step']:
            uav_id = f"UAV_{int(ce['uav_id'])}"
            agv_id = f"AGV_{int(ce['agv_id'])}"
            if uav_id in current_states and agv_id in current_states:
                charging_pairs.append((uav_id, agv_id))
    
    # 事件聚焦：充电期间高亮
    has_charging = len(charging_pairs) > 0
    focus_center = None
    
    if has_charging:
        uav_state = current_states[charging_pairs[0][0]]
        focus_center = scale_coords(uav_state['x'], uav_state['y'])
    
    # 绘制半透明遮罩（聚焦效果）
    if has_charging and focus_center:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), (200, 200, 200), -1)
        cv2.circle(overlay, focus_center, 150, (255, 255, 255), -1)
        frame = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)
    
    # 绘制协同关系连线
    for uav_id, agv_id in charging_pairs:
        uav_state = current_states[uav_id]
        agv_state = current_states[agv_id]
        
        uav_x, uav_y = scale_coords(uav_state['x'], uav_state['y'])
        agv_x, agv_y = scale_coords(agv_state['x'], agv_state['y'])
        
        cv2.line(frame, (uav_x, uav_y), (agv_x, agv_y), (100, 200, 100), 4, cv2.LINE_AA)
        
        mid_x, mid_y = (uav_x + agv_x) // 2, (uav_y + agv_y) // 2 - 10
        frame = put_text_with_bg(frame, "CHARGING", (mid_x - 40, mid_y), 16, (255, 255, 255), (100, 180, 100))
    
    # 绘制实体
    entities_to_draw = []
    for entity_id in all_entities:
        state = current_states.get(entity_id)
        if state:
            entities_to_draw.append((entity_id, state))
    
    for entity_id, state in entities_to_draw:
        x, y = state['x'], state['y']
        status = state['status']
        sx, sy = scale_coords(x, y)
        
        is_charging = entity_id in [p[0] for p in charging_pairs] or entity_id in [p[1] for p in charging_pairs]
        
        if entity_id.startswith('UAV'):
            color = (50, 150, 255) if status != 'charging' else (255, 100, 100)
            
            cv2.circle(frame, (sx, sy), 16, color, -1)
            cv2.circle(frame, (sx, sy), 20, (255, 255, 255), 3)
            
            if is_charging:
                cv2.circle(frame, (sx, sy), 28, (100, 200, 100), 3)
                cv2.circle(frame, (sx, sy), 35, (100, 200, 100), 2)
            
            uav_id = entity_id.replace('UAV_', '')
            label = f"U{uav_id}"
            if status == 'charging':
                label += " (Charging)"
            frame = put_text(frame, label, (sx + 25, sy - 10), 16, (30, 60, 120))
        
        else:
            color = (255, 140, 50)
            
            agv_size = 22
            cv2.rectangle(frame, (sx - agv_size, sy - agv_size), 
                          (sx + agv_size, sy + agv_size), color, -1)
            cv2.rectangle(frame, (sx - agv_size - 3, sy - agv_size - 3), 
                          (sx + agv_size + 3, sy + agv_size + 3), (255, 255, 255), 4)
            
            if is_charging:
                cv2.rectangle(frame, (sx - agv_size - 10, sy - agv_size - 10), 
                              (sx + agv_size + 10, sy + agv_size + 10), (100, 200, 100), 3)
            
            agv_id = entity_id.replace('AGV_', '')
            label = f"AGV{agv_id}"
            if is_charging:
                label += " (Charging Support)"
            elif status == 'moving':
                label += " (Moving)"
            else:
                label += " (Standby)"
            frame = put_text(frame, label, (sx + agv_size + 12, sy + 5), 14, (120, 60, 30))
    
    # 事件字幕
    event_subtitle, event_type = get_event_subtitle(step, events_by_step, charging_events)
    if event_subtitle:
        if event_type == 'charging' or event_type == 'charging_active':
            frame = put_text_with_bg(frame, event_subtitle, (width//2 - 180, 10), 24, (255, 255, 255), (100, 150, 100))
        else:
            frame = put_text_with_bg(frame, event_subtitle, (width//2 - 180, 10), 24, (255, 255, 255), (30, 60, 100))
    
    # 右侧面板
    panel_x = map_w + 20
    panel_y = 100
    frame = put_text(frame, "实时状态", (panel_x, panel_y), 20, (30, 60, 100))
    y_offset = panel_y + 30
    
    frame = put_text(frame, f"Step: {step}", (panel_x, y_offset), 16, (60, 60, 80))
    y_offset += 25
    
    frame = put_text(frame, "当前任务", (panel_x, y_offset), 16, (30, 60, 100))
    y_offset += 15
    for task_id in current_task_ids[:3]:
        frame = put_text(frame, f"T{task_id}", (panel_x, y_offset), 16, (50, 150, 255))
        y_offset += 20
    
    y_offset += 10
    frame = put_text(frame, "实体状态", (panel_x, y_offset), 16, (30, 60, 100))
    y_offset += 15
    
    for entity_id, state in entities_to_draw:
        status = state['status']
        battery = state['battery']
        color = (50, 150, 255) if entity_id.startswith('UAV') else (255, 140, 50)
        text = f"{entity_id}: {status} | {battery:.0f}%"
        frame = put_text(frame, text, (panel_x, y_offset), 14, color)
        y_offset += 20
    
    y_offset += 10
    frame = put_text(frame, "充电状态", (panel_x, y_offset), 16, (30, 60, 100))
    y_offset += 15
    if has_charging:
        for uav_id, agv_id in charging_pairs:
            frame = put_text(frame, f"{uav_id} ← {agv_id}", (panel_x, y_offset), 14, (100, 180, 100))
            y_offset += 20
    else:
        frame = put_text(frame, "No charging", (panel_x, y_offset), 14, (150, 150, 150))
    
    progress = frame_idx / max(state_cache.keys()) if state_cache else 0
    progress_width = int((map_w - 100) * progress)
    cv2.rectangle(frame, (50, height - 45), (map_w - 50, height - 25), (220, 220, 225), -1)
    cv2.rectangle(frame, (50, height - 45), (50 + progress_width, height - 25), (50, 150, 255), -1)
    cv2.rectangle(frame, (50, height - 45), (map_w - 50, height - 25), (150, 150, 170), 2)
    
    if event_subtitle:
        frame = add_bottom_subtitle(frame, event_subtitle, width, height)
    
    return frame


def generate_video(args):
    print("加载数据...")
    dense_df, tasks_df, events_df, metrics, task_coords = load_data(args.run_dir)
    
    print("构建状态缓存...")
    state_cache, all_entities = build_state_cache(dense_df)
    events_by_step = build_events_by_step(events_df)
    charging_events = get_charging_events(events_df)
    
    print(f"  - 充电事件: {len(charging_events)} 次")
    for ce in charging_events:
        print(f"    * UAV{int(ce['uav_id'])}: Step {ce['start_step']}-{ce['end_step']} (AGV{int(ce['agv_id'])})")
    
    max_frame = dense_df['frame_id'].max()
    
    intro_frames = int(args.fps * 4)
    legend_frames = int(args.fps * 4)
    main_frames = int(args.fps * 16)
    summary_frames = int(args.fps * 6)
    
    total_frames = intro_frames + legend_frames + main_frames + summary_frames
    print(f"生成视频: {total_frames} 帧, 约 {total_frames/args.fps:.1f} 秒")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(args.output, fourcc, args.fps, (args.width, args.height))
    
    print("生成片头...")
    intro_frame = create_intro_frame(args.width, args.height)
    for _ in range(intro_frames):
        out.write(intro_frame)
    
    print("生成图例页...")
    legend_frame = create_legend_frame(args.width, args.height)
    for _ in range(legend_frames):
        out.write(legend_frame)
    
    print("生成主过程动画...")
    frame_indices = np.linspace(1, max_frame, main_frames, dtype=int)
    
    for i, frame_idx in enumerate(frame_indices):
        frame = create_main_frame(state_cache, frame_idx, all_entities, task_coords, 
                                  events_by_step, charging_events,
                                  args.width, args.height, args.map_size)
        out.write(frame)
        if (i + 1) % 50 == 0:
            print(f"  进度: {i + 1}/{len(frame_indices)}")
    
    print("生成结果总结...")
    summary_frame = create_summary_frame(args.width, args.height, metrics, charging_events)
    for _ in range(summary_frames):
        out.write(summary_frame)
    
    out.release()
    print(f"视频生成完成: {args.output}")
    print(f"  - 总帧数: {total_frames}")
    print(f"  - 时长: {total_frames/args.fps:.1f} 秒")


def main():
    args = parse_args()
    generate_video(args)


if __name__ == "__main__":
    main()