import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime

# Configure Chinese encoding support
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Ensure we import main functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import main

# Mock data to use when GEMINI_API_KEY is missing
MOCK_REPORT = {
    "title": "今日美股動態與深度聲報 (本地測試)",
    "written_report": {
        "stock_analysis": "### IBD 最新焦點分析\n\n- **AI 資本支出焦點**：根據 IBD 的最新 analysis，Google、Tesla 以及 GE Vernova 的財報公佈後，市場對 AI 資本支出（Capex）進行了嚴密檢視。微軟、谷歌與亞馬遜在 AI 基礎設施上的投資力道未減，但投資人開始關注資本回報率（ROI）。\n- **強勢類股表現**：半導體板塊經歷震盪調整，資金流向有防禦性的民生消費與公用事業類股。TSM、Goldman Sachs 仍然維持在關鍵季線支撐之上，展現抗跌力道。\n- **特斯拉與 SpaceX 整合傳言**：市場熱烈討論 SpaceX 與 Tesla 合併的潛在可能性，以加強 Elon Musk 商業帝國的協同效應。分析師普遍認為此舉難度極高，但仍引發資金情緒波動。",
        "fund_flow": "### 資金流向與板塊輪動\n\n- **板塊輪動**：資金明顯從高估值的科技成長股（Big Tech）流出，流入以價值股、小盤股為主防禦性板塊（如生技醫療、金融股）。\n- **法人動態**：大型機構法人對權值股進行了局部的獲利了結，但在 TSM 與 UnitedHealth 等重要公司季報出爐前，倉位調整相對謹慎。\n- **成交量**：指數成交量略微放大，顯示在高檔賣壓湧現時，低位接盤力道依然強勁，整體市場呈現箱型整理的態勢。",
        "investment_advice": "### 長線投資與布局建議\n\n- **關注強勢板塊龍頭**：在 AI 基礎建設題材上，維持長線分批布局（DCA）看法。尤其是具備定價能力的晶片代工與關鍵硬體零組件廠商。\n- **防禦性配置**：長線部位可適度挪移 10-15% 至受惠於降息循環的金融巨頭（如 Goldman Sachs）或穩定現金流的生技醫療類股。\n- **技術面策略**：多頭格局並未破壞，建議在回測 50 日均線（季線）或 200 日均線（半年線）出現止跌信號時，再進行中長期的加碼部署。"
    },
    "podcast_script": [
        {
            "speaker": "HsiaoChen",
            "text": "哈囉大家，歡迎收聽……今日的美股焦點聲報。我是 HsiaoChen。"
        },
        {
            "speaker": "YunJhe",
            "text": "嗨，大家好，我是 YunJhe。今天美股，真的，有很多精彩的話題耶……特別是，大家最近都在關心的，AI 資本支出，還有類股輪動。"
        },
        {
            "speaker": "HsiaoChen",
            "text": "對啊！聽說，Google 和 Tesla 公佈財報後……大家都在用放大鏡，檢視他們的 AI 投資回報率。這對科技股，有什麼影響嗎？"
        },
        {
            "speaker": "YunJhe",
            "text": "沒錯……現在，法人都在看，這些大科技公司，花了這麼多錢建置 AI 機房……到底，什麼時候才能賺錢。所以短線上，資金有一些調節，跑去一些比較防禦性的板塊……像是金融，或是醫療類股。"
        },
        {
            "speaker": "HsiaoChen",
            "text": "原來是這樣……那對於長線的投資朋友，阿哲，你會有什麼建議呢？"
        },
        {
            "speaker": "YunJhe",
            "text": "我覺得，長線的大趨勢，是沒有變的啦！建議大家，不用過度恐慌……反而可以在指數，回檔到季線附近的時候，分批布局，一些有實質獲利支撐的 AI 龍頭股……或者是防禦型配息股，這樣子，會比較穩健喔。"
        },
        {
            "speaker": "HsiaoChen",
            "text": "好的，非常謝謝阿哲的分享！那今天的聲報就到這邊……我們，明天見囉！"
        },
        {
            "speaker": "YunJhe",
            "text": "大家拜拜……祝大家投資順利！"
        }
    ]
}

