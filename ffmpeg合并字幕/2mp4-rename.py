import os
import re
import sys
import csv

# 确保支持日语（UTF-8编码）
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 罗马数字到阿拉伯数字的映射
roman_to_arabic = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
}

# 中文大写数字到阿拉伯数字的映射
chinese_to_arabic_map = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
}

def chinese_to_arabic(chinese):
    """将中文大写数字转换为阿拉伯数字，支持十以上"""
    try:
        if not chinese:
            return None
        if chinese in chinese_to_arabic_map:
            return chinese_to_arabic_map[chinese]
        
        # 处理“十一”到“十九”
        if chinese.startswith('十') and len(chinese) == 2:
            unit = chinese_to_arabic_map.get(chinese[1], 0)
            return 10 + unit
        # 处理“二十”及以上
        if '十' in chinese:
            parts = chinese.split('十')
            tens = chinese_to_arabic_map.get(parts[0], 1) if parts[0] else 1
            units = chinese_to_arabic_map.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return tens * 10 + units
        return None
    except Exception as e:
        print(f"转换中文数字 {chinese} 时出错：{e}")
        return None

def convert_to_arabic(number):
    """将罗马数字或中文大写数字转换为阿拉伯数字"""
    try:
        if number.upper() in roman_to_arabic:
            return str(roman_to_arabic[number.upper()])
        if number in chinese_to_arabic_map or '十' in number:
            result = chinese_to_arabic(number)
            return str(result) if result is not None else None
        return number  # 如果是阿拉伯数字，直接返回
    except Exception as e:
        print(f"转换数字 {number} 时出错：{e}")
        return None

def get_next_available_number(prefix, folder_path, used_numbers):
    """获取下一个可用的序号，确保不与现有 .mp4 文件冲突"""
    number = 1
    while True:
        if number not in used_numbers:
            new_mp4_path = os.path.join(folder_path, f"{prefix}{number}.mp4")
            if not os.path.exists(new_mp4_path):
                return number
        number += 1

def save_rename_log(folder_path, old_name, new_name):
    """保存重命名日志到文件"""
    log_file = os.path.join(folder_path, "rename_log.txt")
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([folder_path, old_name, new_name])
        print(f"已记录重命名日志：{old_name} -> {new_name}")
    except Exception as e:
        print(f"保存重命名日志失败：{e}")

def restore_original_names(folder_path):
    """根据日志文件恢复原始文件名"""
    log_file = os.path.join(folder_path, "rename_log.txt")
    if not os.path.exists(log_file):
        print(f"错误：在 {folder_path} 中未找到重命名日志文件，无法恢复")
        return

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) != 3:
                    print(f"跳过无效日志记录：{row}")
                    continue
                _, old_name, new_name = row
                old_path = os.path.join(folder_path, old_name)
                new_path = os.path.join(folder_path, new_name)
                if os.path.exists(new_path):
                    os.rename(new_path, old_path)
                    print(f"已将 {new_path} 恢复为 {old_name}")
                else:
                    print(f"错误：文件 {new_path} 不存在，无法恢复")
        print(f"目录 {folder_path} 的文件已恢复")
    except Exception as e:
        print(f"恢复目录 {folder_path} 时出错：{e}")

def extract_number(filename):
    """从文件名中提取序号，优先匹配 第X話、最终話、中文数字等，并删除第之前的字符"""
    try:
        # 优先匹配 第X話（忽略“第”之前的字符）
        match_episode = re.search(r'.*第(\d+)話', filename)
        if match_episode:
            return int(match_episode.group(1)), f"第{match_episode.group(1)}話"
        
        # 匹配 第X（忽略“第”之前的字符）
        match_di = re.search(r'.*第(\d+)', filename)
        if match_di:
            return int(match_di.group(1)), f"第{match_di.group(1)}"
        
        # 处理 最終話，标记为特殊值，稍后分配最高序号
        if '最終話' in filename:
            return float('inf'), "最終話"  # 使用 inf 确保最终話排在最后
        
        # 匹配中文数字+話（如 第一話、十一話）
        match_chinese_episode = re.search(r'.*([一二三四五六七八九十]+)話', filename)
        if match_chinese_episode:
            number = chinese_to_arabic(match_chinese_episode.group(1))
            if number:
                return int(number), f"中文数字 {match_chinese_episode.group(1)}話"
        
        # 匹配 R{数字}
        match_r_number = re.search(r'R(\d+)', filename, re.IGNORECASE)
        if match_r_number:
            return int(match_r_number.group(1)), f"R{match_r_number.group(1)}"
        
        # 匹配普通阿拉伯数字
        match_number = re.search(r'(\d+)', filename)
        if match_number:
            return int(match_number.group(1)), f"阿拉伯数字 {match_number.group(1)}"
        
        # 匹配罗马数字
        match_roman = re.search(r'[IVXLCDM]+', filename, re.IGNORECASE)
        if match_roman:
            number = convert_to_arabic(match_roman.group())
            if number:
                return int(number), f"罗马数字 {match_roman.group()}"
        
        # 匹配中文数字（单独）
        match_chinese = re.search(r'[一二三四五六七八九十]+', filename)
        if match_chinese:
            number = chinese_to_arabic(match_chinese.group())
            if number:
                return int(number), f"中文数字 {match_chinese.group()}"
        
        return None, "无有效序号"
    except Exception as e:
        print(f"处理文件 {filename} 时出错：{e}")
        return None, "错误"

