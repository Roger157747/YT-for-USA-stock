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
                titleAnalysis.innerHTML = '<i class="fa-solid fa-chart-pie"></i> 指數及產業板塊分析 (Index & Sector Analysis)';
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
            
            // Apply auto-linking on report text cards
            autoLinkStocksInElement(analysisText);
            autoLinkStocksInElement(flowText);
            autoLinkStocksInElement(adviceText);
            if (currentMarket === 'tw') {
                autoLinkStocksInElement(recommendText);
            }
            
            reportDate.innerHTML = `<i class="fa-regular fa-clock"></i> 發表日期：${data.date}`;

            // Populate News/Podcast Shows
            populateNewsList(data.finance_shows || data.investing_news || []);

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
            newsListContainer.innerHTML = '<div class="news-loading"><i class="fa-solid fa-circle-exclamation"></i> 無法載入當日影音內容</div>';
            newsCountBadge.textContent = '0 則';
        }
    }

    function showLoadingState() {
        reportTitle.textContent = "讀取中...";
        analysisText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> 載入報告內容中...';
        flowText.innerHTML = "";
        adviceText.innerHTML = "";
        recommendText.innerHTML = "";
        newsListContainer.innerHTML = '<div class="news-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> 載入影音內容中...</div>';
    }

    function populateNewsList(newsItems) {
        newsListContainer.innerHTML = '';
        newsCountBadge.textContent = `${newsItems.length} 則`;

        if (newsItems.length === 0) {
            newsListContainer.innerHTML = '<div class="news-loading">當日無抓取到影音與 Podcast 內容</div>';
            return;
        }

        newsItems.forEach(item => {
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            
            // Extract clean title, link, date, source and summary
            const title = item.title || '無標題';
            const link = item.link || '#';
            const pubDate = item.pubDate || '--';
            const source = item.show || item.author || '未知來源';
            const summary = item.summary || '';
            
            // Render stock tags if available
            const stocksHtml = (item.stocks && item.stocks.length > 0)
                ? `<div class="news-item-stocks">
                     <strong><i class="fa-solid fa-tags"></i> 探討個股：</strong>
                     <div class="stock-tags">
                       ${item.stocks.map(s => `<a href="${getStockUrl(s)}" target="_blank" rel="noopener noreferrer" class="stock-tag">${s}</a>`).join('')}
                     </div>
                   </div>`
                : '';

            // Render discussed issues list if available
            const issuesHtml = (item.issues && item.issues.length > 0)
                ? `<div class="news-item-issues">
                     <strong><i class="fa-solid fa-lightbulb"></i> 討論議題：</strong>
                     <ul>
                       ${item.issues.map(issue => `<li>${issue}</li>`).join('')}
                     </ul>
                   </div>`
                : '';

            newsItem.innerHTML = `
                <a href="${link}" target="_blank" rel="noopener noreferrer" class="news-item-title">${title}</a>
                ${stocksHtml}
                ${issuesHtml}
                ${summary ? `<div class="news-item-summary"><strong><i class="fa-solid fa-align-left"></i> 內容摘要：</strong><p>${summary}</p></div>` : ''}
                <div class="news-item-footer">
                    <span class="news-item-source"><i class="fa-solid fa-microphone"></i> ${source}</span>
                    <span><i class="fa-regular fa-clock"></i> ${pubDate}</span>
                </div>
            `;
            newsListContainer.appendChild(newsItem);
            
            // Apply auto-linking on this news item for any stock names mentioned in other fields
            autoLinkStocksInElement(newsItem);
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
        
        // Convert markdown links [text](url) -> <a href="url" target="_blank" rel="noopener noreferrer">text</a>
        clean = clean.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        
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

    // Get stock quote URL by stock name or ticker
    function getStockUrl(stockName) {
        const twMatch = stockName.match(/\b\d{4}\b/);
        if (twMatch) {
            return `https://tw.stock.yahoo.com/quote/${twMatch[0]}.TW`;
        }
        
        const twNames = ["台積電", "鴻海", "聯發科", "廣達", "緯創", "台達電", "華碩", "仁寶", "日月光", "富邦金", "國泰金", "中信金", "聯電", "技嘉", "微星", "奇鋐", "雙鴻", "世芯", "創意", "信驊", "力積電", "世界先進"];
        for (const name of twNames) {
            if (stockName.includes(name)) {
                const codes = {
                    "台積電": "2330", "鴻海": "2317", "聯發科": "2454", "廣達": "2382",
                    "緯創": "3231", "台達電": "2308", "華碩": "2357", "仁寶": "2324",
                    "日月光": "3711", "富邦金": "2881", "國泰金": "2882", "中信金": "2891",
                    "聯電": "2303", "技嘉": "2376", "微星": "2377", "奇鋐": "3017",
                    "雙鴻": "3324", "世芯": "3661", "創意": "3443", "信驊": "5274",
                    "力積電": "6770", "世界先進": "5347"
                };
                return `https://tw.stock.yahoo.com/quote/${codes[name]}.TW`;
            }
        }
        
        const usTickers = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "AMD", "AVGO", "QCOM", "INTC", "MU", "ASML", "NFLX", "TSM"];
        for (const ticker of usTickers) {
            if (stockName.toUpperCase().includes(ticker)) {
                return `https://finance.yahoo.com/quote/${ticker}`;
            }
        }
        
        const usNames = {
            "輝達": "NVDA", "英偉達": "NVDA", "蘋果": "AAPL", "特斯拉": "TSLA", "微軟": "MSFT", "亞馬遜": "AMZN",
            "谷歌": "GOOGL", "Google": "GOOGL", "臉書": "META", "Meta": "META", "超微": "AMD",
            "博通": "AVGO", "高通": "QCOM", "英特爾": "INTC", "美光": "MU", "艾司摩爾": "ASML",
            "網飛": "NFLX"
        };
        for (const name in usNames) {
            if (stockName.includes(name)) {
                return `https://finance.yahoo.com/quote/${usNames[name]}`;
            }
        }
        
        return `https://finance.yahoo.com/lookup?s=${encodeURIComponent(stockName)}`;
    }

    // Auto-link any stock names in DOM elements safely
    function autoLinkStocksInElement(element) {
        if (!element) return;
        
        const stocksToLink = [
            { name: "台積電", code: "2330", tw: true },
            { name: "聯發科", code: "2454", tw: true },
            { name: "日月光投控", code: "3711", tw: true },
            { name: "日月光", code: "3711", tw: true },
            { name: "力積電", code: "6770", tw: true },
            { name: "世界先進", code: "5347", tw: true },
            { name: "世芯-KY", code: "3661", tw: true },
            { name: "世芯", code: "3661", tw: true },
            { name: "台達電", code: "2308", tw: true },
            { name: "富邦金", code: "2881", tw: true },
            { name: "國泰金", code: "2882", tw: true },
            { name: "中信金", code: "2891", tw: true },
            { name: "鴻海", code: "2317", tw: true },
            { name: "廣達", code: "2382", tw: true },
            { name: "緯創", code: "3231", tw: true },
            { name: "華碩", code: "2357", tw: true },
            { name: "仁寶", code: "2324", tw: true },
            { name: "聯電", code: "2303", tw: true },
            { name: "技嘉", code: "2376", tw: true },
            { name: "微星", code: "2377", tw: true },
            { name: "奇鋐", code: "3017", tw: true },
            { name: "雙鴻", code: "3324", tw: true },
            { name: "創意", code: "3443", tw: true },
            { name: "信驊", code: "5274", tw: true },
            
            { name: "特斯拉", ticker: "TSLA" },
            { name: "特斯勒", ticker: "TSLA" },
            { name: "蘋果", ticker: "AAPL" },
            { name: "微軟", ticker: "MSFT" },
            { name: "亞馬遜", ticker: "AMZN" },
            { name: "輝達", ticker: "NVDA" },
            { name: "英偉達", ticker: "NVDA" },
            { name: "谷歌", ticker: "GOOGL" },
            { name: "Google", ticker: "GOOGL" },
            { name: "Meta", ticker: "META" },
            { name: "臉書", ticker: "META" },
            { name: "超微", ticker: "AMD" },
            { name: "博通", ticker: "AVGO" },
            { name: "高通", ticker: "QCOM" },
            { name: "英特爾", ticker: "INTC" },
            { name: "美光", ticker: "MU" },
            { name: "艾司摩爾", ticker: "ASML" },
            { name: "網飛", ticker: "NFLX" },
            
            { name: "AAPL", ticker: "AAPL" },
            { name: "NVDA", ticker: "NVDA" },
            { name: "TSLA", ticker: "TSLA" },
            { name: "MSFT", ticker: "MSFT" },
            { name: "AMZN", ticker: "AMZN" },
            { name: "GOOGL", ticker: "GOOGL" },
            { name: "GOOG", ticker: "GOOGL" },
            { name: "META", ticker: "META" },
            { name: "AMD", ticker: "AMD" },
            { name: "AVGO", ticker: "AVGO" },
            { name: "QCOM", ticker: "QCOM" },
            { name: "INTC", ticker: "INTC" },
            { name: "MU", ticker: "MU" },
            { name: "ASML", ticker: "ASML" },
            { name: "NFLX", ticker: "NFLX" },
            { name: "TSM", ticker: "TSM" }
        ];

        function traverse(node) {
            if (node.nodeName === 'A' || node.nodeName === 'BUTTON' || node.nodeName === 'SCRIPT' || node.nodeName === 'STYLE') return;
            
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent;
                let replaced = false;
                
                const esc = s => s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                const patternParts = stocksToLink.map(item => {
                    if (/^[A-Z0-9]+$/i.test(item.name)) {
                        return `\\b${esc(item.name)}\\b`;
                    } else {
                        return esc(item.name);
                    }
                });
                
                patternParts.push(`(?<!\\d)(2330|2317|2454|2382|3231|2308|2357|2324|3711|2881|2882|2891|2303|2376|2377|3017|3324|3661|3443|5274|6770|5347)(?!\\d)`);
                
                const regex = new RegExp(`(${patternParts.join('|')})`, 'g');
                let match;
                let lastIndex = 0;
                const parent = node.parentNode;
                const docFragment = document.createDocumentFragment();
                
                while ((match = regex.exec(text)) !== null) {
                    replaced = true;
                    const matchText = match[1];
                    const matchIndex = match.index;
                    
                    if (matchIndex > lastIndex) {
                        docFragment.appendChild(document.createTextNode(text.substring(lastIndex, matchIndex)));
                    }
                    
                    let url = '';
                    if (/^\d{4}$/.test(matchText)) {
                        url = `https://tw.stock.yahoo.com/quote/${matchText}.TW`;
                    } else {
                        const found = stocksToLink.find(x => x.name.toLowerCase() === matchText.toLowerCase());
                        if (found) {
                            if (found.tw) {
                                url = `https://tw.stock.yahoo.com/quote/${found.code}.TW`;
                            } else {
                                url = `https://finance.yahoo.com/quote/${found.ticker}`;
                            }
                        } else {
                            url = `https://finance.yahoo.com/lookup?s=${encodeURIComponent(matchText)}`;
                        }
                    }
                    
                    const anchor = document.createElement('a');
                    anchor.href = url;
                    anchor.target = "_blank";
                    anchor.rel = "noopener noreferrer";
                    anchor.className = "auto-stock-link";
                    anchor.textContent = matchText;
                    docFragment.appendChild(anchor);
                    
                    lastIndex = regex.lastIndex;
                }
                
                if (replaced) {
                    if (lastIndex < text.length) {
                        docFragment.appendChild(document.createTextNode(text.substring(lastIndex)));
                    }
                    parent.replaceChild(docFragment, node);
                }
            } else {
                const children = Array.from(node.childNodes);
                for (const child of children) {
                    traverse(child);
                }
            }
        }
        
        traverse(element);
    }

    // Initialize App
    initApp();
});
