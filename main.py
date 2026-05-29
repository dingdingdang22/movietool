import os
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import argparse
from dataclasses import dataclass
from timeline_analyzer import TimelineAnalyzer
from subtitle_reconstructor import SubtitleReconstructor
from video_processor import VideoProcessor

@dataclass
class AppConfig:
    """全局配置参数数据类"""
    video_path: str
    subtitle_path: str
    output_dir: str
    subtitle_path2: str = ""
    silence_threshold_sec: float = 30.0
    min_segment_minutes: float = 5.0
    max_segment_minutes: float = 10.0
    compress: bool = False

class MainController:
    """
    核心调度模块 (Main Controller)
    负责加载配置项、初始化各模块，并按流水线顺序调度它们。
    """
    def __init__(self, config: AppConfig):
        self.config = config
        
        # 动态调整输出目录：在指定的输出目录下追加以视频文件名命名的子文件夹
        base_name = os.path.splitext(os.path.basename(self.config.video_path))[0]
        self.config.output_dir = os.path.join(self.config.output_dir, base_name)
        
        # 前置准备：确保输出目录存在
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)
            
    def run(self):
        """执行具体的流水线调度逻辑"""
        print(">>> 启动电影字幕智能分割流水线...")
        
        # 任务 4.2: 实例化 Phase 1，获取完整的切割方案
        print(f"[*] 正在分析英文字幕时间轴 (Phase 1): {self.config.subtitle_path}")
        analyzer = TimelineAnalyzer(
            subtitle_path=self.config.subtitle_path,
            silence_threshold=self.config.silence_threshold_sec,
            min_minutes=self.config.min_segment_minutes,
            max_minutes=self.config.max_segment_minutes
        )
        self.split_plans = analyzer.generate_split_plans()
        print(f"[+] 时间轴分析完毕，共规划出 {len(self.split_plans)} 个视频分集。")

        secondary_dialogues = []
        if self.config.subtitle_path2:
            print(f"[*] 正在读取中文字幕文件: {self.config.subtitle_path2}")
            secondary_dialogues = TimelineAnalyzer.parse_subtitles(self.config.subtitle_path2)

        # 任务 4.3: 循环遍历切割方案，调度 Phase 2 生成字幕，调度 Phase 3 生成视频
        # 任务 4.4: 增加终端 UI 反馈，打印运行进度等监控日志。
        base_name = os.path.splitext(os.path.basename(self.config.video_path))[0]
        
        for i, plan in enumerate(self.split_plans, start=1):
            part_name = f"{base_name}_Part{i:02d}"
            print(f"\n[{i}/{len(self.split_plans)}] 正在处理分集: {part_name}")
            
            # 1. 调度 Phase 2: 生成该集字幕
            print(f"    -> [Phase 2] 正在重构并导出字幕...")
            if self.config.subtitle_path2:
                srt_output_path1 = os.path.join(self.config.output_dir, f"{part_name}_en.srt")
                srt_output_path2 = os.path.join(self.config.output_dir, f"{part_name}_zh.srt")
                episode_dialogues = SubtitleReconstructor.generate_zero_baselined_subtitles(analyzer.dialogues, plan)
                SubtitleReconstructor.export_to_srt(episode_dialogues, srt_output_path1)
                episode_dialogues2 = SubtitleReconstructor.generate_zero_baselined_subtitles(secondary_dialogues, plan)
                SubtitleReconstructor.export_to_srt(episode_dialogues2, srt_output_path2)
            else:
                srt_output_path = os.path.join(self.config.output_dir, f"{part_name}.srt")
                episode_dialogues = SubtitleReconstructor.generate_zero_baselined_subtitles(analyzer.dialogues, plan)
                SubtitleReconstructor.export_to_srt(episode_dialogues, srt_output_path)
            
            # 2. 调度 Phase 3: 生成该集视频
            print(f"    -> [Phase 3] 正在裁剪并合并视频片段...")
            final_video_path = os.path.join(self.config.output_dir, f"{part_name}.mp4")
            concat_txt_path = os.path.join(self.config.output_dir, f"{part_name}_concat.txt")
            
            if len(plan.valid_time_ranges) == 1:
                # 只有一个片段时直接输出为最终文件
                valid_range = plan.valid_time_ranges[0]
                VideoProcessor.cut_video_segment(
                    self.config.video_path, valid_range.start_sec, valid_range.end_sec, final_video_path,
                    compress=self.config.compress
                )
            else:
                # 包含多个零碎片段时，先分别裁剪再合并
                temp_segments = []
                total_segs = len(plan.valid_time_ranges)
                for j, valid_range in enumerate(plan.valid_time_ranges, start=1):
                    print(f"        - 裁剪子片段 {j}/{total_segs}...")
                    temp_path = os.path.join(self.config.output_dir, f"{part_name}_seg{j}.mp4")
                    VideoProcessor.cut_video_segment(
                        self.config.video_path, valid_range.start_sec, valid_range.end_sec, temp_path,
                        compress=self.config.compress
                    )
                    temp_segments.append(temp_path)
                
                print(f"        - 无缝合并 {total_segs} 个子片段...")
                VideoProcessor.concat_video_segments(temp_segments, concat_txt_path, final_video_path, compress=self.config.compress)
                
                # 任务 4.5: 收尾机制 - 清理生成的临时合并文本及片段
                print(f"        - 正在清理临时文件...")
                for temp_file in temp_segments + [concat_txt_path]:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except OSError as e:
                        print(f"        [!] 清理临时文件失败: {temp_file}, 原因: {e}")
                
            print(f"    [√] 分集 {part_name} 处理完成。")
            
        print(f"\n🎉 恭喜！所有流水线处理完毕，结果已保存至: {os.path.abspath(self.config.output_dir)}")

