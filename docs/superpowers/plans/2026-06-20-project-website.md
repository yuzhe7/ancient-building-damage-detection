# 项目展示网站 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为古建筑损伤检测系统搭建纯静态单页展示网站（Landing Page），包含 Hero / 功能 / 技术 / 截图 / 下载 5 个段落，部署到 GitHub Pages。

**Architecture:** 单 HTML 文件 + 独立 CSS + 独立 JS，零外部依赖。CSS 使用 CSS 自定义属性实现配色方案，Intersection Observer 实现滚动动画和导航高亮。所有资源使用相对路径。

**Tech Stack:** HTML5 + CSS3（CSS Variables, Flexbox, Grid, Media Queries）+ Vanilla JS（Intersection Observer API）

---

## 文件结构

```
docs/website/
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
└── img/
    ├── hero-bg.png        # Hero 背景纹理（可选，CSS 渐变可替代）
    ├── screenshot-1.jpg
    ├── screenshot-2.jpg
    ├── screenshot-3.jpg
    └── favicon.svg
```

---

### Task 1: 创建目录结构和基础文件

**Files:**

- Create: `docs/website/css/style.css`
- Create: `docs/website/js/main.js`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p docs/website/css docs/website/js docs/website/img
```

- [ ] **Step 2: 创建 style.css 骨架 — CSS 变量和重置样式**

```css
/* === CSS Custom Properties === */
:root {
    --color-paper: #faf6ee;
    --color-vermillion: #b84c3b;
    --color-vermillion-dark: #9a3f30;
    --color-copper: #c4a66a;
    --color-copper-light: #d4c49a;
    --color-bark: #4a3728;
    --color-stone: #8b7355;
    --color-stone-light: #b0a090;

    --font-heading: "Noto Serif SC", "SimSun", "STSong", serif;
    --font-body: "Microsoft YaHei", "PingFang SC", -apple-system, sans-serif;

    --max-width: 1200px;
    --nav-height: 64px;
}

/* === Reset === */
*,
*::before,
*::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    scroll-behavior: smooth;
    font-size: 16px;
}

body {
    font-family: var(--font-body);
    background-color: var(--color-paper);
    color: var(--color-stone);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}

a {
    color: var(--color-vermillion);
    text-decoration: none;
}
a:hover {
    color: var(--color-vermillion-dark);
}

img {
    max-width: 100%;
    height: auto;
    display: block;
}

h1,
h2,
h3,
h4 {
    font-family: var(--font-heading);
    color: var(--color-bark);
    line-height: 1.4;
}
```

- [ ] **Step 3: 创建 main.js 骨架**

```javascript
// 古建筑损伤检测系统 — 展示网站
// 功能：导航高亮、平滑滚动（已由 CSS scroll-behavior 处理）、元素入场动画

document.addEventListener("DOMContentLoaded", () => {
    initNavHighlight();
    initScrollReveal();
    initNavToggle();
});

function initNavHighlight() {
    const sections = document.querySelectorAll("section[id]");
    const navLinks = document.querySelectorAll(".nav-link");

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    navLinks.forEach((link) => {
                        link.classList.toggle("active", link.getAttribute("href") === "#" + entry.target.id);
                    });
                }
            });
        },
        { rootMargin: "-40% 0px -55% 0px" },
    );

    sections.forEach((section) => observer.observe(section));
}

function initScrollReveal() {
    const revealElements = document.querySelectorAll(".reveal");

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.15, rootMargin: "0px 0px -30px 0px" },
    );

    revealElements.forEach((el) => observer.observe(el));
}

