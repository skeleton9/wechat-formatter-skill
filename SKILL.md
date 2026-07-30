---
name: wechat-formatter
description: "Convert Markdown articles into beautifully formatted, copy-paste-ready HTML for the WeChat Official Account (微信公众号) editor. Use this skill when the user wants 排版, 公众号排版, 排版到公众号, 复制到公众号, 微信排版, or mentions a Markdown file to format and paste into the WeChat backend. It emits fully inline-styled section HTML so formatting survives pasting, excludes the title from the copy region, and auto-classifies blockquotes by content keywords."
agent_created: true
---

# WeChat 公众号排版工具

将 Markdown 文章转换为排版精美的 HTML 页面，用户可一键复制正文粘贴到公众号后台编辑器，
格式完整保留。

## When to Use

- 用户说「排版」「公众号排版」「排版到公众号」「复制到公众号」「微信排版」「生成排版」
- 用户提到一个 Markdown 文件，并希望排版后粘贴到公众号
- 用户写完文章后说「帮我排版一下」

## When NOT to Use

- 用户只是要预览网页（用 preview 类能力即可，不要套用本工具）
- 用户只是要编辑 Markdown 文件（用编辑工具）
- 用户要发布到其他平台（知乎、小红书、掘金等）

## Core Principles（铁律）

1. **所有样式必须内联 `style="..."`** — 公众号后台不认 CSS class 与外部 `<style>`，只有
   写在每个标签上的内联样式才能在粘贴后保留。本工具的脚本已默认全部内联。
2. **标题不在复制区域内** — 公众号标题在后台标题栏单独填写。复制区只含正文：脚本将文档
   **首个 H1** 视为标题，放入预览页顶栏（不可复制），正文从 H2 起算。
3. **使用 `<section>` 标签** — 比 `<div>` 在公众号后台兼容性更好，所有块级元素均用
   `<section>` 包裹。
4. **引用框自动分类** — 根据内容关键词自动判断颜色：
   - 🟠 橙色（编者按）：命中「编者按 / 按语 / 译注 / 注：/ 按：/ 点评」等关键词
   - 🔵 蓝色（古文）：命中「曰 / 云：/ 子曰 / 《》/ 诗词 / 论语」等古文体关键词
   - 🟢 绿色（普通）：默认，无特殊关键词

## 配色 × 结构格式（完全解耦，自由组合）

脚本把「**配色**」与「**结构格式**」拆成两个独立维度，二者相乘共有 **10 × 10 = 100 种组合**。
预览页顶部有**两组独立选择器**（配色 / 结构格式），正文实时更新；复制时以当前组合为准。

- **配色（COLOR）**：只决定颜色与字体（强调色、正文/标题色、衬线或黑体、引用三色、代码块、表格、分隔线等）。
- **结构格式（VARIANT）**：只决定标题 / 引用 / 高亮三要素的**结构**（左色条、居中双线、填充色块、虚线标签、填充条、深色块、报刊双线、手账点线、极简细线等）。

**10 套配色**（`--theme`）：

| 配色 id | 名称 | 观感 |
| --- | --- | --- |
| `blue` | 简约蓝（默认） | 通用、科技、资讯 |
| `classic` | 文艺古籍 | 文化、古文、读书、散文（衬线 + 暖金） |
| `tech` | 科技青 | 技术教程、产品 |
| `green` | 清新绿 | 生活、成长、治愈 |
| `warm` | 暖橙生活 | 美食、旅行、亲子（暖橙 + 米色底） |
| `dark` | 暗夜 | 暗色卡片风（深底 + 浅字） |
| `news` | 报刊红 | 资讯、观点、干货长文 |
| `note` | 手账暖 | 随笔、日记、情感（牛皮纸 + 衬线） |
| `minimal` | 极简灰 | 极简、留白、高端调性 |
| `brief` | 商业简报 | 商业、组织、咨询、观点长文（墨蓝 + 编辑感卡片） |

**10 套结构格式**（`--format`）：

