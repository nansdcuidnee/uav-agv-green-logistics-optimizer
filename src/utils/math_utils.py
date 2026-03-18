import math


def calculate_distance(point1, point2):
    """计算两点之间的欧几里得距离
    
    Args:
        point1: 第一个点 (x, y)
        point2: 第二个点 (x, y)
        
    Returns:
        float: 两点之间的距离
    """
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


def generate_random_point(map_size):
    """生成地图内的随机点
    
    Args:
        map_size: 地图尺寸 (width, height)
        
    Returns:
        tuple: 随机点 (x, y)
    """
    import random
    return (random.uniform(0, map_size[0]), random.uniform(0, map_size[1]))


def calculate_angle(point1, point2):
    """计算两点之间的角度
    
    Args:
        point1: 第一个点 (x, y)
        point2: 第二个点 (x, y)
        
    Returns:
        float: 角度（弧度）
    """
    return math.atan2(point2[1] - point1[1], point2[0] - point1[0])


def normalize_angle(angle):
    """归一化角度到 [0, 2π)
    
    Args:
        angle: 角度（弧度）
        
    Returns:
        float: 归一化后的角度
    """
    return angle % (2 * math.pi)