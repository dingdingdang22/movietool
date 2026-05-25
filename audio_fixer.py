import os
import sys
import tkinter as tk
from tkinter import filedialog
from video_processor import VideoProcessor

def main():
    print("======================================================")
    print("     视频音频格式批量修复工具 (Audio Fixer for Web)     ")
    print("======================================================")
    
    # 支持命令行直接传入文件夹路径
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        # 图形界面：弹出文件夹选择框
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        print("[*] 正在拉起文件夹选择窗口...")
        directory = filedialog.askdirectory(
            parent=root,
            title="请选择包含待修复视频的文件夹"
        )
        root.destroy()

    if not directory or not os.path.exists(directory):
        print("[-] 未选择有效文件夹，程序退出。")
        return

    directory = os.path.abspath(directory)
    print(f"[*] 已选择文件夹: {directory}")
    
    # 寻找该目录下所有的 mp4 文件
    mp4_files = [f for f in os.listdir(directory) if f.lower().endswith('.mp4')]
    
    if not mp4_files:
        print("[-] 该文件夹下没有找到 .mp4 视频文件。")
        return
        
    print(f"[*] 共发现 {len(mp4_files)} 个视频文件，准备进行音频兼容性修复 (转为 AAC 编码)...")
    
    success_count = 0
    for idx, filename in enumerate(mp4_files, start=1):
        input_path = os.path.join(directory, filename)
        temp_output = os.path.join(directory, f".temp_fix_{filename}")
        
        print(f"\n    [{idx}/{len(mp4_files)}] 正在极速修复: {filename} ...")
        try:
            # 调用 VideoProcessor 的修复方法，视频流 Copy，音频转 AAC
            VideoProcessor.fix_audio_compatibility(input_path, temp_output)
            
            # 修复成功后，重命名覆盖原文件，实现“存入当前位置”
            os.replace(temp_output, input_path)
            print(f"    [√] {filename} 修复成功并已覆盖原文件。")
            success_count += 1
        except Exception as e:
            print(f"    [!] 修复失败: {e}")
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except OSError:
                    pass
                
    print(f"\n🎉 批量修复完成！成功修复 {success_count}/{len(mp4_files)} 个文件。所有文件均已安全保存回原位置。")

if __name__ == '__main__':
    main()