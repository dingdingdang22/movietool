import os
import pysrt

# ==========================================
# 全局参数配置区
# ==========================================

# 1. 手动指定测试素材路径（请在测试前修改为您本地的真实文件路径）
VIDEO_PATH = r"d:\projects\movie tool\test_movie.mp4"
SUBTITLE_PATH = r"d:\projects\movie tool\test_subtitle.srt"
OUTPUT_DIR = r"d:\projects\movie tool\output"

# 2. 核心算法阈值设定
SILENCE_THRESHOLD_SEC = 30.0   # 连续超过30秒无字幕，判定为需要剔除的冗余片段
MIN_SEGMENT_MINUTES = 5.0      # 最小片段弹性时长（分钟）
MAX_SEGMENT_MINUTES = 10.0     # 最大片段弹性时长（分钟）

def srt_time_to_seconds(srt_time):
    """将 pysrt 的 SubRipTime 对象转换为绝对秒数，方便时间轴计算"""
    return srt_time.hours * 3600 + srt_time.minutes * 60 + srt_time.seconds + srt_time.milliseconds / 1000.0

def analyze_subtitle_timeline(subtitle_path):
    """
    第一阶段：解析字幕文件，探索并计算出保留区和剔除区的时间轴
    """
    if not os.path.exists(subtitle_path):
        print(f"[错误] 找不到字幕文件，请检查路径: {subtitle_path}")
        return
        
    print(f"[*] 正在读取字幕文件: {subtitle_path}")
    subs = pysrt.open(subtitle_path)
    
    if not subs:
        print("[错误] 字幕文件为空或解析失败")
        return

    print(f"[*] 成功加载字幕，共包含 {len(subs)} 条对话。")
    
    # 演示：打印前三条字幕的时间轴信息进行验证
    print("-" * 50)
    for i in range(min(3, len(subs))):
        start_sec = srt_time_to_seconds(subs[i].start)
        end_sec = srt_time_to_seconds(subs[i].end)
        # 将多行字幕合并为一行显示
        text_line = subs[i].text.replace('\n', ' ')
        print(f"字幕 {i+1}: {subs[i].start} --> {subs[i].end} | 文本: {text_line}")
    
    print("-" * 50)
    print(f"[*] 下一步规划：遍历所有字幕，寻找间隔大于 {SILENCE_THRESHOLD_SEC} 秒的剔除区间，并按 {MIN_SEGMENT_MINUTES}-{MAX_SEGMENT_MINUTES} 分钟分段...")

if __name__ == "__main__":
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=== 电影字幕智能分割工具启动 ===")
    analyze_subtitle_timeline(SUBTITLE_PATH)