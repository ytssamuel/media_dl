import yt_dlp
import os
import sys
import re
from datetime import datetime
from pathlib import Path

class YouTubeAudioDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        self.setup_output_dir()
        
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
    
    def download_with_format(self, url, format_id='bestaudio/best'):
        """使用指定格式下載音訊"""
        
        # 取得影片資訊以設定檔名
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = self.sanitize_filename(info.get('title', 'audio'))
        
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
            'writethumbnail': True,  # 下載縮圖
            'postprocessor_args': [
                '-metadata', f'title={title}',
                '-metadata', f'date={datetime.now().year}',
            ],
            'progress_hooks': [self.progress_hook],
        }
        
        try:
            print(f"\n開始下載: {title}")
            print(f"使用格式: {format_id}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            print(f"\n✓ 下載完成！檔案保存在: {self.output_dir}")
            return True
            
        except Exception as e:
            print(f"\n✗ 下載失敗: {str(e)}")
            return False
    
    def progress_hook(self, d):
        """下載進度回調函數"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                percentage = downloaded / total * 100
                speed = d.get('speed', 0)
                speed_mb = speed / 1024 / 1024 if speed else 0
                
                print(f"\r進度: {percentage:6.2f}% | "
                      f"速度: {speed_mb:5.2f} MB/s", end='')
    
    def batch_download(self, urls_file):
        """批次下載多個影片"""
        if not os.path.exists(urls_file):
            print(f"檔案不存在: {urls_file}")
            return
        
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"找到 {len(urls)} 個影片連結")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*50}")
            print(f"正在處理第 {i}/{len(urls)} 個影片")
            print(f"{'='*50}")
            
            if self.is_valid_youtube_url(url):
                self.download_with_format(url)
            else:
                print(f"無效的 YouTube 網址: {url}")
    
    def is_valid_youtube_url(self, url):
        """檢查是否為有效的 YouTube 網址"""
        patterns = [
            r'^https?://(www\.)?youtube\.com/watch\?v=',
            r'^https?://youtu\.be/',
            r'^https?://(www\.)?youtube\.com/embed/',
            r'^https?://(www\.)?youtube\.com/shorts/',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False

def main_menu():
    """主選單"""
    downloader = YouTubeAudioDownloader()
    
    while True:
        print("\n" + "="*50)
        print("YouTube 音訊下載器")
        print("="*50)
        print("1. 單一下載")
        print("2. 批次下載 (從檔案讀取連結)")
        print("3. 設定下載資料夾")
        print("4. 退出")
        print("-"*50)
        
        choice = input("請選擇選項 (1-4): ").strip()
        
        if choice == '1':
            url = input("\n輸入 YouTube 影片網址: ").strip()
            if downloader.is_valid_youtube_url(url):
                # 顯示可用格式
                formats = downloader.get_available_formats(url)
                if formats:
                    format_choice = input("\n選擇格式編號 (直接按 Enter 使用最佳品質): ").strip()
                    if format_choice.isdigit() and 1 <= int(format_choice) <= len(formats):
                        format_id = formats[int(format_choice)-1]['id']
                        downloader.download_with_format(url, format_id)
                    else:
                        downloader.download_with_format(url)
            else:
                print("錯誤：無效的 YouTube 網址！")
                
        elif choice == '2':
            file_path = input("\n輸入包含連結的檔案路徑: ").strip()
            downloader.batch_download(file_path)
            
        elif choice == '3':
            new_dir = input("\n輸入新的下載資料夾路徑: ").strip()
            if new_dir:
                downloader.output_dir = new_dir
                downloader.setup_output_dir()
                print(f"下載資料夾已設定為: {new_dir}")
                
        elif choice == '4':
            print("程式結束")
            sys.exit(0)
            
        else:
            print("無效的選擇，請重新輸入！")

if __name__ == "__main__":
    main_menu()