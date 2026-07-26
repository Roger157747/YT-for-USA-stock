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
from email.utils import parsedate_to_datetime

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

def clean_json_text(text):
    """Extract the first valid JSON object from a string, ignoring markdown code blocks or trailing notes."""
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text


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
    """Download subtitles (both uploader-provided and automatic) for a video and return the file path."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    outtmpl = os.path.join(temp_dir, f"sub_{video_id}")
    ydl_opts = {
        'writesubtitles': True,
        'writeautosub': True,
        'skip_download': True,
        'subtitlesformat': 'vtt',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'subtitleslangs': ['zh-TW', 'zh-Hant', 'zh', 'en', 'all'],
    }
    print(f"Downloading subtitles for video: {video_id}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
            # yt-dlp appends the language code, e.g. sub_VIDEO_ID.en.vtt or sub_VIDEO_ID.zh-TW.vtt
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


def get_taiwan_shows_data():
    """Fetch transcripts and info for '錢線百分百' and '股市現場' filtered by the latest upload date."""
    scraped_data = []
    queries = {
        '錢線百分百': 'ytsearch15:錢線百分百',
        '股市現場': 'ytsearch15:股市現場'
    }
    
    for show_name, query in queries.items():
        print(f"\n--- Scraping Taiwan Show: {show_name} ---")
        ydl_opts = {
            'extract_flat': True,
            'playlistend': 15,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if not info or 'entries' not in info:
                    print(f"No videos found for show: {show_name}")
                    continue
                
                entries = [e for e in info['entries'] if e]
                
                # Extract dates from titles
                dates = []
                for e in entries:
                    title = e.get('title', '')
                    found_dates = re.findall(r'\d{8}', title)
                    if found_dates:
                        dates.extend(found_dates)
                
                if not dates:
                    print(f"No dates found in video titles for show: {show_name}")
                    # If no dates found, fallback to top 3 videos
                    matched_videos = entries[:3]
                else:
                    latest_date = max(dates)
                    print(f"Detected latest show date for {show_name}: {latest_date}")
                    
                    # Filter videos matching this date
                    matched_videos = []
                    for e in entries:
                        title = e.get('title', '')
                        if latest_date in title:
                            matched_videos.append(e)
                            
                    # Prioritize full videos ("整版" or "整集") if present to avoid duplication
                    has_full = any("整版" in e.get('title', '') or "整集" in e.get('title', '') for e in matched_videos)
                    if has_full:
                        matched_videos = [e for e in matched_videos if "整版" in e.get('title', '') or "整集" in e.get('title', '')]
                        print(f"Prioritized full episode segments for date {latest_date}")
                
                print(f"Processing {len(matched_videos)} videos for {show_name}:")
                for e in matched_videos:
                    video_id = e.get('id')
                    title = e.get('title', '')
                    sub_file = download_subtitles(video_id, TEMP_DIR)
                    transcript = clean_vtt_subtitles(sub_file) if sub_file else ""
                    scraped_data.append({
                        'source': show_name,
                        'title': title,
                        'description': e.get('description', ''),
                        'transcript': transcript
                    })
            except Exception as e:
                print(f"Error scraping Taiwan show {show_name}: {e}")
                
    return scraped_data


# --- Popular Finance Shows RSS Feed Scraper ---

def parse_date_to_string(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y/%m/%d")
    except Exception:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y/%m/%d")
        except Exception:
            return date_str[:10]

def fetch_finance_shows_news():
    """Fetch latest uploads from popular Taiwanese/US finance shows (Podcast & YouTube)."""
    print("\n--- Fetching Finance Shows Uploads ---")
    podcast_feeds = {
        "股癌": "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml",
        "財報狗-掌握台股美股時事議題": "https://feed.firstory.me/rss/user/clcftm46z000201z45w1c47fi",
        "CNBC Business News Update": "https://feeds.simplecast.com/oloBAvaH",
        "財經一路發": "https://feed.firstory.me/rss/user/ckuydilxj0ys508026gxkhbp4",
        "財富旺得福": "https://feed.firstory.me/rss/user/clz7uus5t0000ixvp9jpg3kv5"
    }
    youtube_feeds = {
        "只要錢長大": {
            "channel_id": "UCJcPWs0gpYMx_CghPdELUhw",
            "filter": "只要錢長大"
        },
        "財經號角": {
            "channel_id": "UC0lbAQVpenvfA2QqzsRtL_g",
            "filter": None
        },
        "財訊": {
            "channel_id": "UCh2hilgoPIY-kiy1yFCc-xA",
            "filter": None
        }
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    shows_data = []
    
    # 1. Fetch Podcast RSS
    for show, url in podcast_feeds.items():
        try:
            print(f"Fetching Podcast RSS for: {show}")
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                item = root.find('.//item')
                if item is not None:
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else url
                    pub_date_raw = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    pub_date = parse_date_to_string(pub_date_raw)
                    
                    desc = ""
                    desc_elem = item.find('description')
                    if desc_elem is not None and desc_elem.text:
                        desc = desc_elem.text
                    else:
                        itunes_sum = item.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}summary')
                        if itunes_sum is not None and itunes_sum.text:
                            desc = itunes_sum.text
                    
                    desc = re.sub(r'<[^>]+>', '', desc)
                    desc = re.sub(r'\s+', ' ', desc).strip()
                    
                    shows_data.append({
                        "show": show,
                        "title": title,
                        "link": link,
                        "pubDate": pub_date,
                        "rawDescription": desc[:800]
                    })
                else:
                    print(f"No item found for {show}")
            else:
                print(f"Failed to fetch podcast {show}: {r.status_code}")
        except Exception as e:
            print(f"Error parsing podcast feed {show}: {e}")
            
    # 2. Fetch YouTube RSS
    for show, config in youtube_feeds.items():
        try:
            print(f"Fetching YouTube RSS for: {show}")
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={config['channel_id']}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('.//atom:entry', ns)
                
                matched_entry = None
                if config['filter']:
                    for entry in entries:
                        title_elem = entry.find('atom:title', ns)
                        if title_elem is not None and config['filter'] in title_elem.text:
                            matched_entry = entry
                            break
                else:
                    if len(entries) > 0:
                        matched_entry = entries[0]
                        
                if matched_entry is not None:
                    title = matched_entry.find('atom:title', ns).text
                    link = matched_entry.find('atom:link', ns).attrib['href']
                    pub_date_raw = matched_entry.find('atom:published', ns).text
                    pub_date = parse_date_to_string(pub_date_raw)
                    
                    media_ns = {'media': 'http://search.yahoo.com/mrss/'}
                    desc = ""
                    media_desc = matched_entry.find('.//media:description', media_ns)
                    if media_desc is not None and media_desc.text:
                        desc = media_desc.text
                        
                    desc = re.sub(r'<[^>]+>', '', desc)
                    desc = re.sub(r'\s+', ' ', desc).strip()
                    
                    shows_data.append({
                        "show": show,
                        "title": title,
                        "link": link,
                        "pubDate": pub_date,
                        "rawDescription": desc[:800]
                    })
                else:
                    print(f"No matched entry found for YouTube: {show}")
            else:
                print(f"Failed to fetch YouTube RSS for {show}: {r.status_code}")
        except Exception as e:
            print(f"Error parsing YouTube RSS {show}: {e}")
            
    return shows_data


# --- Gemini Analysis & Script Generator ---

def generate_insights_and_podcast(scraped_videos, finance_shows):
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
        
    # Format Finance Shows data for prompt
    shows_text = ""
    for idx, s in enumerate(finance_shows):
        shows_text += f"\n【節目來源: {s['show']}】\n"
        shows_text += f"單集標題: {s['title']}\n"
        shows_text += f"發布日期: {s['pubDate']}\n"
        shows_text += f"節目資訊與描述: {s['rawDescription']}\n"
        shows_text += "-" * 30

    # Assemble complete prompt
    prompt = f"""
