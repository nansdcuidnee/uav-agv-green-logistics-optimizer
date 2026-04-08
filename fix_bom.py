#!/usr/bin/env python3
"""修复文件中的 BOM 字符"""
import codecs

# 修复 run_experiment.py 文件
def fix_bom(file_path):
    try:
        # 读取文件，自动检测并去除 BOM
        with codecs.open(file_path, 'r', 'utf-8-sig') as f:
            content = f.read()
        
        # 重新写入文件，使用无 BOM 的 UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"已修复 {file_path} 中的 BOM 字符")
    except Exception as e:
        print(f"修复 {file_path} 时出错: {e}")

if __name__ == "__main__":
    # 修复目标文件
    fix_bom("experiments/run_experiment.py")
