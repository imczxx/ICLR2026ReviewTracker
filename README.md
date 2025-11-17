# ICLR 2026 Review Tracking System

English | [简体中文](README_zh.md)

> 💡 **Code with AI**: This project is developed with the assistance of AI coding tools.

Track the review change history of ICLR 2026 conference submissions, supporting viewing of all historical versions.

## ✨ Core Features

### 📜 Complete Review History Tracking
- **Preserve All Versions**: Every review modification is recorded, no historical information is lost
- **Version Comparison**: View all historical versions of reviews, track rating and content changes
- **Change Labels**: Automatically mark rating changes (↑ Increase / ↓ Decrease / = No Change)
- **Timeline**: Display creation and modification time for each version

### 🔍 Smart Filtering
- Filter papers by review change type (Rating ↑/↓/=/No Changes/No Reviews)
  - **Rating ↑**: Papers with rating increases
  - **Rating ↓**: Papers with rating decreases
  - **Rating =**: Papers with content changes but same rating
  - **No Changes**: Papers with reviews but no modifications
  - **No Reviews**: Papers without any reviews
- Filter by review type (Reviews/Comments)
- Support Active/Withdrawn paper classification

### 🌐 Modern Web Interface
- **Single Page Application**: Use Hash routing for fast switching
- **Smart Caching**: Instant loading on second visit
- **Responsive Design**: Support for desktop and mobile devices
- **Markdown + LaTeX**: Full support for mathematical formula rendering

## 📁 Project Structure

```
ICLR2026/
├── data/
│   ├── raw/                                    # Raw crawled data
│   │   └── iclr2026_submissions_YYYYMMDD_HHMMSS.json
│   └── iclr2026_submissions_merged.json        # Merged data
├── docs/                                       # Generated static website (GitHub Pages)
│   ├── index.html                              # Homepage
│   ├── paper.html                              # Paper detail template
│   ├── assets/                                 # Static assets
│   │   └── cache-manager.js
│   └── data/                                   # JSON data
│       ├── papers-list.json                    # Paper list
│       ├── papers-meta.json                    # Metadata (with version)
│       └── papers/                             # Paper details
│           └── {paper_id}.json
├── crawl.py                                    # Crawling script
├── merge.py                                    # Merge script (with validation)
├── generate_static_site.py                    # Static site generation script
└── README.md
```

## 🚀 Usage

### 1. Crawl Data

```bash
python crawl.py
```

**Output**: `data/raw/iclr2026_submissions_YYYYMMDD_HHMMSS.json`

### 2. Merge Data

```bash
python merge.py
```

**Features**:
- ✅ Automatically scan all JSON files in `data/raw/`
- ✅ Preserve all review versions (complete modification history)
- ✅ Smart deduplication
- ✅ Support incremental merging
- ✅ Display comparison statistics before and after merging

**Output**: `data/iclr2026_submissions_merged.json`

### 3. Generate Static Website

```bash
python generate_static_site.py
```

**Features**:
- ✅ **JSON Architecture**: Homepage and paper details both use JSON data for dynamic loading
- ✅ **Smart Caching**: Browser automatically caches JSON data, instant loading on second visit
- ✅ **Single Page Application**: Use Hash routing, only need 1 paper.html template
- ✅ **Batch Rendering**: Homepage uses batch rendering to avoid page lag
- ✅ Support Markdown and LaTeX math formula rendering
- ✅ Automatically load nested replies (reply of reply)
- ✅ Review change tracking and filtering
- ✅ Responsive design, clean and readable

**Output**: `docs/` directory
- `docs/index.html` - Homepage (lightweight framework, ~21KB)
- `docs/paper.html` - Paper detail template (single file, ~30KB)
- `docs/data/papers-list.json` - Paper list data (~7.3MB)
- `docs/data/papers-meta.json` - Metadata (with version and timestamp)
- `docs/data/papers/{paper_id}.json` - Paper detail data (19630 files, ~335MB)
- `docs/assets/cache-manager.js` - Cache manager

**Local Preview**:
```bash
# Start local server using Python
cd docs
python -m http.server 8000
# Visit http://localhost:8000
```

**Deploy to GitHub Pages**:
1. Commit and push code to GitHub
2. In repository settings: Settings → Pages → Source → Select `main` branch's `/docs` directory
3. Wait a few minutes, visit `https://{username}.github.io/{repo-name}/`

## 📊 Output Example

```
📊 Before Merge
Total submissions: 19630
Total review entries: 77818
Unique reviews: 77699
Submissions with multi-version reviews: 113

🔄 Starting Merge Process
Processing reviews from merged...
Processing reviews from 20251117_090351...

📊 After Merge
Total submissions: 19630
Total review entries: 77943
Unique reviews: 77794
Submissions with multi-version reviews: 140

📈 Comparison
Review entries: 77818 → 77943 (+125)
Unique reviews: 77699 → 77794 (+95)
Multi-version submissions: 113 → 140 (+27)
```

## 🔄 Daily Updates

```bash
# Crawl latest data, merge and generate website
python crawl.py && python merge.py && python generate_static_site.py
```