function initNavToggle() {
    // Mobile hamburger menu (placeholder for responsive)
    const toggleBtn = document.getElementById("nav-toggle");
    const navMenu = document.getElementById("nav-menu");
    if (toggleBtn && navMenu) {
        toggleBtn.addEventListener("click", () => {
            const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
            toggleBtn.setAttribute("aria-expanded", String(!expanded));
            navMenu.classList.toggle("nav-open");
        });
    }
}
```

- [ ] **Step 4: 提交**

```bash
git add docs/website/
git commit -m "feat: create website directory structure, CSS reset, and JS skeleton"
```

---

### Task 2: 导航栏 — HTML + CSS

**Files:**

- Create: `docs/website/index.html`
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 创建 index.html 基础框架 + 导航栏**

```html
<!DOCTYPE html>
<html lang="zh-CN">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta
            name="description"
            content="古建筑损伤智能检测系统 — 基于YOLOv8深度学习，自动识别裂缝、风化、碱蚀、缺失、苔藓五类古建筑损伤。"
        />
        <title>古建筑损伤智能检测系统</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link
            href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap"
            rel="stylesheet"
        />
        <link rel="stylesheet" href="css/style.css" />
        <link rel="icon" href="img/favicon.svg" type="image/svg+xml" />
    </head>
    <body>
        <!-- 导航栏 -->
        <nav class="navbar" role="navigation" aria-label="主导航">
            <div class="nav-inner">
                <a href="#hero" class="nav-brand" aria-label="返回首页">
                    <span class="nav-icon">🏛️</span>
                    <span class="nav-title">古建筑损伤检测</span>
                </a>

                <button id="nav-toggle" class="nav-toggle" aria-expanded="false" aria-label="展开菜单">
                    <span class="hamburger"></span>
                </button>

                <div id="nav-menu" class="nav-menu">
                    <a href="#features" class="nav-link">核心功能</a>
                    <a href="#tech" class="nav-link">技术架构</a>
                    <a href="#screenshots" class="nav-link">软件截图</a>
                    <a href="#download" class="nav-link nav-cta">下载软件</a>
                </div>
            </div>
        </nav>

        <main>
            <!-- 各段落在此插入 -->
        </main>

        <script src="js/main.js"></script>
    </body>
</html>
```

- [ ] **Step 2: 追加导航栏 CSS 到 style.css**

```css
/* === 导航栏 === */
.navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    height: var(--nav-height);
    background: rgba(250, 246, 238, 0.92);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--color-copper);
}

.nav-inner {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 0 24px;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.nav-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-heading);
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--color-bark);
    text-decoration: none;
}
.nav-brand:hover {
    color: var(--color-vermillion);
}

.nav-icon {
    font-size: 1.3rem;
}

.nav-menu {
    display: flex;
    align-items: center;
    gap: 8px;
}

.nav-link {
    display: inline-block;
    padding: 8px 16px;
    font-size: 0.9rem;
    color: var(--color-stone);
    border-radius: 4px;
    transition:
        color 0.2s,
        background 0.2s;
}
.nav-link:hover {
    color: var(--color-bark);
    background: rgba(196, 166, 106, 0.12);
}
.nav-link.active {
    color: var(--color-vermillion);
}

.nav-cta {
    background: var(--color-vermillion);
    color: #fff !important;
    margin-left: 8px;
    padding: 8px 20px;
    border-radius: 4px;
    font-weight: 500;
    transition: background 0.2s;
}
.nav-cta:hover {
    background: var(--color-vermillion-dark);
}

/* 移动端汉堡按钮 */
.nav-toggle {
    display: none;
}
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add navigation bar with fixed position and mobile-ready markup"
```

---

### Task 3: Hero 段落 — HTML + CSS

**Files:**

- Modify: `docs/website/index.html` (insert Hero section in `<main>`)
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 在 `<main>` 标签内插入 Hero HTML**

```html
<!-- Hero 段落 -->
<section id="hero" class="hero">
    <div class="hero-content">
        <p class="hero-subtitle-en">🏛️ ANCIENT BUILDING DAMAGE DETECTION</p>
        <h1 class="hero-title">古建筑损伤智能检测系统</h1>
        <p class="hero-desc">基于 YOLOv8 深度学习 &nbsp;·&nbsp; 五类损伤自动识别 &nbsp;·&nbsp; 一键生成专业报告</p>
        <div class="hero-actions">
            <a href="#download" class="btn btn-primary">📥 下载软件</a>
            <a href="#features" class="btn btn-secondary">了解更多</a>
        </div>
    </div>
    <div class="hero-scroll-hint">
        <span>向下滚动</span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6" />
        </svg>
    </div>
