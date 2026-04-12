#!/usr/bin/env python3
"""数据加载器模块"""
import os
from pathlib import Path
import yaml
import json


def get_data_root() -> Path:
    """获取数据根目录
    
    Returns:
        Path: 数据根目录路径
    """
    # 从项目根目录开始查找 data 目录
    current_dir = Path(__file__).resolve().parent.parent.parent
    data_root = current_dir / "data"
    return data_root


def resolve_data_path(category: str, filename: str) -> Path:
    """解析数据文件路径
    
    Args:
        category: 数据类别（maps、scenarios、constants、templates、raw、processed）
        filename: 文件名
    
    Returns:
        Path: 数据文件的完整路径
    
    Raises:
        FileNotFoundError: 如果文件不存在
    """
    data_root = get_data_root()
    file_path = data_root / category / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    return file_path


def load_yaml(path_or_category, filename=None) -> dict:
    """加载 YAML 文件
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是 YAML 格式
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if file_path.suffix not in ['.yaml', '.yml']:
        raise ValueError(f"不支持的文件格式: {file_path.suffix}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析错误: {e}")


def load_json(path_or_category, filename=None) -> dict:
    """加载 JSON 文件
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是 JSON 格式
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if file_path.suffix != '.json':
        raise ValueError(f"不支持的文件格式: {file_path.suffix}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析错误: {e}")


def load_data(path_or_category, filename=None) -> dict:
    """自动按扩展名选择加载 YAML 或 JSON 文件
    
    Args:
        path_or_category: 文件路径或数据类别
        filename: 文件名（当 path_or_category 是类别时需要）
    
    Returns:
        dict: 加载的数据
    
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件格式不支持
    """
    if filename is not None:
        # 如果提供了类别和文件名
        file_path = resolve_data_path(path_or_category, filename)
    else:
        # 如果直接提供了文件路径
        file_path = Path(path_or_category)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
    
    suffix = file_path.suffix
    if suffix in ['.yaml', '.yml']:
        return load_yaml(file_path)
    elif suffix == '.json':
        return load_json(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")