## ✨ Core Features

### crawl.py
- Crawl complete data from OpenReview API
- Filename accurate to the second
- Automatically save to `data/raw/`

### merge.py
- Automatically scan and merge all raw files
- Preserve all review version history
- Display statistics comparison before and after merging
- Support incremental merging

### generate_static_site.py
- **JSON Data Generation**: Generate lightweight JSON files instead of massive HTML pages
- **Markdown Support**: Use marked.js to render Markdown content
- **LaTeX Formulas**: Use MathJax to render mathematical formulas
- **Nested Replies**: Automatically load reply of reply via API
- **Review Tracking**: 
  - Display all historical versions of reviews
  - Track rating changes (↑/↓/=)
  - Filter by change type
- **Responsive Design**: Clean, readable modern UI
- **CORS Proxy**: Use corsproxy.io to solve cross-origin issues

## 🌐 Website Features

### Homepage
- **JSON Dynamic Loading**: First load ~7.3MB data, subsequent loads instant from browser cache
- **Batch Rendering**: 200 papers per batch to avoid page lag
- **Smart Caching**: 
  - Browser-side caching: Data cached in your browser's local storage
  - Display cache status and last update time (shows when data was generated in the repository)
  - Refresh button: Clear browser cache and reload latest data from the server/repository
  - Version control: Automatically invalidate old cache when data updates in the repository
- **Paper List**: Display all submissions (Active/Withdrawn)
- **Basic Info**: Title, submission number, date, PDF link
- **Review Statistics**: Number of reviews, change labels
- **Filtering**: Filter by review change type (All/Rating ↑/↓/=/No Changes/No Reviews)
- **Expand Details**: Click "Show details" to dynamically load Keywords, TL;DR, Abstract, etc.

### Paper Detail Page
- **Single Page Application**: Use Hash routing (`paper.html#abc123`), only need 1 HTML template
- **JSON Dynamic Loading**: Load paper data on demand (~20-100KB/paper)
- **Complete Information**: 
  - Metadata: Paper ID, Reviews/Comments count, Review Changes, Links
  - Primary Area, Keywords, TL;DR
  - Abstract (support Markdown and formulas)
- **Reviews and Comments**:
  - Display all review historical versions
  - Automatically load nested replies (reply of reply)
  - Filter by type (All/Rating ↑/↓/=/No Changes/Comments)
  - Display creation time and modification time
  - Support Markdown and LaTeX formulas
- **Time Display**: `13 Nov 2025, 09:34 (modified: 13 Nov 2025, 10:24)`
- **Quick Return**: Click "Back to list" to use browser back, instant return to homepage

## 🏗️ Technical Architecture

### Data Structure
- **JSON Data**: Homepage and paper details both use JSON format storage
  - Homepage: `papers-list.json` (~7.3MB)
  - Metadata: `papers-meta.json` (with version number for cache control)
  - Paper details: `papers/{paper_id}.json` (19630 files, ~335MB)
- **Single Page Application**: Use Hash routing, only need 2 HTML templates
  - `index.html` (~21KB) - Homepage framework
  - `paper.html` (~30KB) - Paper detail template

### Caching Mechanism
- **Browser HTTP Cache**: Automatically cache JSON files
- **Version Control**: Use timestamp version number, automatically invalidate old cache when data updates
- **Memory Cache**: Data saved in memory before page refresh

### Rendering Strategy
- **Batch Rendering**: Homepage renders 200 papers per batch, using `requestAnimationFrame`
- **On-Demand Loading**: Paper details and nested replies loaded on demand from API
- **DocumentFragment**: Reduce number of DOM operations

### Performance
| Scenario | Load Time |
|----------|-----------|
| First visit to homepage | ~1.5-3s |
| Second visit to homepage | ~0.1-0.3s |
| Open paper details | ~0.1s |
| Return to homepage | Instant (browser back) |

### Deployment Requirements
- **Total Size**: ~343MB
- **Largest Single File**: 7.3MB
- **Server**: Requires HTTP server (cannot use file:// protocol directly)
- **Compatibility**: Suitable for static hosting services like GitHub Pages

## 📝 Data Description

- **Raw Data**: `data/raw/` - Complete snapshot of each crawl (not committed to Git)
- **Merged Data**: `data/iclr2026_submissions_merged.json` - Complete data with all historical versions
- **Review Versions**: All different versions of the same review are preserved, modification history can be tracked
- **Static Website**: `docs/` - Generated HTML and JSON files, directly deploy to GitHub Pages

### Review History Tracking Principle

Each time `merge.py` is run:
1. Read all historical snapshots (`data/raw/`)
2. Group by review ID, preserve all versions
3. Record `mdate` (modification time) for each version
4. When displaying on website, show all versions sorted by time

**Example**: A review has 3 versions
- Version 1 (2025-11-10): Rating: 5, Content: "Good paper"
- Version 2 (2025-11-13): Rating: 6, Content: "Good paper, improved"  ← Rating ↑
- Version 3 (2025-11-15): Rating: 6, Content: "Excellent paper"      ← Rating =

The website will display all 3 versions and mark rating changes.
