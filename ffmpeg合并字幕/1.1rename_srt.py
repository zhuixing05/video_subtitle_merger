import os

# 提示用户输入文件夹路径
folder_path = input("请输入要修改的文件夹路径：").strip()

# 检查文件夹路径是否存在
if not os.path.exists(folder_path):
    print(f"错误：文件夹 {folder_path} 不存在！")
    input("按回车键退出...")
    exit(1)

# 递归遍历文件夹及其子目录
for root, _, files in os.walk(folder_path):
    for filename in files:
        # 检查文件是否是srt格式
        if filename.lower().endswith('.srt'):
            # 构建旧文件的完整路径
            old_file_path = os.path.join(root, filename)
            
            # 创建新的文件名，移除“.ja_2”
            new_filename = filename.replace('.ja_2', '')
            
            # 构建新文件的完整路径
            new_file_path = os.path.join(root, new_filename)
            
            # 检查目标文件名是否已存在
            if os.path.exists(new_file_path):
                print(f"警告：{new_filename} 已存在，跳过 {old_file_path}")
                continue
            
            # 重命名文件
            try:
                os.rename(old_file_path, new_file_path)
                print(f"已将 {old_file_path} 重命名为 {new_filename}")
            except Exception as e:
                print(f"错误：无法重命名 {old_file_path}，原因：{e}")

print("批量重命名完成！")
# 添加手动退出确认
input("按回车键退出...")