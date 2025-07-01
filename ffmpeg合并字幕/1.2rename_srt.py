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
chinese_to_arabic = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
}

def convert_to_arabic(number):
    """将罗马数字或中文大写数字转换为阿拉伯数字"""
    try:
        if number.upper() in roman_to_arabic:
            return str(roman_to_arabic[number.upper()])
        if number in chinese_to_arabic:
            return str(chinese_to_arabic[number])
        return number  # 如果是阿拉伯数字，直接返回
    except Exception as e:
        print(f"转换数字 {number} 时出错：{e}")
        return None

def get_next_available_number(prefix, folder_path, used_numbers):
    """获取下一个可用的序号"""
    number = 1
    while True:
        if number not in used_numbers:
            new_srt_path = os.path.join(folder_path, f"{prefix}{number}.srt")
            if not os.path.exists(new_srt_path):
                return number
        number += 1

def save_rename_log(folder_path, old_name, new_name):
    """保存重命名日志到文件"""
    log_file = os.path.join(folder_path, "rename_log_srt.txt")
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([folder_path, old_name, new_name])
        print(f"已记录重命名日志：{old_name} -> {new_name}")
    except Exception as e:
        print(f"保存重命名日志失败：{e}")

def restore_original_names(folder_path):
    """根据日志文件恢复原始文件名"""
    log_file = os.path.join(folder_path, "rename_log_srt.txt")
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
        # 删除日志文件（可选，建议保留以便多次恢复）
        # os.remove(log_file)
        print(f"目录 {folder_path} 的文件已恢复")
    except Exception as e:
        print(f"恢复目录 {folder_path} 时出错：{e}")

