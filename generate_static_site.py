#!/usr/bin/env python3
"""
Generate static HTML site for ICLR 2026 submissions
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Lock, Manager
from datetime import datetime

try:
    import markdown
    HAS_MARKDOWN = True
    # 预创建markdown实例配置
    MD_EXTENSIONS = ['extra', 'nl2br', 'sane_lists', 'codehilite', 'fenced_code']
except ImportError:
    HAS_MARKDOWN = False
    MD_EXTENSIONS = []
    print("Warning: 'markdown' library not found. Installing it will improve formatting.")
    print("Run: pip install markdown")

def load_data(json_path):
    """Load submissions data from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def markdown_to_html(text):
    """Convert Markdown to HTML using markdown library"""
    if not text:
        return ''
    
    if HAS_MARKDOWN:
        # 使用markdown库进行转换，每次创建新实例以避免状态问题
        md = markdown.Markdown(extensions=MD_EXTENSIONS)
        return md.convert(text)
    else:
        # 如果没有markdown库，使用简单的HTML转义和换行处理
        import html
        text = html.escape(text)
        # 保留换行
        text = text.replace('\n\n', '</p><p>')
        text = text.replace('\n', '<br>')
        return f'<p>{text}</p>'

def is_withdrawn(submission):
    """Check if a submission is withdrawn by checking the venue field"""
    venue = submission.get('content', {}).get('venue', {}).get('value', '')
    return 'withdrawn' in venue.lower()

def get_rating_changes(replies):
    """Calculate rating changes from reply history"""
    rating_history = defaultdict(list)
    
    for reply in replies:
        if 'content' in reply and 'rating' in reply['content']:
            reply_id = reply.get('id')
            rating = reply['content']['rating'].get('value')
            version = reply.get('version', 1)
            mdate = reply.get('mdate', 0)
            
            if reply_id and rating:
                rating_history[reply_id].append({
                    'version': version,
                    'rating': rating,
                    'date': mdate
                })
    
    # Calculate changes
    changes = {}
    for reply_id, history in rating_history.items():
        sorted_history = sorted(history, key=lambda x: x['date'])
        if len(sorted_history) > 1:
            old_rating = sorted_history[0]['rating']
            new_rating = sorted_history[-1]['rating']
            changes[reply_id] = new_rating - old_rating
    
    return changes

def count_reply_changes(replies):
    """Count how many replies have rating changes"""
    rating_changes = get_rating_changes(replies)
    return len([c for c in rating_changes.values() if c != 0])

def has_rating_increase(replies):
    """Check if any review has rating increase"""
    rating_changes = get_rating_changes(replies)
    return any(c > 0 for c in rating_changes.values())

def has_rating_decrease(replies):
    """Check if any review has rating decrease"""
    rating_changes = get_rating_changes(replies)
    return any(c < 0 for c in rating_changes.values())

def has_any_changes(replies):
    """Check if any review has been modified (multiple versions)"""
    reply_versions = defaultdict(list)
    
    for reply in replies:
        invitations = reply.get('invitations', [])
        if any('Official_Review' in inv for inv in invitations):
            reply_id = reply.get('id', '')
            mdate = reply.get('mdate', 0)
            if reply_id and mdate:
                reply_versions[reply_id].append(mdate)
    
    for reply_id, mdates in reply_versions.items():
        if len(set(mdates)) > 1:
            return True
    return False

def count_reviews(replies):
    """Count only official reviews (not comments), deduplicated by review ID"""
    review_ids = set()
    for reply in replies:
        invitations = reply.get('invitations', [])
        if any('Official_Review' in inv for inv in invitations):
            reply_id = reply.get('id', '')
            if reply_id:
                review_ids.add(reply_id)
    return len(review_ids)

def count_review_changes_by_type(replies):
    """Count reviews by change type: increased, decreased, nochange (content changed but rating same), and nochanges (never modified)"""
    reply_versions = defaultdict(list)
    rating_changes = get_rating_changes(replies)
    all_review_ids = set()
    
    for reply in replies:
        invitations = reply.get('invitations', [])
        if any('Official_Review' in inv for inv in invitations):
            reply_id = reply.get('id', '')
            if reply_id:
                all_review_ids.add(reply_id)
                mdate = reply.get('mdate', 0)
                if mdate:
                    reply_versions[reply_id].append(mdate)
    
    # 分别统计每种类型
    increase_count = 0
    decrease_count = 0
    nochange_count = 0
    nochanges_count = 0
    
    for reply_id in all_review_ids:
        mdates = reply_versions.get(reply_id, [])
        if len(set(mdates)) > 1:  # 有修改（多个不同的mdate）
            rating_change = rating_changes.get(reply_id, 0)
            if rating_change > 0:
                increase_count += 1
            elif rating_change < 0:
                decrease_count += 1
            else:
                nochange_count += 1
        else:  # 没有修改（只有一个mdate或没有mdate）
            nochanges_count += 1
    
    return increase_count, decrease_count, nochange_count, nochanges_count