</section>
```

- [ ] **Step 2: 追加 Hero CSS**

```css
/* === Hero 段落 === */
.hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: calc(var(--nav-height) + 40px) 24px 60px;
    background: linear-gradient(160deg, #f5f0e8 0%, #ede4d4 25%, #f2ecdd 50%, #e8ddca 75%, #f5f0e8 100%);
    position: relative;
}

/* 宣纸纹理覆盖层 */
.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    opacity: 0.04;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
    pointer-events: none;
}

.hero-content {
    position: relative;
    z-index: 1;
    max-width: 720px;
}

.hero-subtitle-en {
    font-size: 0.75rem;
    letter-spacing: 4px;
    color: var(--color-vermillion);
    margin-bottom: 12px;
    text-transform: uppercase;
}

.hero-title {
    font-size: clamp(2rem, 5vw, 3rem);
    font-weight: 700;
    color: var(--color-bark);
    margin-bottom: 16px;
    letter-spacing: 3px;
}

.hero-desc {
    font-size: 1.05rem;
    color: var(--color-stone);
    margin-bottom: 36px;
    line-height: 1.8;
}

.hero-actions {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
}
```

- [ ] **Step 3: 追加通用按钮 CSS**

```css
/* === 按钮 === */
.btn {
    display: inline-block;
    padding: 13px 32px;
    font-size: 1rem;
    font-weight: 500;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.25s;
    font-family: var(--font-body);
    text-decoration: none;
    border: none;
}

.btn-primary {
    background: var(--color-vermillion);
    color: #fff;
}
.btn-primary:hover {
    background: var(--color-vermillion-dark);
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(184, 76, 59, 0.3);
}

.btn-secondary {
    background: transparent;
    color: var(--color-bark);
    border: 1.5px solid var(--color-copper);
}
.btn-secondary:hover {
    background: rgba(196, 166, 106, 0.12);
    border-color: var(--color-bark);
}

/* 滚动提示 */
.hero-scroll-hint {
    position: absolute;
    bottom: 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: var(--color-copper);
    animation: bounce 2s infinite;
}
@keyframes bounce {
    0%,
    100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(6px);
    }
}
```

- [ ] **Step 4: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add Hero section with background texture and buttons"
```

---

### Task 4: 核心功能段落 — HTML + CSS

**Files:**

- Modify: `docs/website/index.html` (insert after Hero)
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 在 Hero 之后插入功能段落 HTML**

```html
<!-- 核心功能段落 -->
<section id="features" class="section">
    <div class="section-inner">
        <div class="section-header reveal">
            <h2 class="section-title">✨ 核心功能</h2>
            <p class="section-subtitle">检测 → 分析 → 建议 → 报告，全流程覆盖</p>
        </div>
        <div class="features-grid">
            <div class="feature-card reveal">
                <div class="feature-icon">📷</div>
                <h3>四种检测模式</h3>
                <p>支持单图检测、批量检测、视频检测、摄像头实时检测，覆盖不同巡检场景。</p>
            </div>
            <div class="feature-card reveal">
                <div class="feature-icon">🔍</div>
                <h3>五类损伤识别</h3>
                <p>自动识别裂缝（CRACK）、风化侵蚀（W_E）、碱蚀（ALKALI）、缺失（MISS）、苔藓（MOSS）。</p>
            </div>
            <div class="feature-card reveal">
                <div class="feature-icon">🔥</div>
                <h3>损伤热力图 & 评级</h3>
                <p>热力图直观展示损伤分布，自动判定轻微/中等/严重三个等级，优先修缮一目了然。</p>
            </div>
            <div class="feature-card reveal">
                <div class="feature-icon">💡</div>
                <h3>智能修复建议</h3>
                <p>5 类损伤 × 3 种严重度 = 15 条专家级修复建议，检测完成自动匹配推荐方案。</p>
            </div>
            <div class="feature-card reveal">
                <div class="feature-icon">🔄</div>
                <h3>修复前后对比</h3>
                <p>同一墙面修复前后照片自动对比，标注新增/扩大/缩小/稳定/已修复五种变化。</p>
            </div>
            <div class="feature-card reveal">
                <div class="feature-icon">📄</div>
                <h3>一键报告导出</h3>
                <p>自动生成专业 PDF 报告（含封面、汇总表、详情），支持 Excel 数据导出和结果图保存。</p>
            </div>
        </div>
    </div>
</section>
```

