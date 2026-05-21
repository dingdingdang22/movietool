import unittest
import sys
import os

# 将待测试模块加入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../doc')))
from timeline_analyzer import TimelineAnalyzer, DialogueInfo, TimeRange

class TestTimelineAnalyzer(unittest.TestCase):
    def test_split_and_silence_removal(self):
        # 设定阈值：静音>30秒剔除，最小集数5分钟(300秒)，最大10分钟
        analyzer = TimelineAnalyzer(silence_threshold=30.0, min_minutes=5.0, max_minutes=10.0)
        
        dialogues = [
            # 第一段对话：1分钟
            DialogueInfo("Hello", TimeRange(0.0, 60.0)),
            # 停顿 10 秒 (<30秒，不剔除)
            DialogueInfo("World", TimeRange(70.0, 130.0)),
            # 停顿 40 秒 (>30秒，触发剔除产生区间断点)
            DialogueInfo("Gap", TimeRange(170.0, 300.0)),
            # 当前有效时间：60 + 10 + 60 + 130 = 260秒
            # 停顿 10 秒
            DialogueInfo("More", TimeRange(310.0, 370.0)),
            # 当前有效时间：260 + 10 + 60 = 330秒 -> 超过 300秒，进入寻找断点状态
            # 停顿 40 秒 (>30秒) -> 遇到天然静音段，触发切割！
            DialogueInfo("Next Part", TimeRange(410.0, 420.0))
        ]
        
        plans = analyzer.generate_split_plans(dialogues)
        
        # 验证总集数
        self.assertEqual(len(plans), 2)
        
        # 验证第一集
        self.assertEqual(plans[0].part_index, 1)
        self.assertEqual(len(plans[0].valid_time_ranges), 2)
        # 第一集的时间段1: 0.0 - 130.0 (连带短暂停顿合并保留)
        self.assertEqual(plans[0].valid_time_ranges[0].start_sec, 0.0)
        self.assertEqual(plans[0].valid_time_ranges[0].end_sec, 130.0)
        # 第一集的时间段2: 170.0 - 370.0 (成功扣除了 130-170 的长静音)
        self.assertEqual(plans[0].valid_time_ranges[1].start_sec, 170.0)
        self.assertEqual(plans[0].valid_time_ranges[1].end_sec, 370.0)
        
        # 验证第二集
        self.assertEqual(plans[1].part_index, 2)
        self.assertEqual(plans[1].valid_time_ranges[0].start_sec, 410.0)
        self.assertEqual(plans[1].valid_time_ranges[0].end_sec, 420.0)

if __name__ == '__main__':
    unittest.main()