async def main_test():
    print("=" * 60)
    print(" 🚀 美股動態聲報 - 本地 IBD 影片測試運行")
    print("=" * 60)
    
    # Check for Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    mock_mode = False
    
    # Check if key is actually set to a valid-looking key or is missing
    if not api_key or "AIzaSy" not in api_key:
        print("⚠️ 提醒：找不到有效的 GEMINI_API_KEY（.env 內容不正確或未填入金鑰）。")
        print("👉 系統將自動啟動【模擬測試模式】生成預設的台語男女 Podcast 聲報與美股報告，以便您即刻瀏覽 UI 介面！")
        mock_mode = True
    else:
        print(f"✅ 成功載入 API Key: {api_key[:6]}...{api_key[-4:]}")
    
    # Check FFmpeg
    has_ffmpeg = main.check_ffmpeg()
    if has_ffmpeg:
        print("✅ 檢測到系統中已安裝 FFmpeg！")
    else:
        print("⚠️ 提醒：未檢測到 FFmpeg，合併階段將自動啟動【二進位無損拼接技術】。")

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_data = None
    news_items = []

    if not mock_mode:
        # 1. Scrape only 1 latest video from IBD
        print("\n[步驟 1] 正在抓取最新 1 支 IBD 影片資訊...")
        ibd_videos = main.fetch_youtube_videos("https://www.youtube.com/@investorsbusinessdaily/videos", limit=1)
        if not ibd_videos:
            print("❌ 無法取得 IBD 影片資訊，將改為使用模擬數據...")
            mock_mode = True
        else:
            video = ibd_videos[0]
            print(f"🎬 找到影片：{video['title']}")
            
            # Try downloading subtitles
            sub_file = main.download_subtitles(video['id'], main.TEMP_DIR)
            transcript = main.clean_vtt_subtitles(sub_file) if sub_file else ""
            if transcript:
                print(f"📝 成功下載並清洗字幕，字數：{len(transcript)} 字")
            else:
                print("📝 本影片尚未處理好自動字幕，將使用標題和描述作為分析素材。")
                
            scraped_videos = [{
                'source': "Investor's Business Daily",
                'title': video['title'],
                'description': video['description'],
                'transcript': transcript
            }]

            # 2. Scrape Investing.com Stock Market RSS
            print("\n[步驟 2] 正在抓取 Investing.com 財經頭條...")
            news_items = main.fetch_investing_news()
            if news_items:
                news_items = news_items[:5]
                print(f"📰 取得 {len(news_items)} 則頭條新聞。")
            else:
                print("⚠️ 無法取得 Investing.com 新聞，測試將只使用影片數據進行。")

            # 3. Call Gemini
            print("\n[步驟 3] 正在發送給 Gemini 進行整合分析與對話生成...")
            report_data = main.generate_insights_and_podcast(scraped_videos, news_items)
            report_data['date'] = date_str
            report_data['investing_news'] = news_items
    
    if mock_mode or not report_data:
        # Load mock report data
        print("\n[模擬模式] 載入預設的模擬美股報告與劇本...")
        report_data = json.loads(json.dumps(MOCK_REPORT)) # Deep copy
        report_data['date'] = date_str
        
        # Load actual investing news if available
        print("📰 正在嘗試抓取實時 Investing.com 新聞以豐富模擬資料...")
        news_items = main.fetch_investing_news()
        if news_items:
            news_items = news_items[:5]
            report_data['investing_news'] = news_items
        else:
            report_data['investing_news'] = [
                {
                    "title": "Fed官員發言暗示下半年降息步伐可能放緩",
                    "link": "https://www.investing.com",
                    "pubDate": "2026-07-18 12:00:00",
                    "author": "Investing.com (美股新聞)"
                },
                {
                    "title": "NVIDIA新晶片出貨暢旺，帶動科技股早盤反彈",
                    "link": "https://www.investing.com",
                    "pubDate": "2026-07-18 11:30:00",
                    "author": "Investing.com (美股新聞)"
                }
            ]
            
    script = report_data.get('podcast_script', [])
    print(f"🎤 成功準備好書面報告與對話劇本 (劇本共 {len(script)} 句對話)。")

    # 4. Generate audio podcast file
    audio_generated = False
    print("\n[步驟 4] 正在使用 edge-tts 生成各段語音並進行合併...")
    main.clean_temp_dir()
    try:
        # Generate voices in parallel
        temp_files = await main.generate_all_voices(script, main.TEMP_DIR)
        
        latest_mp3 = os.path.join(main.DOCS_DIR, "latest.mp3")
        archive_mp3 = os.path.join(main.ARCHIVE_DIR, f"{date_str}.mp3")
        
        # Merge (automatically uses binary concat fallback if FFmpeg is missing)
        audio_generated = main.merge_audio_files(temp_files, main.TEMP_DIR, latest_mp3)
        if audio_generated:
            # Copy to archive
            import shutil
            shutil.copy(latest_mp3, archive_mp3)
            print(f"🎉 音訊成功合併並儲存至：{latest_mp3}")
            print(f"🎉 歷史封存音檔已寫入：{archive_mp3}")
    except Exception as e:
        print(f"❌ 生成音訊出錯: {e}")
    finally:
        main.clean_temp_dir()

    # If audio generation failed, create placeholder latest.mp3 to avoid error in web
    latest_mp3 = os.path.join(main.DOCS_DIR, "latest.mp3")
    if not audio_generated and not os.path.exists(latest_mp3):
        with open(latest_mp3, 'wb') as f:
            f.write(b'')

    # 5. Save report data to JSON files
    print("\n[步驟 5] 正在將書面資料寫入 docs/ 目錄...")
    latest_json_path = os.path.join(main.DOCS_DIR, "latest.json")
    with open(latest_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"📝 儲存最新 JSON 報告至：{latest_json_path}")
    
    archive_json_path = os.path.join(main.ARCHIVE_DIR, f"{date_str}.json")
    with open(archive_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"📝 儲存歷史歸檔 JSON 至：{archive_json_path}")

    # 6. Update archive list index
    main.update_archive_list(date_str, report_data.get('title', '美股動態焦點（本地測試）'))
    
    print("\n" + "=" * 60)
    print(" 🎉 測試執行完畢！")
    print("=" * 60)
    print("下一步操作指引：")
    print("1. 請在瀏覽器重新整理 http://localhost:8000，即可觀看並收聽最新的重點報告！")

if __name__ == '__main__':
    asyncio.run(main_test())
