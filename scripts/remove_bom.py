#!/usr/bin/env python3
"""
移除文件中的 BOM 字符，支持移除连续开头的多个 BOM
"""

import os


def remove_bom(file_path):
    """移除文件开头的所有连续 BOM 字符
    
    Args:
        file_path: 文件路径
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 移除所有连续的 BOM 字符
        bom_count = 0
        bom_bytes = b'\xef\xbb\xbf'
        while content.startswith(bom_bytes):
            content = content[3:]
            bom_count += 1
        
        if bom_count > 0:
            with open(file_path, 'wb') as f:
                f.write(content)
            print(f"已移除 {file_path} 中的 {bom_count} 个 BOM 字符")
        # else:
        #     print(f"{file_path} 中没有 BOM 字符")
    except Exception as e:
        print(f"处理 {file_path} 时出错: {e}")


def main():
    """主函数"""
    # 需要跳过的目录
    skip_dirs = {'.git', '.venv', 'results/runs_backup_20260428'}
    
    # 支持的文件扩展名
    supported_extensions = {'.py', '.yaml', '.yml', '.md', '.txt'}
    
    for root, dirs, files in os.walk('.'):
        # 移除需要跳过的目录
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        
        for file in files:
            # 检查文件扩展名
            _, ext = os.path.splitext(file)
            if ext.lower() in supported_extensions:
                file_path = os.path.join(root, file)
                remove_bom(file_path)


if __name__ == "__main__":
    main()