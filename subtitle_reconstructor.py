from typing import List, Any
import copy
import pysrt

class SubtitleReconstructor:
    """
    字幕重构模块 (Subtitle Reconstructor)
    负责根据 `SplitPlan` 重构和输出分集字幕文件。
    """
    
    @staticmethod
    def extract_subtitles_for_plan(dialogues: List[Any], split_plan: Any) -> List[Any]:
        """
        任务 2.1: 根据传入的 SplitPlan 的原视频保留区间，提取对应的字幕条目。
        
        :param dialogues: 原视频的全局字幕列表 (元素为包含 time_range 属性的 DialogueInfo)
        :param split_plan: 当前分集的切割计划，包含 valid_time_ranges (TimeRange 列表)
        :return: 当前分集所需保留的 DialogueInfo 列表
        """
        extracted_dialogues = []
        
        for dialogue in dialogues:
            # 取字幕时间段的中点，避免因浮点数精度或极微小的边界误差导致漏判
            # 因为 Phase 1 的切分点在几十秒的静音处，中点判定法是100%安全的
            mid_sec = (dialogue.time_range.start_sec + dialogue.time_range.end_sec) / 2.0
            
            # 检查该字幕中点是否落在当前 SplitPlan 的任何一个保留区间内
            for valid_range in split_plan.valid_time_ranges:
                if valid_range.start_sec <= mid_sec <= valid_range.end_sec:
                    extracted_dialogues.append(dialogue)
                    break
                    
        return extracted_dialogues

    @staticmethod
    def recalculate_timestamps(dialogues: List[Any], valid_time_ranges: List[Any]) -> None:
        """
        任务 2.2: 实现时间戳重计算算法：扣除被剔除的静音片段耗时。
        遍历字幕列表，将原有时间戳就地映射到扣除静音片段后的新连续时间轴上。
        """
        for dialogue in dialogues:
            dialogue.time_range.start_sec = SubtitleReconstructor._map_to_continuous_time(
                dialogue.time_range.start_sec, valid_time_ranges
            )
            dialogue.time_range.end_sec = SubtitleReconstructor._map_to_continuous_time(
                dialogue.time_range.end_sec, valid_time_ranges
            )

    @staticmethod
    def _map_to_continuous_time(original_time_sec: float, valid_time_ranges: List[Any]) -> float:
        continuous_time = 0.0
        for valid_range in valid_time_ranges:
            if original_time_sec < valid_range.start_sec:
                return continuous_time
            if valid_range.start_sec <= original_time_sec <= valid_range.end_sec:
                continuous_time += (original_time_sec - valid_range.start_sec)
                return continuous_time
            continuous_time += (valid_range.end_sec - valid_range.start_sec)
        return continuous_time

    @classmethod
    def generate_zero_baselined_subtitles(cls, dialogues: List[Any], split_plan: Any) -> List[Any]:
        """
        任务 2.3: 实现分集基准归零。
        提取全局字幕并进行深拷贝，在应用相对时间映射的同时确保各集独立归零。
        """
        extracted = cls.extract_subtitles_for_plan(dialogues, split_plan)
        
        # 深拷贝实现分集隔离，确保该计划的修改不会污染全局基准时间
        episode_dialogues = copy.deepcopy(extracted)
        
        cls.recalculate_timestamps(episode_dialogues, split_plan.valid_time_ranges)
        
        # 基准兜底校验：消除极微小的浮点数误差带来的负数错位
        for dialogue in episode_dialogues:
            dialogue.time_range.start_sec = max(0.0, dialogue.time_range.start_sec)
            dialogue.time_range.end_sec = max(0.0, dialogue.time_range.end_sec)
            
        return episode_dialogues

    @staticmethod
    def export_to_srt(dialogues: List[Any], output_path: str) -> None:
        """
        任务 2.4: 利用 pysrt 将修改后的字幕对象输出分集的双语 .srt 文件。
        
        :param dialogues: 重计算基准时间后的字幕列表
        :param output_path: 输出的 .srt 文件路径
        """
        subs = pysrt.SubRipFile()
        for i, dialogue in enumerate(dialogues, start=1):
            # 将秒数转换为整数毫秒，以适配 pysrt.SubRipTime 的实例化
            start_ms = int(dialogue.time_range.start_sec * 1000)
            end_ms = int(dialogue.time_range.end_sec * 1000)
            
            start_time = pysrt.SubRipTime(milliseconds=start_ms)
            end_time = pysrt.SubRipTime(milliseconds=end_ms)
            
            item = pysrt.SubRipItem(index=i, start=start_time, end=end_time, text=dialogue.text)
            subs.append(item)
            
        subs.save(output_path, encoding='utf-8')