def parse_args() -> AppConfig:
    """解析命令行参数并生成全局配置"""
    
    # 针对双击 exe 闪退的友好拦截与提示
    if len(sys.argv) == 1:
        print("======================================================")
        print("  欢迎使用 电影字幕智能分割工具 (Movie Smart Splitter)  ")
        print("======================================================")
        print("[*] 检测到直接双击运行，正在启动图形化文件选择器...")
        
        root = tk.Tk()
        root.withdraw()  # 隐藏 Tkinter 主界面
        root.attributes('-topmost', True)  # 窗口置顶，防止被后台控制台黑框遮挡
        
        print("\n[->] 请在弹出的窗口中选择【原始视频文件】...")
        video_path = filedialog.askopenfilename(
            parent=root,
            title="1/2 请选择原始视频文件",
            filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("所有文件", "*.*")]
        )
        if not video_path:
            print("[-] 取消了选择，程序退出。")
            sys.exit(0)
            
        print("[->] 请在弹出的窗口中选择【英文字幕文件(.srt)】...")
        subtitle_path = filedialog.askopenfilename(
            parent=root,
            title="2/2 请选择英文字幕文件 (.srt)",
            filetypes=[("SRT字幕文件", "*.srt"), ("所有文件", "*.*")]
        )
        if not subtitle_path:
            print("[-] 取消了选择，程序退出。")
            sys.exit(0)
            
        print("[->] 请在弹出的窗口中选择【中文字幕文件(.srt)】(可选)...")
        subtitle_path2 = filedialog.askopenfilename(
            parent=root,
            title="可选: 请选择中文字幕文件 (没有请直接点击取消)",
            filetypes=[("SRT字幕文件", "*.srt"), ("所有文件", "*.*")]
        )
        if not subtitle_path2:
            print("[-] 未选择中文字幕文件，按单字幕模式处理。")
            subtitle_path2 = ""
            
        print("[->] 请在弹出的窗口中确认【静音剔除阈值】...")
        silence_threshold = simpledialog.askfloat(
            parent=root,
            title="参数设置 (1/3)",
            prompt="请输入静音剔除阈值 (秒)：\n(连续无对话超过此时长将被剔除)",
            initialvalue=30.0,
            minvalue=0.0
        )
        if silence_threshold is None: silence_threshold = 30.0  # 用户点取消时的默认兜底值

        print("[->] 请在弹出的窗口中确认【最小分集时长】...")
        min_minutes = simpledialog.askfloat(
            parent=root,
            title="参数设置 (2/3)",
            prompt="请输入最小分集时长 (分钟)：",
            initialvalue=5.0,
            minvalue=0.1
        )
        if min_minutes is None: min_minutes = 5.0

        print("[->] 请在弹出的窗口中确认【最大分集时长】...")
        max_minutes = simpledialog.askfloat(
            parent=root,
            title="参数设置 (3/3)",
            prompt="请输入最大分集时长 (分钟)：\n(达到此时长将强制切割，需大于最小分集时长)",
            initialvalue=10.0,
            minvalue=min_minutes
        )
        if max_minutes is None: max_minutes = 10.0
            
        print("[->] 请在弹出的窗口中确认【是否启用网络串流优化】...")
        compress_video = messagebox.askyesno(
            title="参数设置 (4/4)",
            message="是否启用网络串流优化？\n(转码至720p并开启Web优化，速度较慢但文件更小、支持边下边播)"
        )

        print(f"\n[+] 视频路径: {video_path}")
        print(f"[+] 英文字幕路径: {subtitle_path}")
        if subtitle_path2:
            print(f"[+] 中文字幕路径: {subtitle_path2}")
        print(f"[+] 阈值设定: 静音剔除 {silence_threshold}秒 | 分集时长 {min_minutes}-{max_minutes}分钟 | 开启压缩: {compress_video}\n")
        
        root.destroy()
        
        return AppConfig(
            video_path=video_path,
            subtitle_path=subtitle_path,
            subtitle_path2=subtitle_path2,
            output_dir='../output',
            silence_threshold_sec=silence_threshold,
            min_segment_minutes=min_minutes,
            max_segment_minutes=max_minutes,
            compress=compress_video
        )

    parser = argparse.ArgumentParser(description="电影字幕智能分割工具 (Movie Smart Splitter)")
    parser.add_argument('-v', '--video', required=True, help="原始视频文件路径")
    parser.add_argument('-s', '--subtitle', required=True, help="英文字幕文件路径 (.srt)")
    parser.add_argument('-s2', '--subtitle2', default="", help="中文字幕文件路径 (.srt, 可选)")
    parser.add_argument('-o', '--output', default='../output', help="输出目录路径 (默认为 ../output)")
    parser.add_argument('--silence-threshold', type=float, default=30.0, help="静音剔除阈值/秒 (默认 30.0)")
    parser.add_argument('--min-minutes', type=float, default=5.0, help="最小分集时长/分钟 (默认 5.0)")
    parser.add_argument('--max-minutes', type=float, default=10.0, help="最大分集时长/分钟 (默认 10.0)")
    parser.add_argument('--compress', action='store_true', help="开启视频压缩(720p)及网络串流优化")
    
    args = parser.parse_args()
    return AppConfig(
        video_path=args.video,
        subtitle_path=args.subtitle,
        subtitle_path2=args.subtitle2,
        output_dir=args.output,
        silence_threshold_sec=args.silence_threshold,
        min_segment_minutes=args.min_minutes,
        max_segment_minutes=args.max_minutes,
        compress=args.compress
    )

if __name__ == '__main__':
    config = parse_args()
    controller = MainController(config)
    controller.run()