from dataclasses import dataclass, field
from typing import List

@dataclass
class TimeRange:
    """表示一个绝对的时间段，单位为秒"""
    start_sec: float
    end_sec: float

    @property
    def duration(self) -> float:
        """计算时间段的持续时长"""
        return max(0.0, self.end_sec - self.start_sec)

@dataclass
class DialogueInfo:
    """包含单句对话的内容及对应的时间范围"""
    text: str
    time_range: TimeRange

@dataclass
class SplitPlan:
    """切割方案：包含第几集及该集需要保留的原视频有效时间段列表"""
    part_index: int
    valid_time_ranges: List[TimeRange] = field(default_factory=list)