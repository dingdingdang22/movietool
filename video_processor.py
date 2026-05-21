import subprocess
import logging
import sys
import os
from typing import List

class VideoProcessor:
    """
    视频处理模块 (Video Processor / FFmpeg Wrapper)
    负责执行实际的视频物理裁剪与拼接操作。
    封装所有的 FFmpeg 底层命令。
    """

    @staticmethod
    def get_ffmpeg_path() -> str:
        """获取 ffmpeg 可执行文件的路径，兼容 PyInstaller 打包后的路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，寻找解压后的临时目录中的 ffmpeg.exe
            return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
        else:
            # 开发环境下，默认使用系统环境变量中的 ffmpeg
            return 'ffmpeg'

    @staticmethod
    def run_ffmpeg(command: List[str]) -> subprocess.CompletedProcess:
        """
        任务 3.1: 封装基础 FFmpeg 调用命令 (subprocess.run)。
        
        :param command: FFmpeg 命令参数列表 (如 ['ffmpeg', '-i', ...])
        :return: CompletedProcess 对象，包含执行状态和输出流信息
        """
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            error_msg = f"FFmpeg 执行失败 (退出码: {result.returncode})!\n执行命令: {' '.join(command)}\n错误信息:\n{result.stderr}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
            
        return result

    @classmethod
    def cut_video_segment(cls, input_path: str, start_sec: float, end_sec: float, output_path: str, compress: bool = False) -> subprocess.CompletedProcess:
        """
        任务 3.2: 实现单段视频的高速流拷贝裁剪。
        任务 3.6: 增加 compress 参数支持，转码为 720p 并且启用 Web 优化。
        利用 FFmpeg 的快速定位机制和 stream copy 实现无损极速裁剪。
        
        :param input_path: 原始视频路径
        :param start_sec: 截取起始时间 (秒)
        :param end_sec: 截取结束时间 (秒)
        :param output_path: 输出视频片段的路径
        :param compress: 是否开启转码压缩和网络串流优化
        """
        command = [
            cls.get_ffmpeg_path(),
            '-y',                  # 强制覆盖同名输出文件
            '-ss', str(start_sec), # 起始时间
            '-to', str(end_sec),   # 结束时间
            '-i', input_path       # 输入文件
        ]
        if compress:
            command.extend([
                '-vf', 'scale=-2:720',      # 等比例缩放，高度限制为 720p (宽度自动适配偶数)
                '-c:v', 'libx264',          # 视频使用 H.264 编码
                '-crf', '28',               # 提高 CRF 值 (23->28)，数值越大体积越小，28是低码率较高画质的甜点值
                '-preset', 'slow',          # 使用 slow 预设，用稍长的编码时间换取更小的文件体积
                '-c:a', 'aac',              # 音频使用 AAC 编码
                '-b:a', '96k',              # 降低音频码率到 96k (人声对话场景完全足够)
                '-movflags', '+faststart'   # Web 串流优化，便于边下边播
            ])
        else:
            command.extend(['-c', 'copy'])  # 音视频流直接拷贝，免重新编码
            
        command.append(output_path)
        return cls.run_ffmpeg(command)

    @classmethod
    def concat_video_segments(cls, segment_paths: List[str], concat_txt_path: str, output_path: str, compress: bool = False) -> subprocess.CompletedProcess:
        """
        任务 3.3: 实现同一集中多个零碎保留片段的无缝拼接。
        任务 3.6: 增加 compress 参数，拼接时若开启压缩则追加 Web 优化标志。
        使用 FFmpeg 的 concat demuxer 将多个物理片段快速拼接成一个完整的视频文件。
        
        :param segment_paths: 待拼接的视频片段路径列表
        :param concat_txt_path: 临时生成的 concat.txt 文件路径
        :param output_path: 最终输出的合并视频路径
        """
        # 生成 FFmpeg 要求的 concat 文本文件格式 (如: file 'segment1.mp4')
        with open(concat_txt_path, 'w', encoding='utf-8') as f:
            for path in segment_paths:
                # 转换为绝对路径，避免 FFmpeg 根据 concat.txt 所在目录进行错误的相对路径拼接
                abs_path = os.path.abspath(path)
                # 将 Windows 的反斜杠转换为正斜杠，防止 FFmpeg 解析路径时发生转义错误
                safe_path = abs_path.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
                
        command = [
            cls.get_ffmpeg_path(),
            '-y',                  # 强制覆盖同名输出文件
            '-f', 'concat',        # 指定使用 concat 分离器
            '-safe', '0',          # 允许使用绝对路径
            '-i', concat_txt_path, # 输入为生成的 txt 列表文件
            '-c', 'copy'           # 音视频流直接拷贝，免重新编码
        ]
        if compress:
            command.extend(['-movflags', '+faststart'])
            
        command.append(output_path)
        
        return cls.run_ffmpeg(command)