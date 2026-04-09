#!/usr/bin/env python3
"""
移除文件中的 BOM 字符
"""

import os
import re


def remove_bom(file_path):
    """移除文件中的 BOM 字符
    
    Args:
        file_path: 文件路径
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 移除 BOM 字符
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            with open(file_path, 'wb') as f:
                f.write(content)
            print(f"已移除 {file_path} 中的 BOM 字符")
        else:
            print(f"{file_path} 中没有 BOM 字符")
    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")


def main():
    """主函数"""
    # 遍历所有 Python 文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                remove_bom(file_path)


if __name__ == "__main__":
    main()