def process_directory(folder_path, new_prefix):
    """处理单个目录中的 .mp4 文件"""
    try:
        # 收集所有 .mp4 文件
        files = os.listdir(folder_path)
        mp4_files = [f for f in files if f.lower().endswith('.mp4')]

        # 检测已存在的目标文件名中的序号
        used_numbers = set()
        for filename in files:
            match = re.match(rf"{re.escape(new_prefix)}(\d+)\.mp4", filename, re.IGNORECASE)
            if match:
                used_numbers.add(int(match.group(1)))
            match_r = re.match(rf"R{re.escape(new_prefix)}(\d+)\.mp4", filename, re.IGNORECASE)
            if match_r:
                used_numbers.add(int(match_r.group(1)))

        # 提取所有文件的序号
        file_numbers = []
        all_arabic = True
        for filename in mp4_files:
            if re.match(rf"({re.escape(new_prefix)}|R{re.escape(new_prefix)})\d+\.mp4", filename, re.IGNORECASE):
                print(f"跳过已符合目标格式的文件：{os.path.join(folder_path, filename)}")
                continue
            number, source = extract_number(filename)
            if number is None:
                all_arabic = False
                print(f"警告：在 {folder_path} 中，{filename} {source}，跳过")
                continue
            file_numbers.append((filename, number))
            print(f"文件 {filename}：检测到 {source}，提取序号 {number}")

        # 按序号排序，确保最終話在最后
        file_numbers.sort(key=lambda x: x[1])

        # 重命名文件
        for filename, original_number in file_numbers:
            try:
                new_number = get_next_available_number(new_prefix, folder_path, used_numbers)
                used_numbers.add(new_number)
                new_basename = f"{new_prefix}{new_number}"
                old_path = os.path.join(folder_path, filename)
                ext = 'mp4'
                new_path = os.path.join(folder_path, f"{new_basename}.{ext}")
                os.rename(old_path, new_path)
                print(f"已将 {old_path} 重命名为 {new_basename}.{ext}")
                save_rename_log(folder_path, filename, f"{new_basename}.{ext}")
            except Exception as e:
                print(f"错误：无法重命名 {old_path}，原因：{e}")
                continue
    except Exception as e:
        print(f"处理目录 {folder_path} 时出错：{e}")

# 主程序
try:
    print("选择操作模式：")
    print("1. 重命名文件")
    print("2. 恢复原始文件名")
    mode = input("请输入模式（1 或 2）：").strip()
    
    if mode not in ['1', '2']:
        print("错误：无效的模式选择！")
        input("按回车键退出...")
        sys.exit(1)

    root_folder = input("请输入要修改的根文件夹路径：").strip()
    if not os.path.exists(root_folder):
        print(f"错误：根文件夹 {root_folder} 不存在！")
        input("按回车键退出...")
        sys.exit(1)

    if mode == '1':
        for dirpath, dirnames, _ in os.walk(root_folder):
            files = os.listdir(dirpath)
            if any(f.lower().endswith('.mp4') for f in files):
                try:
                    print(f"\n发现子目录：{dirpath}")
                    new_prefix = input(f"请输入 {dirpath} 的新文件名前缀（直接按回车跳过）：").strip()
                    if not new_prefix:
                        print(f"跳过子目录 {dirpath} 的处理")
                        continue
                    process_directory(dirpath, new_prefix)
                except Exception as e:
                    print(f"处理子目录 {dirpath} 时出错：{e}")
                    continue
    elif mode == '2':
        for dirpath, dirnames, _ in os.walk(root_folder):
            if os.path.exists(os.path.join(dirpath, "rename_log.txt")):
                try:
                    print(f"\n发现日志文件，恢复目录：{dirpath}")
                    restore_original_names(dirpath)
                except Exception as e:
                    print(f"恢复子目录 {dirpath} 时出错：{e}")
                    continue

    print("\n操作完成！")
    input("按回车键退出...")
except Exception as e:
    print(f"程序运行出错：{e}")
    input("按回车键退出...")
    sys.exit(1)