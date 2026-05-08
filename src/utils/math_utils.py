import math

# ==================== 精度配置常量 ====================
EPSILON = 1e-9                    # 浮点数比较容差
COORDINATE_PRECISION = 1          # 坐标精度（保留1位小数）
DISTANCE_EPSILON = 1e-6           # 距离比较容差


def is_close(a: float, b: float, epsilon: float = EPSILON) -> bool:
    """判断两个浮点数是否相等（带容差）"""
    return abs(a - b) < epsilon


def is_close_points(point1, point2, epsilon: float = DISTANCE_EPSILON) -> bool:
    """判断两个点是否在距离容差范围内相等"""
    distance = calculate_distance(point1, point2)
    return distance < epsilon


def round_coordinate(coord: float) -> float:
    """按照统一精度舍入坐标值"""
    return round(coord, COORDINATE_PRECISION)


def round_point(point) -> tuple:
    """按照统一精度舍入点坐标"""
    return (round_coordinate(point[0]), round_coordinate(point[1]))


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