| 格式 id | 名称 | 标题结构 | 引用结构 | 高亮结构 |
| --- | --- | --- | --- | --- |
| `sidebar` | 左色条 | 左侧色条 | 左条色块 | 纯色加粗 |
| `seal` | 居中双线 | 居中双线 | 双框描边 | 朱批金 |
| `chip` | 色块 | 填充色块 | 圆角卡片 | 背景药丸 |
| `marker` | 虚线签 | 虚线标签 | 胶带条 | 背景标记 |
| `card` | 填充条 | 填充条 | 阴影卡片 | 背景药丸 |
| `night` | 深色块 | 深色块 | 暗色卡片 | 深底药丸 |
| `news` | 报刊双线 | 双线 | 粗左条 | 波浪下划线 |
| `note` | 手账点线 | 点线 | 虚线框 | 荧光笔 |
| `minimal` | 极简线 | 居中细线 | 无框大引号 | 纯粗体 |
| `report` | 简报体 | 顶规标题 | 卡片引文（左条） | 药丸高亮 |

> 复现旧「整模板」观感：文艺古籍 = `classic` 配色 + `seal` 格式；科技青 = `tech` + `chip`；
> 报刊风 = `news` + `news`；手账风 = `note` + `note`；极简线 = `minimal` + `minimal`，以此类推。

所有差异均以内联样式写入，粘贴后完整保留。

## Workflow

### 1. 确认输入与输出

- 输入：用户提供的 `.md` 文件路径。若用户提供的是纯文本而非文件，先写入临时 `.md` 再处理。
- 输出：在同目录生成 `<原名>.wechat.html` 预览文件（可用 `--output` 指定）。
- 可选参数：
  - `--title "自定义标题"`：覆盖首个 H1 检测到的标题
  - `--theme <配色>`：默认配色（`blue`/`classic`/`tech`/`green`/`warm`/`dark`/`news`/`note`/`minimal`/`brief`），
    预览页内仍可切换配色与格式任意组合
  - `--format <格式>`：默认结构格式（`sidebar`/`seal`/`chip`/`marker`/`card`/`night`/`news`/`note`/`minimal`/`report`）
  - `--list-themes`：仅列出全部配色与格式并退出
  - `--app -o <输出.html>`：**生成独立编辑器**（不绑定单篇文章）。页面内置示例文档、支持「📂 打开」载入本地 `.md`、「🆕 新建」清空、「复制正文」，且**草稿自动保存在本机浏览器**；可直接 `file://` 打开，或用 `--serve` 起本地静态服务获得最佳剪贴板支持
  - `--serve <目录>`：在指定目录启动本地静态服务（`http.server`，默认端口 8000），用于托管独立编辑器

### 2. 运行转换脚本

用 managed Python 执行（避免污染用户环境）：

```bash
/Users/gelin/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  ~/.workbuddy/skills/wechat-formatter/scripts/build_wechat_html.py \
  <输入.md> -o <输出.html> [--title "标题"] [--theme classic --format seal]
```

脚本为**纯标准库实现**，无需任何第三方依赖，开箱即用。

### 2.1 生成独立编辑器（可当独立服务 / 工具站）

每篇生成的 `.wechat.html` 本身就是「编辑 + 预览」的小应用，但它把那篇文章的 Markdown 写死在页面里。若要一个**可反复使用、不绑定单篇**的编辑器，用 `--app` 生成：

```bash
python3 ~/.workbuddy/skills/wechat-formatter/scripts/build_wechat_html.py --app -o ~/.workbuddy/skills/wechat-formatter/app/index.html
# 本地起服务（推荐，剪贴板支持最好）
python3 ~/.workbuddy/skills/wechat-formatter/scripts/build_wechat_html.py --serve ~/.workbuddy/skills/wechat-formatter/app
# 然后浏览器打开 http://localhost:8000/index.html
```

该独立编辑器与单篇预览**共用同一套解析器/渲染器**（已验证 Python 与浏览器端逐块 JSON 100% 一致），只是：
- 默认载入一篇内置示例文档（覆盖全部块类型，作引导）；
- 顶栏多了「📂 打开」（读本地 `.md`）、「🆕 新建」（清空）；
- 编辑框内容**自动存进浏览器 localStorage**，下次打开自动恢复草稿；
- 依旧支持左右拖拽、手机预览、配色×格式 100 种组合、一键复制。
生成的单文件可直接部署到任意静态托管（CloudStudio / GitHub Pages / Nginx 等），即成为一个在线公众号排版工具。

