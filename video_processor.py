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
    def get_english_audio_track_index(cls, input_path: str) -> int:
        """
        运行 ffmpeg -i 获取媒体信息，解析并寻找英文(eng/english)音轨。
        返回音频轨的 0-based 索引（例如第一个音轨返回 0，第二个返回 1）。
        如果没找到英文音轨，默认返回 0。如果没有音轨，返回 -1。
        """
        import re
        try:
            cmd = [cls.get_ffmpeg_path(), '-i', input_path]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stderr
            
            audio_streams = []
            current_stream = None
            audio_counter = 0
            
            for line in output.splitlines():
                if 'Stream #0:' in line and 'Audio:' in line:
                    current_stream = {
                        'index': audio_counter,
                        'raw_line': line,
                        'metadata': []
                    }
                    audio_streams.append(current_stream)
                    audio_counter += 1
                elif current_stream is not None:
                    if 'Stream #0:' in line:
                        current_stream = None
                    else:
                        current_stream['metadata'].append(line)
            
            if not audio_streams:
                return -1
                
            for stream in audio_streams:
                if re.search(r'\((eng|english)\)', stream['raw_line'], re.IGNORECASE):
                    return stream['index']
                for meta in stream['metadata']:
                    if re.search(r'(language|title)\s*:\s*(eng|english|英文)', meta, re.IGNORECASE):
                        return stream['index']
                        
            return 0
        except Exception as e:
            logging.error(f"解析音轨失败: {e}，默认使用第一轨")
            return 0

    @classmethod
    def download_model(cls, url: str, dest_path: str):
        """下载模型并显示进度"""
        import urllib.request
        print(f"[*] 正在从 {url} 下载 AI 模型...")
        
        def reporthook(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = min(100.0, read_so_far * 100 / total_size)
                if block_num % 1000 == 0:
                    sys.stdout.write(f"\r下载进度: {percent:.1f}% ({read_so_far / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB)")
                    sys.stdout.flush()
            else:
                sys.stdout.write(f"\r已下载: {read_so_far / (1024*1024):.1f}MB")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, dest_path, reporthook)
        print("\n[+] 模型下载完成！")

    @classmethod
    def ensure_sherpa_onnx_installed(cls):
        """检查并确保 sherpa-onnx 和 soundfile 安装成功"""
        try:
            import sherpa_onnx
            import soundfile
        except ImportError:
            print("[*] 检测到未安装 AI 人声分离依赖包 (sherpa-onnx, soundfile)，正在尝试自动安装...")
            import subprocess
            import sys
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "sherpa-onnx", "soundfile"],
                    check=True
                )
                print("[+] AI 依赖包自动安装成功！")
            except Exception as e:
                logging.error(f"自动安装依赖包失败: {e}。请手动运行 pip install sherpa-onnx soundfile")
                raise RuntimeError(f"缺失 AI 依赖包且自动安装失败，详情: {e}")

    @classmethod
    def run_ai_vocal_separation(cls, wav_path: str, output_dir: str) -> str:
        """
        使用 sherpa-onnx 与 UVR_MDXNET_9482 模型分离人声，
        返回生成的纯伴奏（Instrumental）WAV 文件的绝对路径。
        """
        cls.ensure_sherpa_onnx_installed()
        import sherpa_onnx
        import soundfile as sf
        import numpy as np

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_dir = os.path.join(app_dir, 'models')
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)

        model_name = 'UVR_MDXNET_9482.onnx'
        model_path = os.path.join(model_dir, model_name)
        
        if not os.path.exists(model_path):
            url = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/source-separation-models/{model_name}"
            print(f"[!] 未检测到 AI 模型 {model_name}，准备自动从网络下载...")
            print("如果下载速度过慢或失败，您可以手动下载该文件并放入以下目录：")
            print(f"目录: {model_dir}")
            print(f"下载链接: {url}")
            try:
                cls.download_model(url, model_path)
            except Exception as e:
                if os.path.exists(model_path):
                    try: os.remove(model_path)
                    except: pass
                raise RuntimeError(f"自动下载模型失败: {e}。请根据上方提示手动下载并放置模型文件后再试。")

        print("[*] 正在载入 AI 人声分离模型...")
        config = sherpa_onnx.OfflineSourceSeparationConfig(
            model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                    model=model_path,
                ),
                num_threads=4,
                debug=False,
                provider="cpu",
            )
        )
        if not config.validate():
            raise ValueError("AI 配置文件校验失败，请检查模型文件是否完好。")

        separator = sherpa_onnx.OfflineSourceSeparation(config)

        samples, sample_rate = sf.read(wav_path, dtype="float32", always_2d=True)
        samples = np.transpose(samples)
        samples = np.ascontiguousarray(samples)

        print("[*] 正在通过 AI 提取背景伴奏音轨（基于 CPU 运算，这可能需要 1~2 分钟，请稍候）...")
        output = separator.process(sample_rate=sample_rate, samples=samples)

        non_vocals = output.stems[1].data
        non_vocals = np.transpose(non_vocals)

        part_name = os.path.splitext(os.path.basename(wav_path))[0]
        temp_inst_path = os.path.join(output_dir, f".temp_inst_{part_name}.wav")
        
        sf.write(temp_inst_path, non_vocals, samplerate=output.sample_rate)
        
        return temp_inst_path

    @classmethod
    def cut_video_segment(cls, input_path: str, start_sec: float, end_sec: float, output_path: str, compress: bool = True) -> subprocess.CompletedProcess:
        """
        实现单段视频的高速裁剪，并生成 AI 消音双音轨。
        1. 寻找英文音轨；
        2. 裁剪原声英文视频为临时文件；
        3. 提取原声英文音轨为 WAV 文件；
        4. 调用 AI (UVR-MDX-NET) 分离伴奏；
        5. 合并原声与 AI 伴奏，生成双音轨视频（720p 默认压缩）。
        
        :param input_path: 原始视频路径
        :param start_sec: 截取起始时间 (秒)
        :param end_sec: 截取结束时间 (秒)
        :param output_path: 输出视频片段的路径
        :param compress: 是否开启转码压缩和网络串流优化
        """
        eng_idx = cls.get_english_audio_track_index(input_path)
        
        output_dir = os.path.dirname(os.path.abspath(output_path))
        part_name = os.path.splitext(os.path.basename(output_path))[0]
        
        # 定义临时文件路径
        temp_video_path = os.path.join(output_dir, f".temp_vid_{part_name}.mp4")
        temp_eng_wav = os.path.join(output_dir, f".temp_eng_{part_name}.wav")
        temp_inst_wav = None

        try:
            # 1. 裁剪视频并转码（保留原声英文音轨）
            cmd_cut = [
                cls.get_ffmpeg_path(),
                '-y',
                '-ss', str(start_sec),
                '-to', str(end_sec),
                '-i', input_path
            ]
            if eng_idx >= 0:
                cmd_cut.extend(['-map', '0:v:0', '-map', f'0:a:{eng_idx}'])
            else:
                cmd_cut.extend(['-map', '0:v:0'])

            if compress:
                cmd_cut.extend([
                    '-vf', 'scale=-2:720',
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-crf', '28',
                    '-preset', 'slow',
                ])
                if eng_idx >= 0:
                    cmd_cut.extend([
                        '-c:a', 'aac',
                        '-ac', '2',
                        '-b:a', '96k'
                    ])
            else:
                if eng_idx >= 0:
                    cmd_cut.extend(['-c:v', 'copy', '-c:a', 'copy'])
                else:
                    cmd_cut.extend(['-c:v', 'copy'])
            
            cmd_cut.append(temp_video_path)
            cls.run_ffmpeg(cmd_cut)

            # 如果没有音频轨，直接重命名并返回
            if eng_idx < 0:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_video_path, output_path)
                return subprocess.CompletedProcess(cmd_cut, 0)

            # 2. 提取原声英文轨为无损 WAV，准备 AI 分离
            cmd_ext = [
                cls.get_ffmpeg_path(),
                '-y',
                '-ss', str(start_sec),
                '-to', str(end_sec),
                '-i', input_path,
                '-map', f'0:a:{eng_idx}',
                '-c:a', 'pcm_s16le',
                '-ac', '2',
                temp_eng_wav
            ]
            cls.run_ffmpeg(cmd_ext)

            # 3. 运行 AI 分离获取伴奏 WAV
            temp_inst_wav = cls.run_ai_vocal_separation(temp_eng_wav, output_dir)

            # 4. 双音轨封装
            cmd_merge = [
                cls.get_ffmpeg_path(),
                '-y',
                '-i', temp_video_path,
                '-i', temp_inst_wav,
                '-map', '0:v:0',
                '-map', '0:a:0',
                '-map', '1:a:0',
                '-c:v', 'copy',
                '-c:a:0', 'copy',
                '-c:a:1', 'aac',
                '-ac:1', '2',
                '-b:a:1', '96k',
                '-metadata:s:a:0', 'title=English',
                '-metadata:s:a:1', 'title=Accompaniment'
            ]
            if compress:
                cmd_merge.extend(['-movflags', '+faststart'])
                
            cmd_merge.append(output_path)
            result = cls.run_ffmpeg(cmd_merge)
            return result

        finally:
            # 5. 清理所有临时文件
            for path in [temp_video_path, temp_eng_wav]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError as e:
                    logging.warning(f"清理临时文件失败: {path}, 原因: {e}")
            if temp_inst_wav and os.path.exists(temp_inst_wav):
                try:
                    os.remove(temp_inst_wav)
                except OSError:
                    pass

    @classmethod
    def concat_video_segments(cls, segment_paths: List[str], concat_txt_path: str, output_path: str, compress: bool = False) -> subprocess.CompletedProcess:
        """
        任务 3.3: 实现同一集中多个零碎保留片段的无缝拼接。
        任务 3.6: 增加 compress 参数，拼接时若开启压缩则追加 Web 优化标志，保障合并后视频依然支持 faststart 边下边播。
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
            '-map', '0',           # 显式映射所有流，保留切片中的双音轨
            '-c', 'copy'           # 音视频流直接拷贝，免重新编码
        ]
        if compress:
            command.extend(['-movflags', '+faststart'])
            
        command.append(output_path)
        
        return cls.run_ffmpeg(command)

    @classmethod
    def fix_audio_compatibility(cls, input_path: str, output_path: str) -> subprocess.CompletedProcess:
        """
        新增：修复已处理视频的音频格式兼容性。
        原样拷贝视频流（极速），强制将音频流重新编码为 AAC，并加入 faststart 优化以支持 iPhone/Safari 播放。
        
        :param input_path: 原始视频路径
        :param output_path: 修复后视频的临时输出路径
        """
        command = [
            cls.get_ffmpeg_path(),
            '-y',
            '-i', input_path,
            '-c:v', 'copy',             # 视频流直接拷贝，免去耗时的重编码
            '-c:a', 'aac',              # 强制音频使用 AAC 编码以满足 iOS Safari 要求
            '-ac', '2',                 # 强制双声道立体声，避免 5.1 等多声道导致 AAC 编码报错
            '-b:a', '96k',              # 锁定音频码率
            '-movflags', '+faststart',  # 启用 Web 边下边播串流优化
            output_path
        ]
        return cls.run_ffmpeg(command)