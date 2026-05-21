from typing import List, Optional
from dataclasses import dataclass
import pysrt

# --- 依赖数据结构 (Phase 1.1 延续) ---
@dataclass
class TimeRange:
    start_sec: float
    end_sec: float

@dataclass
class DialogueInfo:
    text: str
    time_range: TimeRange

@dataclass
class SplitPlan:
    part_index: int
    valid_time_ranges: List[TimeRange]

class TimelineAnalyzer:
    def __init__(self, subtitle_path: Optional[str] = None, silence_threshold: float = 30.0, min_minutes: float = 5.0, max_minutes: float = 10.0):
        self.subtitle_path = subtitle_path
        self.silence_threshold = silence_threshold
        self.min_seconds = min_minutes * 60.0
        self.max_seconds = max_minutes * 60.0
        self.dialogues = self.parse_subtitles(subtitle_path) if subtitle_path else []

    @staticmethod
    def parse_subtitles(subtitle_path: str) -> List[DialogueInfo]:
        """使用 pysrt 读取并解析字幕文件"""
        dialogues = []
        try:
            subs = pysrt.open(subtitle_path)
            for sub in subs:
                start_sec = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + sub.start.milliseconds / 1000.0
                end_sec = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + sub.end.milliseconds / 1000.0
                dialogues.append(DialogueInfo(text=sub.text, time_range=TimeRange(start_sec, end_sec)))
        except Exception as e:
            print(f"[错误] 解析字幕文件 {subtitle_path} 失败: {e}")
        return dialogues

    def find_elastic_split_indices(self, dialogues: Optional[List[DialogueInfo]] = None) -> List[int]:
        """
        Task 1.4: 基于弹性的切割点搜索算法
        累加保留时间，当达到 MIN_SEGMENT_MINUTES 时，在随后的停顿中寻找最大间隙（或理想的自然停顿）作为切割点。
        """
        if dialogues is None:
            dialogues = self.dialogues
        split_indices = []
        if not dialogues:
            return split_indices

        current_valid_time = 0.0
        looking_for_split = False
        max_pause = -1.0
        best_split_idx = -1

        for i in range(len(dialogues) - 1):
            curr_dlg = dialogues[i]
            next_dlg = dialogues[i + 1]

            dialogue_duration = curr_dlg.time_range.end_sec - curr_dlg.time_range.start_sec
            pause_duration = next_dlg.time_range.start_sec - curr_dlg.time_range.end_sec
            is_silence = pause_duration >= self.silence_threshold

            # 累加实际保留的时长（对话本身时长 + 未被静音剔除的短暂停顿）
            current_valid_time += dialogue_duration
            if not is_silence:
                current_valid_time += pause_duration

            if current_valid_time >= self.min_seconds:
                looking_for_split = True

            if looking_for_split:
                # 记录找到的最大停顿及其索引，为后续 1.5 强制兜底逻辑做准备
                if pause_duration > max_pause:
                    max_pause = pause_duration
                    best_split_idx = i

                # Task 1.4 核心: 若处于寻找状态且遇到天然静音段，则直接在此进行弹性切割
                if is_silence:
                    split_indices.append(i)
                    # 发生切割，重置状态累计下一集
                    current_valid_time = 0.0
                    looking_for_split = False
                    max_pause = -1.0
                    best_split_idx = -1

                # 预留: Task 1.5 (MAX_SEGMENT_MINUTES)
                elif current_valid_time >= self.max_seconds:
                    # 强制兜底逻辑：在已记录的最大间隙处切割（若无则在当前点切割）
                    cut_idx = best_split_idx if best_split_idx != -1 else i
                    split_indices.append(cut_idx)

                    # 重置状态
                    current_valid_time = 0.0
                    looking_for_split = False
                    max_pause = -1.0
                    best_split_idx = -1

                    # 时长补偿计算：把 cut_idx 之后到当前 i 的已遍历时长准确补偿给下一集
                    for j in range(cut_idx + 1, i + 1):
                        current_valid_time += (dialogues[j].time_range.end_sec - dialogues[j].time_range.start_sec)
                        pause_dur = dialogues[j + 1].time_range.start_sec - dialogues[j].time_range.end_sec
                        if pause_dur < self.silence_threshold:
                            current_valid_time += pause_dur

        return split_indices

    def generate_split_plans(self, dialogues: Optional[List[DialogueInfo]] = None) -> List[SplitPlan]:
        """
        Task 1.6: 组装 SplitPlan 列表输出
        根据算出的切割点和静音剔除规则，生成标准化、带有保留时间段数组的分集方案。
        """
        if dialogues is None:
            dialogues = self.dialogues
        plans = []
        if not dialogues:
            return plans

        split_indices = set(self.find_elastic_split_indices(dialogues))
        
        part_idx = 1
        current_ranges = []
        current_start = dialogues[0].time_range.start_sec
        current_end = dialogues[0].time_range.end_sec

        for i in range(len(dialogues)):
            curr_dlg = dialogues[i]
            current_end = curr_dlg.time_range.end_sec
            is_split_point = i in split_indices

            if i < len(dialogues) - 1:
                next_dlg = dialogues[i + 1]
                pause = next_dlg.time_range.start_sec - current_end
                
                if is_split_point:
                    current_ranges.append(TimeRange(start_sec=current_start, end_sec=current_end))
                    plans.append(SplitPlan(part_index=part_idx, valid_time_ranges=current_ranges))
                    part_idx += 1
                    current_ranges = []
                    current_start = next_dlg.time_range.start_sec
                elif pause >= self.silence_threshold:
                    current_ranges.append(TimeRange(start_sec=current_start, end_sec=current_end))
                    current_start = next_dlg.time_range.start_sec
            else:
                current_ranges.append(TimeRange(start_sec=current_start, end_sec=current_end))
                plans.append(SplitPlan(part_index=part_idx, valid_time_ranges=current_ranges))

        return plans