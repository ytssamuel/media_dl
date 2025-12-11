import yt_dlp
import os
import sys
import re
import subprocess
import threading
import time
import platform
from datetime import datetime
from pathlib import Path

class YouTubeAudioDownloader:
    def __init__(self, output_dir="downloads", ffmpeg_path=None):
        self.output_dir = output_dir
        self.ffmpeg_path = ffmpeg_path or self.find_ffmpeg()
        self.setup_output_dir()
        self.setup_ffmpeg()
        self.conversion_progress = 0
        self.total_duration = 0
        self.is_converting = False
        
    def find_ffmpeg(self):
        """嘗試尋找系統中的 FFmpeg"""
        system = platform.system()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 根據作業系統設定 FFmpeg 路徑
        if system == "Windows":
            ffmpeg_name = "ffmpeg.exe"
            custom_path = os.path.join(script_dir, "ffmpeg-master-latest-win64-gpl", "bin", ffmpeg_name)
            if os.path.exists(custom_path):
                return custom_path
            
            # 檢查常見的 Windows 安裝路徑
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            ]
            if os.getenv('USERNAME'):
                common_paths.append(
                    r"C:\Users\{}\AppData\Local\ffmpeg\bin\ffmpeg.exe".format(os.getenv('USERNAME'))
                )
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        else:  # macOS 或 Linux
            ffmpeg_name = "ffmpeg"
            # 檢查本地目錄
            custom_path = os.path.join(script_dir, "ffmpeg", "bin", ffmpeg_name)
            if os.path.exists(custom_path):
                return custom_path
            
            # 檢查系統 PATH
            try:
                result = subprocess.run(
                    ["which", "ffmpeg"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
            
            # 檢查常見 Unix 路徑
            common_paths = [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg",  # macOS Apple Silicon
                "/home/linuxbrew/.linuxbrew/bin/ffmpeg",  # Linux Homebrew
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    def setup_ffmpeg(self):
        """設定 FFmpeg 路徑"""
        if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            # 取得 ffmpeg 目錄
            ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
            
            # 根據作業系統檢查 ffprobe
            system = platform.system()
            ffprobe_name = "ffprobe.exe" if system == "Windows" else "ffprobe"
            ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_name)
            
            # 設定 yt-dlp 的 FFmpeg 路徑
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
            
            print(f"✓ FFmpeg 路徑已設定: {self.ffmpeg_path}")
            
            # 測試 FFmpeg
            try:
                result = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "ffmpeg version" in result.stdout:
                    print("✓ FFmpeg 測試成功")
                else:
                    print("⚠ FFmpeg 版本檢查失敗")
            except:
                print("⚠ FFmpeg 測試失敗，但仍將嘗試使用")
        else:
            print("⚠ 未找到 FFmpeg，yt-dlp 將嘗試使用內建下載器")
    
    def setup_output_dir(self):
        """建立輸出目錄"""
        Path(self.output_dir).mkdir(exist_ok=True)
        
    def sanitize_filename(self, filename):
        """清理檔名中的無效字元"""
        # 移除或替換 Windows/Unix 檔案系統中無效的字元
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip()
        # 限制檔案長度
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def get_available_formats(self, url):
        """取得可用的格式資訊"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                print("\n可用的音訊格式:")
                audio_formats = []
                for f in formats:
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        format_id = f.get('format_id')
                        ext = f.get('ext')
                        bitrate = f.get('abr', 'N/A')
                        filesize = f.get('filesize')
                        size_str = f"{filesize/1024/1024:.2f} MB" if filesize else "N/A"
                        
                        audio_formats.append({
                            'id': format_id,
                            'ext': ext,
                            'bitrate': bitrate,
                            'size': size_str
                        })
                
                # 排序並顯示
                audio_formats.sort(key=lambda x: float(x['bitrate']) if x['bitrate'] != 'N/A' else 0, reverse=True)
                
                for i, fmt in enumerate(audio_formats[:10], 1):  # 只顯示前10個
                    print(f"{i:2}. 格式: {fmt['id']:6} | 副檔名: {fmt['ext']:4} | "
                          f"位元率: {fmt['bitrate']:6} kbps | 大小: {fmt['size']}")
                
                return audio_formats
                
        except Exception as e:
            print(f"取得格式資訊失敗: {str(e)}")
            return []
    
    def ffmpeg_progress_hook(self, d):
        """FFmpeg 轉換進度回調"""
        if d['status'] == 'started':
            self.is_converting = True
            print("\n正在轉換為 MP3...")
        elif d['status'] == 'processing':
            # 解析 FFmpeg 輸出以取得進度
            pass
        elif d['status'] == 'finished':
            self.is_converting = False
            print("\r轉換完成！" + " " * 50)
    
    def download_with_format(self, url, format_id='bestaudio/best'):
        """使用指定格式下載音訊"""
        
        # 取得影片資訊以設定檔名
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = self.sanitize_filename(info.get('title', 'audio'))
                self.total_duration = info.get('duration', 0)
        except Exception as e:
            print(f"取得影片資訊失敗: {str(e)}")
            title = "youtube_audio"
            self.total_duration = 0
        
        # 設定下載選項
        ydl_opts = {
            'format': format_id,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(self.output_dir, f'{title}.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'writethumbnail': False,
            'progress_hooks': [self.progress_hook],
            'postprocessor_hooks': [self.ffmpeg_progress_hook],
            'ffmpeg_location': os.path.dirname(self.ffmpeg_path) if self.ffmpeg_path else None,
        }
        
        try:
            print(f"\n開始下載: {title}")
            print(f"使用格式: {format_id}")
            if self.ffmpeg_path:
                print(f"FFmpeg 路徑: {self.ffmpeg_path}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 添加額外的 metadata
                info_dict = ydl.extract_info(url, download=True)
                
                # 如果下載成功，嘗試添加 metadata
                output_file = os.path.join(self.output_dir, f"{title}.mp3")
                if os.path.exists(output_file):
                    self.add_metadata(output_file, info_dict)
            
            print(f"\n✓ 下載完成！檔案保存在: {self.output_dir}")
            return True
            
        except Exception as e:
            print(f"\n✗ 下載失敗: {str(e)}")
            # 顯示詳細錯誤資訊
            import traceback
            traceback.print_exc()
            return False
    
    def add_metadata(self, audio_file, info_dict):
        """為音訊檔案添加 metadata"""
        if not self.ffmpeg_path:
            return
        
        try:
            title = info_dict.get('title', '')
            artist = info_dict.get('uploader', '')
            thumbnail_url = info_dict.get('thumbnail', '')
            
            # 下載縮圖
            if thumbnail_url:
                import requests
                thumbnail_path = os.path.join(self.output_dir, "temp_cover.jpg")
                
                try:
                    response = requests.get(thumbnail_url, timeout=10)
                    with open(thumbnail_path, 'wb') as f:
                        f.write(response.content)
                    
                    # 使用 FFmpeg 添加 metadata 和封面
                    cmd = [
                        self.ffmpeg_path,
                        '-i', audio_file,
                        '-i', thumbnail_path,
                        '-map', '0:0',
                        '-map', '1:0',
                        '-c', 'copy',
                        '-id3v2_version', '3',
                        '-metadata', f'title={title}',
                        '-metadata', f'artist={artist}',
                        '-metadata', f'album={title}',
                        '-codec', 'copy',
                        '-disposition:v:0', 'attached_pic',
                        audio_file + '.temp.mp3'
                    ]
                    
                    subprocess.run(cmd, capture_output=True, text=True)
                    
                    # 替換原始檔案
                    os.remove(audio_file)
                    os.rename(audio_file + '.temp.mp3', audio_file)
                    
                    # 刪除臨時縮圖
                    os.remove(thumbnail_path)
                    
                    print("✓ 已添加 metadata 和封面")
                    
                except:
                    # 如果添加失敗，保留原始檔案
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        
        except Exception as e:
            print(f"添加 metadata 失敗: {str(e)}")
    
    def progress_hook(self, d):
        """下載進度回調函數"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                percentage = downloaded / total * 100
                speed = d.get('speed', 0)
                speed_mb = speed / 1024 / 1024 if speed else 0
                
                print(f"\r下載進度: {percentage:6.2f}% | "
                      f"速度: {speed_mb:5.2f} MB/s", end='')
        elif d['status'] == 'finished':
            print(f"\r下載完成: 100.00%" + " " * 30)
            # 啟動 FFmpeg 進度監控
            if self.total_duration > 0:
                threading.Thread(target=self.monitor_conversion, daemon=True).start()
    
    def monitor_conversion(self):
        """監控 FFmpeg 轉換進度"""
        print("\n正在轉換為 MP3...")
        if self.total_duration > 0:
            duration_str = f"{int(self.total_duration // 3600):02d}:{int((self.total_duration % 3600) // 60):02d}:{int(self.total_duration % 60):02d}"
            print(f"影片總長度: {duration_str}")
        
        start_time = time.time()
        dots = 0
        
        while self.is_converting or (time.time() - start_time < 5):
            elapsed = time.time() - start_time
            
            # 估算進度（基於時間）
            if self.total_duration > 0:
                # FFmpeg 轉換通常比實際播放快，這裡用一個係數
                estimated_progress = min(95, (elapsed / (self.total_duration * 0.1)) * 100)
                bar_length = 40
                filled = int(bar_length * estimated_progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                print(f"\r轉換進度: [{bar}] {estimated_progress:5.1f}% | 已耗時: {elapsed_str}", end='', flush=True)
            else:
                # 如果沒有時長資訊，顯示動畫
                dots = (dots + 1) % 4
                elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                print(f"\r轉換中{'.' * dots}{' ' * (3 - dots)} | 已耗時: {elapsed_str}", end='', flush=True)
            
            time.sleep(0.5)
        
        print("\r轉換完成！" + " " * 60)
    
    def batch_download(self, urls_file):
        """批次下載多個影片"""
        if not os.path.exists(urls_file):
            print(f"檔案不存在: {urls_file}")
            return
        
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"找到 {len(urls)} 個影片連結")
        
        success_count = 0
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*50}")
            print(f"正在處理第 {i}/{len(urls)} 個影片")
            print(f"{'='*50}")
            
            if self.is_valid_youtube_url(url):
                if self.download_with_format(url):
                    success_count += 1
            else:
                print(f"無效的 YouTube 網址: {url}")
        
        print(f"\n{'='*50}")
        print(f"批次下載完成！成功: {success_count}/{len(urls)}")
    
    def is_valid_youtube_url(self, url):
        """檢查是否為有效的 YouTube 網址"""
        patterns = [
            r'^https?://(www\.)?youtube\.com/watch\?v=',
            r'^https?://youtu\.be/',
            r'^https?://(www\.)?youtube\.com/embed/',
            r'^https?://(www\.)?youtube\.com/shorts/',
            r'^https?://(www\.)?youtube\.com/playlist\?list=',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def check_ffmpeg_installation(self):
        """檢查 FFmpeg 安裝狀態"""
        if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            try:
                result = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "ffmpeg version" in result.stdout:
                    version_line = result.stdout.split('\n')[0]
                    return True, version_line
                else:
                    return False, "FFmpeg 版本檢查失敗"
            except Exception as e:
                return False, f"FFmpeg 測試失敗: {str(e)}"
        else:
            return False, "未找到 FFmpeg"

def main_menu():
    """主選單"""
    print("\n" + "="*60)
    print("YouTube 音訊下載器 - 進階版")
    print("="*60)
    
    # 設定 FFmpeg 路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_ffmpeg = os.path.join(script_dir, "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
    
    if os.path.exists(default_ffmpeg):
        ffmpeg_path = default_ffmpeg
        print(f"✓ 檢測到 FFmpeg 路徑: {ffmpeg_path}")
    else:
        print("⚠ 未在預設路徑找到 FFmpeg")
        custom_path = input("請輸入 FFmpeg 完整路徑 (直接按 Enter 跳過): ").strip()
        ffmpeg_path = custom_path if custom_path else None
    
    # 建立下載器實例
    downloader = YouTubeAudioDownloader(ffmpeg_path=ffmpeg_path)
    
    # 檢查 FFmpeg
    ffmpeg_ok, ffmpeg_info = downloader.check_ffmpeg_installation()
    if ffmpeg_ok:
        print(f"✓ {ffmpeg_info}")
    else:
        print(f"⚠ {ffmpeg_info}")
        print("注意: 部分功能可能無法正常運作")
    
    while True:
        print("\n" + "="*50)
        print("主選單")
        print("="*50)
        print("1. 單一下載")
        print("2. 批次下載 (從檔案讀取連結)")
        print("3. 設定下載資料夾")
        print("4. 檢查/更新 FFmpeg 路徑")
        print("5. 測試 FFmpeg")
        print("6. 退出")
        print("-"*50)
        
        choice = input("請選擇選項 (1-6): ").strip()
        
        if choice == '1':
            url = input("\n輸入 YouTube 影片網址: ").strip()
            if downloader.is_valid_youtube_url(url):
                # 顯示可用格式
                formats = downloader.get_available_formats(url)
                if formats:
                    print("\n格式選擇:")
                    print("  - 輸入格式編號 (1, 2, 3...)")
                    print("  - 直接按 Enter 使用最佳品質")
                    print("  - 輸入 'best' 使用最佳音質")
                    print("  - 輸入 'worst' 使用最小檔案")
                    
                    format_choice = input("\n請選擇: ").strip()
                    
                    if format_choice.isdigit() and 1 <= int(format_choice) <= len(formats):
                        format_id = formats[int(format_choice)-1]['id']
                        downloader.download_with_format(url, format_id)
                    elif format_choice.lower() == 'worst':
                        downloader.download_with_format(url, 'worstaudio/worst')
                    else:
                        downloader.download_with_format(url, 'bestaudio/best')
                else:
                    downloader.download_with_format(url)
            else:
                print("錯誤：無效的 YouTube 網址！")
                
        elif choice == '2':
            file_path = input("\n輸入包含連結的檔案路徑: ").strip()
            if os.path.exists(file_path):
                downloader.batch_download(file_path)
            else:
                print(f"錯誤：檔案不存在 - {file_path}")
                
        elif choice == '3':
            new_dir = input("\n輸入新的下載資料夾路徑: ").strip()
            if new_dir:
                downloader.output_dir = new_dir
                downloader.setup_output_dir()
                print(f"✓ 下載資料夾已設定為: {new_dir}")
                
        elif choice == '4':
            new_ffmpeg = input("\n輸入 FFmpeg 完整路徑: ").strip()
            if new_ffmpeg and os.path.exists(new_ffmpeg):
                downloader.ffmpeg_path = new_ffmpeg
                downloader.setup_ffmpeg()
                print(f"✓ FFmpeg 路徑已更新")
            else:
                print("錯誤：路徑不存在或無效")
                
        elif choice == '5':
            print("\n測試 FFmpeg...")
            success, info = downloader.check_ffmpeg_installation()
            if success:
                print(f"✓ FFmpeg 正常: {info}")
            else:
                print(f"✗ {info}")
                
        elif choice == '6':
            print("\n感謝使用！程式結束")
            sys.exit(0)
            
        else:
            print("無效的選擇，請重新輸入！")

def quick_download():
    """快速下載模式（命令列參數）"""
    import argparse
    
    # 取得腳本目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_ffmpeg_path = os.path.join(script_dir, "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
    
    parser = argparse.ArgumentParser(description='YouTube 音訊下載器')
    parser.add_argument('url', help='YouTube 影片網址')
    parser.add_argument('-o', '--output', default='downloads', help='輸出資料夾')
    parser.add_argument('-f', '--ffmpeg', default=default_ffmpeg_path, 
                       help='FFmpeg 路徑')
    parser.add_argument('-q', '--quality', default='192', help='MP3 音質 (128, 192, 256, 320)')
    parser.add_argument('-fmt', '--format', default='bestaudio/best', help='下載格式')
    
    args = parser.parse_args()
    
    # 建立下載器
    downloader = YouTubeAudioDownloader(
        output_dir=args.output,
        ffmpeg_path=args.ffmpeg if os.path.exists(args.ffmpeg) else None
    )
    
    # 開始下載
    downloader.download_with_format(args.url, args.format)

if __name__ == "__main__":
    # 檢查是否有命令列參數
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # 快速下載模式
        quick_download()
    else:
        # 互動式選單模式
        try:
            main_menu()
        except KeyboardInterrupt:
            print("\n\n程式被使用者中斷")
        except Exception as e:
            print(f"\n程式發生錯誤: {str(e)}")
            input("按 Enter 鍵退出...")