- [ ] **Step 2: 追加通用段落 + 功能卡片 CSS**

```css
/* === 通用段落 === */
.section {
    padding: 80px 24px;
}

.section-inner {
    max-width: var(--max-width);
    margin: 0 auto;
}

.section-header {
    text-align: center;
    margin-bottom: 48px;
}

.section-title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 10px;
    position: relative;
    display: inline-block;
}

/* 标题下方铜金装饰线 */
.section-title::after {
    content: "";
    display: block;
    width: 48px;
    height: 3px;
    background: var(--color-copper);
    margin: 12px auto 0;
    border-radius: 2px;
}

.section-subtitle {
    font-size: 1rem;
    color: var(--color-stone-light);
    margin-top: 8px;
}

/* === 功能卡片网格 === */
.features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
}

.feature-card {
    background: rgba(255, 255, 255, 0.5);
    border: 1px solid var(--color-copper-light);
    border-radius: 8px;
    padding: 32px 24px;
    text-align: center;
    transition:
        transform 0.3s,
        box-shadow 0.3s;
    position: relative;
}

.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 28px rgba(74, 55, 40, 0.1);
}

.feature-icon {
    font-size: 2.2rem;
    margin-bottom: 16px;
}

.feature-card h3 {
    font-size: 1.1rem;
    margin-bottom: 10px;
    color: var(--color-bark);
}

.feature-card p {
    font-size: 0.9rem;
    line-height: 1.7;
    color: var(--color-stone);
}
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add features section with 6-card grid layout"
```

---

### Task 5: 技术架构段落 — HTML + CSS

**Files:**

- Modify: `docs/website/index.html` (insert after features)
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 在功能段落之后插入技术架构 HTML**

```html
<!-- 技术架构段落 -->
<section id="tech" class="section section-alt">
    <div class="section-inner">
        <div class="section-header reveal">
            <h2 class="section-title">🧠 技术架构</h2>
            <p class="section-subtitle">基于 Ultralytics YOLOv8 构建，PyQt5 桌面界面，支持 GPU 加速推理</p>
        </div>

        <!-- 技术栈流程 -->
        <div class="tech-flow reveal">
            <div class="tech-node">
                <div class="tech-node-icon">🧩</div>
                <strong>YOLOv8</strong>
                <p>目标检测引擎<br />mAP@50: 0.85+</p>
            </div>
            <div class="tech-arrow">→</div>
            <div class="tech-node">
                <div class="tech-node-icon">🖥️</div>
                <strong>PyQt5</strong>
                <p>桌面应用界面<br />宣纸古建主题</p>
            </div>
            <div class="tech-arrow">→</div>
            <div class="tech-node">
                <div class="tech-node-icon">📊</div>
                <strong>ReportLab</strong>
                <p>PDF 报告引擎<br />自动排版生成</p>
            </div>
            <div class="tech-arrow">→</div>
            <div class="tech-node">
                <div class="tech-node-icon">📦</div>
                <strong>PyInstaller</strong>
                <p>单文件打包<br />即开即用</p>
            </div>
        </div>

        <!-- 损伤类型指标 -->
        <div class="tech-stats reveal">
            <h3>五类损伤检测指标</h3>
            <p class="section-subtitle" style="text-align:center;margin-bottom:24px">
                以下数据为训练集评估结果，实际运行可通过"性能指标"功能复现
            </p>
            <div class="stats-table-wrapper">
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>损伤类型</th>
                            <th>精确率 (P)</th>
                            <th>召回率 (R)</th>
                            <th>F1 分数</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🔴 裂缝 CRACK</td>
                            <td>—</td>
                            <td>—</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td>🟠 风化侵蚀 W_E</td>
                            <td>—</td>
                            <td>—</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td>⚪ 碱蚀 ALKALI</td>
                            <td>—</td>
                            <td>—</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td>🟣 缺失 MISS</td>
                            <td>—</td>
                            <td>—</td>
                            <td>—</td>
                        </tr>
                        <tr>
                            <td>🟢 苔藓 MOSS</td>
                            <td>—</td>
                            <td>—</td>
                            <td>—</td>
                        </tr>
                    </tbody>
                </table>
                <p class="table-note">* 运行 <code>性能指标.py</code> 获取最新评估数据后填入</p>
            </div>
        </div>
    </div>
</section>
```

