# ICLR 2026 Review 追踪系统

[English](README.md) | 简体中文

> 💡 **AI辅助开发**: 本项目使用AI编程工具辅助开发。

追踪ICLR 2026会议投稿的review变化历史，支持查看所有历史版本。

## ✨ 核心特性

### 📜 完整的Review历史追踪
- **保留所有版本**：每次review修改都会被记录，不会丢失任何历史信息
- **版本对比**：可以查看review的所有历史版本，追踪rating和内容的变化
- **变化标签**：自动标注rating变化（↑ 增加 / ↓ 减少 / = 不变）
- **时间轴**：显示每个版本的创建和修改时间

### 🔍 智能筛选
- 按review变化类型筛选论文（Rating ↑/↓/=/No Changes/No Reviews）
  - **Rating ↑**: 有rating上升的论文
  - **Rating ↓**: 有rating下降的论文
  - **Rating =**: 内容修改但rating不变的论文
  - **No Changes**: 有review但从未修改的论文
  - **No Reviews**: 没有任何review的论文
- 按review类型筛选（Reviews/Comments）
- 支持Active/Withdrawn论文分类

### 🌐 现代化Web界面
- **单页应用**：使用Hash路由，快速切换
- **智能缓存**：二次访问瞬间加载
- **响应式设计**：支持桌面和移动设备
- **Markdown + LaTeX**：完整支持数学公式渲染

## 📁 项目结构

```
ICLR2026/
├── data/
│   ├── raw/                                    # 原始抓取数据
│   │   └── iclr2026_submissions_YYYYMMDD_HHMMSS.json
│   └── iclr2026_submissions_merged.json        # 合并后的数据
├── docs/                                       # 生成的静态网站（GitHub Pages）
│   ├── index.html                              # 主页
│   ├── paper.html                              # 论文详情模板
│   ├── assets/                                 # 静态资源
│   │   └── cache-manager.js
│   └── data/                                   # JSON数据
│       ├── papers-list.json                    # 论文列表
│       ├── papers-meta.json                    # 元数据（含版本号）
│       └── papers/                             # 论文详情
│           └── {paper_id}.json
├── crawl.py                                    # 抓取脚本
├── merge.py                                    # 合并脚本（含验证）
├── generate_static_site.py                    # 静态网站生成脚本
└── README.md
```

## 🚀 使用方法

### 1. 抓取数据

```bash
python crawl.py
```

**输出**: `data/raw/iclr2026_submissions_YYYYMMDD_HHMMSS.json`

### 2. 合并数据

```bash
python merge.py
```

**功能**:
- ✅ 自动扫描 `data/raw/` 下的所有JSON文件
- ✅ 保留所有review版本（完整修改历史）
- ✅ 智能去重
- ✅ 支持增量合并
- ✅ 显示合并前后的对比统计

**输出**: `data/iclr2026_submissions_merged.json`

### 3. 生成静态网站

```bash
python generate_static_site.py
```

**功能**:
- ✅ **JSON化架构**：主页和论文详情都使用JSON数据动态加载
- ✅ **智能缓存**：浏览器自动缓存JSON数据，二次访问瞬间加载
- ✅ **单页应用**：使用Hash路由，只需1个paper.html模板
- ✅ **分批渲染**：主页使用分批渲染，避免页面卡顿
- ✅ 支持Markdown和LaTeX数学公式渲染
- ✅ 自动加载嵌套回复（reply的reply）
- ✅ Review变化追踪和筛选
- ✅ 响应式设计，简洁易读

**输出**: `docs/` 目录
- `docs/index.html` - 主页（轻量级框架，~21KB）
- `docs/paper.html` - 论文详情模板（单个文件，~30KB）
- `docs/data/papers-list.json` - 论文列表数据（~7.3MB）
- `docs/data/papers-meta.json` - 元数据（含版本号和时间戳）
- `docs/data/papers/{paper_id}.json` - 论文详情数据（19630个文件，~335MB）
- `docs/assets/cache-manager.js` - 缓存管理器

**本地预览**:
```bash
# 使用Python启动本地服务器
cd docs
python -m http.server 8000
# 访问 http://localhost:8000
```

**部署到GitHub Pages**:
1. 提交并推送代码到GitHub
2. 在仓库设置中：Settings → Pages → Source → 选择 `main` 分支的 `/docs` 目录
3. 等待几分钟，访问 `https://{username}.github.io/{repo-name}/`

## 📊 输出示例

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

## 🔄 日常更新

```bash
# 抓取最新数据、合并并生成网站
python crawl.py && python merge.py && python generate_static_site.py
```

## ✨ 核心特性

### crawl.py
- 从OpenReview API抓取完整数据
- 文件名精确到秒
- 自动保存到 `data/raw/`

### merge.py
- 自动扫描并合并所有原始文件
- 保留所有review版本历史
- 显示合并前后的统计对比
- 支持增量合并

