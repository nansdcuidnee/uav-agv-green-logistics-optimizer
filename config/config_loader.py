"""配置加载模块"""
import os
import yaml


def deep_merge(base, override):
    """深合并两个字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
    
    Returns:
        dict: 合并后的字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def normalize_config(config):
    """规范化配置格式
    
    Args:
        config: 原始配置
    
    Returns:
        dict: 规范化后的配置
    """
    # 规范化 map_size
    if 'map_size' in config:
        map_size = config['map_size']
        if isinstance(map_size, list) and len(map_size) == 2:
            # 转换旧格式 [width, height] 为新格式 {width: ..., height: ...}
            config['map_size'] = {
                'width': map_size[0],
                'height': map_size[1]
            }
            print("[DEPRECATED] map_size 使用了旧格式 [width, height]，已自动转换为新格式")
    
    # 规范化 time_window
    if 'time_window' in config:
        time_window = config['time_window']
        if isinstance(time_window, dict):
            if 'size' in time_window and 'min' not in time_window and 'max' not in time_window:
                # 转换旧格式 {size: ...} 为新格式 {min: 0, max: ...}
                config['time_window'] = {
                    'min': 0,
                    'max': time_window['size']
                }
                print("[DEPRECATED] time_window 使用了旧格式 {size: ...}，已自动转换为新格式")
    
    # 规范化 no_fly_zones
    if 'num_no_fly_zones' in config:
        # 转换旧格式 num_no_fly_zones 为新格式 no_fly_zones.count
        if 'no_fly_zones' not in config:
            config['no_fly_zones'] = {
                'count': config['num_no_fly_zones']
            }
            print("[DEPRECATED] 使用了旧字段 num_no_fly_zones，已自动转换为新格式 no_fly_zones.count")
    elif 'no_fly_zones' in config and isinstance(config['no_fly_zones'], dict) and 'count' in config['no_fly_zones']:
        # 为了向后兼容，添加旧字段
        config['num_no_fly_zones'] = config['no_fly_zones']['count']
        print("[DEPRECATED] 为了向后兼容，添加了旧字段 num_no_fly_zones")
    
    return config


def load_config(config_path, visited=None, path_stack=None):
    """加载场景配置文件，支持继承
    
    Args:
        config_path: 配置文件路径
        visited: 已访问的配置文件路径，用于检测循环继承
        path_stack: 配置文件路径栈，用于显示循环继承链路
    
    Returns:
        dict: 配置信息
    """
    if visited is None:
        visited = set()
    if path_stack is None:
        path_stack = []
    
    # 规范化路径
    config_path = os.path.abspath(config_path)
    
    # 检测循环继承
    if config_path in visited:
        # 构建循环继承链路
        cycle_path = path_stack + [os.path.basename(config_path)]
        cycle_str = ' -> '.join(cycle_path)
        raise ValueError(f"循环继承检测到: {cycle_str}")
    
    # 添加到已访问集合和路径栈
    visited.add(config_path)
    path_stack.append(os.path.basename(config_path))
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        # 尝试旧路径兼容
        old_path = os.path.join(os.path.dirname(config_path), os.path.basename(config_path))
        if os.path.exists(old_path):
            print(f"[DEPRECATED] 配置文件路径已变更，使用旧路径: {old_path}")
            config_path = old_path
        else:
            # 尝试其他可能的路径
            possible_paths = [
                os.path.join('configs', 'base', os.path.basename(config_path)),
                os.path.join('configs', 'generated', os.path.basename(config_path)),
                os.path.join('configs', 'explicit', os.path.basename(config_path)),
                os.path.join('configs', 'experiments', os.path.basename(config_path)),
                os.path.join('configs', 'tests', os.path.basename(config_path))
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"[DEPRECATED] 配置文件路径已变更，使用新路径: {path}")
                    config_path = path
                    break
            else:
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    # 加载当前配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 处理继承
    if 'extends' in config:
        extends_path = config['extends']
        # 构建继承文件的完整路径
        extends_full_path = os.path.join(os.path.dirname(config_path), extends_path)
        # 递归加载父配置
        parent_config = load_config(extends_full_path, visited.copy(), path_stack.copy())
        # 深合并配置（子配置覆盖父配置）
        config = deep_merge(parent_config, config)
        # 移除 extends 字段
        del config['extends']
    
    # 规范化配置格式
    config = normalize_config(config)
    
    # 从路径栈中移除当前文件
    path_stack.pop()
    
    return config
