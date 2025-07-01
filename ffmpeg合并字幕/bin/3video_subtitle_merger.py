import os
from pathlib import Path
import subprocess
import logging
from datetime import datetime
import sys
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# 配置日志
def setup_logging(directory):
    """配置日志，输出到控制台和文件"""
    log_filename = f"embed_subtitles_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = Path(directory) / log_filename
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # 设置为 DEBUG 以记录更多信息
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger, log_path

def find_matching_files(directory):
    """查找目录及其子目录中匹配的 SRT 和 MP4 文件对"""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"目录 {directory} 不存在")

    srt_files = list(directory.rglob("*.srt"))
    mp4_files = list(directory.rglob("*.mp4"))
    
    pairs = []
    for srt in srt_files:
        srt_name = srt.stem
        for mp4 in mp4_files:
            mp4_name = mp4.stem
            if srt_name == mp4_name and srt.parent == mp4.parent:
                pairs.append((mp4, srt))
                break
        else:
            logger.warning(f"未找到与 {srt} 匹配的 MP4 文件")
    
    return pairs

def get_video_duration(video_path):
    """获取视频时长（秒）"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"获取 {video_path.name} 时长失败: {str(e)}")
        return None

def detect_nvenc_support(logger):
    """检测系统是否支持 NVIDIA NVENC 编码器"""
    try:
        cmd = ["ffmpeg", "-encoders"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if "h264_nvenc" in result.stdout:
            logger.info("检测到 NVIDIA NVENC 支持，将优先使用 GPU 加速")
            return True
        else:
            logger.warning("未检测到 NVIDIA NVENC 支持，将使用 libx264 (CPU 编码)")
            return False
    except Exception as e:
        logger.warning(f"检测 NVENC 支持失败: {str(e)}，将使用 libx264 (CPU 编码)")
        return False

def embed_subtitles(video_path, subtitle_path, output_path, logger, use_nvenc):
    """使用 PowerShell 调用 FFmpeg 将 SRT 字幕嵌入 MP4 视频，显示进度，支持 GPU 加速，失败回退 CPU"""
    try:
        # 获取视频总时长
        duration = get_video_duration(video_path)
        if duration is None:
            duration = 1  # 避免除零

        # FFmpeg 命令路径转义
        video_path_escaped = str(video_path).replace('"', '\\"')
        subtitle_path_escaped = str(subtitle_path).replace('"', '\\"').replace('\\', '\\\\').replace(':', '\\:')
        output_path_escaped = str(output_path).replace('"', '\\"')

        # 尝试 NVENC 编码（如果启用）
        if use_nvenc:
            ffmpeg_cmd = (
                f'ffmpeg -i "{video_path_escaped}" '
                f'-vf "subtitles=\'{subtitle_path_escaped}\':force_style=\'FontName=Arial,FontSize=16,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=40,BackColour=&H00000000\'" '
                f'-c:v h264_nvenc -preset p7 -rc vbr -b:v 1M -c:a copy -y "{output_path_escaped}"'
            )
            encoder_desc = "GPU (h264_nvenc)"
            logger.debug(f"尝试 NVENC 编码命令: {ffmpeg_cmd}")

            # 运行 NVENC 命令
            powershell_cmd = ["powershell", "-Command", ffmpeg_cmd]
            process = subprocess.Popen(
                powershell_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stderr_lines = []
            with tqdm(total=100, desc=f"处理 {video_path.name} ({encoder_desc})", unit="%", position=0, leave=True) as pbar:
                time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
                last_progress = 0
                
                for line in process.stderr:
                    stderr_lines.append(line)
                    match = time_pattern.search(line)
                    if match:
                        hours, minutes, seconds, centiseconds = map(int, match.groups())
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        progress = (current_time / duration) * 100 if duration > 0 else 0
                        progress = min(progress, 100)
                        pbar.update(progress - last_progress)
                        last_progress = progress
                
                process.wait()
            
            if process.returncode == 0:
                logger.info(f"成功处理: {output_path} ({encoder_desc})")
            else:
                logger.warning(f"NVENC 编码失败: {video_path.name}\nFFmpeg 返回码: {process.returncode}\nFFmpeg 错误输出:\n{''.join(stderr_lines)}")
                logger.info(f"回退到 CPU 编码 (libx264) 处理 {video_path.name}")
                use_nvenc = False  # 切换到 CPU 编码

        # 如果 NVENC 未启用或失败，使用 CPU 编码
        if not use_nvenc:
            ffmpeg_cmd = (
                f'ffmpeg -i "{video_path_escaped}" '
                f'-vf "subtitles=\'{subtitle_path_escaped}\':force_style=\'FontName=Arial,FontSize=16,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=40,BackColour=&H00000000\'" '
                f'-c:v libx264 -preset medium -crf 23 -c:a copy -y "{output_path_escaped}"'
            )
            encoder_desc = "CPU (libx264)"
            logger.debug(f"执行 CPU 编码命令: {ffmpeg_cmd}")

            # 运行 CPU 编码命令
            powershell_cmd = ["powershell", "-Command", ffmpeg_cmd]
            process = subprocess.Popen(
                powershell_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            stderr_lines = []
            with tqdm(total=100, desc=f"处理 {video_path.name} ({encoder_desc})", unit="%", position=0, leave=True) as pbar:
                time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
                last_progress = 0
                
                for line in process.stderr:
                    stderr_lines.append(line)
                    match = time_pattern.search(line)
                    if match:
                        hours, minutes, seconds, centiseconds = map(int, match.groups())
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        progress = (current_time / duration) * 100 if duration > 0 else 0
                        progress = min(progress, 100)
                        pbar.update(progress - last_progress)
                        last_progress = progress
                
                process.wait()
            
            if process.returncode != 0:
                logger.error(f"CPU 编码失败: {video_path.name} ({encoder_desc})\nFFmpeg 返回码: {process.returncode}\nFFmpeg 错误输出:\n{''.join(stderr_lines)}")
                return
            logger.info(f"成功处理: {output_path} ({encoder_desc})")

        # 删除原始文件
        try:
            video_path.unlink()
            logger.info(f"删除原始文件: {video_path}")
        except Exception as e:
            logger.error(f"删除 {video_path} 失败: {str(e)}")
        try:
            subtitle_path.unlink()
            logger.info(f"删除原始文件: {subtitle_path}")
        except Exception as e:
            logger.error(f"删除 {subtitle_path} 失败: {str(e)}")
        
        # 重命名输出文件，去掉 'R' 前缀
        final_path = output_path.parent / output_path.name[1:]
        try:
            output_path.rename(final_path)
            logger.info(f"重命名 {output_path} 为 {final_path}")
        except Exception as e:
            logger.error(f"重命名 {output_path} 失败: {str(e)}")
    
    except Exception as e:
        logger.error(f"处理 {video_path.name} 时出错: {str(e)}")

def main():
    """主函数：处理目录及其子目录中的所有匹配文件"""
    global logger
    log_path = None
    
    try:
        # 获取目录
        if len(sys.argv) > 1:
            target_directory = sys.argv[1]
        else:
            target_directory = input("请输入要处理的目录路径: ").strip()
        
        # 验证目录
        target_directory = Path(target_directory).resolve()
        if not target_directory.is_dir():
            raise ValueError(f"目录 {target_directory} 不存在")
        
        # 确保在 Windows 环境下
        if os.name != 'nt':
            raise OSError("此脚本仅支持 Windows 环境")
        
        # 初始化日志
        logger, log_path = setup_logging(target_directory)
        logger.info(f"开始处理目录: {target_directory}")
        
        # 检测 NVENC 支持
        use_nvenc = detect_nvenc_support(logger)
        
        pairs = find_matching_files(target_directory)
        if not pairs:
            logger.warning("未找到任何匹配的 SRT 和 MP4 文件对")
            return

        # 使用线程池处理
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [
                executor.submit(embed_subtitles, video_path, subtitle_path, video_path.parent / f"R{video_path.name}", logger, use_nvenc)
                for video_path, subtitle_path in pairs
            ]
            # 等待所有任务完成
            for future in futures:
                future.result()
            
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
    finally:
        logger.info("处理完成")
        # 关闭日志处理器
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        # 删除日志文件
        if log_path and log_path.exists():
            try:
                log_path.unlink()
                logger.info(f"删除日志文件: {log_path.name}")
            except Exception as e:
                logger.error(f"删除日志文件 {log_path.name} 失败: {str(e)}")

if __name__ == "__main__":
    main()