- [ ] **Step 2: 追加技术段落 CSS**

```css
/* === 技术段落 === */
.section-alt {
    background: rgba(196, 166, 106, 0.06);
}

.tech-flow {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    gap: 12px;
    margin-bottom: 60px;
    flex-wrap: wrap;
}

.tech-node {
    background: var(--color-bark);
    color: var(--color-paper);
    padding: 24px 18px;
    border-radius: 8px;
    text-align: center;
    min-width: 140px;
    flex: 0 0 auto;
}
.tech-node strong {
    display: block;
    margin: 8px 0 4px;
    font-size: 0.95rem;
}
.tech-node p {
    font-size: 0.78rem;
    opacity: 0.8;
    line-height: 1.5;
}
.tech-node-icon {
    font-size: 1.6rem;
}

.tech-arrow {
    align-self: center;
    font-size: 1.5rem;
    color: var(--color-copper);
    padding: 0 4px;
    margin-top: 12px;
}

.tech-stats h3 {
    text-align: center;
    font-size: 1.3rem;
    margin-bottom: 24px;
}

.stats-table-wrapper {
    overflow-x: auto;
    max-width: 640px;
    margin: 0 auto;
}

.stats-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.stats-table th,
.stats-table td {
    padding: 12px 16px;
    text-align: center;
    border-bottom: 1px solid var(--color-copper-light);
}

.stats-table th {
    background: var(--color-bark);
    color: var(--color-paper);
    font-weight: 500;
}

.stats-table tbody tr:hover {
    background: rgba(196, 166, 106, 0.08);
}

.table-note {
    text-align: center;
    font-size: 0.8rem;
    color: var(--color-stone-light);
    margin-top: 12px;
}
.table-note code {
    background: rgba(196, 166, 106, 0.15);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.85em;
}
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add tech architecture section with flow diagram and metrics table"
```

---

### Task 6: 软件截图段落 — HTML + CSS

**Files:**

- Modify: `docs/website/index.html` (insert after tech)
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 在技术段落之后插入截图 HTML**

```html
<!-- 软件截图段落 -->
<section id="screenshots" class="section">
    <div class="section-inner">
        <div class="section-header reveal">
            <h2 class="section-title">🖼️ 软件截图</h2>
            <p class="section-subtitle">宣纸古建主题界面，专业与美感兼备</p>
        </div>
        <div class="screenshots-grid reveal">
            <figure class="screenshot-card">
                <img src="img/screenshot-1.jpg" alt="损伤检测主界面" loading="lazy" />
                <figcaption>📷 检测主界面 — 自动标注五类损伤，显示类型、置信度、面积占比</figcaption>
            </figure>
            <figure class="screenshot-card">
                <img src="img/screenshot-2.jpg" alt="损伤热力图" loading="lazy" />
                <figcaption>🔥 损伤热力图 — 红色区域为损伤密集区，优先修缮一目了然</figcaption>
            </figure>
            <figure class="screenshot-card">
                <img src="img/screenshot-3.jpg" alt="PDF检测报告" loading="lazy" />
                <figcaption>📄 自动生成 PDF 报告 — 含封面、汇总表、检测详情、修复建议</figcaption>
            </figure>
        </div>
        <p class="table-note" style="text-align:center;margin-top:16px">* 运行软件截取实际界面图片后替换占位图</p>
    </div>
</section>
```

- [ ] **Step 2: 追加截图段落 CSS**

