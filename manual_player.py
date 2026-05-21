import os
import sys

def manual_sync_test(video_path: str, subtitle_path: str) -> None:
    """
    任务 3.5: 手动联调测试辅助脚本
    验证新切割的视频与生成的字幕是否同步。
    """
    if not os.path.exists(video_path) or not os.path.exists(subtitle_path):
        print("[-] 找不到指定的视频或字幕文件，请检查路径！")
        return
        
    print("=========== 联调测试 (手动验证) ===========")
    print(f"[+] 视频路径: {video_path}")
    print(f"[+] 字幕路径: {subtitle_path}")
    print("[*] 提示: 多数现代播放器（PotPlayer/VLC）在视频与字幕同名且同级时会自动挂载。")
    print("[*] 正在拉起系统默认播放器...")
    
    try:
        # 利用 Windows 原生接口拉起默认关联的视频播放器
        if sys.platform == "win32":
            os.startfile(video_path)
        else:
            print("[-] 当前非 Windows 平台，请手动使用播放器打开对应文件。")
    except Exception as e:
        print(f"[-] 播放器拉起失败: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python manual_player.py <video_path> <subtitle_path>")
    else:
        manual_sync_test(sys.argv[1], sys.argv[2])