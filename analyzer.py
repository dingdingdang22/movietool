import pysrt
from typing import List
from models import DialogueInfo, TimeRange

def parse_subtitles(subtitle_path: str) -> List[DialogueInfo]:
    """
    读取字幕文件并将其转换为核心数据结构 DialogueInfo 列表。
    
    :param subtitle_path: SRT 字幕文件的本地路径
    :return: 包含字幕文本及精确时间范围的 DialogueInfo 列表
    """
    # pysrt.open 默认会尝试猜测编码，为确保兼容性可依需显式指定 encoding='utf-8'
    subs = pysrt.open(subtitle_path)
    dialogues: List[DialogueInfo] = []
    
    for sub in subs:
        # pysrt 中 ordinal 属性返回总毫秒数，将其转为绝对秒数
        start_sec = sub.start.ordinal / 1000.0
        end_sec = sub.end.ordinal / 1000.0
        
        time_range = TimeRange(start_sec=start_sec, end_sec=end_sec)
        dialogue_info = DialogueInfo(text=sub.text, time_range=time_range)
        dialogues.append(dialogue_info)
        
    return dialogues