### generate_static_site.py
- **JSON数据生成**: 生成轻量级JSON文件而非大量HTML页面
- **Markdown支持**: 使用marked.js渲染Markdown内容
- **LaTeX公式**: 使用MathJax渲染数学公式
- **嵌套回复**: 自动通过API加载reply的reply
- **Review追踪**: 
  - 显示review的所有历史版本
  - 追踪rating变化（↑/↓/=）
  - 按变化类型筛选
- **响应式设计**: 简洁、易读的现代UI
- **CORS代理**: 使用corsproxy.io解决跨域问题

## 🌐 网站功能

### 主页
- **JSON动态加载**: 首次加载~7.3MB数据，后续从浏览器缓存瞬间加载
- **分批渲染**: 每批200个论文，避免页面卡顿
- **智能缓存**: 
  - 浏览器端缓存：数据缓存在浏览器本地存储中
  - 显示缓存状态和最后更新时间（显示仓库中数据的生成时间）
  - Refresh按钮：清除浏览器缓存并从服务器/仓库重新加载最新数据
  - 版本控制：仓库数据更新时自动失效旧缓存
- **论文列表**: 显示所有投稿（Active/Withdrawn）
- **基本信息**: 标题、submission number、日期、PDF链接
- **Review统计**: reviews数量、变化标签
- **筛选功能**: 按review变化类型筛选（All/Rating ↑/↓/=/No Changes/No Reviews）
- **展开详情**: 点击"Show details"动态加载Keywords、TL;DR、Abstract等

### 论文详情页
- **单页应用**: 使用Hash路由（`paper.html#abc123`），只需1个HTML模板
- **JSON动态加载**: 按需加载论文数据（~20-100KB/篇）
- **完整信息**: 
  - Metadata: Paper ID、Reviews/Comments数量、Review Changes、Links
  - Primary Area、Keywords、TL;DR
  - Abstract（支持Markdown和公式）
- **Reviews和Comments**:
  - 显示所有review历史版本
  - 自动加载嵌套回复（reply的reply）
  - 按类型筛选（All/Rating ↑/↓/=/No Changes/Comments）
  - 显示创建时间和修改时间
  - 支持Markdown和LaTeX公式
- **时间显示**: `13 Nov 2025, 09:34 (modified: 13 Nov 2025, 10:24)`
- **快速返回**: 点击"Back to list"使用浏览器后退，瞬间返回主页

## 🏗️ 技术架构

### 数据结构
- **JSON化数据**: 主页和论文详情都使用JSON格式存储
  - 主页：`papers-list.json` (~7.3MB)
  - 元数据：`papers-meta.json` (含版本号，用于缓存控制)
  - 论文详情：`papers/{paper_id}.json` (19630个文件，~335MB)
- **单页应用**: 使用Hash路由，只需2个HTML模板
  - `index.html` (~21KB) - 主页框架
  - `paper.html` (~30KB) - 论文详情模板

### 缓存机制
- **浏览器HTTP缓存**: 自动缓存JSON文件
- **版本控制**: 使用时间戳版本号，数据更新时自动失效旧缓存
- **内存缓存**: 页面刷新前数据保存在内存中

### 渲染策略
- **分批渲染**: 主页每批渲染200个论文，使用`requestAnimationFrame`
- **按需加载**: 论文详情和nested replies按需从API加载
- **DocumentFragment**: 减少DOM操作次数

### 性能表现
| 场景 | 加载时间 |
|------|---------|
| 首次访问主页 | ~1.5-3秒 |
| 二次访问主页 | ~0.1-0.3秒 |
| 打开论文详情 | ~0.1秒 |
| 返回主页 | 瞬间（浏览器后退） |

### 部署要求
- **总大小**: ~343MB
- **最大单文件**: 7.3MB
- **服务器**: 需要HTTP服务器（不能直接用file://协议）
- **兼容性**: 适合GitHub Pages等静态托管服务

## 📝 数据说明

- **原始数据**: `data/raw/` - 每次抓取的完整快照（不提交到Git）
- **合并数据**: `data/iclr2026_submissions_merged.json` - 包含所有历史版本的完整数据
- **Review版本**: 同一review的不同版本都会保留，可追踪修改历史
- **静态网站**: `docs/` - 生成的HTML和JSON文件，直接部署到GitHub Pages

### Review历史追踪原理

每次运行`merge.py`时：
1. 读取所有历史快照（`data/raw/`）
2. 按review ID分组，保留所有版本
3. 记录每个版本的`mdate`（修改时间）
4. 在网站中显示时，按时间排序展示所有版本

**示例**：某个review有3个版本
- 版本1（2025-11-10）：Rating: 5, 内容: "Good paper"
- 版本2（2025-11-13）：Rating: 6, 内容: "Good paper, improved"  ← Rating ↑
- 版本3（2025-11-15）：Rating: 6, 内容: "Excellent paper"      ← Rating =

网站会显示所有3个版本，并标注rating变化。
