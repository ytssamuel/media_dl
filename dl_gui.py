import yt_dlp
import os
import sys
import re
import subprocess
import threading
import time
import platform
import zipfile
import tarfile
import urllib.request
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import queue
import ssl
import certifi

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下載器 - GUI 版本")
        self.root.geometry("900x700")
        
        # 初始化變數
        self.output_dir = os.path.join(os.getcwd(), "downloads")
        self.ffmpeg_path = self.find_ffmpeg()
        self.is_downloading = False
        self.total_duration = 0
        self.conversion_progress = 0
        self.is_converting = False
        self.log_queue = queue.Queue()
        
        # 設定 SSL 憑證
        self.setup_ssl()
        
        # 設定 FFmpeg
        self.setup_ffmpeg()
        self.setup_output_dir()
        
        # 建立 GUI
        self.create_widgets()
        
        # 啟動日誌更新
        self.update_log()
    
    def setup_ssl(self):
        """設定 SSL 憑證"""
        try:
            # 使用 certifi 提供的憑證
            ssl._create_default_https_context = ssl._create_unverified_context
            self.log("已設定 SSL 憑證處理")
        except Exception as e:
            self.log(f"SSL 設定警告: {str(e)}")
        
    def find_ffmpeg(self):
        """尋找 FFmpeg"""
        system = platform.system()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 根據作業系統設定 FFmpeg 執行檔名稱
        if system == "Windows":
            ffmpeg_name = "ffmpeg.exe"
            ffmpeg_dir = "ffmpeg-master-latest-win64-gpl"
        else:  # macOS 或 Linux
            ffmpeg_name = "ffmpeg"
            ffmpeg_dir = "ffmpeg"
        
        # 檢查本地 FFmpeg
        local_ffmpeg = os.path.join(script_dir, ffmpeg_dir, "bin", ffmpeg_name)
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        
        # 檢查系統 PATH 中的 FFmpeg
        ffmpeg_in_path = self.check_ffmpeg_in_path()
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        # 檢查常見路徑 (Windows)
        if system == "Windows":
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    def check_ffmpeg_in_path(self):
        """檢查 FFmpeg 是否在系統 PATH 中"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # FFmpeg 在 PATH 中，取得完整路徑
                which_result = subprocess.run(
                    ["which", "ffmpeg"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if which_result.returncode == 0:
                    ffmpeg_path = which_result.stdout.strip()
                    return ffmpeg_path if ffmpeg_path else "ffmpeg"
                
                # 如果 which 失敗，返回命令名稱
                if platform.system() == "Windows":
                    return "ffmpeg.exe"
                else:
                    return "ffmpeg"
        except:
            pass
        return None
    
    def download_ffmpeg(self):
        """下載 FFmpeg"""
        system = platform.system()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.log("正在下載 FFmpeg...")
        
        try:
            if system == "Windows":
                # Windows: 下載預編譯版本
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                download_path = os.path.join(script_dir, "ffmpeg.zip")
                extract_dir = script_dir
                
                self.log("正在下載 Windows 版 FFmpeg...")
                urllib.request.urlretrieve(url, download_path, self.download_progress)
                
                self.log("正在解壓縮...")
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                os.remove(download_path)
                ffmpeg_path = os.path.join(script_dir, "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
                
            elif system == "Darwin":  # macOS
                # macOS: 建議使用 Homebrew，或下載靜態編譯版本
                self.log("macOS 系統偵測到")
                self.log("正在嘗試使用 Homebrew 安裝 FFmpeg...")
                
                try:
                    # 檢查是否已安裝 Homebrew
                    subprocess.run(["brew", "--version"], check=True, capture_output=True)
                    
                    # 使用 Homebrew 安裝
                    self.log("使用 Homebrew 安裝 FFmpeg...")
                    result = subprocess.run(
                        ["brew", "install", "ffmpeg"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        ffmpeg_path = "ffmpeg"
                        self.log("✓ FFmpeg 安裝成功 (透過 Homebrew)")
                    else:
                        raise Exception("Homebrew 安裝失敗")
                        
                except:
                    # Homebrew 不可用，下載靜態編譯版本
                    self.log("Homebrew 不可用，下載靜態編譯版本...")
                    url = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
                    download_path = os.path.join(script_dir, "ffmpeg.zip")
                    ffmpeg_dir = os.path.join(script_dir, "ffmpeg", "bin")
                    os.makedirs(ffmpeg_dir, exist_ok=True)
                    
                    urllib.request.urlretrieve(url, download_path, self.download_progress)
                    
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(ffmpeg_dir)
                    
                    os.remove(download_path)
                    ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg")
                    
                    # 給予執行權限
                    os.chmod(ffmpeg_path, 0o755)
                
            else:  # Linux
                self.log("Linux 系統偵測到")
                self.log("正在嘗試使用套件管理器安裝 FFmpeg...")
                
                # 嘗試不同的套件管理器
                package_managers = [
                    (["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", "ffmpeg"]),  # Debian/Ubuntu
                    (["sudo", "yum", "check-update"], ["sudo", "yum", "install", "-y", "ffmpeg"]),  # RedHat/CentOS
                    (["sudo", "dnf", "check-update"], ["sudo", "dnf", "install", "-y", "ffmpeg"]),  # Fedora
                    (["sudo", "pacman", "-Sy"], ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]),  # Arch
                ]
                
                installed = False
                for update_cmd, install_cmd in package_managers:
                    try:
                        self.log(f"嘗試: {' '.join(install_cmd)}")
                        subprocess.run(update_cmd, check=False, capture_output=True, timeout=30)
                        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode == 0:
                            ffmpeg_path = "ffmpeg"
                            self.log("✓ FFmpeg 安裝成功")
                            installed = True
                            break
                    except:
                        continue
                
                if not installed:
                    # 下載靜態編譯版本
                    self.log("使用靜態編譯版本...")
                    url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                    download_path = os.path.join(script_dir, "ffmpeg.tar.xz")
                    
                    urllib.request.urlretrieve(url, download_path, self.download_progress)
                    
                    self.log("正在解壓縮...")
                    with tarfile.open(download_path, 'r:xz') as tar_ref:
                        tar_ref.extractall(script_dir)
                    
                    os.remove(download_path)
                    
                    # 找到解壓後的目錄
                    for item in os.listdir(script_dir):
                        if item.startswith("ffmpeg-") and os.path.isdir(os.path.join(script_dir, item)):
                            ffmpeg_path = os.path.join(script_dir, item, "ffmpeg")
                            os.chmod(ffmpeg_path, 0o755)
                            break
            
            self.log("✓ FFmpeg 下載並設定完成")
            return ffmpeg_path
            
        except Exception as e:
            self.log(f"✗ FFmpeg 下載失敗: {str(e)}")
            return None
    
    def download_progress(self, block_num, block_size, total_size):
        """下載進度回調"""
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            self.log(f"下載進度: {percent:.1f}%")
    
    def setup_ffmpeg(self):
        """設定 FFmpeg"""
        if self.ffmpeg_path:
            if os.path.isabs(self.ffmpeg_path) and os.path.exists(self.ffmpeg_path):
                # 如果是絕對路徑，將目錄加入 PATH
                ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
                if ffmpeg_dir not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                    self.log(f"已將 FFmpeg 路徑加入環境變數: {ffmpeg_dir}")
            else:
                # 如果是命令名稱，檢查是否在 PATH 中
                self.log(f"使用系統 FFmpeg: {self.ffmpeg_path}")
    
    def setup_output_dir(self):
        """建立輸出目錄"""
        Path(self.output_dir).mkdir(exist_ok=True)
    
    def create_widgets(self):
        """建立 GUI 元件"""
        # 主要容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置權重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 標題
        title_label = ttk.Label(main_frame, text="YouTube 下載器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # URL 輸入區
        ttk.Label(main_frame, text="YouTube 網址:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=60)
        self.url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 取得播放清單按鈕
        self.fetch_playlist_btn = ttk.Button(main_frame, text="取得播放清單", command=self.fetch_playlist)
        self.fetch_playlist_btn.grid(row=1, column=2, pady=5, padx=5)
        
        # 播放清單區域（初始隱藏）
        self.playlist_frame = ttk.LabelFrame(main_frame, text="播放清單", padding="10")
        self.playlist_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.playlist_frame.grid_remove()  # 初始隱藏
        
        # 播放清單樹狀視圖
        playlist_container = ttk.Frame(self.playlist_frame)
        playlist_container.pack(fill=tk.BOTH, expand=True)
        
        # 滾動條
        playlist_scroll = ttk.Scrollbar(playlist_container)
        playlist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_tree = ttk.Treeview(
            playlist_container,
            columns=("title", "duration", "url"),
            show="tree headings",
            height=8,
            yscrollcommand=playlist_scroll.set
        )
        playlist_scroll.config(command=self.playlist_tree.yview)
        
        self.playlist_tree.heading("#0", text="選擇")
        self.playlist_tree.heading("title", text="標題")
        self.playlist_tree.heading("duration", text="長度")
        self.playlist_tree.heading("url", text="網址")
        
        self.playlist_tree.column("#0", width=50)
        self.playlist_tree.column("title", width=400)
        self.playlist_tree.column("duration", width=80)
        self.playlist_tree.column("url", width=0, stretch=False)
        
        self.playlist_tree.pack(fill=tk.BOTH, expand=True)
        
        # 播放清單按鈕區
        playlist_btn_frame = ttk.Frame(self.playlist_frame)
        playlist_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(playlist_btn_frame, text="全選", command=self.select_all_playlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(playlist_btn_frame, text="取消全選", command=self.deselect_all_playlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(playlist_btn_frame, text="下載選中項目", command=self.download_selected_playlist).pack(side=tk.LEFT, padx=5)
        
        # 下載類型選擇
        type_frame = ttk.LabelFrame(main_frame, text="下載類型", padding="10")
        type_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.download_type = tk.StringVar(value="audio")
        ttk.Radiobutton(type_frame, text="僅音訊 (MP3)", variable=self.download_type, value="audio").pack(side=tk.LEFT, padx=20)
        ttk.Radiobutton(type_frame, text="影片 (MP4)", variable=self.download_type, value="video").pack(side=tk.LEFT, padx=20)
        
        # 音訊品質選擇（僅音訊模式）
        self.audio_quality_frame = ttk.LabelFrame(main_frame, text="音訊品質", padding="10")
        self.audio_quality_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.audio_quality = tk.StringVar(value="192")
        ttk.Radiobutton(self.audio_quality_frame, text="128 kbps", variable=self.audio_quality, value="128").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(self.audio_quality_frame, text="192 kbps", variable=self.audio_quality, value="192").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(self.audio_quality_frame, text="256 kbps", variable=self.audio_quality, value="256").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(self.audio_quality_frame, text="320 kbps", variable=self.audio_quality, value="320").pack(side=tk.LEFT, padx=10)
        
        # 影片品質選擇（僅影片模式）
        self.video_quality_frame = ttk.LabelFrame(main_frame, text="影片品質", padding="10")
        self.video_quality_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.video_quality_frame.grid_remove()  # 初始隱藏
        
        self.video_quality = tk.StringVar(value="1080p")
        ttk.Radiobutton(self.video_quality_frame, text="720p", variable=self.video_quality, value="720p").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(self.video_quality_frame, text="1080p", variable=self.video_quality, value="1080p").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(self.video_quality_frame, text="最佳品質", variable=self.video_quality, value="best").pack(side=tk.LEFT, padx=10)
        
        # 監聽下載類型變化
        self.download_type.trace('w', self.on_download_type_change)
        
        # Cookies 設定
        cookies_frame = ttk.LabelFrame(main_frame, text="⚠️ Cookies 設定（必須！解決機器人驗證）", padding="10")
        cookies_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 說明標籤
        info_label = ttk.Label(
            cookies_frame, 
            text="如遇「Sign in to confirm you're not a bot」錯誤，請先在瀏覽器登入 YouTube，然後選擇對應瀏覽器：",
            foreground="red"
        )
        info_label.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        # Safari 警告標籤
        if platform.system() == "Darwin":  # macOS
            safari_warning = ttk.Label(
                cookies_frame,
                text="⚠ macOS 用戶注意：Safari 需要「完全磁碟取用權限」，建議使用 Chrome 或 Firefox！",
                foreground="orange",
                font=("", 9, "bold")
            )
            safari_warning.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        browser_frame = ttk.Frame(cookies_frame)
        browser_frame.pack(fill=tk.X)
        
        ttk.Label(browser_frame, text="從瀏覽器匯入 Cookies:").pack(side=tk.LEFT, padx=5)
        
        self.browser_choice = tk.StringVar(value="none")
        browsers = [
            ("不使用", "none"),
            ("Chrome", "chrome"),
            ("Firefox", "firefox"),
            ("Safari", "safari"),
            ("Edge", "edge"),
            ("Brave", "brave")
        ]
        
        for text, value in browsers:
            ttk.Radiobutton(browser_frame, text=text, variable=self.browser_choice, value=value).pack(side=tk.LEFT, padx=5)
        
        # 輸出目錄選擇
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(dir_frame, text="輸出目錄:").pack(side=tk.LEFT, padx=5)
        self.dir_label = ttk.Label(dir_frame, text=self.output_dir, relief=tk.SUNKEN, width=50)
        self.dir_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="選擇目錄", command=self.choose_directory).pack(side=tk.LEFT, padx=5)
        
        # 下載按鈕
        self.download_btn = ttk.Button(main_frame, text="開始下載", command=self.start_download, style="Accent.TButton")
        self.download_btn.grid(row=8, column=0, columnspan=3, pady=10)
        
        # 進度條
        self.progress_var = tk.DoubleVar()
        self.progress_bar = Progressbar(main_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_label = ttk.Label(main_frame, text="等待中...")
        self.progress_label.grid(row=10, column=0, columnspan=3, pady=5)
        
        # 日誌輸出區
        log_frame = ttk.LabelFrame(main_frame, text="下載日誌", padding="10")
        log_frame.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(11, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=80, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # FFmpeg 狀態
        if self.ffmpeg_path:
            ffmpeg_status = f"✓ FFmpeg 已就緒 ({platform.system()})"
        else:
            ffmpeg_status = "⚠ 未找到 FFmpeg"
        
        self.status_label = ttk.Label(main_frame, text=ffmpeg_status)
        self.status_label.grid(row=12, column=0, columnspan=3, pady=5)
        
        # 下載 FFmpeg 按鈕（如果未找到）
        if not self.ffmpeg_path:
            self.download_ffmpeg_btn = ttk.Button(
                main_frame, 
                text="下載並安裝 FFmpeg", 
                command=self.auto_download_ffmpeg
            )
            self.download_ffmpeg_btn.grid(row=13, column=0, columnspan=3, pady=5)
    
    def auto_download_ffmpeg(self):
        """自動下載 FFmpeg（背景執行緒）"""
        self.download_ffmpeg_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._download_ffmpeg_thread, daemon=True).start()
    
    def _download_ffmpeg_thread(self):
        """下載 FFmpeg 的執行緒"""
        ffmpeg_path = self.download_ffmpeg()
        if ffmpeg_path:
            self.ffmpeg_path = ffmpeg_path
            self.setup_ffmpeg()
            self.root.after(0, lambda: self.status_label.config(
                text=f"✓ FFmpeg 已就緒 ({platform.system()})"
            ))
            self.root.after(0, lambda: messagebox.showinfo("成功", "FFmpeg 安裝完成！"))
            if hasattr(self, 'download_ffmpeg_btn'):
                self.root.after(0, self.download_ffmpeg_btn.grid_remove)
        else:
            self.root.after(0, lambda: self.download_ffmpeg_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: messagebox.showerror(
                "錯誤", 
                "FFmpeg 自動安裝失敗。\n\n請手動安裝：\n" +
                "Windows: 下載並解壓到程式目錄\n" +
                "macOS: brew install ffmpeg\n" +
                "Linux: sudo apt-get install ffmpeg"
            ))
    
    def on_download_type_change(self, *args):
        """當下載類型改變時切換品質選項"""
        if self.download_type.get() == "audio":
            self.audio_quality_frame.grid()
            self.video_quality_frame.grid_remove()
        else:
            self.audio_quality_frame.grid_remove()
            self.video_quality_frame.grid()
    
    def log(self, message):
        """添加日誌訊息"""
        self.log_queue.put(message)
    
    def update_log(self):
        """更新日誌顯示"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_log)
    
    def choose_directory(self):
        """選擇輸出目錄"""
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.dir_label.config(text=self.output_dir)
            self.setup_output_dir()
            self.log(f"輸出目錄已變更為: {self.output_dir}")
    
    def fetch_playlist(self):
        """取得播放清單"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "請輸入 YouTube 網址！")
            return
        
        # 檢查是否為播放清單
        if 'list=' not in url:
            messagebox.showinfo("提示", "這不是播放清單網址，將直接下載單一影片。")
            return
        
        self.log("正在取得播放清單資訊...")
        self.fetch_playlist_btn.config(state=tk.DISABLED)
        
        # 在新執行緒中取得播放清單
        threading.Thread(target=self._fetch_playlist_thread, args=(url,), daemon=True).start()
    
    def _fetch_playlist_thread(self, url):
        """取得播放清單的執行緒函數"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': False,
                'nocheckcertificate': True,  # 跳過 SSL 憑證驗證
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    # 清空現有項目
                    self.root.after(0, lambda: self.playlist_tree.delete(*self.playlist_tree.get_children()))
                    
                    playlist_title = info.get('title', '播放清單')
                    total_videos = len(info['entries'])
                    
                    self.log(f"找到播放清單: {playlist_title}")
                    self.log(f"共 {total_videos} 個影片")
                    
                    # 添加到樹狀視圖
                    for idx, entry in enumerate(info['entries'], 1):
                        if entry:
                            title = entry.get('title', f'影片 {idx}')
                            duration = entry.get('duration', 0)
                            duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "未知"
                            video_url = entry.get('url', '') or f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                            
                            self.root.after(0, lambda t=title, d=duration_str, u=video_url: 
                                          self.playlist_tree.insert("", tk.END, values=(t, d, u), tags=('unchecked',)))
                    
                    # 顯示播放清單框架
                    self.root.after(0, self.playlist_frame.grid)
                    self.log("播放清單載入完成！")
                else:
                    self.log("這不是播放清單網址")
        
        except Exception as e:
            self.log(f"取得播放清單失敗: {str(e)}")
        finally:
            self.root.after(0, lambda: self.fetch_playlist_btn.config(state=tk.NORMAL))
    
    def select_all_playlist(self):
        """全選播放清單項目"""
        for item in self.playlist_tree.get_children():
            self.playlist_tree.item(item, tags=('checked',))
            # 添加勾選標記
            values = self.playlist_tree.item(item)['values']
            self.playlist_tree.item(item, text="✓")
    
    def deselect_all_playlist(self):
        """取消全選播放清單項目"""
        for item in self.playlist_tree.get_children():
            self.playlist_tree.item(item, tags=('unchecked',))
            self.playlist_tree.item(item, text="")
    
    def download_selected_playlist(self):
        """下載選中的播放清單項目"""
        # 切換選中狀態
        selected = self.playlist_tree.selection()
        for item in selected:
            current_tags = self.playlist_tree.item(item)['tags']
            if 'checked' in current_tags:
                self.playlist_tree.item(item, tags=('unchecked',))
                self.playlist_tree.item(item, text="")
            else:
                self.playlist_tree.item(item, tags=('checked',))
                self.playlist_tree.item(item, text="✓")
        
        # 如果是點擊按鈕，開始下載
        if not selected:
            # 取得所有已勾選的項目
            checked_items = []
            for item in self.playlist_tree.get_children():
                if 'checked' in self.playlist_tree.item(item)['tags']:
                    values = self.playlist_tree.item(item)['values']
                    checked_items.append(values[2])  # URL
            
            if not checked_items:
                messagebox.showwarning("警告", "請先選擇要下載的項目！")
                return
            
            self.log(f"準備下載 {len(checked_items)} 個項目...")
            threading.Thread(target=self._download_playlist_thread, args=(checked_items,), daemon=True).start()
    
    # 綁定點擊事件
    def on_playlist_click(self, event):
        """處理播放清單項目點擊"""
        item = self.playlist_tree.selection()
        if item:
            for i in item:
                current_tags = self.playlist_tree.item(i)['tags']
                if 'checked' in current_tags:
                    self.playlist_tree.item(i, tags=('unchecked',))
                    self.playlist_tree.item(i, text="")
                else:
                    self.playlist_tree.item(i, tags=('checked',))
                    self.playlist_tree.item(i, text="✓")
    
    def _download_playlist_thread(self, urls):
        """下載播放清單的執行緒函數"""
        self.is_downloading = True
        self.root.after(0, lambda: self.download_btn.config(state=tk.DISABLED))
        
        success_count = 0
        total = len(urls)
        
        for idx, url in enumerate(urls, 1):
            self.log(f"\n{'='*50}")
            self.log(f"下載進度: {idx}/{total}")
            self.log(f"{'='*50}")
            
            if self._download_single(url):
                success_count += 1
            
            # 更新整體進度
            overall_progress = (idx / total) * 100
            self.root.after(0, lambda p=overall_progress: self.progress_var.set(p))
        
        self.log(f"\n批次下載完成！成功: {success_count}/{total}")
        self.is_downloading = False
        self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.progress_label.config(text="下載完成！"))
    
    def start_download(self):
        """開始下載"""
        if self.is_downloading:
            messagebox.showwarning("警告", "已有下載任務正在進行！")
            return
        
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "請輸入 YouTube 網址！")
            return
        
        if not self.is_valid_youtube_url(url):
            messagebox.showerror("錯誤", "無效的 YouTube 網址！")
            return
        
        self.log(f"開始下載: {url}")
        self.download_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # 在新執行緒中下載
        threading.Thread(target=self._download_thread, args=(url,), daemon=True).start()
    
    def _download_thread(self, url):
        """下載執行緒"""
        self.is_downloading = True
        success = self._download_single(url)
        self.is_downloading = False
        
        self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
        
        if success:
            self.root.after(0, lambda: messagebox.showinfo("成功", "下載完成！"))
        else:
            self.root.after(0, lambda: messagebox.showerror("錯誤", "下載失敗！"))
    
    def _download_single(self, url):
        """下載單一影片/音訊"""
        try:
            # 取得影片資訊時也使用 cookies
            info_opts = {'quiet': True, 'nocheckcertificate': True}
            
            browser = self.browser_choice.get()
            if browser != "none":
                try:
                    info_opts['cookiesfrombrowser'] = (browser,)
                    self.log(f"使用 {browser.capitalize()} 瀏覽器的 Cookies")
                except Exception as cookie_error:
                    # Safari 在 macOS 上可能有權限問題
                    if browser == "safari" and platform.system() == "Darwin":
                        self.log(f"⚠ Safari Cookies 讀取失敗: {str(cookie_error)}")
                        self.log("💡 Safari 需要完全磁碟存取權限")
                        self.log("請改用 Chrome 或 Firefox，或按照以下步驟授予權限：")
                        self.log("1. 系統偏好設定 > 安全性與隱私 > 隱私權")
                        self.log("2. 選擇「完全磁碟取用權限」")
                        self.log("3. 點擊 + 並添加終端機或此應用程式")
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Safari 權限問題",
                            "無法讀取 Safari 的 Cookies！\n\n" +
                            "macOS 的 Safari 需要「完全磁碟取用權限」。\n\n" +
                            "建議：\n" +
                            "• 改用 Chrome 或 Firefox（推薦）\n" +
                            "• 或授予權限：\n" +
                            "  系統偏好設定 > 安全性與隱私 > 隱私權 >\n" +
                            "  完全磁碟取用權限 > 添加終端機"
                        ))
                        # 移除 cookies 設定，嘗試不使用 cookies
                        info_opts.pop('cookiesfrombrowser', None)
                    else:
                        raise
            
            # 取得影片資訊
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = self.sanitize_filename(info.get('title', 'download'))
                self.total_duration = info.get('duration', 0)
            
            self.log(f"標題: {title}")
            if self.total_duration > 0:
                duration_str = f"{int(self.total_duration // 3600):02d}:{int((self.total_duration % 3600) // 60):02d}:{int(self.total_duration % 60):02d}"
                self.log(f"長度: {duration_str}")
            
            # 根據下載類型設定選項
            if self.download_type.get() == "audio":
                success = self._download_audio(url, title)
            else:
                success = self._download_video(url, title)
            
            return success
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"✗ 下載失敗: {error_msg}")
            
            # 檢查是否為機器人驗證問題
            if "bot" in error_msg.lower() or "sign in" in error_msg.lower():
                self.log("\n" + "="*50)
                self.log("🤖 偵測到機器人驗證問題！")
                self.log("="*50)
                
                if browser == "none":
                    self.log("💡 解決方法：")
                    self.log("1. 在您的瀏覽器（Chrome/Firefox）登入 YouTube")
                    self.log("   ⚠ 注意：Safari 在 macOS 上需要額外權限，建議用 Chrome")
                    self.log("2. 在「Cookies 設定」區域選擇對應的瀏覽器")
                    self.log("3. 重新嘗試下載")
                    self.log("")
                    
                    # 顯示彈窗提示
                    self.root.after(0, lambda: messagebox.showwarning(
                        "需要 Cookies 驗證",
                        "YouTube 要求驗證！\n\n" +
                        "請按照以下步驟操作：\n\n" +
                        "1. 在 Chrome 或 Firefox 瀏覽器登入 YouTube\n" +
                        "   （建議用 Chrome，Safari 需要額外權限）\n" +
                        "2. 在下方「Cookies 設定」選擇對應的瀏覽器\n" +
                        "3. 重新嘗試下載\n\n" +
                        "這樣可以使用您的登入狀態繞過機器人驗證。"
                    ))
                else:
                    self.log(f"⚠ 已選擇 {browser.capitalize()} 但仍失敗")
                    self.log("💡 可能的原因：")
                    self.log(f"1. {browser.capitalize()} 瀏覽器未登入 YouTube")
                    self.log(f"2. {browser.capitalize()} 的 Cookies 已過期")
                    
                    if browser == "safari" and platform.system() == "Darwin":
                        self.log("3. Safari 需要「完全磁碟取用權限」（macOS 限制）")
                        self.log("   建議：改用 Chrome 或 Firefox")
                    else:
                        self.log("3. 瀏覽器版本不相容")
                    
                    self.log("")
                    self.log("建議：重新登入 YouTube 或嘗試其他瀏覽器（推薦 Chrome）")
                    
                    # 顯示彈窗提示
                    self.root.after(0, lambda b=browser: messagebox.showerror(
                        "Cookies 驗證失敗",
                        f"無法從 {b.capitalize()} 讀取有效的 Cookies！\n\n" +
                        f"請確認：\n" +
                        f"1. {b.capitalize()} 瀏覽器已登入 YouTube\n" +
                        f"2. {b.capitalize()} 瀏覽器保持開啟狀態\n" +
                        ("3. Safari 需要「完全磁碟取用權限」\n\n建議改用 Chrome 或 Firefox！" if b == "safari" else "3. 嘗試在瀏覽器中重新登入 YouTube")
                    ))
            
            import traceback
            traceback.print_exc()
            return False
    
    def _download_audio(self, url, title):
        """下載音訊"""
        quality = self.audio_quality.get()
        
        # 設定 FFmpeg 路徑
        ffmpeg_location = None
        if self.ffmpeg_path:
            if os.path.isabs(self.ffmpeg_path) and os.path.exists(self.ffmpeg_path):
                # 如果是絕對路徑，使用目錄
                ffmpeg_location = os.path.dirname(self.ffmpeg_path)
            else:
                # 如果只是命令名稱 (如 "ffmpeg")，設為 None 讓系統自動尋找
                ffmpeg_location = None
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'outtmpl': os.path.join(self.output_dir, f'{title}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [self.progress_hook],
            'postprocessor_hooks': [self.postprocessor_hook],
            'ffmpeg_location': ffmpeg_location,
            'nocheckcertificate': True,  # 跳過 SSL 憑證驗證
        }
        
        # 添加 cookies 支援
        browser = self.browser_choice.get()
        if browser != "none":
            ydl_opts['cookiesfrombrowser'] = (browser,)
            self.log(f"使用 {browser.capitalize()} 瀏覽器的 Cookies")
        
        try:
            self.root.after(0, lambda: self.progress_label.config(text="正在下載..."))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.log(f"✓ 下載完成: {title}.mp3")
            return True
            
        except Exception as e:
            self.log(f"✗ 下載失敗: {str(e)}")
            if "bot" in str(e).lower() or "sign in" in str(e).lower():
                self.log("💡 提示：請在 Cookies 設定中選擇您的瀏覽器以解決機器人驗證問題")
            return False
    
    def _download_video(self, url, title):
        """下載影片"""
        quality = self.video_quality.get()
        
        # 根據品質選擇格式
        if quality == "720p":
            format_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        elif quality == "1080p":
            format_str = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        else:
            format_str = 'bestvideo+bestaudio/best'
        
        # 設定 FFmpeg 路徑
        ffmpeg_location = None
        if self.ffmpeg_path:
            if os.path.isabs(self.ffmpeg_path) and os.path.exists(self.ffmpeg_path):
                # 如果是絕對路徑，使用目錄
                ffmpeg_location = os.path.dirname(self.ffmpeg_path)
            else:
                # 如果只是命令名稱 (如 "ffmpeg")，設為 None 讓系統自動尋找
                ffmpeg_location = None
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.output_dir, f'{title}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [self.progress_hook],
            'postprocessor_hooks': [self.postprocessor_hook],
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_location,
            'nocheckcertificate': True,  # 跳過 SSL 憑證驗證
        }
        
        # 添加 cookies 支援
        browser = self.browser_choice.get()
        if browser != "none":
            ydl_opts['cookiesfrombrowser'] = (browser,)
            self.log(f"使用 {browser.capitalize()} 瀏覽器的 Cookies")
        
        # 如果需要合併音視頻,添加後處理器
        if '+' in format_str:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        
        try:
            self.root.after(0, lambda: self.progress_label.config(text="正在下載..."))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.log(f"✓ 下載完成: {title}.mp4")
            return True
            
        except Exception as e:
            self.log(f"✗ 下載失敗: {str(e)}")
            if "bot" in str(e).lower() or "sign in" in str(e).lower():
                self.log("💡 提示：請在 Cookies 設定中選擇您的瀏覽器以解決機器人驗證問題")
            return False
    
    def progress_hook(self, d):
        """下載進度回調"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            if total:
                percentage = (downloaded / total) * 100
                speed = d.get('speed', 0)
                speed_mb = speed / 1024 / 1024 if speed else 0
                eta = d.get('eta', 0)
                
                self.root.after(0, lambda p=percentage: self.progress_var.set(p))
                self.root.after(0, lambda p=percentage, s=speed_mb, e=eta: self.progress_label.config(
                    text=f"下載中: {p:.1f}% | 速度: {s:.2f} MB/s | 剩餘: {e}s"
                ))
        
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.progress_label.config(text="下載完成，正在處理..."))
            self.log("✓ 檔案下載完成")
            
            # 只有在音訊下載時才啟動轉換監控（因為需要轉換成 MP3）
            if self.download_type.get() == "audio" and self.total_duration > 0:
                threading.Thread(target=self.monitor_conversion, daemon=True).start()
    
    def postprocessor_hook(self, d):
        """後處理進度回調"""
        if d['status'] == 'started':
            self.is_converting = True
            self.log("開始轉換...")
            self.root.after(0, lambda: self.progress_label.config(text="正在轉換格式..."))
        elif d['status'] == 'finished':
            self.is_converting = False
            self.log("✓ 格式轉換完成")
            self.root.after(0, lambda: self.progress_label.config(text="處理完成！"))
            self.root.after(0, lambda: self.progress_var.set(100))
    
    def monitor_conversion(self):
        """監控轉換進度"""
        if self.total_duration <= 0:
            return
        
        start_time = time.time()
        max_wait_time = max(10, self.total_duration * 0.5)  # 最多等待影片長度的一半時間，但至少10秒
        
        while self.is_converting and (time.time() - start_time < max_wait_time):
            elapsed = time.time() - start_time
            
            # 估算進度（基於已耗時）
            estimated_progress = min(95, (elapsed / max_wait_time) * 100)
            
            elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
            
            self.root.after(0, lambda p=estimated_progress, e=elapsed_str: 
                          self.progress_label.config(text=f"轉換中: {p:.1f}% | 已耗時: {e}"))
            
            time.sleep(0.5)
        
        # 如果轉換已完成，不要覆蓋「處理完成」的訊息
        if not self.is_converting:
            return
        
        # 如果超時仍在轉換中，記錄警告但不影響使用
        if self.is_converting:
            self.log("⚠ 轉換時間較長，請耐心等待...")
            elapsed_str = f"{int((time.time() - start_time) // 60):02d}:{int((time.time() - start_time) % 60):02d}"
            self.root.after(0, lambda e=elapsed_str: 
                          self.progress_label.config(text=f"轉換中... | 已耗時: {e}"))
    
    def sanitize_filename(self, filename):
        """清理檔名"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip()
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
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

def main():
    """主程式"""
    root = tk.Tk()
    
    # 設定主題樣式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 綁定播放清單點擊事件
    app = YouTubeDownloaderGUI(root)
    app.playlist_tree.bind('<Button-1>', app.on_playlist_click)
    
    # 啟動主迴圈
    root.mainloop()

if __name__ == "__main__":
    main()