def generate_css():
    """Generate CSS styles"""
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #ffffff; color: #1a1a1a; line-height: 1.7; }
.container { max-width: 1100px; margin: 0 auto; padding: 30px 20px; }
header { background: #ffffff; border-bottom: 1px solid #e5e5e5; padding: 25px 0; margin-bottom: 35px; }
header h1 { text-align: center; font-size: 2em; font-weight: 600; color: #1a1a1a; letter-spacing: -0.5px; }
.tabs { display: flex; gap: 8px; margin-bottom: 25px; border-bottom: 1px solid #e5e5e5; }
.tab { padding: 10px 20px; cursor: pointer; background: transparent; border: none; font-size: 15px; font-weight: 500; color: #666; border-bottom: 2px solid transparent; transition: all 0.2s; }
.tab:hover { color: #1a1a1a; }
.tab.active { color: #1a1a1a; border-bottom-color: #1a1a1a; }
.filters { background: #fafafa; padding: 18px 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e5e5e5; }
.filter-group { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.filter-btn { padding: 7px 14px; border: 1px solid #d0d0d0; background: #ffffff; color: #333; border-radius: 5px; cursor: pointer; font-size: 13px; transition: all 0.2s; font-weight: 500; }
.filter-btn:hover { border-color: #1a1a1a; color: #1a1a1a; background: #fafafa; }
.filter-btn.active { background: #1a1a1a; color: #ffffff; border-color: #1a1a1a; }
.filter-count { font-size: 12px; opacity: 0.7; margin-left: 4px; }
.paper-list { display: grid; gap: 18px; }
.paper-card { background: #ffffff; padding: 22px; border-radius: 6px; border: 1px solid #e5e5e5; transition: all 0.2s; }
.paper-card:hover { border-color: #1a1a1a; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.paper-title { font-size: 1.15em; font-weight: 600; margin-bottom: 6px; line-height: 1.4; }
.paper-title a { color: #1a1a1a; text-decoration: none; }
.paper-title a:hover { color: #0066cc; }
.paper-info-line { font-size: 0.82em; color: #666; margin-bottom: 3px; line-height: 1.5; }
.pdf-link { color: #0066cc; text-decoration: none; font-weight: 500; }
.pdf-link:hover { text-decoration: underline; }
.paper-toggle { font-size: 0.82em; color: #666; cursor: pointer; margin: 8px 0 6px 0; user-select: none; display: inline-block; }
.paper-toggle:hover { color: #0066cc; }
.paper-details { margin: 8px 0 10px 0; padding: 0; background: transparent; border: none; font-size: 0.88em; line-height: 1.6; color: #555; }
.detail-section { margin: 6px 0; color: #555; }
.detail-section strong { color: #666; font-weight: 500; font-size: 0.9em; }
.paper-meta { display: flex; gap: 12px; font-size: 0.88em; color: #666; flex-wrap: wrap; align-items: center; margin-top: 8px; }
.meta-item { display: flex; align-items: center; gap: 5px; }
.badge { padding: 4px 10px; border-radius: 4px; font-size: 0.85em; font-weight: 500; }
.badge-increase { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
.badge-decrease { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
.badge-ratingnochange { background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }
.badge-nochanges { background: #f5f5f5; color: #757575; border: 1px solid #e0e0e0; }
.tab-content { display: none; }
.tab-content.active { display: block; }
.hidden { display: none !important; }
.detail-container { background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e5e5e5; margin-bottom: 20px; }
.back-link { display: inline-block; margin-bottom: 18px; color: #0066cc; text-decoration: none; font-weight: 500; font-size: 0.92em; }
.back-link:hover { text-decoration: underline; }
.metadata-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin: 18px 0; }
.metadata-item { padding: 12px 14px; background: #fafafa; border-radius: 5px; border: 1px solid #e5e5e5; }
.metadata-label { font-weight: 600; color: #666; font-size: 0.8em; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
.metadata-value { color: #1a1a1a; font-size: 0.88em; line-height: 1.5; }
.abstract { margin: 20px 0; padding: 20px; background: #fafafa; border-radius: 6px; line-height: 1.6; border: 1px solid #e5e5e5; font-size: 0.88em; }
.abstract h3 { font-size: 1em; margin-bottom: 10px; color: #1a1a1a; font-weight: 600; }
.replies-section { margin-top: 25px; }
.replies-section h2 { font-size: 1.25em; margin-bottom: 15px; color: #1a1a1a; font-weight: 600; }
.reply-card { background: #ffffff; padding: 18px 20px; border-radius: 6px; margin-bottom: 12px; border: 1px solid #e5e5e5; font-size: 0.86em; }
.reply-card:hover { border-color: #d0d0d0; }
.author-reply { background: #fffbf0; border: 1px solid #ffe0b2; }
.reply-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 5px; }
.reply-meta { font-size: 0.92em; color: #666; display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.reply-date { font-size: 0.88em; color: #999; }
.badge-author { background: #ff9800; color: white; border: none; }
.content-section { margin: 5px 0; }
.content-label { font-weight: 600; color: #1a1a1a; margin-bottom: 3px; font-size: 0.9em; }
.content-text { color: #333; line-height: 1.55; font-size: 0.9em; }
.content-text p { margin: 6px 0; }
.content-text h1, .content-text h2, .content-text h3 { margin: 10px 0 6px 0; color: #1a1a1a; font-weight: 600; }
.content-text h1 { font-size: 1.25em; }
.content-text h2 { font-size: 1.12em; }
.content-text h3 { font-size: 1.03em; }
.content-text strong { font-weight: 600; color: #1a1a1a; }
.content-text em { font-style: italic; }
.content-text code { background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; font-size: 0.88em; color: #c7254e; border: 1px solid #e5e5e5; }
.content-text ul, .content-text ol { margin: 8px 0; padding-left: 28px; }
.content-text li { margin: 4px 0; line-height: 1.6; }
.content-text blockquote { border-left: 3px solid #0066cc; padding-left: 12px; margin: 8px 0; color: #666; font-style: italic; }
.content-text a { color: #0066cc; text-decoration: none; }
.content-text a:hover { text-decoration: underline; }
.version-toggle { cursor: pointer; color: #0066cc; font-size: 0.86em; margin-top: 8px; user-select: none; font-weight: 500; }
.version-toggle:hover { text-decoration: underline; }
.old-versions { display: none; margin-top: 10px; padding: 12px; background: #ffffff; border-radius: 5px; border: 1px solid #e5e5e5; }
.old-versions.show { display: block; }
.version-item { padding: 10px; margin: 6px 0; background: #fafafa; border-radius: 4px; font-size: 0.88em; border: 1px solid #e5e5e5; }
.stats { text-align: center; padding: 12px; background: #fafafa; border-radius: 6px; margin-bottom: 20px; font-size: 0.9em; color: #666; border: 1px solid #e5e5e5; }
"""

def generate_js():
    """Generate JavaScript for interactivity"""
    return """
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
    updateFilters(tabName);
}

function updateFilters(tabName) {
    const papers = document.querySelectorAll(`#${tabName} .paper-card`);
    const activeFilter = document.querySelector(`#${tabName} .filter-btn.active`)?.dataset.filter || 'all';
    
    papers.forEach(paper => {
        if (activeFilter === 'all') {
            paper.classList.remove('hidden');
        } else {
            const hasChange = paper.dataset.hasChange === 'true';
            const hasIncrease = paper.dataset.hasIncrease === 'true';
            const hasDecrease = paper.dataset.hasDecrease === 'true';
            const hasRatingNochange = paper.dataset.hasRatingnochange === 'true';
            const hasReviews = paper.dataset.hasReviews === 'true';
            
            let show = false;
            if (activeFilter === 'increase' && hasIncrease) show = true;
            if (activeFilter === 'decrease' && hasDecrease) show = true;
            if (activeFilter === 'ratingnochange' && hasRatingNochange) show = true;
            // No Changes: 有review但没有任何变化
            if (activeFilter === 'nochanges' && !hasChange && hasReviews) show = true;
            // No Reviews: 没有review
            if (activeFilter === 'noreviews' && !hasReviews) show = true;
            
            paper.classList.toggle('hidden', !show);
        }
    });
    
    updateStats(tabName);
}

function toggleFilter(tabName, filterName) {
    // 单选模式：移除所有active，只激活当前按钮
    document.querySelectorAll(`#${tabName} .filter-btn`).forEach(b => b.classList.remove('active'));
    document.querySelector(`#${tabName} .filter-btn[data-filter="${filterName}"]`).classList.add('active');
    
    updateFilters(tabName);
}

function updateStats(tabName) {
    // 统计功能已移除，保留函数以避免错误
}

function toggleVersions(replyId) {
    const versionsDiv = document.getElementById('versions-' + replyId);
    if (versionsDiv) {
        versionsDiv.classList.toggle('show');
    }
}

function toggleReplyFilter(filterName) {
    // 单选模式：移除所有active，只激活当前按钮
    document.querySelectorAll('.replies-section .filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.replies-section .filter-btn[data-filter="${filterName}"]`).classList.add('active');
    
    // 筛选reply卡片
    const replyCards = document.querySelectorAll('.reply-card');
    replyCards.forEach(card => {
        if (filterName === 'all') {
            card.classList.remove('hidden');
        } else {
            const cardFilter = card.dataset.replyFilter;
            card.classList.toggle('hidden', cardFilter !== filterName);
        }
    });
}

async function loadDetails(paperId) {
    const detailsDiv = document.getElementById('details-' + paperId);
    const toggleBtn = event.target;
    
    // 如果已经展开，则收起
    if (detailsDiv.style.display === 'block') {
        detailsDiv.style.display = 'none';
        toggleBtn.textContent = '▼ Show details';
        return;
    }
    
    // 如果已经加载过内容，直接展开
    if (detailsDiv.innerHTML.trim() !== '') {
        detailsDiv.style.display = 'block';
        toggleBtn.textContent = '▲ Hide details';
        return;
    }
    
    // 显示加载中
    detailsDiv.innerHTML = '<div style="color: #999; font-size: 0.85em;">Loading...</div>';
    detailsDiv.style.display = 'block';
    toggleBtn.textContent = '▲ Hide details';
    
    try {
        // 通过CORS代理访问OpenReview API
        const proxyUrl = 'https://corsproxy.io/?';
        const apiUrl = `https://api2.openreview.net/notes?id=${paperId}`;
        const response = await fetch(proxyUrl + encodeURIComponent(apiUrl), {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.notes && data.notes.length > 0) {
            const note = data.notes[0];
            const content = note.content;
            
            let html = '';
            
            // Keywords
            if (content.keywords && content.keywords.value && content.keywords.value.length > 0) {
                html += `<div class="detail-section"><strong>Keywords:</strong> ${content.keywords.value.join('; ')}</div>`;
            }
            
            // TL;DR
            const tldr = content.TLDR?.value || content.tldr?.value || '';
            if (tldr) {
                html += `<div class="detail-section"><strong>TL;DR:</strong> ${tldr}</div>`;
            }
            
            // Abstract
            if (content.abstract && content.abstract.value) {
                const abstractHtml = typeof marked !== 'undefined' ? marked.parse(content.abstract.value) : content.abstract.value.replace(/\\n/g, '<br>');
                html += `<div class="detail-section"><strong>Abstract:</strong><div style="margin-top: 4px;">${abstractHtml}</div></div>`;
            }
            
            // Supplementary Material
            if (content.supplementary_material && content.supplementary_material.value) {
                const suppUrl = content.supplementary_material.value.startsWith('/') 
                    ? 'https://openreview.net' + content.supplementary_material.value 
                    : content.supplementary_material.value;
                const fileExt = suppUrl.split('.').pop().toLowerCase();
                html += `<div class="detail-section"><strong>Supplementary Material:</strong> <a href="${suppUrl}" target="_blank" class="pdf-link">${fileExt}</a></div>`;
            }
            
            // Primary Area
            const primaryArea = content.primary_area?.value || '';
            if (primaryArea) {
                html += `<div class="detail-section"><strong>Primary Area:</strong> ${primaryArea}</div>`;
            }
            
            detailsDiv.innerHTML = html || '<div style="padding: 10px; color: #666;">No additional details available.</div>';
            
            // 触发MathJax渲染
            if (window.MathJax) {
                MathJax.typesetPromise([detailsDiv]).catch((err) => console.log('MathJax error:', err));
            }
        } else {
            detailsDiv.innerHTML = '<div style="padding: 10px; color: #999;">Failed to load details.</div>';
        }
    } catch (error) {
        console.error('Error loading details:', error);
        detailsDiv.innerHTML = '<div style="padding: 10px; color: #c62828;">Error loading details. Please try again.</div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateStats('active');
    updateStats('withdrawn');
});
"""

def generate_index_html_lightweight():
    """Generate lightweight index.html that loads data from JSON"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ICLR 2026 Submissions</title>
    <style>{generate_css()}</style>
    <script>
    MathJax = {{
        tex: {{
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            processEnvironments: true
        }},
        options: {{
            skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
        }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="assets/cache-manager.js"></script>
</head>
<body>
    <header>
        <div class="container">
            <h1>ICLR 2026 Submissions</h1>
            <div id="cache-status" style="text-align: center; margin-top: 8px;"></div>
        </div>
    </header>
    <div class="container">
        <div id="loading" style="text-align: center; padding: 40px; color: #666;">
            <div style="font-size: 1.2em; margin-bottom: 10px;">Loading papers...</div>
            <div style="font-size: 0.9em;">Please wait</div>
        </div>
        <div id="main-content" style="display: none;">
            <div class="tabs">
                <button class="tab active" data-tab="active" onclick="switchTab('active')">Active Submissions <span id="active-count"></span></button>
                <button class="tab" data-tab="withdrawn" onclick="switchTab('withdrawn')">Withdrawn Submissions <span id="withdrawn-count"></span></button>
            </div>
            <div id="active" class="tab-content active"></div>
            <div id="withdrawn" class="tab-content"></div>
        </div>
    </div>
    <script>{generate_js()}</script>
    <script>
// 全局变量
let allPapers = [];
let cache = new PapersCache();

// 页面加载
document.addEventListener('DOMContentLoaded', async () => {{
    try {{
        // 显示缓存状态
        const status = cache.getStatus();
        if (status.cached) {{
            document.getElementById('cache-status').innerHTML = 
                `<div style="display: inline-block; padding: 6px 12px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; font-size: 0.8em; color: #2e7d32;">✓ Data from: ${{status.lastUpdate}}</div>`;
        }}
        
        // 加载数据
        allPapers = await cache.loadPapers();
        
        // 渲染页面
        renderAllPapers();
        
        // 隐藏loading，显示内容
        document.getElementById('loading').style.display = 'none';
        document.getElementById('main-content').style.display = 'block';
        
        // 更新缓存状态
        const newStatus = cache.getStatus();
        document.getElementById('cache-status').innerHTML = 
            `<div style="display: inline-flex; align-items: center; gap: 8px;">
                <span style="padding: 6px 12px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; font-size: 0.8em; color: #2e7d32;">✓ Data from: ${{newStatus.lastUpdate}}</span>
                <button onclick="refreshData()" style="padding: 6px 12px; background: #ffffff; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 0.8em; color: #333; cursor: pointer; font-weight: 500;">Refresh from Repo</button>
            </div>`;
    }} catch (error) {{
        console.error('Failed to load papers:', error);
        document.getElementById('loading').innerHTML = 
            '<div style="color: #c62828;">Failed to load papers. <button onclick="location.reload()">Retry</button></div>';
    }}
}});

// 刷新数据
function refreshData() {{
    cache.clear();
    location.reload();
}}

// 渲染所有论文
function renderAllPapers() {{
    const activePapers = allPapers.filter(p => !p.withdrawn);
    const withdrawnPapers = allPapers.filter(p => p.withdrawn);
    
    document.getElementById('active-count').textContent = `(${{activePapers.length}})`;
    document.getElementById('withdrawn-count').textContent = `(${{withdrawnPapers.length}})`;
    
    renderPaperList(activePapers, 'active');
    renderPaperList(withdrawnPapers, 'withdrawn');
}}

// 渲染论文列表（分批渲染优化）
function renderPaperList(papers, tabId) {{
    // 统计各类型数量
    let countIncrease = 0, countDecrease = 0, countNochange = 0, countNochanges = 0, countNoReviews = 0;
    papers.forEach(p => {{
        if (p.reviews === 0) {{
            countNoReviews++;
        }} else {{
            const hasAnyChange = p.changes.increase > 0 || p.changes.decrease > 0 || p.changes.nochange > 0;
            if (p.changes.increase > 0) countIncrease++;
            if (p.changes.decrease > 0) countDecrease++;
            if (p.changes.nochange > 0) countNochange++;
            // No Changes: 有review但所有review都没有修改过
            if (!hasAnyChange) countNochanges++;
        }}
    }});
    
    // 生成筛选器
    let html = `
        <div class="filters"><div class="filter-group">
            <button class="filter-btn active" data-filter="all" onclick="toggleFilter('${{tabId}}', 'all')">All <span class="filter-count">(${{papers.length}})</span></button>
            <button class="filter-btn" data-filter="increase" onclick="toggleFilter('${{tabId}}', 'increase')">Rating ↑ <span class="filter-count">(${{countIncrease}})</span></button>
            <button class="filter-btn" data-filter="decrease" onclick="toggleFilter('${{tabId}}', 'decrease')">Rating ↓ <span class="filter-count">(${{countDecrease}})</span></button>
            <button class="filter-btn" data-filter="ratingnochange" onclick="toggleFilter('${{tabId}}', 'ratingnochange')">Rating = <span class="filter-count">(${{countNochange}})</span></button>
            <button class="filter-btn" data-filter="nochanges" onclick="toggleFilter('${{tabId}}', 'nochanges')">No Changes <span class="filter-count">(${{countNochanges}})</span></button>
            <button class="filter-btn" data-filter="noreviews" onclick="toggleFilter('${{tabId}}', 'noreviews')">No Reviews <span class="filter-count">(${{countNoReviews}})</span></button>
        </div></div>
        <div class="paper-list" id="list-${{tabId}}"></div>`;
    
    document.getElementById(tabId).innerHTML = html;
    
    // 分批渲染论文卡片（每批200个）
    const batchSize = 200;
    let currentIndex = 0;
    const listContainer = document.getElementById(`list-${{tabId}}`);
    
    function renderBatch() {{
        const endIndex = Math.min(currentIndex + batchSize, papers.length);
        const fragment = document.createDocumentFragment();
        
        for (let i = currentIndex; i < endIndex; i++) {{
            const paper = papers[i];
            const card = createPaperCard(paper);
            fragment.appendChild(card);
        }}
        
        listContainer.appendChild(fragment);
        currentIndex = endIndex;
        
        // 每批次渲染后都应用当前筛选状态
        updateFilters(tabId);
        
        if (currentIndex < papers.length) {{
            requestAnimationFrame(renderBatch);
        }}
    }}
    
    renderBatch();
}}

// 创建单个论文卡片
function createPaperCard(paper) {{
    const div = document.createElement('div');
    div.className = 'paper-card';
    
    const hasChanges = paper.changes.increase + paper.changes.decrease + paper.changes.nochange > 0;
    const hasIncrease = paper.changes.increase > 0;
    const hasDecrease = paper.changes.decrease > 0;
    const hasNochange = paper.changes.nochange > 0;
    const hasReviews = paper.reviews > 0;
    
    div.dataset.paperId = paper.id;
    div.dataset.hasChange = hasChanges;
    div.dataset.hasIncrease = hasIncrease;
    div.dataset.hasDecrease = hasDecrease;
    div.dataset.hasRatingnochange = hasNochange;
    div.dataset.hasReviews = hasReviews;
    
    // 格式化时间
    const cdate = new Date(paper.cdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}});
    const mdate = paper.mdate && paper.mdate !== paper.cdate ? 
        new Date(paper.mdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) : null;
    const dateDisplay = mdate ? `${{cdate}} (modified: ${{mdate}})` : cdate;
    
    // PDF URL
    let pdfUrl = paper.pdf;
    if (pdfUrl && pdfUrl.startsWith('/')) {{
        pdfUrl = 'https://openreview.net' + pdfUrl;
    }}
    
    div.innerHTML = `
        <div class="paper-title"><a href="paper.html#${{paper.id}}">${{paper.title}}</a></div>
        <div class="paper-info-line">${{paper.venue}} ${{paper.number}}</div>
        <div class="paper-info-line">${{dateDisplay}}${{pdfUrl ? ' • <a href="' + pdfUrl + '" target="_blank" class="pdf-link">PDF</a>' : ''}}</div>
        <div class="paper-toggle" onclick="loadDetails('${{paper.id}}')">▼ Show details</div>
        <div class="paper-details" id="details-${{paper.id}}" style="display:none;"></div>
        <div class="paper-meta">
            <span class="meta-item">📝 ${{paper.reviews}} reviews</span>
            ${{hasIncrease ? `<span class="badge badge-increase">Rating ↑ (${{paper.changes.increase}})</span>` : ''}}
            ${{hasDecrease ? `<span class="badge badge-decrease">Rating ↓ (${{paper.changes.decrease}})</span>` : ''}}
            ${{hasNochange ? `<span class="badge badge-ratingnochange">Rating = (${{paper.changes.nochange}})</span>` : ''}}
            ${{!hasChanges ? '<span class="badge badge-nochanges">No Changes</span>' : ''}}
        </div>`;
    
    return div;
}}
    </script>
</body>
</html>"""
    
    return html


def generate_papers_json(submissions):
    """Generate JSON data for papers list"""
    from datetime import datetime
    
    papers_data = []
    for submission in submissions:
        content = submission.get('content', {})
        paper_id = submission.get('id', '')
        number = submission.get('number', '')
        cdate = submission.get('cdate', 0)
        mdate = submission.get('mdate', 0)
        venue = content.get('venue', {}).get('value', 'ICLR 2026 Conference Submission')
        pdf_url = content.get('pdf', {}).get('value', '')
        title = content.get('title', {}).get('value', 'Untitled')
        
        # 计算review统计
        replies = submission.get('details', {}).get('directReplies', [])
        review_count = count_reviews(replies)
        increase_count, decrease_count, ratingnochange_count, nochanges_count = count_review_changes_by_type(replies)
        
        papers_data.append({
            'id': paper_id,
            'title': title,
            'number': number,
            'cdate': cdate,
            'mdate': mdate,
            'venue': venue,
            'pdf': pdf_url,
            'reviews': review_count,
            'changes': {
                'increase': increase_count,
                'decrease': decrease_count,
                'nochange': ratingnochange_count,
                'nochanges': nochanges_count
            },
            'withdrawn': is_withdrawn(submission)
        })
    
    return papers_data

def generate_paper_template_html():
    """Generate single page template for paper details"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paper - ICLR 2026</title>
    <style>{generate_css()}</style>
    <script>
    MathJax = {{
        tex: {{
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            processEnvironments: true
        }},
        options: {{
            skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
        }}
    }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <header>
        <div class="container">
            <h1>ICLR 2026 Submissions</h1>
        </div>
    </header>
    <div class="container">
        <a href="javascript:void(0)" onclick="goBack()" class="back-link">← Back to list</a>
        <div id="loading" style="text-align: center; padding: 40px; color: #666;">
            <div style="font-size: 1.2em; margin-bottom: 10px;">Loading paper...</div>
            <div style="font-size: 0.9em;">Please wait</div>
        </div>
        <div id="paper-content" style="display: none;"></div>
    </div>
    <script>{generate_js()}</script>
    <script>
// 智能返回函数
function goBack() {{
    // 检查是否有 referrer 且来自同一站点
    if (document.referrer && document.referrer.includes(window.location.host)) {{
        history.back();
    }} else {{
        // 如果是直接打开或来自外部链接，跳转到主页
        window.location.href = 'index.html';
    }}
}}

// 加载论文详情
async function loadPaper() {{
    const paperId = location.hash.slice(1);
    if (!paperId) {{
        document.getElementById('loading').innerHTML = '<div style="color: #c62828;">No paper ID specified</div>';
        return;
    }}
    
    try {{
        const response = await fetch(`data/papers/${{paperId}}.json`);
        if (!response.ok) throw new Error('Paper not found');
        
        const paper = await response.json();
        renderPaper(paper);
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('paper-content').style.display = 'block';
        
        // 更新标题
        document.title = paper.content.title + ' - ICLR 2026';
    }} catch (error) {{
        console.error('Failed to load paper:', error);
        document.getElementById('loading').innerHTML = 
            '<div style="color: #c62828;">Failed to load paper. <a href="index.html">Back to list</a></div>';
    }}
}}

// 渲染论文
function renderPaper(paper) {{
    const content = paper.content;
    const cdate = paper.cdate ? new Date(paper.cdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) : 'Unknown';
    const mdate = paper.mdate && paper.mdate !== paper.cdate ? 
        new Date(paper.mdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) : null;
    
    let pdfUrl = content.pdf;
    if (pdfUrl && pdfUrl.startsWith('/')) {{
        pdfUrl = 'https://openreview.net' + pdfUrl;
    }}
    
    const forumUrl = `https://openreview.net/forum?id=${{paper.id}}`;
    
    // 计算review统计
    const replies = paper.replies || [];
    let reviewCount = 0;
    let commentCount = 0;
    replies.forEach(r => {{
        const invitations = r.invitations || [];
        if (invitations.some(inv => inv.includes('Official_Review'))) reviewCount++;
        else if (invitations.some(inv => inv.includes('Official_Comment'))) commentCount++;
    }});
    
    let html = `
        <div class="detail-container">
            <h1 class="paper-title">${{content.title}}</h1>
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Paper ID</div>
                    <div class="metadata-value">${{paper.id}}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Submission Number</div>
                    <div class="metadata-value">${{content.venue}} ${{paper.number}}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Date</div>
                    <div class="metadata-value">${{cdate}}${{mdate ? ' (modified: ' + mdate + ')' : ''}}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Reviews / Comments</div>
                    <div class="metadata-value">${{reviewCount}} reviews / ${{commentCount}} comments</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Links</div>
                    <div class="metadata-value">
                        <a href="${{forumUrl}}" target="_blank">OpenReview</a>
                        ${{pdfUrl ? ' | <a href="' + pdfUrl + '" target="_blank">PDF</a>' : ''}}
                    </div>
                </div>
            </div>
            
            <div class="metadata-item" style="margin-top: 12px;">
                <div class="metadata-label">Primary Area</div>
                <div class="metadata-value">${{content.primary_area || 'N/A'}}</div>
            </div>
            
            ${{content.keywords && content.keywords.length > 0 ? 
                '<div class="metadata-item" style="margin-top: 8px;"><div class="metadata-label">Keywords</div><div class="metadata-value">' + content.keywords.join(', ') + '</div></div>' 
                : ''}}
            
            ${{content.tldr ? 
                '<div class="metadata-item" style="margin-top: 8px;"><div class="metadata-label">TL;DR</div><div class="metadata-value">' + content.tldr + '</div></div>' 
                : ''}}
            
            <div class="abstract">
                <h3>Abstract</h3>
                <div>${{typeof marked !== 'undefined' ? marked.parse(content.abstract) : content.abstract}}</div>
            </div>
        </div>
        
        <div class="replies-section">
            <h2>Reviews and Comments (${{replies.length}})</h2>
            <div id="nested-loading" style="padding: 10px; margin-bottom: 15px; color: #666; font-size: 0.9em; background: #fafafa; border-radius: 5px; border: 1px solid #e5e5e5;">
                Loading nested replies...
            </div>
            <div class="filters" id="reply-filters" style="display: none;">
                <div class="filter-group">
                    <button class="filter-btn active" data-filter="all" onclick="toggleReplyFilter('all')">All <span class="filter-count" id="count-all"></span></button>
                    <button class="filter-btn" data-filter="increase" onclick="toggleReplyFilter('increase')">Rating ↑ <span class="filter-count" id="count-increase"></span></button>
                    <button class="filter-btn" data-filter="decrease" onclick="toggleReplyFilter('decrease')">Rating ↓ <span class="filter-count" id="count-decrease"></span></button>
                    <button class="filter-btn" data-filter="ratingnochange" onclick="toggleReplyFilter('ratingnochange')">Rating = <span class="filter-count" id="count-nochange"></span></button>
                    <button class="filter-btn" data-filter="nochanges" onclick="toggleReplyFilter('nochanges')">No Changes <span class="filter-count" id="count-nochanges"></span></button>
                    <button class="filter-btn" data-filter="comments" onclick="toggleReplyFilter('comments')">Comments <span class="filter-count" id="count-comments"></span></button>
                </div>
            </div>
            <div id="replies-container"></div>
        </div>`;
    
    document.getElementById('paper-content').innerHTML = html;
    
    // 渲染replies（使用现有的逻辑）
    renderReplies(replies);
    
    // 加载nested replies
    loadNestedReplies(paper.id);
    
    // 触发MathJax渲染
    if (window.MathJax) {{
        MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err));
    }}
}}

// 渲染replies（完整版）
function renderReplies(replies) {{
    if (!replies || replies.length === 0) {{
        document.getElementById('replies-container').innerHTML = '<div style="padding: 20px; color: #666;">No replies yet.</div>';
        return;
    }}
    
    // 按reply ID分组
    const repliesById = {{}};
    replies.forEach(reply => {{
        const id = reply.id;
        if (!repliesById[id]) {{
            repliesById[id] = [];
        }}
        repliesById[id].push(reply);
    }});
    
    // 排序每组的版本（按mdate，最新的在前）
    Object.keys(repliesById).forEach(id => {{
        repliesById[id].sort((a, b) => (b.mdate || 0) - (a.mdate || 0));
    }});
    
    // 按最新修改时间排序reply IDs
    const sortedReplyIds = Object.keys(repliesById).sort((a, b) => {{
        const aLatest = Math.max(...repliesById[a].map(v => v.mdate || 0));
        const bLatest = Math.max(...repliesById[b].map(v => v.mdate || 0));
        return bLatest - aLatest;
    }});
    
    // 统计各类型数量
    let countAll = 0, countIncrease = 0, countDecrease = 0, countNochange = 0, countNochanges = 0, countComments = 0;
    
    let html = '';
    
    sortedReplyIds.forEach(replyId => {{
        const versions = repliesById[replyId];
        const latest = versions[0];
        const content = latest.content || {{}};
        const invitations = latest.invitations || [];
        
        const isReview = invitations.some(inv => inv.includes('Official_Review'));
        const isComment = invitations.some(inv => inv.includes('Official_Comment'));
        const isAuthorResponse = latest.signatures && latest.signatures.some(sig => sig.includes('Authors'));
        
        // 计算rating变化
        let ratingChange = 0;
        let filterType = 'nochanges';
        if (isComment) {{
            filterType = 'comments';
            countComments++;
        }} else if (isReview && versions.length > 1) {{
            const oldRating = versions[versions.length - 1].content?.rating?.value;
            const newRating = latest.content?.rating?.value;
            if (oldRating !== undefined && newRating !== undefined) {{
                ratingChange = newRating - oldRating;
                if (ratingChange > 0) {{
                    filterType = 'increase';
                    countIncrease++;
                }} else if (ratingChange < 0) {{
                    filterType = 'decrease';
                    countDecrease++;
                }} else {{
                    filterType = 'ratingnochange';
                    countNochange++;
                }}
            }} else {{
                countNochanges++;
            }}
        }} else {{
            countNochanges++;
        }}
        countAll++;
        
        const reviewer = latest.signatures ? latest.signatures[0].split('/').pop() : 'Anonymous';
        const cdate = latest.cdate || 0;
        const mdate = latest.mdate || 0;
        
        // 格式化时间
        const cdateStr = cdate ? new Date(cdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) + ', ' + new Date(cdate).toLocaleTimeString('en-GB', {{hour: '2-digit', minute: '2-digit', hour12: false}}) : 'Unknown';
        const mdateStr = mdate ? new Date(mdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) + ', ' + new Date(mdate).toLocaleTimeString('en-GB', {{hour: '2-digit', minute: '2-digit', hour12: false}}) : 'Unknown';
        const dateDisplay = (cdate && mdate && cdate !== mdate) ? cdateStr + ' (modified: ' + mdateStr + ')' : cdateStr;
        
        const cardClass = isAuthorResponse ? 'reply-card author-reply' : 'reply-card';
        
        html += `<div class="${{cardClass}}" data-reply-filter="${{filterType}}" data-reply-id="${{replyId}}">`;
        html += `<div class="reply-header"><div class="reply-meta">`;
        html += `<strong>${{reviewer}}</strong>`;
        if (isAuthorResponse) {{
            html += `<span class="badge badge-author">Author Response</span>`;
        }}
        html += `<span class="reply-date">${{dateDisplay}}</span>`;
        html += `</div></div>`;
        
        // 显示内容（支持Markdown）
        for (let key in content) {{
            const value = content[key]?.value;
            if (value !== undefined && value !== null && key !== 'title') {{
                const label = key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                html += `<div class="content-section">`;
                html += `<div class="content-label">${{label}}</div>`;
                // 只对字符串类型使用marked解析
                let processedValue;
                if (typeof value === 'string') {{
                    processedValue = typeof marked !== 'undefined' ? marked.parse(value) : value.replace(/\\n/g, '<br>');
                }} else {{
                    processedValue = String(value);
                }}
                html += `<div class="content-text">${{processedValue}}</div>`;
                html += `</div>`;
            }}
        }}
        
        // 如果有多个版本，显示旧版本
        if (versions.length > 1) {{
            html += `<div class="version-toggle" onclick="toggleVersions('${{replyId}}')">▼ Show ${{versions.length - 1}} older version(s)</div>`;
            html += `<div class="old-versions" id="versions-${{replyId}}">`;
            
            for (let i = 1; i < versions.length; i++) {{
                const oldVersion = versions[i];
                const oldContent = oldVersion.content || {{}};
                const oldMdate = oldVersion.mdate || 0;
                const oldMdateStr = oldMdate ? new Date(oldMdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) + ', ' + new Date(oldMdate).toLocaleTimeString('en-GB', {{hour: '2-digit', minute: '2-digit', hour12: false}}) : 'Unknown';
                
                html += `<div class="version-item">`;
                html += `<div style="font-weight: 600; margin-bottom: 8px; color: #666;">Version from ${{oldMdateStr}}</div>`;
                
                for (let key in oldContent) {{
                    const value = oldContent[key]?.value;
                    if (value !== undefined && value !== null && key !== 'title') {{
                        const label = key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                        html += `<div class="content-section">`;
                        html += `<div class="content-label">${{label}}</div>`;
                        // 只对字符串类型使用marked解析
                        let processedValue;
                        if (typeof value === 'string') {{
                            processedValue = typeof marked !== 'undefined' ? marked.parse(value) : value.replace(/\\n/g, '<br>');
                        }} else {{
                            processedValue = String(value);
                        }}
                        html += `<div class="content-text">${{processedValue}}</div>`;
                        html += `</div>`;
                    }}
                }}
                
                html += `</div>`;
            }}
            
            html += `</div>`;
        }}
        
        html += `</div>`;
    }});
    
    document.getElementById('replies-container').innerHTML = html;
    
    // 更新筛选器统计
    document.getElementById('count-all').textContent = `(${{countAll}})`;
    document.getElementById('count-increase').textContent = `(${{countIncrease}})`;
    document.getElementById('count-decrease').textContent = `(${{countDecrease}})`;
    document.getElementById('count-nochange').textContent = `(${{countNochange}})`;
    document.getElementById('count-nochanges').textContent = `(${{countNochanges}})`;
    document.getElementById('count-comments').textContent = `(${{countComments}})`;
    
    // 显示筛选器
    document.getElementById('reply-filters').style.display = 'block';
}}

// 筛选replies
function toggleReplyFilter(filterName) {{
    // 单选模式
    document.querySelectorAll('.replies-section .filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.replies-section .filter-btn[data-filter="${{filterName}}"]`).classList.add('active');
    
    // 筛选reply卡片（只筛选顶层的reply，不包括nested replies）
    const allReplyCards = document.querySelectorAll('.reply-card');
    allReplyCards.forEach(card => {{
        const isNested = card.closest('.nested-replies') !== null;
        
        if (isNested) {{
            return; // nested replies跟随父级
        }}
        
        if (filterName === 'all') {{
            card.classList.remove('hidden');
            const nestedContainer = card.querySelector('.nested-replies');
            if (nestedContainer) nestedContainer.style.display = 'block';
        }} else {{
            const cardFilter = card.dataset.replyFilter;
            const shouldShow = cardFilter === filterName;
            card.classList.toggle('hidden', !shouldShow);
            
            const nestedContainer = card.querySelector('.nested-replies');
            if (nestedContainer) {{
                nestedContainer.style.display = shouldShow ? 'block' : 'none';
            }}
        }}
    }});
}}

// 切换版本显示
function toggleVersions(replyId) {{
    const versionsDiv = document.getElementById('versions-' + replyId);
    if (versionsDiv) {{
        versionsDiv.classList.toggle('show');
    }}
}}

// 加载nested replies
async function loadNestedReplies(paperId) {{
    const loadingDiv = document.getElementById('nested-loading');
    
    try {{
        const proxyUrl = 'https://corsproxy.io/?';
        const apiUrl = `https://api2.openreview.net/notes?id=${{paperId}}&details=replies`;
        const response = await fetch(proxyUrl + encodeURIComponent(apiUrl));
        
        if (!response.ok) throw new Error(`HTTP error! status: ${{response.status}}`);
        
        const data = await response.json();
        
        if (data.notes && data.notes.length > 0) {{
            const note = data.notes[0];
            const allReplies = note.details?.replies || [];
            
            // 构建reply树
            const replyTree = {{}};
            allReplies.forEach(reply => {{
                const replyTo = reply.replyto || paperId;
                if (!replyTree[replyTo]) replyTree[replyTo] = [];
                replyTree[replyTo].push(reply);
            }});

            // 为每个direct reply添加nested replies
            let nestedCount = 0;
            document.querySelectorAll('.reply-card').forEach(card => {{
                // 直接从 data-reply-id 获取 replyId
                const replyId = card.dataset.replyId;

                if (replyId && replyTree[replyId]) {{
                    const nestedReplies = replyTree[replyId];
                    nestedReplies.sort((a, b) => (a.cdate || 0) - (b.cdate || 0));

                    const nestedContainer = document.createElement('div');
                    nestedContainer.className = 'nested-replies';
                    nestedContainer.style.marginLeft = '30px';
                    nestedContainer.style.marginTop = '10px';
                    
                    nestedReplies.forEach(nestedReply => {{
                        const nestedCard = createReplyCard(nestedReply, true);
                        nestedContainer.appendChild(nestedCard);
                        nestedCount++;
                    }});
                    
                    card.appendChild(nestedContainer);
                }}
            }});
            
            if (nestedCount > 0) {{
                loadingDiv.innerHTML = `<span style="color: #2e7d32;">✓ Loaded ${{nestedCount}} nested replies</span>`;
                setTimeout(() => loadingDiv.style.display = 'none', 3000);
                if (window.MathJax) MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
            }} else {{
                loadingDiv.style.display = 'none';
            }}
        }} else {{
            loadingDiv.innerHTML = '<span style="color: #999;">No nested replies found</span>';
            setTimeout(() => loadingDiv.style.display = 'none', 2000);
        }}
    }} catch (error) {{
        console.error('Error loading nested replies:', error);
        loadingDiv.innerHTML = '<span style="color: #c62828;">Failed to load nested replies</span>';
        setTimeout(() => loadingDiv.style.display = 'none', 3000);
    }}
}}

// 创建reply卡片
function createReplyCard(reply, isNested = false) {{
    const card = document.createElement('div');
    const content = reply.content || {{}};
    const isAuthorResponse = reply.signatures && reply.signatures.some(sig => sig.includes('Authors'));
    
    card.className = isAuthorResponse ? 'reply-card author-reply' : 'reply-card';
    if (isNested) {{
        card.style.fontSize = '0.92em';
        card.style.marginBottom = '8px';
    }}
    
    const reviewer = reply.signatures ? reply.signatures[0].split('/').pop() : 'Anonymous';
    const cdate = reply.cdate || 0;
    const mdate = reply.mdate || 0;
    
    const cdateStr = cdate ? new Date(cdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) + ', ' + new Date(cdate).toLocaleTimeString('en-GB', {{hour: '2-digit', minute: '2-digit', hour12: false}}) : 'Unknown';
    const mdateStr = mdate ? new Date(mdate).toLocaleDateString('en-GB', {{day: '2-digit', month: 'short', year: 'numeric'}}) + ', ' + new Date(mdate).toLocaleTimeString('en-GB', {{hour: '2-digit', minute: '2-digit', hour12: false}}) : 'Unknown';
    const dateDisplay = (cdate && mdate && cdate !== mdate) ? cdateStr + ' (modified: ' + mdateStr + ')' : cdateStr;
    
    let html = '<div class="reply-header"><div class="reply-meta">';
    html += '<strong>' + reviewer + '</strong>';
    if (isAuthorResponse) html += '<span class="badge badge-author">Author Response</span>';
    html += '<span class="reply-date">' + dateDisplay + '</span>';
    html += '</div></div>';
    
    for (let key in content) {{
        const value = content[key]?.value;
        if (value !== undefined && value !== null && key !== 'title') {{
            const label = key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
            html += '<div class="content-section">';
            html += '<div class="content-label">' + label + '</div>';
            let processedValue;
            if (typeof value === 'string') {{
                processedValue = typeof marked !== 'undefined' ? marked.parse(value) : value.replace(/\\n/g, '<br>');
            }} else {{
                processedValue = String(value);
            }}
            html += '<div class="content-text">' + processedValue + '</div>';
            html += '</div>';
        }}
    }}
    
    card.innerHTML = html;
    return card;
}}

// 监听hash变化
window.addEventListener('hashchange', loadPaper);
window.addEventListener('load', loadPaper);
    </script>
</body>
</html>"""
    
    return html

def generate_paper_detail_json(submission):
    """Generate JSON data for a single paper detail"""
    content = submission.get('content', {})
    
    # 提取所有需要的字段
    paper_data = {
        'id': submission.get('id', ''),
        'number': submission.get('number', ''),
        'cdate': submission.get('cdate', 0),
        'mdate': submission.get('mdate', 0),
        'content': {
            'title': content.get('title', {}).get('value', 'Untitled'),
            'abstract': content.get('abstract', {}).get('value', ''),
            'tldr': content.get('TLDR', {}).get('value', '') or content.get('tldr', {}).get('value', ''),
            'keywords': content.get('keywords', {}).get('value', []),
            'primary_area': content.get('primary_area', {}).get('value', ''),
            'venue': content.get('venue', {}).get('value', 'ICLR 2026 Conference Submission'),
            'pdf': content.get('pdf', {}).get('value', ''),
            'supplementary_material': content.get('supplementary_material', {}).get('value', '')
        },
        'replies': submission.get('details', {}).get('directReplies', []),
        'withdrawn': is_withdrawn(submission)
    }
    
    return paper_data

def main():
    """Main function to generate the static site"""
    # Load data
    data_path = 'data/iclr2026_submissions_merged.json'
    print(f"Loading data from {data_path}...")
    submissions = load_data(data_path)
    print(f"Loaded {len(submissions)} submissions")
    
    # Create output directory
    output_dir = Path('docs')
    output_dir.mkdir(exist_ok=True)
    data_dir = output_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    papers_data_dir = data_dir / 'papers'
    papers_data_dir.mkdir(exist_ok=True)
    assets_dir = output_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)
    
    # Generate JSON data for papers list
    print("Generating papers JSON data...")
    from datetime import datetime
    papers_data = generate_papers_json(submissions)
    
    # Save papers list JSON (固定文件名)
    papers_json_filename = 'papers-list.json'
    with open(data_dir / papers_json_filename, 'w', encoding='utf-8') as f:
        json.dump(papers_data, f, ensure_ascii=False)
    
    # Save metadata JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    meta_data = {
        'version': timestamp,
        'lastUpdate': int(datetime.now().timestamp() * 1000),
        'totalPapers': len(submissions),
        'dataFile': papers_json_filename
    }
    with open(data_dir / 'papers-meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta_data, f, ensure_ascii=False, indent=2)
    
    print(f"  - Generated {papers_json_filename} ({len(papers_data)} papers)")
    print(f"  - Generated papers-meta.json")
    
    # Generate cache manager JS
    print("Generating cache-manager.js...")
    cache_manager_js = """/**
 * ICLR 2026 Papers Cache Manager
 * 使用浏览器HTTP缓存 + 版本控制
 * 当版本号变化时，添加时间戳参数强制刷新
 */
class PapersCache {
  constructor() {
    this.META_KEY = 'iclr2026_papers_meta';
    this.cachedPapers = null;
  }
  
  // 加载数据（智能缓存）
  async loadPapers() {
    // 1. 如果内存中已有数据，直接返回（页面刷新前有效）
    if (this.cachedPapers) {
      console.log('✓ Loading from memory cache');
      return this.cachedPapers;
    }
    
    // 2. 获取元数据
    const meta = await fetch('data/papers-meta.json?t=' + Date.now()).then(r => r.json());
    const localMeta = JSON.parse(localStorage.getItem(this.META_KEY) || '{}');
    
    // 3. 检查版本是否变化
    let dataUrl = `data/${meta.dataFile}`;
    if (localMeta.version !== meta.version) {
      // 版本变化，添加时间戳强制刷新
      console.log('↓ New version detected, fetching from server');
      dataUrl += '?t=' + Date.now();
      localStorage.setItem(this.META_KEY, JSON.stringify(meta));
    } else {
      // 版本未变化，使用浏览器缓存
      console.log('✓ Loading from browser cache (version matched)');
    }
    
    // 4. 加载数据
    const papers = await fetch(dataUrl).then(r => r.json());
    
    // 5. 保存到内存
    this.cachedPapers = papers;
    
    console.log(`✓ Loaded ${papers.length} papers (version: ${meta.version})`);
    return papers;
  }
  
  // 清除缓存
  clear() {
    localStorage.removeItem(this.META_KEY);
    this.cachedPapers = null;
    console.log('✓ Cache cleared');
  }
  
  // 获取缓存状态
  getStatus() {
    const meta = JSON.parse(localStorage.getItem(this.META_KEY) || '{}');
    if (meta.version) {
      return {
        cached: true,
        version: meta.version,
        lastUpdate: new Date(meta.lastUpdate).toLocaleString(),
        totalPapers: meta.totalPapers
      };
    }
    return { cached: false };
  }
}
"""
    with open(assets_dir / 'cache-manager.js', 'w', encoding='utf-8') as f:
        f.write(cache_manager_js)
    print("  - Generated cache-manager.js")
    
    # Generate lightweight index page
    print("Generating index.html (lightweight version)...")
    index_html = generate_index_html_lightweight()
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("  - Generated index.html (~50KB)")
    
    # Generate paper.html (single page template)
    print("Generating paper.html (single page template)...")
    paper_html = generate_paper_template_html()
    with open(output_dir / 'paper.html', 'w', encoding='utf-8') as f:
        f.write(paper_html)
    print("  - Generated paper.html (~30KB)")
    
    # Generate individual paper JSON files
    print("Generating paper detail JSON files...")
    total = len(submissions)
    
    for i, submission in enumerate(submissions):
        paper_id = submission.get('id', f'paper_{i}')
        paper_data = generate_paper_detail_json(submission)
        
        output_path = papers_data_dir / f'{paper_id}.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(paper_data, f, ensure_ascii=False)
        
        if (i + 1) % 1000 == 0 or (i + 1) == total:
            print(f"  Generated {i + 1}/{total} JSON files...")
    
    print("\n✅ Site generated successfully in 'docs' directory!")
    print("   - Index page: docs\\index.html")
    print("   - Paper template: docs\\paper.html")
    print(f"   - Paper JSON files: docs\\data\\papers ({total} files)")
    print("   - Papers list JSON: docs\\data\\papers-list.json")
    print("\n⚠️  IMPORTANT: To view the site, you must use a local web server:")
    print("   cd docs")
    print("   python -m http.server 8000")
    print("   Then open http://localhost:8000 in your browser")
    print("\n   (Do NOT open index.html directly with file:// protocol)")

if __name__ == '__main__':
    main()
