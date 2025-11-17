/**
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
