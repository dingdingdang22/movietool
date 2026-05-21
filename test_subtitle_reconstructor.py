import unittest
import sys
import os

# 引入需要测试的重构模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'doc')))
from subtitle_reconstructor import SubtitleReconstructor

# 模拟 Phase 1 的核心数据结构
class TimeRange:
    def __init__(self, start, end):
        self.start_sec = start
        self.end_sec = end

class DialogueInfo:
    def __init__(self, start, end, text):
        self.time_range = TimeRange(start, end)
        self.text = text

class SplitPlan:
    def __init__(self, valid_ranges):
        self.valid_time_ranges = valid_ranges

class TestSubtitleReconstructor(unittest.TestCase):
    def test_timeline_recalculation_logic(self):
        """
        任务 2.5: 测试验证校验新生成的字幕时间轴是否有逻辑断层或负数。
        """
        # 模拟一个切割计划：保留 0-10秒 和 20-30秒，即中间剔除了 10-20秒 (共10秒) 的静音
        plan = SplitPlan([
            TimeRange(0.0, 10.0),
            TimeRange(20.0, 30.0)
        ])
        
        # 模拟全局字幕对话
        dialogues = [
            DialogueInfo(2.0, 5.0, "Hello"),         # 位于第一段保留区
            DialogueInfo(8.0, 9.0, "World"),         # 位于第一段保留区
            DialogueInfo(22.0, 25.0, "After gap"),   # 位于第二段保留区
            DialogueInfo(28.0, 29.0, "End")          # 位于第二段保留区
        ]
        
        result = SubtitleReconstructor.generate_zero_baselined_subtitles(dialogues, plan)
        
        self.assertEqual(len(result), 4)
        
        for i in range(len(result)):
            # 验证 1：不能有负数，且起始时间必须小于等于结束时间
            self.assertGreaterEqual(result[i].time_range.start_sec, 0.0, "起始时间不能为负数")
            self.assertGreaterEqual(result[i].time_range.end_sec, result[i].time_range.start_sec, "结束时间必须大于等于起始时间")
            
            # 验证 2：时间轴必须连续正向递增，不能有逻辑断层错位
            if i > 0:
                self.assertGreaterEqual(result[i].time_range.start_sec, result[i-1].time_range.end_sec, "字幕时间轴必须顺序递增，不能出现重叠或倒流")

if __name__ == '__main__':
    unittest.main()