你是一個資深的美股分析與產業專家，同時也是一位極具創意與人氣的 Podcast 製作人。
請仔細閱讀並整合以下收集到的當日最新美股市場資訊（包含 CNBC 和 IBD 節目音軌字幕摘要、熱門財經 YouTube 與 Podcast 節目的最新描述與標題）：

【YouTube 美股節目字幕/摘要】
{videos_text}

【熱門財經影音最新單集資訊】
{shows_text}

=========================================

請根據上述數據，產出一個結構化的 JSON 內容，必須嚴格符合以下格式與要求，且不要有額外的包裹文字或 HTML tags：

【輸出 JSON 結構需求】
{{
  "title": "今日美股動態與深度聲報",
  "written_report": {{
    "stock_analysis": "指數及產業板塊分析內容（繁體中文，格式請使用 Markdown。需包含主要指數走勢如標普/那指/道瓊/費半、主要板塊走勢、強勢股突破或季報分析、特定產業趨勢）",
    "fund_flow": "資金流向內容（繁體中文，格式請使用 Markdown。需分析板塊輪動、避險情緒、法人機構動向與市場成交量討論）",
    "investment_advice": "長線投資建議內容（繁體中文，格式請使用 Markdown。需包含長期資產配置趨勢、可關注標的之技術與基本面建議）"
  }},
  "finance_shows": [
    {{
      "show": "節目來源名稱（字串，例如：股癌、財報狗-掌握台股美股時事議題、CNBC Business News Update、財經一路發、財富旺得福、只要錢長大、財經號角、財訊）",
      "title": "單集原標題（字串，直接沿用上方提供的單集標題，絕對不要做任何日期前綴修改，不要包含日期）",
      "link": "該節目的連結（字串，沿用提供給你的連結）",
      "pubDate": "發布日期（字串，格式為 YYYY/MM/DD）",
      "stocks": ["主要探討個股代碼/名稱1", "主要探討個股代碼/名稱2"...], // 陣列，提取該單集核心探討的所有個股，包含美股代號如 輝達 (NVDA)、蘋果 (AAPL) 或台股如 台積電 (2330)。若無提到個股則為空陣列。
      "issues": ["主要探討經濟與投資議題1", "主要探討經濟與投資議題2"...], // 陣列，提取該單集核心討論之股票、總體經濟、財報或投資議題（如：AI晶片需求放緩、美聯儲降息決議等）。
      "summary": "以繁體中文針對該單集標題與描述進行內容重點整理（字串，限 50 到 100 字，言簡意賅地敘述出該集的核心議題或觀點）。注意：請將『[月/日] 集數編號』（例如：『[07/25] EP682』；若是無集數編號的節目，請以『[月/日] 節目名稱』前綴，例如『[07/25] 只要錢長大』）顯示在 summary 文字描述的最前面，不要顯示在 title 上"
    }}
  ],
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
3. **表情停頓與語調引導（極重要）**：對話文字中請適當多使用標點符號（如逗號『，』、頓號『、』、省略號『……』或空格）來引導語音引擎產生自然停頓，避免語氣聽起來過於機械化或機械式地一口氣念完。
4. **角色名稱限制**：對話劇本的 `speaker` 欄位值僅能為 `"HsiaoChen"` 與 `"YunJhe"`。
"""

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing!")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(clean_json_text(response.text))
        print("Gemini response parsed successfully!")
        return data
    except Exception as e:
        print(f"Error calling or parsing Gemini API: {e}")
        # Fallback dictionary if API fails
        fallback_shows = []
        for s in finance_shows:
            ep_match = re.search(r'EP\d+', s['title'])
            prefix = ep_match.group(0) if ep_match else s['show']
            fallback_shows.append({
                "show": s['show'],
                "title": s['title'],
                "link": s['link'],
                "pubDate": s['pubDate'],
                "stocks": [],
                "issues": [],
                "summary": f"[{s['pubDate'][5:]}] {prefix} 重點整理：內容獲取暫時失敗，請至原影音連結觀看。"
            })
        return {
            "title": f"美股每日聲報 ({datetime.now().strftime('%Y-%m-%d')})",
            "written_report": {
                "stock_analysis": "分析生成暫時失敗，請稍候重試或檢查 API 設定。",
                "fund_flow": "目前無資金流動資料。",
                "investment_advice": "目前無建議。"
            },
            "finance_shows": fallback_shows,
            "podcast_script": [
                {"speaker": "HsiaoChen", "text": "不好意思，今天我們的 AI 生成系統遇到了一些問題，請明天再收聽我們的精彩解析！"},
                {"speaker": "YunJhe", "text": "對啊，大家先看看各影音節目的最新內容，祝大家投資順利！"}
            ]
        }


def generate_taiwan_insights_and_podcast(scraped_videos, finance_shows):
    """Aggregate Taiwan data and call Gemini API to generate the Taiwan stock report and dialogue JSON."""
    print("\n--- Sending Taiwan request to Google Gemini API ---")
    
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
        
    # Format Finance Shows data for prompt
    shows_text = ""
    for idx, s in enumerate(finance_shows):
        shows_text += f"\n【節目來源: {s['show']}】\n"
        shows_text += f"單集標題: {s['title']}\n"
        shows_text += f"發布日期: {s['pubDate']}\n"
        shows_text += f"節目資訊與描述: {s['rawDescription']}\n"
        shows_text += "-" * 30

    # Assemble complete prompt
    prompt = f"""
你是一個資深的台股分析與產業專家，同時也是一位極具創意與人氣的 Podcast 製作人。
請仔細閱讀並整合以下收集到的當日/前一日最新台股市場資訊（包含非凡錢線百分百和股市現場節目音軌字幕摘要、熱門財經 YouTube 與 Podcast 節目的最新描述與標題）：

【YouTube 台股節目字幕/摘要】
{videos_text}

【熱門財經影音最新單集資訊】
{shows_text}

=========================================

請根據上述數據，產出一個結構化的 JSON 內容，必須嚴格符合以下格式與要求，且不要有額外的包裹文字或 HTML tags：

【輸出 JSON 結構需求】
{{
  "title": "今日台股焦點與深度聲報",
  "written_report": {{
    "stock_market": "股市行情內容（繁體中文，格式請使用 Markdown。需包含加權指數走勢、大盤支撐壓力、櫃買指數及主要權值股如台積電、聯發科、鴻海等之表現與技術分析）",
    "industry_analysis": "產業分析內容（繁體中文，格式請使用 Markdown。需深入分析今日強勢或熱門族群，如半導體、AI伺服器/BBU/CPO、航運、綠能、金融等產業趨勢與利多）",
    "fund_flow": "資金流向內容（繁體中文，格式請使用 Markdown。需分析外資、投信、自營商三大法人買賣超動向、融資融券變化、市場成交量能變化與避險情緒討論）",
    "stock_recommendations": "長、短線個股推薦（繁體中文，格式請使用 Markdown。需具體列出適合長線佈局與短線操作的潛力個股，並簡要分析其基本面利基、技術面進出場點位與防守停損位置）"
  }},
  "finance_shows": [
    {{
      "show": "節目來源名稱（字串，例如：股癌、財報狗-掌握台股美股時事議題、CNBC Business News Update、財經一路發、財富旺得福、只要錢長大、財經號角、財訊）",
      "title": "單集原標題（字串，直接沿用上方提供的單集標題，絕對不要做任何日期前綴修改，不要包含日期）",
      "link": "該節目的連結（字串，沿用提供給你的連結）",
      "pubDate": "發布日期（字串，格式為 YYYY/MM/DD）",
      "stocks": ["主要探討個股代碼/名稱1", "主要探討個股代碼/名稱2"...], // 陣列，提取該單集核心探討的所有個股，包含台股代號如 台積電 (2330)、鴻海 (2317) 等。若無提到個股則為空陣列。
      "issues": ["主要探討經濟與投資議題1", "主要探討經濟與投資議題2"...], // 陣列，提取該單集核心討論之股票、總體經濟、財報或投資議題。
      "summary": "以繁體中文針對該單集標題與描述進行內容重點整理（字串，限 50 到 100 字，言簡意賅地敘述出該集的核心議題或觀點）。注意：請將『[月/日] 集數編號』（例如：『[07/25] EP682』；若是無集數編號的節目，請以『[月/日] 節目名稱』前綴，例如『[07/25] 只要錢長大』）顯示在 summary 文字描述的最前面，不要顯示在 title 上"
    }}
  ],
  "podcast_script": [
    {{
      "speaker": "HsiaoChen",
      "text": "主持人的話（繁體中文，台灣腔，口語化，例如：『哈囉大家，歡迎收聽今日的台股焦點聲報。我是 HsiaoChen。』）"
    }},
    {{
      "speaker": "YunJhe",
      "text": "專家的話（繁體中文，台灣腔，口語化，例如：『嗨，大家好，我是 YunJhe。今天台股加權指數真的是驚心動魄，特別是台積電...』）"
    }}
    // 依此類推，設計 12 - 18 輪的男女對話，深入且生動地討論上述書面分析中的核心台股資訊。
    // 每段話長度大約 60-150 字，以保持談話順暢度，整體對話長度約在 1200 到 1800 字之間。
  ]
}}

【關鍵細節要求】
1. **繁體中文與台灣常用財經用語**：報告和對話中請務必使用台灣的財經與口語用語。例如：『加權指數』、『櫃買指數』、『法人買賣超』、『季線/半年線/年線』、『除權息』、『個股推薦』。
2. **台灣腔口語發音語助詞**：對話必須像真實的台灣人對話，自然融入語助詞，如『對啊』、『沒錯』、『我覺得說...』、『像是...』、『這樣子』、『真的耶』、『吼』。
3. **表情停頓與語調引導（極重要）**：對話文字中請適當多使用標點符號（如逗號『，』、頓號『、』、省略號『……』或空格）來引導語音引擎產生自然停頓，避免語氣聽起來過於機械化。
4. **角色名稱限制**：對話劇本的 `speaker` 欄位值僅能為 `"HsiaoChen"` 與 `"YunJhe"`。
"""

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing!")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(clean_json_text(response.text))
        print("Gemini Taiwan response parsed successfully!")
        return data
    except Exception as e:
        print(f"Error calling or parsing Gemini API for Taiwan: {e}")
        fallback_shows = []
        for s in finance_shows:
            ep_match = re.search(r'EP\d+', s['title'])
            prefix = ep_match.group(0) if ep_match else s['show']
            fallback_shows.append({
                "show": s['show'],
                "title": s['title'],
                "link": s['link'],
                "pubDate": s['pubDate'],
                "stocks": [],
                "issues": [],
                "summary": f"[{s['pubDate'][5:]}] {prefix} 重點整理：內容獲取暫時失敗，請至原影音連結觀看。"
            })
        return {
            "title": f"台股每日分析 ({datetime.now().strftime('%Y-%m-%d')})",
            "written_report": {
                "stock_market": "台股行情分析生成暫時失敗，請稍候重試或檢查 API 設定。",
                "industry_analysis": "目前無產業分析資料。",
                "fund_flow": "目前無三大法人資金流動資料。",
                "stock_recommendations": "目前無個股推薦。"
            },
            "finance_shows": fallback_shows,
            "podcast_script": [
                {"speaker": "HsiaoChen", "text": "不好意思，今天我們的台股 AI 生成系統遇到了一些問題，請明天再收聽我們的精彩解析！"},
                {"speaker": "YunJhe", "text": "對啊，大家先看看相關影音內容，祝大家操作順利！"}
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
    """Generate individual voice mp3 files with controlled concurrency to avoid rate limiting."""
    print("Generating voice audio chunks...")
    semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent tasks
    
    async def generate_with_retry(text, voice, out_path, turn_idx):
        async with semaphore:
            for attempt in range(3):
                try:
                    await generate_voice_chunk(text, voice, out_path)
                    return
                except Exception as e:
                    if attempt == 2:
                        print(f"❌ Final attempt failed for turn {turn_idx}: {e}")
                        raise e
                    print(f"⚠️ Error generating turn {turn_idx} (attempt {attempt+1}): {e}. Retrying in 1.5s...")
                    await asyncio.sleep(1.5)

    tasks = []
    temp_files = []
    for idx, turn in enumerate(script):
        speaker = turn.get('speaker', 'HsiaoChen')
        text = turn.get('text', '')
        # Map to Taiwanese Neural Voices
        voice = "zh-TW-HsiaoChenNeural" if speaker == "HsiaoChen" else "zh-TW-YunJheNeural"
        
        out_path = os.path.join(temp_dir, f"turn_{idx:03d}.mp3")
        temp_files.append(out_path)
        
        tasks.append(generate_with_retry(text, voice, out_path, idx))
        
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


def update_archive_list(date_str, title, filename="archive_list.json"):
    """Add new report date to docs/<filename> in front, keeping top 30 unique items."""
    list_path = os.path.join(DOCS_DIR, filename)
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
    print(f"Archive registry list {filename} updated.")


def main():
    start_time = datetime.now()
    print(f"Pipeline started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Common: Fetch popular finance shows latest uploads
    finance_shows = fetch_finance_shows_news()
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # ------------------ US Market Pipeline ------------------
    print("\n=================== STARTING US MARKET PIPELINE ===================")
    try:
        # Fetch US YouTube transcripts
        scraped_us_videos = get_all_scraped_videos_data()
        
        # Call Gemini to generate US Report & Dialogue Script
        us_report_data = generate_insights_and_podcast(scraped_us_videos, finance_shows)
        us_report_data['date'] = date_str
        
        # Generate US audio podcast file
        us_audio_generated = False
        clean_temp_dir()
        try:
            temp_files = asyncio.run(generate_all_voices(us_report_data.get('podcast_script', []), TEMP_DIR))
            latest_mp3 = os.path.join(DOCS_DIR, "latest.mp3")
            archive_mp3 = os.path.join(ARCHIVE_DIR, f"{date_str}.mp3")
            
            us_audio_generated = merge_audio_files(temp_files, TEMP_DIR, latest_mp3)
            if us_audio_generated:
                import shutil
                shutil.copy(latest_mp3, archive_mp3)
                print(f"Archived US audio saved to: {archive_mp3}")
        except Exception as e:
            print(f"Error generating US audio: {e}")
        finally:
            clean_temp_dir()
            
        # Ensure latest.mp3 exists
        latest_mp3 = os.path.join(DOCS_DIR, "latest.mp3")
        if not us_audio_generated and not os.path.exists(latest_mp3):
            with open(latest_mp3, 'wb') as f:
                f.write(b'')
                
        # Write US JSON report
        latest_json_path = os.path.join(DOCS_DIR, "latest.json")
        with open(latest_json_path, 'w', encoding='utf-8') as f:
            json.dump(us_report_data, f, ensure_ascii=False, indent=2)
        print(f"Latest US report data saved to: {latest_json_path}")
        
        archive_json_path = os.path.join(ARCHIVE_DIR, f"{date_str}.json")
        with open(archive_json_path, 'w', encoding='utf-8') as f:
            json.dump(us_report_data, f, ensure_ascii=False, indent=2)
        print(f"Archived US report data saved to: {archive_json_path}")
        
        # Update US archive list
        update_archive_list(date_str, us_report_data.get('title', '美股動態焦點'), "archive_list.json")
        
    except Exception as e:
        print(f"❌ Error in US Market Pipeline: {e}")
        
    # ------------------ Taiwan Market Pipeline ------------------
    print("\n=================== STARTING TAIWAN MARKET PIPELINE ===================")
    try:
        # Fetch Taiwan YouTube transcripts
        scraped_tw_videos = get_taiwan_shows_data()
        
        # Call Gemini to generate Taiwan Report & Dialogue Script
        tw_report_data = generate_taiwan_insights_and_podcast(scraped_tw_videos, finance_shows)
        tw_report_data['date'] = date_str
        
        # Generate Taiwan audio podcast file
        tw_audio_generated = False
        clean_temp_dir()
        try:
            temp_files = asyncio.run(generate_all_voices(tw_report_data.get('podcast_script', []), TEMP_DIR))
            latest_tw_mp3 = os.path.join(DOCS_DIR, "latest_tw.mp3")
            archive_tw_mp3 = os.path.join(ARCHIVE_DIR, f"tw_{date_str}.mp3")
            
            tw_audio_generated = merge_audio_files(temp_files, TEMP_DIR, latest_tw_mp3)
            if tw_audio_generated:
                import shutil
                shutil.copy(latest_tw_mp3, archive_tw_mp3)
                print(f"Archived Taiwan audio saved to: {archive_tw_mp3}")
        except Exception as e:
            print(f"Error generating Taiwan audio: {e}")
        finally:
            clean_temp_dir()
            
        # Ensure latest_tw.mp3 exists
        latest_tw_mp3 = os.path.join(DOCS_DIR, "latest_tw.mp3")
        if not tw_audio_generated and not os.path.exists(latest_tw_mp3):
            with open(latest_tw_mp3, 'wb') as f:
                f.write(b'')
                
        # Write Taiwan JSON report
        latest_tw_json_path = os.path.join(DOCS_DIR, "latest_tw.json")
        with open(latest_tw_json_path, 'w', encoding='utf-8') as f:
            json.dump(tw_report_data, f, ensure_ascii=False, indent=2)
        print(f"Latest Taiwan report data saved to: {latest_tw_json_path}")
        
        archive_tw_json_path = os.path.join(ARCHIVE_DIR, f"tw_{date_str}.json")
        with open(archive_tw_json_path, 'w', encoding='utf-8') as f:
            json.dump(tw_report_data, f, ensure_ascii=False, indent=2)
        print(f"Archived Taiwan report data saved to: {archive_tw_json_path}")
        
        # Update Taiwan archive list
        update_archive_list(date_str, tw_report_data.get('title', '台股焦點分析'), "archive_list_tw.json")
        
    except Exception as e:
        print(f"❌ Error in Taiwan Market Pipeline: {e}")
        
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\nPipeline finished successfully in {duration:.1f} seconds at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()

