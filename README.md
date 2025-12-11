# YouTube 下載器 🎵🎬

一個功能完整的 YouTube 影片/音訊下載工具，支援 GUI 圖形介面和命令列操作。

## ✨ 功能特色

### 🖥️ GUI 版本 (`dl_gui.py`)
- **直覺的圖形介面** - 使用 tkinter 打造的現代化 GUI
- **雙模式下載** - 支援純音訊 (MP3) 和影片 (MP4) 下載
- **播放清單支援** - 可批次下載整個 YouTube 播放清單
- **多種品質選擇**
  - 音訊：128/192/256/320 kbps
  - 影片：720p/1080p/最佳品質
- **瀏覽器 Cookies 整合** - 繞過 YouTube 機器人驗證
  - 支援 Chrome、Firefox、Safari、Edge、Brave
  - macOS 用戶建議使用 Chrome 或 Firefox（Safari 需要額外權限）
- **即時進度顯示** - 下載速度、進度條、剩餘時間
- **自動 FFmpeg 設定** - 智慧偵測並配置 FFmpeg
- **詳細日誌輸出** - 方便追蹤下載狀態

### 💻 命令列版本 (`dl2.py`)
- **進階格式選擇** - 查看並選擇特定音訊格式
- **批次下載** - 從文件讀取多個連結批次下載
- **Metadata 支援** - 自動添加標題、藝術家和封面
- **互動式選單** - 友善的命令列介面
- **快速下載模式** - 支援命令列參數直接下載

## 📋 系統需求

- **Python 3.7+**
- **FFmpeg** (音訊轉換必需)
- **作業系統**：Windows、macOS、Linux

## 🚀 安裝步驟

### 1. 克隆專案
```bash
git clone https://github.com/YOUR_USERNAME/youtube_download.git
cd youtube_download
```

### 2. 建立虛擬環境（建議）
```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 4. 安裝 FFmpeg

#### macOS (使用 Homebrew)
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

#### Windows
1. 從 [FFmpeg 官網](https://ffmpeg.org/download.html) 下載
2. 解壓到專案目錄或系統 PATH
3. 或使用程式內建的自動下載功能

## 📖 使用方法

### GUI 版本

```bash
python dl_gui.py
```

**操作步驟：**
1. 輸入 YouTube 影片或播放清單網址
2. 選擇下載類型（音訊/影片）
3. 選擇品質
4. **重要：如遇機器人驗證**
   - 在瀏覽器（Chrome/Firefox）登入 YouTube
   - 在「Cookies 設定」選擇對應瀏覽器
5. 點擊「開始下載」

### 命令列版本

#### 互動式選單
```bash
python dl2.py
```

#### 快速下載模式
```bash
# 基本使用
python dl2.py "https://youtu.be/VIDEO_ID"

# 指定輸出目錄
python dl2.py "https://youtu.be/VIDEO_ID" -o ./my_music

# 指定音質
python dl2.py "https://youtu.be/VIDEO_ID" -q 320

# 指定格式
python dl2.py "https://youtu.be/VIDEO_ID" -fmt bestaudio
```

#### 批次下載
建立 `urls.txt` 檔案：
```
https://youtu.be/VIDEO_ID_1
https://youtu.be/VIDEO_ID_2
https://youtu.be/VIDEO_ID_3
# 這是註解，會被忽略
```

執行批次下載：
```bash
python dl2.py
# 選擇選項 2
```

## 🔧 進階設定

### 解決 macOS Safari Cookies 權限問題

Safari 需要「完全磁碟取用權限」才能讀取 Cookies：

1. 系統偏好設定 > 安全性與隱私 > 隱私權
2. 選擇「完全磁碟取用權限」
3. 點擊 + 並添加「終端機」應用程式
4. 重新啟動程式

**建議：直接使用 Chrome 或 Firefox，無需額外設定！**

### 自訂 FFmpeg 路徑

如果 FFmpeg 未自動偵測，可手動設定：

**GUI 版本：**
- 程式會在啟動時提示下載或設定

**命令列版本：**
```bash
python dl2.py -f /path/to/ffmpeg
```

## 📁 專案結構

```
youtube_download/
├── dl_gui.py              # GUI 版本主程式
├── dl2.py                 # 命令列版本主程式
├── dl.py                  # 簡化版（舊版）
├── requirements.txt       # Python 相依套件
├── README.md             # 專案說明文件
├── .gitignore            # Git 忽略檔案
├── downloads/            # 預設下載目錄（自動建立）
└── .venv/                # 虛擬環境（建議）
```

## 🐛 常見問題

### Q: 出現「Sign in to confirm you're not a bot」錯誤
**A:** 這是 YouTube 的機器人驗證。解決方法：
1. 在 Chrome 或 Firefox 登入 YouTube
2. 在程式的「Cookies 設定」選擇對應瀏覽器
3. 重新下載

### Q: FFmpeg not found
**A:** 請按照「安裝 FFmpeg」章節安裝，或使用 GUI 的自動下載功能

### Q: SSL Certificate 錯誤
**A:** 程式已內建處理，如仍有問題請更新 `certifi`：
```bash
pip install --upgrade certifi
```

### Q: macOS Safari Cookies 讀取失敗
**A:** Safari 需要額外權限，建議改用 Chrome 或 Firefox

### Q: 下載速度很慢
**A:** 
- 檢查網路連線
- 嘗試選擇較低的品質
- YouTube 可能有限速，請稍後再試

## 🔒 隱私與安全

- 本程式僅用於個人使用
- 不會收集或上傳任何個人資訊
- Cookies 僅用於繞過 YouTube 驗證，不會儲存或傳送
- 請遵守 YouTube 服務條款和著作權法規

## 📝 授權

MIT License

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## ⚠️ 免責聲明

本工具僅供學習和個人使用。請尊重內容創作者的著作權，不要用於商業用途或非法下載受版權保護的內容。

## 📮 聯絡方式

如有問題或建議，請透過 GitHub Issues 聯絡。

---

**享受您的下載體驗！** 🎉

如果覺得有幫助，請給個 ⭐ Star！
