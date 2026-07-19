document.addEventListener('DOMContentLoaded', () => {
    // Audio Player Elements
    const audio = document.getElementById('market-audio');
    const btnPlayPause = document.getElementById('btn-play-pause');
    const btnMute = document.getElementById('btn-mute');
    const progressBar = document.getElementById('progress-bar');
    const progressBarWrapper = document.getElementById('progress-bar-wrapper');
    const progressHandle = document.getElementById('progress-handle');
    const currentTimeLabel = document.getElementById('current-time');
    const durationTimeLabel = document.getElementById('duration-time');
    const volumeSlider = document.getElementById('volume-slider');
    const visualizer = document.getElementById('visualizer');

    // Content Display Elements
    const reportTitle = document.getElementById('report-title');
    const reportDate = document.getElementById('report-date');
    const analysisText = document.getElementById('analysis-text');
    const flowText = document.getElementById('flow-text');
    const adviceText = document.getElementById('advice-text');
    const newsListContainer = document.getElementById('news-list-container');
    const newsCountBadge = document.getElementById('news-count');
    const dateSelect = document.getElementById('date-select');
    
    // Tab & Custom Card Elements
    const tabUs = document.getElementById('tab-us');
    const tabTw = document.getElementById('tab-tw');
    const cardRecommend = document.getElementById('card-recommend');
    const recommendText = document.getElementById('recommend-text');
    const titleAnalysis = document.getElementById('title-analysis');
    const titleFlow = document.getElementById('title-flow');
    const titleAdvice = document.getElementById('title-advice');
    const appLogoTitle = document.getElementById('app-logo-title');
    const appLogoSubtitle = document.getElementById('app-logo-subtitle');

    // Playback and Tab state
    let isPlaying = false;
    let currentReportData = null;
    let currentMarket = 'us'; // 'us' or 'tw'


    // --- Audio Player Logic ---
    function togglePlay() {
        if (!audio.src) return;
        
        if (audio.paused) {
            audio.play().then(() => {
                isPlaying = true;
                btnPlayPause.innerHTML = '<i class="fa-solid fa-pause"></i>';
                visualizer.classList.add('playing');
            }).catch(e => console.error("Error playing audio:", e));
        } else {
            audio.pause();
            isPlaying = false;
            btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
            visualizer.classList.remove('playing');
        }
    }

    btnPlayPause.addEventListener('click', togglePlay);

    // Audio progress updates
    audio.addEventListener('timeupdate', () => {
        const currentTime = audio.currentTime;
        const duration = audio.duration || 0;
        
        // Update progress bar width
        const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;
        progressBar.style.width = `${progressPercent}%`;
        progressHandle.style.left = `${progressPercent}%`;
        
        // Update current time label
        currentTimeLabel.textContent = formatTime(currentTime);
    });

    audio.addEventListener('loadedmetadata', () => {
        durationTimeLabel.textContent = formatTime(audio.duration || 0);
    });

    audio.addEventListener('ended', () => {
        isPlaying = false;
        btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
        visualizer.classList.remove('playing');
        progressBar.style.width = '0%';
        progressHandle.style.left = '0%';
        currentTimeLabel.textContent = '0:00';
    });

    // Helper: format time in MM:SS
    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Drag / Click on progress bar
    progressBarWrapper.addEventListener('click', (e) => {
        if (!audio.duration) return;
        const rect = progressBarWrapper.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const width = rect.width;
        const seekTime = (clickX / width) * audio.duration;
        audio.currentTime = seekTime;
    });

    // Mute/Volume Logic
    btnMute.addEventListener('click', () => {
        audio.muted = !audio.muted;
        if (audio.muted) {
            btnMute.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
            volumeSlider.value = 0;
        } else {
            btnMute.innerHTML = audio.volume > 0.5 ? '<i class="fa-solid fa-volume-high"></i>' : '<i class="fa-solid fa-volume-low"></i>';
            volumeSlider.value = audio.volume;
        }
    });

    volumeSlider.addEventListener('input', (e) => {
        const value = e.target.value;
        audio.volume = value;
        audio.muted = (value === '0');
        
        if (audio.muted) {
            btnMute.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
        } else if (value > 0.5) {
            btnMute.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
        } else {
            btnMute.innerHTML = '<i class="fa-solid fa-volume-low"></i>';
        }
    });

    // --- Loading Data Logic ---
    async function initApp() {
        try {
            const listFilename = currentMarket === 'us' ? 'archive_list.json' : 'archive_list_tw.json';
            const response = await fetch(listFilename);
            if (!response.ok) throw new Error(`Could not fetch ${listFilename}`);
            
            const archives = await response.json();
            populateDateSelect(archives);
            
            // Default load latest
            loadReport('latest');
        } catch (error) {
            console.error("Initialization error:", error);
            reportTitle.textContent = "資料庫加載失敗";
            analysisText.textContent = "無法從伺服器取得美股/台股聲報資料庫，請確認 JSON 檔案是否存在。";
            flowText.textContent = "";
            adviceText.textContent = "";
            recommendText.textContent = "";
        }
    }

    function populateDateSelect(archives) {
        dateSelect.innerHTML = '';
        
        // Add "Latest" option
        const latestOpt = document.createElement('option');
        latestOpt.value = 'latest';
        latestOpt.textContent = '最新日報 (今日)';
        dateSelect.appendChild(latestOpt);

        // Add history archives
        archives.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.date;
            opt.textContent = `${item.date} (${item.title || (currentMarket === 'us' ? '美股動態' : '台股動態')})`;
            dateSelect.appendChild(opt);
        });
    }

    async function loadReport(date) {
        showLoadingState();
        
        let url = '';
        let audioUrl = '';
        
        if (currentMarket === 'us') {
            url = date === 'latest' ? 'latest.json' : `archive/${date}.json`;
            audioUrl = date === 'latest' ? 'latest.mp3' : `archive/${date}.mp3`;
        } else {
            url = date === 'latest' ? 'latest_tw.json' : `archive/tw_${date}.json`;
            audioUrl = date === 'latest' ? 'latest_tw.mp3' : `archive/tw_${date}.mp3`;
        }

        // Cache busting for latest reports to ensure freshness
        if (date === 'latest') {
            url += `?t=${Date.now()}`;
            audioUrl += `?t=${Date.now()}`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Could not load report for ${date}`);
            
            const data = await response.json();
            currentReportData = data;
            
            // Update UI Titles and Layout based on market
            if (currentMarket === 'us') {
                cardRecommend.style.display = 'none';
                titleAnalysis.innerHTML = '<i class="fa-solid fa-chart-pie"></i> 股市與產業分析 (Stock & Industry Analysis)';
                titleFlow.innerHTML = '<i class="fa-solid fa-money-bill-transfer"></i> 資金流向 (Fund Flow)';
                titleAdvice.innerHTML = '<i class="fa-solid fa-gem"></i> 長線投資方向建議 (Long-term Advice)';
                
                reportTitle.textContent = data.title || `${data.date} 美股每日聲報`;
                
                analysisText.innerHTML = formatMarkdown(data.written_report.stock_analysis);
                flowText.innerHTML = formatMarkdown(data.written_report.fund_flow);
                adviceText.innerHTML = formatMarkdown(data.written_report.investment_advice);
            } else {
                cardRecommend.style.display = 'block';
                titleAnalysis.innerHTML = '<i class="fa-solid fa-chart-line"></i> 股市行情 (Market Trend)';
                titleFlow.innerHTML = '<i class="fa-solid fa-chart-pie"></i> 產業分析 (Industry Analysis)';
                titleAdvice.innerHTML = '<i class="fa-solid fa-money-bill-transfer"></i> 資金流向 (Fund Flow)';
                
                reportTitle.textContent = data.title || `${data.date} 台股焦點分析`;
                
                analysisText.innerHTML = formatMarkdown(data.written_report.stock_market);
                flowText.innerHTML = formatMarkdown(data.written_report.industry_analysis);
                adviceText.innerHTML = formatMarkdown(data.written_report.fund_flow);
                recommendText.innerHTML = formatMarkdown(data.written_report.stock_recommendations);
            }
            
            reportDate.innerHTML = `<i class="fa-regular fa-clock"></i> 發表日期：${data.date}`;

            // Populate News
            populateNewsList(data.investing_news || []);

            // Setup Audio Source
            audio.src = audioUrl;
            audio.load();
            
            // Reset player states
            isPlaying = false;
            btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
            visualizer.classList.remove('playing');
            progressBar.style.width = '0%';
            progressHandle.style.left = '0%';
            currentTimeLabel.textContent = '0:00';
            
        } catch (error) {
            console.error("Error loading report:", error);
            reportTitle.textContent = "加載報告失敗";
            analysisText.textContent = `無法加載日期為 ${date} 的報告。請確認該報告的資料檔案是否已生成。`;
            flowText.textContent = "";
            adviceText.textContent = "";
            recommendText.textContent = "";
            newsListContainer.innerHTML = '<div class="news-loading"><i class="fa-solid fa-circle-exclamation"></i> 無法載入當日頭條新聞</div>';
            newsCountBadge.textContent = '0 則';
        }
    }

    function showLoadingState() {
        reportTitle.textContent = "讀取中...";
        analysisText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> 載入報告內容中...';
        flowText.innerHTML = "";
        adviceText.innerHTML = "";
        recommendText.innerHTML = "";
        newsListContainer.innerHTML = '<div class="news-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> 載入新聞中...</div>';
    }

    function populateNewsList(newsItems) {
        newsListContainer.innerHTML = '';
        newsCountBadge.textContent = `${newsItems.length} 則`;

        if (newsItems.length === 0) {
            newsListContainer.innerHTML = '<div class="news-loading">當日無抓取到 Investing.com 新聞</div>';
            return;
        }

        newsItems.forEach(item => {
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            
            // Extract clean title and link
            const title = item.title || '無標題';
            const link = item.link || '#';
            const pubDate = item.pubDate || '--';
            const source = item.author || 'Investing.com';
            
            newsItem.innerHTML = `
                <a href="${link}" target="_blank" rel="noopener noreferrer" class="news-item-title">${title}</a>
                <div class="news-item-footer">
                    <span class="news-item-source"><i class="fa-solid fa-globe"></i> ${source}</span>
                    <span><i class="fa-regular fa-clock"></i> ${pubDate}</span>
                </div>
            `;
            newsListContainer.appendChild(newsItem);
        });
    }

    // A simple parser to convert basic markdown/linebreaks to HTML
    function formatMarkdown(text) {
        if (!text) return '';
        
        // Escape HTML to prevent XSS
        let clean = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
        // Bold formatting **text** -> <strong>text</strong>
        clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert unordered list items starting with - or *
        let lines = clean.split('\n');
        let formattedLines = [];
        let inList = false;
        
        lines.forEach(line => {
            let trimmed = line.trim();
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                if (!inList) {
                    formattedLines.push('<ul>');
                    inList = true;
                }
                formattedLines.push(`<li>${trimmed.substring(2)}</li>`);
            } else {
                if (inList) {
                    formattedLines.push('</ul>');
                    inList = false;
                }
                if (trimmed) {
                    formattedLines.push(`<p>${line}</p>`);
                }
            }
        });
        
        if (inList) {
            formattedLines.push('</ul>');
        }
        
        return formattedLines.join('\n');
    }

    // Handle Dropdown Change
    dateSelect.addEventListener('change', (e) => {
        loadReport(e.target.value);
    });

    // Handle Market Tab Switching
    function switchMarket(market) {
        if (currentMarket === market) return;
        
        currentMarket = market;
        
        // Toggle Active Classes and header text
        if (currentMarket === 'us') {
            tabUs.classList.add('active');
            tabTw.classList.remove('active');
            appLogoTitle.textContent = '美股每日聲報';
            appLogoSubtitle.textContent = 'US Market Daily Audio Insight';
        } else {
            tabTw.classList.add('active');
            tabUs.classList.remove('active');
            appLogoTitle.textContent = '台股每日分析';
            appLogoSubtitle.textContent = 'Taiwan Market Daily Analysis';
        }
        
        // Stop current audio playback
        audio.pause();
        isPlaying = false;
        btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
        visualizer.classList.remove('playing');
        
        // Re-initialize app for the selected market
        initApp();
    }

    tabUs.addEventListener('click', () => switchMarket('us'));
    tabTw.addEventListener('click', () => switchMarket('tw'));

    // Initialize App
    initApp();
});