```css
/* === 软件截图 === */
.screenshots-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
}

.screenshot-card {
    background: #fff;
    border: 1px solid var(--color-copper-light);
    border-radius: 8px;
    overflow: hidden;
    transition:
        transform 0.3s,
        box-shadow 0.3s;
}

.screenshot-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 28px rgba(74, 55, 40, 0.12);
}

.screenshot-card img {
    width: 100%;
    aspect-ratio: 16 / 10;
    object-fit: cover;
    display: block;
}

.screenshot-card figcaption {
    padding: 14px 16px;
    font-size: 0.85rem;
    color: var(--color-stone);
    text-align: center;
    line-height: 1.6;
}
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add screenshots section with 3-image grid and captions"
```

---

### Task 7: 下载段落 — HTML + CSS

**Files:**

- Modify: `docs/website/index.html` (insert after screenshots)
- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 在截图段落之后插入下载 HTML**

```html
<!-- 下载段落 -->
<section id="download" class="section section-alt">
    <div class="section-inner">
        <div class="section-header reveal">
            <h2 class="section-title">📥 下载软件</h2>
            <p class="section-subtitle">Windows 平台 · 即开即用 · 支持 GPU / CPU 推理</p>
        </div>

        <div class="download-box reveal">
            <div class="download-info">
                <div class="download-version">
                    <span class="version-tag">v1.0</span>
                    <span>最新版本</span>
                </div>
                <ul class="download-specs">
                    <li>🖥️ 系统要求：Windows 10 / 11（64 位）</li>
                    <li>💾 安装包大小：约 450 MB（含模型权重）</li>
                    <li>⚡ 支持 GPU（CUDA）加速推理，也可 CPU 运行</li>
                    <li>📦 解压即用，无需安装 Python 环境</li>
                </ul>
                <div class="download-actions">
                    <a
                        href="https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/古建筑损伤检测系统.zip"
                        class="btn btn-primary btn-large"
                    >
                        ⬇ 下载安装包（ZIP · ~450MB）
                    </a>
                    <p class="download-note">下载较慢？<a href="#" class="mirror-link">123 云盘备用链接 &rarr;</a></p>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- 页脚 -->
<footer class="site-footer">
    <div class="section-inner">
        <p>
            © 2026 古建筑损伤智能检测系统 &nbsp;|&nbsp; 基于
            <a href="https://github.com/ultralytics/ultralytics" target="_blank" rel="noopener">Ultralytics YOLOv8</a>
            构建
        </p>
    </div>
</footer>
```

- [ ] **Step 2: 追加下载段落 + 页脚 CSS**

```css
/* === 下载段落 === */
.download-box {
    max-width: 600px;
    margin: 0 auto;
    background: #fff;
    border: 2px solid var(--color-copper);
    border-radius: 12px;
    padding: 40px 36px;
    text-align: center;
}

.download-version {
    margin-bottom: 20px;
}

.version-tag {
    display: inline-block;
    background: var(--color-bark);
    color: var(--color-paper);
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-right: 8px;
}

.download-specs {
    list-style: none;
    text-align: left;
    margin-bottom: 28px;
    display: inline-block;
}

.download-specs li {
    padding: 6px 0;
    font-size: 0.9rem;
    color: var(--color-stone);
}

.btn-large {
    padding: 16px 40px;
    font-size: 1.1rem;
}

.download-note {
    margin-top: 14px;
    font-size: 0.82rem;
    color: var(--color-stone-light);
}

.mirror-link {
    color: var(--color-stone);
    text-decoration: underline;
}

/* === 页脚 === */
.site-footer {
    text-align: center;
    padding: 32px 24px;
    border-top: 1px solid var(--color-copper-light);
    font-size: 0.82rem;
    color: var(--color-stone-light);
}
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/index.html docs/website/css/style.css
git commit -m "feat: add download section with specs and footer"
```

---

### Task 8: 滚动入场动画 CSS

**Files:**

- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 追加滚动动画 CSS**