### 3. 交付预览文件

- 用 `present_files` 将生成的 `.wechat.html` 交付给用户（会自动打开预览面板）。
- 告知用户：预览页**顶部两组选择器可分别选配色与结构格式**，正文实时更新；右上角「📋 复制正文」
  按钮以**当前组合**一键复制富文本；到公众号后台标题栏填标题、正文区 `Ctrl/⌘+V` 粘贴即可，格式完整保留。
- **编辑 + 预览模式（默认左右布局、宽度可拖拽）**：预览页**默认即为「左编辑 / 右预览」**的左右分栏——左侧是 Markdown 源文编辑框，
  右侧实时预览，在框内改稿会**实时**重解析并刷新右侧预览与复制内容，无需重新跑脚本。顶栏右侧有「?」按钮，点击展开使用说明（默认收起，避免占版面）。
  页面整体不滚动：左侧编辑区与右侧预览区**各自独立滚动**。中间分隔条可**拖动**调整左右宽度（18%–82%），
  也可点顶栏「📱 手机」把右侧预览锁定为 **375px 手机宽度**（编辑区取剩余空间）查看窄屏效果，点「👁 仅预览」隐藏编辑区只看排版
  （窄屏下默认进入仅预览，点「✏️ 编辑」切到全宽编辑）。改完直接「复制正文」即可；也可在编辑区
  手敲 `--- 分节文字`、`> [!01] 标题`、`> [!compare] A | B` 等新块语法即时看效果。

### 4. 支持的元素

脚本覆盖常见文章排版所需 Markdown 语法：

- 标题 H1–H6（H1 作标题不进正文；H2 结构随模板 `variant` 变化：左色条 / 居中双线 / 填充色块 / 虚线标签 / 填充条 / 深色块 / 报刊双线 / 手账点线 / 极简细线）
- 段落、加粗 `**`、斜体 `*`、删除线 `~~`、行内代码 `` ` ``
- 链接 `[text](url)`、图片 `![alt](url)`（独立成行的图片居中并带圆角阴影）
- 有序 / 无序列表（支持基础单层）
- 引用 `>` （自动三色分类，见 Core Principles 4）
- 围栏代码块 ```` ``` ````（深色背景、等宽、自动换行）
- 表格 `| a | b |` + 分隔行（带边框与表头底色）
- 分隔线 `---` （渲染为居中圆点装饰线）
- 分栏分隔线（文字可自定义，强烈推荐）：
  - `--- 任意文字` 或 `*** 任意文字`（独立成行，分隔符后接空格 + 文字）：渲染为居中 "— 任意文字 —" 装饰分栏，**文字可任意修改**，适合中文文章分节（如 `--- 缘起`、`--- 三个判断`）
  - 旧写法 `SECTION 01`（大写 `SECTION` + 空格 + 数字）仍兼容，渲染为 "— SECTION 01 —"
  - 单独 `---`（无文字）仍是普通圆点装饰分隔线
- 标签卡片 `> [!标签] 内容`：引用块首行以 `[!标签]` 开头，渲染为带小标签的强调卡片（主题色左条 + 标签 + 内容），区别于普通三色引用
- 编号洞察卡 `> [!01] 标题` + 后续行作描述：引用块首行以 `[!数字]` 开头，渲染为「大号数字 + 标题 + 描述」的卡片（左主题色条 + 浅卡片底），适合「01 / 02 / 03」式逐条洞察。数字写两位（01、02…）更整齐。
- 对比双栏 `> [!compare] 左标题 | 右标题`：引用块首行以 `[!compare]` 开头，两栏标题用 `|` 分隔；其下**每行** `> 左内容 | 右内容` 自动作为一行两列对照（逐行对照，无需 `|||`）。渲染为并排两栏对照卡（左栏主色标题、右栏绿色标题，行与行、列与列均有分隔线），适合「传统 vs 优秀」「旧方案 vs 新方案」类对照。

## Implementation Notes（给执行实例的提示）

