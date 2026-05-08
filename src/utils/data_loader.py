#!/usr/bin/env python3
"""数据加载器模块"""
import os
from pathlib import Path
import yaml
import json
import logging
from functools import lru_cache
from typing import Optional, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 合法的数据类别列表
VALID_CATEGORIES = {
    'maps',           # 地图数据
    'scenarios',      # 场景配置
    'constants',      # 常量参数
    'templates',      # 模板文件
    'raw',            # 原始数据
    'processed'       # 处理后数据
}

# 文件内容缓存，使用LRU策略
# 缓存大小限制为100，避免内存占用过大
_file_content_cache: Dict[str, Any] = {}
_CACHE_MAX_SIZE = 100


def _add_to_cache(key: str, data: Any) -> None:
    """添加数据到缓存
    
    Args:
        key: 缓存键（文件绝对路径）
        data: 缓存数据
    """
    # 如果缓存已满，移除最早的10%条目
    if len(_file_content_cache) >= _CACHE_MAX_SIZE:
        # 获取最早访问的键（字典在Python 3.7+保持插入顺序）
        oldest_keys = list(_file_content_cache.keys())[:int(_CACHE_MAX_SIZE * 0.1)]
        for k in oldest_keys:
            del _file_content_cache[k]
            logger.debug(f"缓存淘汰: {k}")
    
    _file_content_cache[key] = data
    logger.debug(f"缓存添加: {key}")


def _get_from_cache(key: str) -> Optional[Any]:
    """从缓存获取数据
    
    Args:
        key: 缓存键（文件绝对路径）
    
    Returns:
        Optional[Any]: 缓存的数据，如果不存在返回None
    """
    return _file_content_cache.get(key)


def _clear_cache() -> None:
    """清空缓存"""
    _file_content_cache.clear()
    logger.info("数据加载缓存已清空")


def get_data_root() -> Path:
    """获取数据根目录
    
    Returns:
        Path: 数据根目录路径
    """
    current_dir = Path(__file__).resolve().parent.parent.parent
    data_root = current_dir / "data"
    
    # 验证数据根目录存在
    if not data_root.exists():
        raise FileNotFoundError(f"数据根目录不存在: {data_root}")
    if not data_root.is_dir():
        raise NotADirectoryError(f"数据根目录路径不是目录: {data_root}")
    
    return data_root


def resolve_data_path(category: str, filename: str) -> Path:
    """解析数据文件路径
    
    Args:
        category: 数据类别（maps、scenarios、constants、templates、raw、processed）
        filename: 文件名
    
    Returns:
        Path: 数据文件的完整路径
    
    Raises:
        ValueError: 如果类别不合法
        FileNotFoundError: 如果文件不存在
    """
    # 校验类别参数
    if not isinstance(category, str):
        raise ValueError(f"类别参数必须是字符串类型，当前类型: {type(category)}")
    
    category = category.strip()
    if not category:
        raise ValueError("类别参数不能为空")
    
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"不合法的数据类别: '{category}'。"
            f"合法类别包括: {', '.join(sorted(VALID_CATEGORIES))}"
        )
    
    # 校验文件名
    if not isinstance(filename, str):
        raise ValueError(f"文件名必须是字符串类型，当前类型: {type(filename)}")
    
    filename = filename.strip()
    if not filename:
        raise ValueError("文件名不能为空")
    
    # 安全检查：防止路径遍历攻击
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValueError(f"文件名包含非法字符: {filename}")
    
    data_root = get_data_root()
    file_path = data_root / category / filename
    
    if not file_path.exists():
        # 尝试查找带扩展名的文件
        for ext in ['.yaml', '.yml', '.json']:
            alt_path = file_path.with_suffix(ext)
            if alt_path.exists():
                logger.warning(f"文件 {file_path} 不存在，使用替代路径: {alt_path}")
                return alt_path
        
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if not file_path.is_file():
        raise FileNotFoundError(f"路径不是文件: {file_path}")
    
    return file_path


def load_yaml(path_or_category, filename=None) -> dict:
    """加载 YAML 文件（带缓存）
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是 YAML 格式或参数错误
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        if not isinstance(path_or_category, (str, Path)):
            raise ValueError(f"路径参数必须是字符串或Path对象，当前类型: {type(path_or_category)}")
        
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not file_path.is_file():
            raise FileNotFoundError(f"路径不是文件: {file_path}")
    
    # 检查文件扩展名
    if file_path.suffix not in ['.yaml', '.yml']:
        raise ValueError(f"不支持的文件格式: {file_path.suffix}，仅支持 .yaml 和 .yml")
    
    # 获取文件绝对路径作为缓存键
    abs_path = str(file_path.resolve())
    
    # 检查缓存
    cached_data = _get_from_cache(abs_path)
    if cached_data is not None:
        logger.debug(f"命中缓存: {abs_path}")
        return cached_data.copy() if isinstance(cached_data, dict) else cached_data
    
    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data is None:
            logger.warning(f"YAML 文件为空: {file_path}")
            data = {}
        
        # 添加到缓存
        _add_to_cache(abs_path, data)
        
        return data.copy() if isinstance(data, dict) else data
    
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析错误: {e}")
    except Exception as e:
        raise RuntimeError(f"读取文件失败: {file_path}, 错误: {e}")


def load_json(path_or_category, filename=None) -> dict:
    """加载 JSON 文件（带缓存）
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是 JSON 格式或参数错误
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        if not isinstance(path_or_category, (str, Path)):
            raise ValueError(f"路径参数必须是字符串或Path对象，当前类型: {type(path_or_category)}")
        
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not file_path.is_file():
            raise FileNotFoundError(f"路径不是文件: {file_path}")
    
    # 检查文件扩展名
    if file_path.suffix != '.json':
        raise ValueError(f"不支持的文件格式: {file_path.suffix}，仅支持 .json")
    
    # 获取文件绝对路径作为缓存键
    abs_path = str(file_path.resolve())
    
    # 检查缓存
    cached_data = _get_from_cache(abs_path)
    if cached_data is not None:
        logger.debug(f"命中缓存: {abs_path}")
        return cached_data.copy() if isinstance(cached_data, dict) else cached_data
    
    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 添加到缓存
        _add_to_cache(abs_path, data)
        
        return data.copy() if isinstance(data, dict) else data
    
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析错误: {e}")
    except Exception as e:
        raise RuntimeError(f"读取文件失败: {file_path}, 错误: {e}")


def load_data(path_or_category, filename=None) -> dict:
    """自动按扩展名选择加载 YAML 或 JSON 文件（带缓存）
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件格式不支持或参数错误
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        if not isinstance(path_or_category, (str, Path)):
            raise ValueError(f"路径参数必须是字符串或Path对象，当前类型: {type(path_or_category)}")
        
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not file_path.is_file():
            raise FileNotFoundError(f"路径不是文件: {file_path}")
    
    suffix = file_path.suffix.lower()
    if suffix in ['.yaml', '.yml']:
        return load_yaml(file_path)
    elif suffix == '.json':
        return load_json(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 .yaml、.yml 和 .json")