```css
/* === 滚动入场动画 === */
.reveal {
    opacity: 0;
    transform: translateY(30px);
    transition:
        opacity 0.6s ease-out,
        transform 0.6s ease-out;
}

.reveal.visible {
    opacity: 1;
    transform: translateY(0);
}

/* 延迟动画（卡片逐个浮现） */
.feature-card:nth-child(1) {
    transition-delay: 0s;
}
.feature-card:nth-child(2) {
    transition-delay: 0.08s;
}
.feature-card:nth-child(3) {
    transition-delay: 0.16s;
}
.feature-card:nth-child(4) {
    transition-delay: 0.08s;
}
.feature-card:nth-child(5) {
    transition-delay: 0.16s;
}
.feature-card:nth-child(6) {
    transition-delay: 0.24s;
}
```

- [ ] **Step 2: 提交**

```bash
git add docs/website/css/style.css
git commit -m "feat: add scroll-reveal animations with staggered delays"
```

---

### Task 9: 响应式设计 CSS

**Files:**

- Modify: `docs/website/css/style.css` (append)

- [ ] **Step 1: 追加响应式媒体查询 CSS**

```css
/* === 响应式 — 平板端 === */
@media (max-width: 1024px) {
    .features-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 18px;
    }

    .screenshots-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 18px;
    }

    .tech-flow {
        gap: 8px;
    }

    .tech-node {
        min-width: 120px;
        padding: 16px 12px;
    }
    .tech-node strong {
        font-size: 0.85rem;
    }
    .tech-node p {
        font-size: 0.72rem;
    }

    .section {
        padding: 60px 20px;
    }
}

/* === 响应式 — 手机端 === */
@media (max-width: 768px) {
    :root {
        --nav-height: 56px;
    }

    html {
        font-size: 15px;
    }

    .features-grid,
    .screenshots-grid {
        grid-template-columns: 1fr;
        gap: 16px;
    }

    .hero {
        min-height: 90vh;
        padding: calc(var(--nav-height) + 20px) 16px 40px;
    }

    .hero-title {
        font-size: 1.7rem;
        letter-spacing: 1px;
    }
    .hero-desc {
        font-size: 0.9rem;
    }
    .hero-actions {
        flex-direction: column;
        align-items: center;
    }

    .section {
        padding: 48px 16px;
    }
    .section-title {
        font-size: 1.5rem;
    }

    /* 导航栏移动端适配 */
    .nav-toggle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        background: none;
        border: 1px solid var(--color-copper);
        border-radius: 4px;
        cursor: pointer;
        padding: 0;
    }

    .hamburger {
        display: block;
        width: 20px;
        height: 2px;
        background: var(--color-bark);
        position: relative;
        transition: background 0.2s;
    }
    .hamburger::before,
    .hamburger::after {
        content: "";
        position: absolute;
        left: 0;
        width: 20px;
        height: 2px;
        background: var(--color-bark);
        transition: transform 0.2s;
    }
    .hamburger::before {
        top: -6px;
    }
    .hamburger::after {
        top: 6px;
    }

    .nav-menu {
        display: none;
        position: absolute;
        top: var(--nav-height);
        left: 0;
        right: 0;
        flex-direction: column;
        background: rgba(250, 246, 238, 0.98);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--color-copper);
        padding: 12px 20px;
        gap: 4px;
    }

    .nav-menu.nav-open {
        display: flex;
    }

    .nav-link {
        width: 100%;
        padding: 12px 16px;
    }
    .nav-cta {
        margin-left: 0;
        text-align: center;
    }

    /* 技术流程改为纵向 */
    .tech-flow {
        flex-direction: column;
        align-items: center;
    }

    .tech-arrow {
        transform: rotate(90deg);
        margin: 0;
    }

    .download-box {
        padding: 28px 20px;
        border-radius: 8px;
    }
}
```

- [ ] **Step 2: 提交**

```bash
git add docs/website/css/style.css
git commit -m "feat: add responsive CSS for tablet and mobile breakpoints"
```

---

### Task 10: 生成占位图片和网站图标

**Files:**

- Create: `docs/website/img/favicon.svg`
- Create: `docs/website/img/screenshot-1.jpg` (占位)
- Create: `docs/website/img/screenshot-2.jpg` (占位)
- Create: `docs/website/img/screenshot-3.jpg` (占位)

- [ ] **Step 1: 创建 SVG favicon**