- **配色与格式解耦**：文件顶部 `COLORS` 字典只放颜色/字体（无结构），`VARIANT_ORDER`/`VARIANT_LABELS`
  描述结构格式；`make_styles(colors, variant)` 先生成基础样式再由 `_variant_overrides(colors, f, variant)`
  叠加结构样式（标题/引用/高亮）。`STYLES` 是 `{(color, variant): 样式字典}` 的笛卡尔积（10×10=100）。
  新增配色/格式只需分别改 `COLORS` 或 `_variant_overrides` 分支，并补 `COLOR_ORDER`/`VARIANT_ORDER` 列表。
- **预览页实时组合**：为支持 100 种组合又不预渲染 100 份正文，预览页把「解析后的块 JSON」与「全部组合
  的样式 JSON」嵌入页面，由一段**页面内 JS 渲染器**（`renderBlock`/`parseInline` 忠实复刻 Python 逻辑）
  在切换选择器时实时渲染。默认组合仍由 Python `convert()` 渲染为 `__DEF_BODY__`，保证复制内容 100% 正确；
  JS 仅用于实时预览切换。**已用 Node 校验：Python 与 JS 对同一组合的输出逐字一致。**
- **编辑 + 预览（浏览器端 Markdown 解析器）**：预览页内嵌源文（`var SOURCE = ...`）并新增 `parseMarkdown()`，
  它是 Python `split_blocks` 的**逐行忠实移植**（含 `> [!...]` 标签/洞察/对比、表格、列表、SECTION 分栏等全部分支）。
  页面**默认即为左右分栏**（左编辑框、右预览），文本框改稿经 250ms 防抖后重跑 `parseMarkdown` → 更新 `BLOCKS` → `applyCombo`
  重渲染；帮助说明收到顶栏「?」弹层里（点击展开 / Esc 或点外侧关闭）。整页 `overflow:hidden`，`.split` 占满剩余视口高度，
  左右 pane 各自 `overflow:auto` 独立滚动。中间分隔条可拖动调整左右宽度（CSS 变量 `--edit-w`，18%–82%），「📱 手机」切换 `body.phone` 把右侧预览锁定为 375px
  手机宽度；「👁 仅预览」切换 `body.preview-only` 隐藏编辑区（窄屏 `<900px` 默认仅预览、点「✏️ 编辑」切全宽编辑）。
  复制始终取最新 `wechat-body` innerHTML。因 parser 与 Python 同构，**初始渲染（init 跑一次 parseMarkdown）与
  Python 兜底 BLOCKS 完全一致**。**已用 Node 抽取页面内真实 JS 跑同一份源文，与 Python `build_blocks_json`
  逐块 JSON 比对：在「空转/4 筐」(11 块) 与「独立开发者下一站」(20 块，含表格/列表/分隔线/各卡片) 两篇上均 100% 一致。**
- **历史 bug 修复**：`parse_inline` 中加粗/斜体/删除线的替换串原用 `rf"<... style=\"{...}\">"`（raw f-string
  里的 `\"` 会原样输出成非法 HTML 反斜杠，导致 `style=\"...\"`）。已改为 `f'<... style="{...}">\\1...'`，
  输出合规 `style="..."`，与 JS 渲染一致。
- 行内解析顺序固定为：行内代码 → HTML 转义 → 图片 → 链接 → 加粗 → 删除线 → 斜体，
  以保证嵌套与转义正确。
- 复制逻辑优先使用 `ClipboardItem('text/html')` 写入富文本，失败时回退到
  `execCommand('copy')` 选中复制，兼顾现代浏览器与老旧环境。
- 切勿在生成的正文里引入 `<style>`、`<link>` 或 class 属性——那会在粘贴时被公众号后台剥离。
- 配色底色（body_bg）必须写在每个内容块的外层 `<section>` 上（sec/sec_head/ul_sec/hr_sec/table_sec/img_sec），**不能只放在最外层容器**——因为"复制正文"复制的是容器 innerHTML，最外层容器的背景不会进入剪贴板，粘贴后底色会丢失。段间留白用 `padding` 而非 `margin`，保证底色连续无缝。