def process_directory(folder_path, new_prefix):
    """处理单个目录中的srt文件"""
    try:
        # 收集所有srt文件
        files = os.listdir(folder_path)
        srt_files = [f for f in files if f.lower().endswith('.srt')]

        # 检测已存在的目标文件名中的序号
        used_numbers = set()
        for filename in files:
            match = re.match(rf"{re.escape(new_prefix)}(\d+)\.srt", filename, re.IGNORECASE)
            if match:
                used_numbers.add(int(match.group(1)))
            match_r = re.match(rf"R{re.escape(new_prefix)}(\d+)\.srt", filename, re.IGNORECASE)
            if match_r:
                used_numbers.add(int(match_r.group(1)))

        # 检查是否所有文件都包含顺序的阿拉伯数字（优先匹配“第X話”或“第X”）
        all_arabic = True
        arabic_numbers = []
        for filename in srt_files:
            if re.match(rf"({re.escape(new_prefix)}|R{re.escape(new_prefix)})\d+\.srt", filename, re.IGNORECASE):
                print(f"跳过已符合目标格式的文件：{os.path.join(folder_path, filename)}")
                continue
            # 优先匹配“第X話”或“第X”
            match_episode = re.search(r'第(\d+)話', filename)
            if match_episode:
                number = int(match_episode.group(1))
                arabic_numbers.append((filename, number))
                print(f"文件 {filename}：检测到 第{number}話，提取序号 {number}")
                continue
            match_di = re.search(r'第(\d+)', filename)
            if match_di:
                number = int(match_di.group(1))
                arabic_numbers.append((filename, number))
                print(f"文件 {filename}：检测到 第{number}，提取序号 {number}")
                continue
            # 其他数字提取方式
            match_number = re.search(r'(\d+)', filename)
            if match_number:
                number = int(match_number.group(1))
                arabic_numbers.append((filename, number))
                print(f"文件 {filename}：检测到阿拉伯数字 {number}")
            else:
                all_arabic = False
                print(f"文件 {filename}：未检测到阿拉伯数字，退出阿拉伯数字优先模式")
                break

        # 如果所有文件都包含阿拉伯数字，按数字排序并重命名
        if all_arabic and arabic_numbers:
            arabic_numbers.sort(key=lambda x: x[1])
            for srt_filename, original_number in arabic_numbers:
                try:
                    new_number = get_next_available_number(new_prefix, folder_path, used_numbers)
                    used_numbers.add(new_number)
                    new_basename = f"{new_prefix}{new_number}"
                    old_srt_path = os.path.join(folder_path, srt_filename)
                    new_srt_path = os.path.join(folder_path, f"{new_basename}.srt")
                    os.rename(old_srt_path, new_srt_path)
                    print(f"已将 {old_srt_path} 重命名为 {new_basename}.srt")
                    save_rename_log(folder_path, srt_filename, f"{new_basename}.srt")
                except Exception as e:
                    print(f"错误：无法重命名 {old_srt_path}，原因：{e}")
                    continue
            return

        # 如果不全包含阿拉伯数字，回退到原逻辑
        file_numbers = []
        max_number = 0
        for filename in srt_files:
            try:
                if re.match(rf"({re.escape(new_prefix)}|R{re.escape(new_prefix)})\d+\.srt", filename, re.IGNORECASE):
                    print(f"跳过已符合目标格式的文件：{os.path.join(folder_path, filename)}")
                    continue
                match_episode = re.search(r'第(\d+)話', filename)
                if match_episode:
                    number = int(match_episode.group(1))
                    file_numbers.append((filename, number))
                    max_number = max(max_number, number)
                    print(f"文件 {filename}：清理为 第{number}，提取序号 {number}")
                    continue
                match_di = re.search(r'第(\d+)', filename)
                if match_di:
                    number = int(match_di.group(1))
                    file_numbers.append((filename, number))
                    max_number = max(max_number, number)
                    print(f"文件 {filename}：清理为 第{number}，提取序号 {number}")
                    continue
                if '最終話' in filename:
                    number = max_number + 1
                    file_numbers.append((filename, number))
                    max_number = max(max_number, number)
                    print(f"文件 {filename}：识别为最終話，分配序号 {number}")
                    continue
                match_r_number = re.search(r'R(\d+)', filename, re.IGNORECASE)
                if match_r_number:
                    number = int(match_r_number.group(1))
                    file_numbers.append((filename, number))
                    max_number = max(max_number, number)
                    print(f"文件 {filename}：提取序号 {number}")
                    continue
                match_number = re.search(r'(\d+)', filename)
                if match_number:
                    number = int(match_number.group(1))
                    file_numbers.append((filename, number))
                    max_number = max(max_number, number)
                    print(f"文件 {filename}：提取序号 {number}")
                    continue
                match_roman = re.search(r'[IVXLCDM]+', filename, re.IGNORECASE)
                if match_roman:
                    number = convert_to_arabic(match_roman.group())
                    if number:
                        number = int(number)
                        file_numbers.append((filename, number))
                        max_number = max(max_number, number)
                        print(f"文件 {filename}：提取罗马数字 {match_roman.group()}，转换为序号 {number}")
                    continue
                match_chinese = re.search(r'[一二三四五六七八九十]+', filename)
                if match_chinese:
                    number = convert_to_arabic(match_chinese.group())
                    if number:
                        number = int(number)
                        file_numbers.append((filename, number))
                        max_number = max(max_number, number)
                        print(f"文件 {filename}：提取中文数字 {match_chinese.group()}，转换为序号 {number}")
                    continue
                print(f"警告：在 {folder_path} 中，{filename} 未找到数字、罗马数字、中文数字或第X話，跳过")
            except Exception as e:
                print(f"处理文件 {os.path.join(folder_path, filename)} 时出错：{e}")
                continue

        file_numbers.sort(key=lambda x: x[1])
        for srt_filename, original_number in file_numbers:
            try:
                new_number = get_next_available_number(new_prefix, folder_path, used_numbers)
                used_numbers.add(new_number)
                new_basename = f"{new_prefix}{new_number}"
                old_srt_path = os.path.join(folder_path, srt_filename)
                new_srt_path = os.path.join(folder_path, f"{new_basename}.srt")
                os.rename(old_srt_path, new_srt_path)
                print(f"已将 {old_srt_path} 重命名为 {new_basename}.srt")
                save_rename_log(folder_path, srt_filename, f"{new_basename}.srt")
            except Exception as e:
                print(f"错误：无法重命名 {old_srt_path}，原因：{e}")
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
            if srt_files := [f for f in os.listdir(dirpath) if f.lower().endswith('.srt')]:
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
            if os.path.exists(os.path.join(dirpath, "rename_log_srt.txt")):
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