```bash
cat > docs/website/img/favicon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#4A3728"/>
  <text x="32" y="44" font-family="serif" font-size="36" text-anchor="middle" fill="#FAF6EE">🏛️</text>
</svg>
EOF
```

- [ ] **Step 2: 用现有项目图片作为初始占位图**

```bash
# 使用项目中已有的检测结果图片作为初始占位
cp test_result_check.jpg docs/website/img/screenshot-1.jpg 2> /dev/null || echo "需要手动添加 screenshot-1.jpg"
cp test_heatmap_debug.jpg docs/website/img/screenshot-2.jpg 2> /dev/null || echo "需要手动添加 screenshot-2.jpg"
cp test_report.pdf docs/website/img/screenshot-3.jpg 2> /dev/null || echo "需要手动添加 screenshot-3.jpg"
```

- [ ] **Step 3: 提交**

```bash
git add docs/website/img/
git commit -m "feat: add favicon and placeholder screenshots"
```

---

### Task 11: 最终审查和本地预览

- [ ] **Step 1: 检查文件完整性**

```bash
echo "=== 文件清单 ==="
find docs/website -type f | sort
echo ""
echo "=== HTML 结构验证 ==="
echo "需要确认 index.html 中包含以下 5 个 section："
grep -c '<section id=' docs/website/index.html
echo "个 section（应为 5）"
```

预期输出：5 个 section（hero, features, tech, screenshots, download）

- [ ] **Step 2: 用浏览器打开本地文件**

```bash
echo "请用浏览器打开以下文件预览："
echo "file:///E:/ultralytics-8.4.14/docs/website/index.html"
```

手动检查项目：

- 所有段落是否正确显示
- 导航栏点击是否平滑滚动
- 浏览器窗口缩放是否响应式适配
- 按钮样式和配色是否一致

- [ ] **Step 3: 提交最终版本**

```bash
git add docs/website/
git commit -m "feat: complete project showcase website"
```

---

### Task 12: GitHub Pages 部署准备

- [ ] **Step 1: 确认 GitHub 仓库中的部署路径**

确保仓库中 `docs/website/` 目录存在且在 GitHub 上可见。

- [ ] **Step 2: 配置 GitHub Pages**

在仓库 Settings → Pages 中：

- Source: "Deploy from a branch"
- Branch: `main`
- Folder: `/docs`

访问地址为 `https://<username>.github.io/<repo>/website/`

- [ ] **Step 3: 创建 GitHub Release 并上传安装包**

```bash
# 1. 在 GitHub 网页端进入 Releases → "Create a new release"
# 2. Tag: v1.0
# 3. Title: 古建筑损伤检测系统 v1.0
# 4. 上传文件: dist/古建筑损伤检测系统.zip
# 5. 点击 "Publish release"
```

- [ ] **Step 4: 更新下载链接**

将 `docs/website/index.html` 中的下载按钮链接替换为实际的 GitHub Releases URL：

```html
<!-- 将 YOUR_USERNAME 和 YOUR_REPO 替换为实际值 -->
<a
    href="https://github.com/<实际用户名>/<实际仓库名>/releases/latest/download/古建筑损伤检测系统.zip"
    class="btn btn-primary btn-large"
>
    ⬇ 下载安装包（ZIP · ~450MB）
</a>
```

- [ ] **Step 5: 提交配置更新**

```bash
git add docs/website/index.html
git commit -m "chore: update download link with actual GitHub Releases URL"
git push origin main
```

---

## 素材补充清单

以下素材需要在网站正式上线前补充（不在本次实现计划内）：

| 素材         | 操作                                      | 优先级 |
| ------------ | ----------------------------------------- | ------ |
| 检测界面截图 | 运行 `系统.py`，检测一张图片，截取主窗口  | 高     |
| 热力图截图   | 检测后切换到热力图模式，截取              | 高     |
| PDF 报告预览 | 导出 PDF 后截取封面/代表性页面            | 高     |
| 性能指标数据 | 运行 `python 性能指标.py`，将输出填入表格 | 中     |
| 自定义域名   | 可选：购买域名并配置 CNAME                | 低     |
