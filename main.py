import os
import re
import sys
import json
import asyncio
import subprocess
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import yt_dlp
import google.generativeai as genai

# Enable standard output encoding for Chinese characters in Windows terminal
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# --- Configuration ---
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(WORKSPACE_DIR, "docs")
ARCHIVE_DIR = os.path.join(DOCS_DIR, "archive")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp_assets")

# Load local .env file if it exists (with .env.txt fallback for Windows users)
dotenv_path = os.path.join(WORKSPACE_DIR, ".env")
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(WORKSPACE_DIR, ".env.txt")

if os.path.exists(dotenv_path):
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# Ensure folders exist
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


# --- Helper Functions ---

def check_ffmpeg():
    """Check if ffmpeg is available in the system PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except Exception:
        return False


def clean_vtt_subtitles(vtt_path):
    """Clean VTT subtitles file to extract unique readable text."""
    if not os.path.exists(vtt_path):
        return ""
    
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        cleaned_lines = []
        timestamp_regex = re.compile(r'\d{2}:\d{2}:\d{2}')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if 'WEBVTT' in line or 'Kind:' in line or 'Language:' in line:
                continue
            if timestamp_regex.search(line):
                continue
            
            # Remove XML/HTML formatting tags like <c> or </c>
            line = re.sub(r'<[^>]+>', '', line)
            
            # Add to list if not identical to the last added line
            if not cleaned_lines or cleaned_lines[-1] != line:
                cleaned_lines.append(line)
                
        text = " ".join(cleaned_lines)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        print(f"Error cleaning VTT subtitles {vtt_path}: {e}")
        return ""


# --- YouTube Scraper Mod ---

def fetch_youtube_videos(query_or_url, limit=5):
    """Fetch video metadata list from search query or channel URL."""
    print(f"Fetching video list for: {query_or_url} (limit: {limit})")
    ydl_opts = {
        'extract_flat': True,
        'playlistend': limit,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query_or_url, download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'description': entry.get('description', ''),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}"
                        })
            elif info:
                # Single video case
                videos.append({
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description', ''),
                    'url': f"https://www.youtube.com/watch?v={info.get('id')}"
                })
        except Exception as e:
            print(f"Error extracting info for {query_or_url}: {e}")
    return videos


def download_subtitles(video_id, temp_dir):
    """Download automatic subtitles for a video and return the file path."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    outtmpl = os.path.join(temp_dir, f"sub_{video_id}")
    ydl_opts = {
        'writeautosub': True,
        'skip_download': True,
        'subtitlesformat': 'vtt',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    print(f"Downloading subtitles for video: {video_id}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
            # yt-dlp appends the language code, e.g. sub_VIDEO_ID.en.vtt or sub_VIDEO_ID.en-US.vtt
            for f in os.listdir(temp_dir):
                if f.startswith(f"sub_{video_id}") and f.endswith(".vtt"):
                    return os.path.join(temp_dir, f)
        except Exception as e:
            print(f"Subtitles not available or download failed for {video_id}: {e}")
    return None


def get_all_scraped_videos_data():
    """Fetch transcripts and info for CNBC Fast Money, Closing Bell Overtime and IBD."""
    scraped_data = []
    
    # 1. CNBC Fast Money (Search Query)
    print("\n--- Scraping CNBC Fast Money ---")
    fm_videos = fetch_youtube_videos("ytsearch4:CNBC Fast Money", limit=4)
    for v in fm_videos:
        sub_file = download_subtitles(v['id'], TEMP_DIR)
        transcript = clean_vtt_subtitles(sub_file) if sub_file else ""
        scraped_data.append({
            'source': 'CNBC Fast Money',
            'title': v['title'],
            'description': v['description'],
            'transcript': transcript
        })
        
    # 2. CNBC Closing Bell: Overtime (Search Query)
    print("\n--- Scraping CNBC Closing Bell Overtime ---")
    cb_videos = fetch_youtube_videos("ytsearch4:CNBC Closing Bell Overtime", limit=4)
    for v in cb_videos:
        sub_file = download_subtitles(v['id'], TEMP_DIR)
        transcript = clean_vtt_subtitles(sub_file) if sub_file else ""
        scraped_data.append({
            'source': 'CNBC Closing Bell Overtime',
            'title': v['title'],
            'description': v['description'],
            'transcript': transcript
        })
        
    # 3. Investor's Business Daily (Channel Videos)
    print("\n--- Scraping Investor's Business Daily ---")
    ibd_videos = fetch_youtube_videos("https://www.youtube.com/@investorsbusinessdaily/videos", limit=3)
    for v in ibd_videos:
        sub_file = download_subtitles(v['id'], TEMP_DIR)
        transcript = clean_vtt_subtitles(sub_file) if sub_file else ""
        scraped_data.append({
            'source': "Investor's Business Daily",
            'title': v['title'],
            'description': v['description'],
            'transcript': transcript
        })
        
    return scraped_data


# --- Investing.com RSS Feed Scraper ---

def fetch_investing_news():
    """Parse Investing.com RSS feeds and extract news item headlines and links."""
    print("\n--- Scraping Investing.com News Feeds ---")
    urls = {
        '美股新聞': 'https://www.investing.com/rss/news_25.rss',
        '經濟指標': 'https://www.investing.com/rss/news_95.rss',
        '公司盈餘': 'https://www.investing.com/rss/news_1062.rss'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    news_items = []
    
    for category, url in urls.items():
        try:
            print(f"Fetching: {category} ({url})")
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                items = root.findall('.//item')
                print(f"Found {len(items)} items in {category}")
                for item in items[:8]:  # Get top 8 items per category
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    author = item.find('author').text if item.find('author') is not None else 'Investing.com'
                    
                    if title:
                        news_items.append({
                            'title': title,
                            'link': link,
                            'pubDate': pubDate,
                            'author': f"{author} ({category})"
                        })
            else:
                print(f"Failed to fetch {category}, Status: {r.status_code}")
        except Exception as e:
            print(f"Error parsing RSS {category}: {e}")
            
    return news_items


# --- Gemini Analysis & Script Generator ---

def generate_insights_and_podcast(scraped_videos, news_items):
    """Aggregate data and call Gemini API to generate the report and dialogue JSON."""
    print("\n--- Sending request to Google Gemini API ---")
    
    # Format YouTube data for prompt
    videos_text = ""
    for idx, v in enumerate(scraped_videos):
        videos_text += f"\n【來源: {v['source']}】\n"
        videos_text += f"標題: {v['title']}\n"
        desc = v.get('description') or ""
        videos_text += f"描述: {desc[:300]}...\n"
        if v['transcript']:
            videos_text += f"字幕全文摘要: {v['transcript'][:1500]}...\n"
        else:
            videos_text += "（無字幕，以標題和描述分析）\n"
        videos_text += "-" * 30
        
    # Format News data for prompt
    news_text = ""
    for idx, n in enumerate(news_items):
        news_text += f"- {n['title']} (來源: {n['author']}, 時間: {n['pubDate']})\n"

    # Assemble complete prompt
    prompt = f"""
你是一個資深的美股分析與產業專家，同時也是一位極具創意與人氣的 Podcast 製作人。
請仔細閱讀並整合以下收集到的當日最新美股市場資訊（包含 CNBC 和 IBD 節目音軌字幕摘要、Investing.com 當日即時財經頭條與盈餘數據）：

【YouTube 美股節目字幕/摘要】
{videos_text}

【Investing.com 財經頭條】
{news_text}

=========================================

請根據上述數據，產出一個結構化的 JSON 內容，必須嚴格符合以下格式與要求，且不要有額外的包裹文字或 HTML tags：

【輸出 JSON 結構需求】
{{
  "title": "今日美股動態與深度聲報",
  "written_report": {{
    "stock_analysis": "股市與產業分析內容（繁體中文，格式請使用 Markdown。需包含主要板塊走勢、強勢股突破或季報分析、特定產業趨勢）",
    "fund_flow": "資金流向內容（繁體中文，格式請使用 Markdown。需分析板塊輪動、避險情緒、法人機構動向與市場成交量討論）",
    "investment_advice": "長線投資建議內容（繁體中文，格式請使用 Markdown。需包含長期資產配置趨勢、可關注標的之技術與基本面建議）"
  }},
  "podcast_script": [
    {{
      "speaker": "HsiaoChen",
      "text": "主持人的話（繁體中文，台灣腔，口語化，例如：『哈囉大家，歡迎收聽今日的美股焦點聲報。我是 HsiaoChen。』）"
    }},
    {{
      "speaker": "YunJhe",
      "text": "專家的話（繁體中文，台灣腔，口語化，例如：『嗨，大家好，我是 YunJhe。今天美股真的有很多精彩的話題，特別是...』）"
    }}
    // 依此類推，設計 12 - 18 輪的男女對話，深入且生動地討論上述書面分析中的核心美股資訊。
    // 每段話長度大約 60-150 字，以保持談話順暢度，整體對話長度約在 1200 到 1800 字之間。
  ]
}}

【關鍵細節要求】
1. **繁體中文與台灣常用用語**：報告和對話中請務必使用台灣的財經與口語用語。例如：『板塊』可寫為『板塊類股』，並使用『升息/降息』、『季報/財報』、『指數/均線』。
2. **台灣腔口語發音語助詞**：對話必須像真實的台灣人對話，自然融入語助詞，如『對啊』、『沒錯』、『我覺得說...』、『像是...』、『這樣子』、『真的耶』。
3. **表情停頓與語調引導（極重要）**：對話文字中請適當多使用標點符號（如逗號『，』、頓號『、』、省略號『……』或空格）來引導語音引擎產生自然停頓，避免語氣聽起來過於機械化或機械式地一口氣唸完。
4. **角色名稱限制**：對話劇本的 `speaker` 欄位值僅能為 `"HsiaoChen"` (代表女聲主播) 與 `"YunJhe"` (代表男聲專家)，這與後續 TTS 的配音模型直接關聯。
"""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is missing!")
        sys.exit(1)
        
    genai.configure(api_key=api_key)
    
    # Use gemini-3.5-flash for compatibility and speed
    model = genai.GenerativeModel("gemini-3.5-flash")
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        print("Gemini response parsed successfully!")
        return data
    except Exception as e:
        print(f"Error calling or parsing Gemini API: {e}")
        # Fallback dictionary if API fails
        return {
            "title": f"美股每日聲報 ({datetime.now().strftime('%Y-%m-%d')})",
            "written_report": {
                "stock_analysis": "分析生成暫時失敗，請稍候重試或檢查 API 設定。",
                "fund_flow": "目前無資金流動資料。",
                "investment_advice": "目前無建議。"
            },
            "podcast_script": [
                {"speaker": "HsiaoChen", "text": "不好意思，今天我們的 AI 生成系統遇到了一些問題，請明天再收聽我們的精彩解析！"},
                {"speaker": "YunJhe", "text": "對啊，大家先看看 Investing.com 的頭條新聞，祝大家投資順利！"}
            ]
        }


# --- Edge TTS Audio Generator Mod ---

async def generate_voice_chunk(text, voice, output_path):
    """Async voice generator using edge-tts, optimized with a slight speed slowdown for natural pacing."""
    import edge_tts
    # Slowing down the speech rate by -6% makes neural voices sound much more human-like
    communicate = edge_tts.Communicate(text, voice, rate="-6%")
    await communicate.save(output_path)


async def generate_all_voices(script, temp_dir):
    """Generate individual voice mp3 files in parallel."""
    print("Generating voice audio chunks...")
    tasks = []
    temp_files = []
    
    for idx, turn in enumerate(script):
        speaker = turn.get('speaker', 'HsiaoChen')
        text = turn.get('text', '')
        # Map to Taiwanese Neural Voices
        voice = "zh-TW-HsiaoChenNeural" if speaker == "HsiaoChen" else "zh-TW-YunJheNeural"
        
        out_path = os.path.join(temp_dir, f"turn_{idx:03d}.mp3")
        temp_files.append(out_path)
        
        tasks.append(generate_voice_chunk(text, voice, out_path))
        
    await asyncio.gather(*tasks)
    return temp_files


def merge_audio_files(temp_files, temp_dir, output_mp3_path):
    """Merge separate speaker mp3 files with silence gaps using ffmpeg concat demuxer, falling back to binary append if ffmpeg is missing."""
    print("Merging audio chunks...")
    
    has_ffmpeg = check_ffmpeg()
    
    if has_ffmpeg:
        # 1. Generate a 0.5-second silent audio file matching format
        silence_file = os.path.join(temp_dir, "silence.mp3")
        # edge-tts output is generally 24000Hz mono.
        cmd_silence = [
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'anullsrc=r=24000:cl=mono', 
            '-t', '0.5', silence_file
        ]
        
        try:
            subprocess.run(cmd_silence, capture_output=True, check=True)
        except Exception as e:
            print(f"Error generating silence chunk: {e}. Proceeding without silence gaps.")
            silence_file = None

        # 2. Write the input list file for ffmpeg concat
        list_file_path = os.path.join(temp_dir, "input_list.txt")
        with open(list_file_path, 'w', encoding='utf-8') as f:
            for idx, file_path in enumerate(temp_files):
                # Using relative file names prevents path escaping bugs
                rel_path = os.path.basename(file_path)
                f.write(f"file '{rel_path}'\n")
                if silence_file and idx < len(temp_files) - 1:
                    f.write("file 'silence.mp3'\n")
                    
        # 3. Concatenate using ffmpeg
        cmd_concat = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', 'input_list.txt', '-c', 'copy', 'output_merged.mp3'
        ]
        
        try:
            # Run command with cwd inside the temp directory so paths are local
            subprocess.run(cmd_concat, cwd=temp_dir, capture_output=True, check=True)
            # Move final merged file to output path
            merged_temp_path = os.path.join(temp_dir, 'output_merged.mp3')
            if os.path.exists(merged_temp_path):
                if os.path.exists(output_mp3_path):
                    os.remove(output_mp3_path)
                import shutil
                shutil.move(merged_temp_path, output_mp3_path)
                print(f"Podcast successfully created using FFmpeg at: {output_mp3_path}")
                return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            print(f"Error during FFmpeg merge: {e}")
            
    # Binary concatenation fallback (no FFmpeg required)
    print("⚠️ FFmpeg 缺失或執行失敗。正在使用二進位拼接技術合併 MP3 檔案...")
    try:
        if os.path.exists(output_mp3_path):
            os.remove(output_mp3_path)
            
        with open(output_mp3_path, 'wb') as out_f:
            for file_path in temp_files:
                with open(file_path, 'rb') as in_f:
                    out_f.write(in_f.read())
                    
        print(f"Podcast 成功透過二進位拼接合併完成於: {output_mp3_path}")
        return True
    except Exception as e:
        print(f"二進位合併失敗: {e}")
        
    return False


# --- Main Pipeline Runner ---

def clean_temp_dir():
    """Delete all files inside TEMP_DIR and recreate it."""
    import shutil
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
        except Exception as e:
            print(f"Warning: could not clean temp folder: {e}")
    os.makedirs(TEMP_DIR, exist_ok=True)


def update_archive_list(date_str, title):
    """Add new report date to docs/archive_list.json in front, keeping top 30 unique items."""
    list_path = os.path.join(DOCS_DIR, "archive_list.json")
    archives = []
    
    if os.path.exists(list_path):
        try:
            with open(list_path, 'r', encoding='utf-8') as f:
                archives = json.load(f)
        except Exception:
            archives = []
            
    # Check if date already exists
    exists = any(item.get('date') == date_str for item in archives)
    if not exists:
        archives.insert(0, {
            "date": date_str,
            "title": title
        })
        
    # Cap archives to maximum 30 historical records
    archives = archives[:30]
    
    with open(list_path, 'w', encoding='utf-8') as f:
        json.dump(archives, f, ensure_ascii=False, indent=2)
    print("Archive registry list updated.")


def main():
    start_time = datetime.now()
    print(f"Pipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Fetch Investing.com headlines
    news_items = fetch_investing_news()
    
    # 2. Fetch YouTube transcripts and details
    scraped_videos = get_all_scraped_videos_data()
    
    # 3. Call Gemini to generate Report & Dialogue Script
    report_data = generate_insights_and_podcast(scraped_videos, news_items)
    
    # Add date and investing news items back to JSON data
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_data['date'] = date_str
    report_data['investing_news'] = news_items
    
    # 4. Generate audio podcast file
    audio_generated = False
    
    clean_temp_dir()
    try:
        # Generate speech files (run async loop)
        temp_files = asyncio.run(generate_all_voices(report_data.get('podcast_script', []), TEMP_DIR))
        
        # Destination audio paths
        latest_mp3 = os.path.join(DOCS_DIR, "latest.mp3")
        archive_mp3 = os.path.join(ARCHIVE_DIR, f"{date_str}.mp3")
        
        # Merge (uses FFmpeg if available, otherwise falls back to binary concat)
        audio_generated = merge_audio_files(temp_files, TEMP_DIR, latest_mp3)
        if audio_generated:
            # Copy to archive folder
            import shutil
            shutil.copy(latest_mp3, archive_mp3)
            print(f"Archived audio saved to: {archive_mp3}")
    except Exception as e:
        print(f"Error generating audio: {e}")
    finally:
        # Clean up files inside TEMP_DIR
        clean_temp_dir()

    # If audio generation failed, create a dummy or warning file so pages do not break
    latest_mp3 = os.path.join(DOCS_DIR, "latest.mp3")
    if not audio_generated and not os.path.exists(latest_mp3):
        # Create empty file or log error
        with open(latest_mp3, 'wb') as f:
            f.write(b'')
            
    # 5. Write reports JSON to docs/
    # Latest report json
    latest_json_path = os.path.join(DOCS_DIR, "latest.json")
    with open(latest_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"Latest report data saved to: {latest_json_path}")
    
    # Archive report json
    archive_json_path = os.path.join(ARCHIVE_DIR, f"{date_str}.json")
    with open(archive_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"Archived report data saved to: {archive_json_path}")
    
    # 6. Update list index
    update_archive_list(date_str, report_data.get('title', '美股動態焦點'))
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"Pipeline finished successfully in {duration:.1f} seconds at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
