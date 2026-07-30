#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_wechat_html.py — Markdown -> 公众号排版 HTML（配色 × 结构格式 自由组合）

将 Markdown 文章转换为「可直接复制到公众号后台」的 HTML：
  * 所有样式内联（style="..." 写在每个标签上），粘贴后格式完整保留
  * 正文用 <section> 包裹（公众号后台兼容性优于 <div>）
  * 文档首个 H1 视为标题，不进入复制区（标题在后台单独填写）
  * 引用块按内容关键词自动分类：蓝(古文) / 橙(编者按) / 绿(普通)
  * 配色（COLOR）与结构格式（VARIANT）完全解耦，可任意组合：
      - 10 套配色：简约蓝 / 文艺古籍 / 科技青 / 清新绿 / 暖橙生活 /
                   暗夜 / 报刊红 / 手账暖 / 极简灰 / 商业简报
      - 10 套结构格式（标题/引用/高亮三要素结构各异）：
                   左色条 / 居中双线 / 色块 / 虚线签 / 填充条 /
                   深色块 / 报刊双线 / 手账点线 / 极简线 / 简报体
      - 二者相乘共有 100 种组合，预览页上方两组选择器可实时切换
  * 扩展块级元素（受参考文章「SECTION 分栏 + 标签卡片」启发）：
      - 分栏分隔线：
          · 单独一行写 `--- 任意文字`（或 `*** 任意文字`）→ 渲染为居中 "— 任意文字 —"，文字可任意修改
          · 旧写法 `SECTION 01` 仍兼容，渲染为 "— SECTION 01 —"
          · 单独 `---`（无文字）仍是普通无文字分隔线
      - 标签卡片：引用块首行写 `> [!核心判断]` → 渲染为带标签的强调卡片
      - 编号洞察卡：引用块首行写 `> [!01] 标题` → 大号数字 + 标题 + 描述的卡片
      - 对比双栏：引用块首行写 `> [!compare] 左标题 | 右标题`，后续每行 `> 左内容 | 右内容` 自动分两列（逐行对照，无需 `|||`）
        → 渲染为两栏对照卡（左主色 / 右绿色，制造对照）
  * 默认组合（--theme 配色 + --format 格式）由 Python 渲染，保证复制内容正确无误；
    其余组合由页面内 JS 渲染器实时生成，文件小巧。

用法:
  python3 build_wechat_html.py input.md -o output.html
  python3 build_wechat_html.py input.md --theme classic --format seal   # 文艺古籍观感
  python3 build_wechat_html.py input.md --list-themes                   # 列出全部配色与格式
  python3 build_wechat_html.py --app -o app.html                        # 生成独立编辑器（不绑定单篇）
  python3 build_wechat_html.py --serve <目录>                           # 在目录起本地静态服务（托管独立编辑器）
依赖: 仅 Python 标准库
"""

import argparse
import html
import json
import os
import re
import sys

# ----------------------------------------------------------------------------
# 字体
# ----------------------------------------------------------------------------
SANS = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
SERIF = "'Songti SC','SimSun','Noto Serif SC',serif"

# ----------------------------------------------------------------------------
# 配色方案（仅颜色，不含结构；结构由 VARIANT 决定）
# ----------------------------------------------------------------------------
COLORS = {
    "blue": dict(  # 简约蓝
        accent="#4a90d9", text="#3f3f3f", heading="#2e2e2e", strong="#1a1a1a", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#2d2d2d", code_fg="#f8f8f2",
        inline_bg="#f6f8fa", inline_fg="#c7254e",
        qb_bd="#4a90d9", qb_bg="#f0f7ff", qb_fg="#2b5c8a",
        qo_bd="#e8833a", qo_bg="#fff7ef", qo_fg="#9a5a1e",
        qg_bd="#2ecc71", qg_bg="#f0fbf4", qg_fg="#2c7a4b",
        hr="#e0e0e0", t_bd="#e6e6e6", th_bg="#f5f7fa", th_fg="#333333",
    ),
    "classic": dict(  # 文艺古籍（暖金 + 衬线）
        accent="#8c6d3f", text="#4a4036", heading="#2b2419", strong="#2b2419", font=SERIF,
        sec_bg="transparent", body_bg="#fdfaf3", code_bg="#3a342b", code_fg="#efe7d6",
        inline_bg="#f3ead4", inline_fg="#8c5a2b",
        qb_bd="#3b4a8a", qb_bg="#eef0fb", qb_fg="#2c356f",
        qo_bd="#b5793a", qo_bg="#fbf2e6", qo_fg="#7a4a1e",
        qg_bd="#5a8a4a", qg_bg="#eef6ea", qg_fg="#3c6230",
        hr="#d8c9a8", t_bd="#ddd0b5", th_bg="#f3ead4", th_fg="#4a4036",
    ),
    "tech": dict(  # 科技青
        accent="#00b8d4", text="#37474f", heading="#102a43", strong="#102a43", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#0d2a35", code_fg="#b2ebf2",
        inline_bg="#e0f7fa", inline_fg="#00697a",
        qb_bd="#00b8d4", qb_bg="#e0f7fa", qb_fg="#006064",
        qo_bd="#ff8f00", qo_bg="#fff3e0", qo_fg="#e65100",
        qg_bd="#00c853", qg_bg="#e8f5e9", qg_fg="#1b5e20",
        hr="#cfd8dc", t_bd="#cfd8dc", th_bg="#eceff1", th_fg="#102a43",
    ),
    "green": dict(  # 清新绿
        accent="#2ecc71", text="#3f5145", heading="#24402f", strong="#24402f", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#1f3d2b", code_fg="#d6f5e0",
        inline_bg="#eafaf0", inline_fg="#1e7d45",
        qb_bd="#3498db", qb_bg="#eaf4fd", qb_fg="#1f6fb2",
        qo_bd="#e67e22", qo_bg="#fdf0e3", qo_fg="#9c5414",
        qg_bd="#2ecc71", qg_bg="#eafaf0", qg_fg="#1e7d45",
        hr="#d5e8d8", t_bd="#d5e8d8", th_bg="#eef9f1", th_fg="#24402f",
    ),
    "warm": dict(  # 暖橙生活
        accent="#e8833a", text="#4a3f38", heading="#3a2e26", strong="#3a2e26", font=SANS,
        sec_bg="transparent", body_bg="#fffaf5", code_bg="#3a2a20", code_fg="#f3e3d6",
        inline_bg="#fbeee2", inline_fg="#9a5320",
        qb_bd="#5b8def", qb_bg="#eaf1fd", qb_fg="#2c4f9e",
        qo_bd="#e8833a", qo_bg="#fff1e6", qo_fg="#9a5320",
        qg_bd="#57b894", qg_bg="#ecf8f1", qg_fg="#2c7a55",
        hr="#ecd9c8", t_bd="#ecd9c8", th_bg="#fbeee2", th_fg="#3a2e26",
    ),
    "dark": dict(  # 暗夜
        accent="#82aaff", text="#d7dce5", heading="#ffffff", strong="#ffffff", font=SANS,
        sec_bg="#1e2127", body_bg="#16181d", code_bg="#0d0f13", code_fg="#c5e1a5",
        inline_bg="#2a2f3a", inline_fg="#82aaff",
        qb_bd="#82aaff", qb_bg="#1b2330", qb_fg="#aac4ff",
        qo_bd="#ffb074", qo_bg="#2a2118", qo_fg="#ffcf9e",
        qg_bd="#7ee0a8", qg_bg="#16241c", qg_fg="#a7f0c8",
        hr="#333842", t_bd="#333842", th_bg="#232730", th_fg="#d7dce5",
    ),
    "news": dict(  # 报刊红
        accent="#c0392b", text="#333333", heading="#1a1a1a", strong="#1a1a1a", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#2d2d2d", code_fg="#f8f8f2",
        inline_bg="#f4e8e6", inline_fg="#c0392b",
        qb_bd="#34495e", qb_bg="#f1f3f5", qb_fg="#2c3e50",
        qo_bd="#c0392b", qo_bg="#fdf0ee", qo_fg="#8e2a1f",
        qg_bd="#2e7d5b", qg_bg="#eef6f1", qg_fg="#1f5c41",
        hr="#cccccc", t_bd="#dddddd", th_bg="#f5f5f5", th_fg="#1a1a1a",
    ),
    "note": dict(  # 手账暖（牛皮纸 + 衬线）
        accent="#e0a93b", text="#5b4a3a", heading="#3a2e22", strong="#3a2e22", font=SERIF,
        sec_bg="transparent", body_bg="#fdf8ef", code_bg="#3a342b", code_fg="#efe7d6",
        inline_bg="#f7ecd2", inline_fg="#9a6b1e",
        qb_bd="#6b8cae", qb_bg="#eef2f8", qb_fg="#3a4a5a",
        qo_bd="#d99a3a", qo_bg="#fbf2e2", qo_fg="#7a521c",
        qg_bd="#7faa5e", qg_bg="#eef5e8", qg_fg="#4a6b34",
        hr="#e3d6bf", t_bd="#e6dcc6", th_bg="#f7ecd2", th_fg="#3a2e22",
    ),
    "minimal": dict(  # 极简灰
        accent="#9aa0a6", text="#444444", heading="#222222", strong="#222222", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#2d2d2d", code_fg="#f8f8f2",
        inline_bg="#f2f2f2", inline_fg="#444444",
        qb_bd="#bbbbbb", qb_bg="transparent", qb_fg="#555555",
        qo_bd="#dddddd", qo_bg="transparent", qo_fg="#555555",
        qg_bd="#cccccc", qg_bg="transparent", qg_fg="#555555",
        hr="#dddddd", t_bd="#e0e0e0", th_bg="#f7f7f7", th_fg="#222222",
    ),
    "brief": dict(  # 商业简报（墨蓝 + 编辑感卡片，适合商业/组织/咨询类长文）
        accent="#1f3a5f", text="#33373d", heading="#16191d", strong="#111111", font=SANS,
        sec_bg="transparent", body_bg="#ffffff", code_bg="#1f2933", code_fg="#d7e3ee",
        inline_bg="#eef2f7", inline_fg="#1f3a5f",
        qb_bd="#1f3a5f", qb_bg="#eef2f7", qb_fg="#1a3c5e",
        qo_bd="#c8842b", qo_bg="#fbf3e6", qo_fg="#8a5a1e",
        qg_bd="#3f7d5a", qg_bg="#eef5f0", qg_fg="#2c5a40",
        hr="#d9dde2", t_bd="#d9dde2", th_bg="#eef2f7", th_fg="#16191d",
    ),
}

COLOR_ORDER = ["blue", "classic", "tech", "green", "warm", "dark", "news", "note", "minimal", "brief"]
COLOR_LABELS = {
    "blue": "简约蓝", "classic": "文艺古籍", "tech": "科技青",
    "green": "清新绿", "warm": "暖橙生活", "dark": "暗夜",
    "news": "报刊红", "note": "手账暖", "minimal": "极简灰", "brief": "商业简报",
}
DEFAULT_COLOR = "blue"

# ----------------------------------------------------------------------------
# 结构格式（VARIANT）：决定标题/引用/高亮三要素的「结构」，与配色无关
# 每种格式在 H2 / quote_* / strong 三处采用不同结构：
#   sidebar=左色条        seal=居中双线+双框     chip=填充色块
#   marker=虚线标签+胶带条  card=填充条+阴影卡     night=深色块
#   news=双线+粗左条+波浪线  note=点线+虚线框+荧光笔  minimal=居中细线+大引号
# ----------------------------------------------------------------------------
VARIANT_ORDER = ["sidebar", "seal", "chip", "marker", "card", "night", "news", "note", "minimal", "report"]
VARIANT_LABELS = {
    "sidebar": "左色条", "seal": "居中双线", "chip": "色块", "marker": "虚线签",
    "card": "填充条", "night": "深色块", "news": "报刊双线", "note": "手账点线",
    "minimal": "极简线", "report": "简报体",
}
VARIANT_DESC = {
    "sidebar": "标题左侧色条 / 左条引文 / 纯色加粗",
    "seal": "标题居中双线 / 双框引文 / 朱批金",
    "chip": "标题填充色块 / 圆角引文卡 / 背景药丸",
    "marker": "标题虚线标签 / 胶带条引文 / 背景标记",
    "card": "标题填充条 / 阴影引文卡 / 背景药丸",
    "night": "深色块标题 / 暗色引文卡 / 深底药丸",
    "news": "标题双线 / 粗左条引文 / 波浪下划线",
    "note": "标题点线 / 虚线框引文 / 荧光笔",
    "minimal": "标题居中细线 / 大引号无框引文 / 纯粗体",
    "report": "标题顶规 / 卡片引文 / 药丸高亮",
}
DEFAULT_FORMAT = "sidebar"

# 历史「整模板」映射：旧 9 套观感 = 配色 + 对应格式，方便复现
LEGACY_PRESETS = {
    "blue": ("blue", "sidebar"), "classic": ("classic", "seal"), "tech": ("tech", "chip"),
    "green": ("green", "marker"), "warm": ("warm", "card"), "dark": ("dark", "night"),
    "news": ("news", "news"), "note": ("note", "note"), "minimal": ("minimal", "minimal"),
}

# ----------------------------------------------------------------------------
# 引用分类关键词
# ----------------------------------------------------------------------------
QUOTE_EDITOR_KEYWORDS = [
    "编者按", "按语", "作者按", "小编按", "编辑按", "译注", "译者按",
    "注：", "注:", "按：", "按:", "批注", "点评", "编者：", "编者:",
]
QUOTE_ANCIENT_KEYWORDS = [
    "曰", "云：", "云:", "子曰", "诗云", "夫", "盖", "然则", "呜呼",
    "嗟乎", "嗟夫", "《", "》", "唐宋", "先秦", "诗经", "楚辞", "论语",
    "孟子", "老子", "庄子", "史记", "古文", "诗词", "赋曰", "辞曰",
]


# ----------------------------------------------------------------------------
# 由「配色 + 格式」生成内联样式字典
# ----------------------------------------------------------------------------
def _txt(f, color):
    """仅设置颜色与字体族（不附带字号/行高，以免覆盖标题、段落各自的尺寸设定）。"""
    return f"color:{color};font-family:{f};"


def _variant_overrides(p, f, variant):
    """按 variant 返回标题/引用/高亮等元素的结构化内联样式（不只是颜色变化）。

    与配色解耦：这里只描述「结构」，颜色取自传入的配色字典 p。
    """
    a = p["accent"]; h = p["heading"]; sc = p["strong"]
    qb = {"bd": p["qb_bd"], "bg": p["qb_bg"], "fg": p["qb_fg"]}
    qo = {"bd": p["qo_bd"], "bg": p["qo_bg"], "fg": p["qo_fg"]}
    qg = {"bd": p["qg_bd"], "bg": p["qg_bg"], "fg": p["qg_fg"]}
    hr = p["hr"]

    def q_side(q):
        return (f"padding:1.4em 18px;border-radius:8px;font-size:15px;line-height:1.75;"
                f"color:{q['fg']};font-family:{f};border-left:4px solid {q['bd']};background-color:{q['bg']};")
    def q_box(q, radius="10px", shadow="0 4px 14px rgba(0,0,0,0.06)", bar=""):
        left = f"border-left:{bar} solid {q['bd']};" if bar else ""
        return (f"padding:1.4em 18px;border-radius:{radius};font-size:15px;line-height:1.75;"
                f"color:{q['fg']};font-family:{f};border:1px solid {q['bd']};background-color:{q['bg']};"
                f"box-shadow:{shadow};{left}")
    def q_frame(q):
        return (f"padding:1.4em 18px;border-radius:4px;font-size:15px;line-height:1.75;"
                f"color:{q['fg']};font-family:{f};border:1px solid {q['bd']};outline:1px solid {q['bd']};"
                f"outline-offset:3px;background-color:{q['bg']};")
    def q_tape(q):
        return (f"padding:1.4em 18px;border-radius:0 10px 10px 0;font-size:15px;line-height:1.75;"
                f"color:{q['fg']};font-family:{f};border-left:6px solid {q['bd']};background-color:{q['bg']};")
    def q_bare(q):
        return (f"padding:1em 0;font-size:16px;line-height:1.8;font-style:italic;"
                f"color:{q['fg']};font-family:{f};border:none;background-color:transparent;")

    o = {}
    if variant == "sidebar":
        o["h2"] = (f"display:block;margin:0;padding:0 0 0 12px;font-size:20px;font-weight:bold;"
                   f"line-height:1.4;{_txt(f, h)}border-left:4px solid {a};")
        o["strong"] = f"font-weight:bold;color:{sc};"
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_side(q)
        o["q_glyph"] = ""
    elif variant == "seal":
        o["h2"] = (f"display:block;margin:0;padding:0 0 10px;text-align:center;font-size:20px;"
                   f"font-weight:bold;line-height:1.4;letter-spacing:1px;{_txt(f, h)}border-bottom:3px double {a};")
        o["strong"] = f"font-weight:bold;color:{a};"
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_frame(q)
        o["q_glyph"] = ""
    elif variant == "chip":
        o["h2"] = (f"display:inline-block;margin:0;padding:6px 14px;font-size:18px;font-weight:bold;"
                   f"line-height:1.4;letter-spacing:0.5px;color:#ffffff;background-color:{a};border-radius:6px;")
        o["strong"] = (f"font-weight:bold;color:{a};background-color:{p['inline_bg']};padding:0 4px;border-radius:3px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_box(q)
        o["q_glyph"] = ""
    elif variant == "marker":
        o["h2"] = (f"display:block;margin:0;padding:8px 12px;font-size:19px;font-weight:bold;"
                   f"line-height:1.4;{_txt(f, h)}background-color:{qg['bg']};border-left:4px dashed {a};border-radius:4px;")
        o["strong"] = (f"font-weight:bold;color:{h};background-color:{qg['bg']};padding:0 3px;border-radius:2px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_tape(q)
        o["q_glyph"] = ""
    elif variant == "card":
        o["h2"] = (f"display:block;margin:0;padding:8px 14px;font-size:19px;font-weight:bold;"
                   f"line-height:1.4;color:#ffffff;background-color:{a};border-radius:8px;letter-spacing:0.5px;")
        o["strong"] = (f"font-weight:bold;color:{a};background-color:{p['inline_bg']};padding:1px 4px;border-radius:4px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_box(q, radius="12px")
        o["q_glyph"] = ""
    elif variant == "night":
        o["h2"] = (f"display:block;margin:0;padding:8px 14px;font-size:19px;font-weight:bold;"
                   f"line-height:1.4;color:{a};background-color:#232730;border-left:4px solid {a};border-radius:8px;letter-spacing:0.5px;")
        o["strong"] = (f"font-weight:bold;color:{a};background-color:#2a2f3a;padding:1px 4px;border-radius:4px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_box(q, radius="12px", shadow="0 4px 14px rgba(0,0,0,0.4)")
        o["q_glyph"] = ""
    elif variant == "news":
        o["h2"] = (f"display:block;margin:0;padding:0 0 8px;font-size:20px;font-weight:bold;"
                   f"line-height:1.4;letter-spacing:1px;{_txt(f, h)}border-bottom:3px double {a};")
        o["strong"] = (f"font-weight:bold;color:{sc};text-decoration:underline;text-decoration-style:wavy;"
                       f"text-decoration-color:{a};")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_box(q, radius="0", shadow="none", bar="8px")
        o["q_glyph"] = ""
    elif variant == "note":
        o["h2"] = (f"display:block;margin:0;padding:0 0 6px;font-size:20px;font-weight:bold;"
                   f"line-height:1.4;letter-spacing:1px;{_txt(f, h)}border-bottom:2px dotted {a};")
        o["strong"] = (f"font-weight:bold;color:#3a2e22;background-color:rgba(255,221,87,0.55);padding:0 3px;border-radius:2px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = (f"padding:1.4em 18px;border-radius:10px;font-size:15px;line-height:1.75;"
                    f"color:{q['fg']};font-family:{f};border:2px dashed {q['bd']};background-color:{q['bg']};")
        o["q_glyph"] = ""
    elif variant == "minimal":
        o["h2"] = (f"display:block;margin:0;padding:8px 0;text-align:center;font-size:19px;font-weight:bold;"
                   f"line-height:1.4;letter-spacing:2px;{_txt(f, h)}border-top:1px solid {hr};border-bottom:1px solid {hr};")
        o["strong"] = f"font-weight:bold;color:{sc};"
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_bare(q)
        o["q_glyph"] = (f'<span style="display:block;font-family:{f};font-size:42px;line-height:0.7;'
                        f'color:{a};font-weight:bold;">“</span>')
    elif variant == "report":
        o["h2"] = (f"display:block;margin:0;padding:14px 0 8px;font-size:20px;font-weight:bold;"
                   f"line-height:1.4;letter-spacing:1px;{_txt(f, h)}border-top:3px solid {a};")
        o["strong"] = (f"font-weight:bold;color:{a};background-color:{p['inline_bg']};padding:1px 4px;border-radius:3px;")
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_box(q, radius="8px", bar="6px")
        o["q_glyph"] = ""
    else:  # 兜底：sidebar
        o["h2"] = (f"display:block;margin:0;padding:0 0 0 12px;font-size:20px;font-weight:bold;"
                   f"line-height:1.4;{_txt(f, h)}border-left:4px solid {a};")
        o["strong"] = f"font-weight:bold;color:{sc};"
        for k, q in (("quote_blue", qb), ("quote_orange", qo), ("quote_green", qg)):
            o[k] = q_side(q)
        o["q_glyph"] = ""
    return o


def make_styles(colors, variant):
    f = colors["font"]
    base = {
        "accent": colors["accent"],
        "text": colors["text"],
        "font": f,
        "body_bg": colors["body_bg"],
        "sec": f"box-sizing:border-box;padding:0.75em 0;",
        "sec_head": f"box-sizing:border-box;padding:1.3em 0 0.6em;",
        "p": f"margin:0;padding:0;{_txt(f, colors['text'])}font-size:16px;line-height:1.75;letter-spacing:0.5px;text-align:justify;",
        "h3": f"display:block;margin:0;padding:0;font-size:18px;font-weight:bold;line-height:1.4;{_txt(f, colors['heading'])}",
        "h4": f"display:block;margin:0;padding:0;font-size:16px;font-weight:bold;{_txt(f, colors['heading'])}",
        "h5": f"display:block;margin:0;padding:0;font-size:15px;font-weight:bold;{_txt(f, colors['heading'])}",
        "h6": f"display:block;margin:0;padding:0;font-size:14px;font-weight:bold;{_txt(f, colors['heading'])}",
        "em": f"font-style:italic;{_txt(f, colors['text'])}",
        "del": "text-decoration:line-through;color:#999999;",
        "a": f"color:{colors['accent']};text-decoration:none;border-bottom:1px solid {colors['accent']};",
        "code": f"background-color:{colors['inline_bg']};color:{colors['inline_fg']};padding:2px 6px;"
                f"border-radius:4px;font-size:14px;font-family:Consolas,'Courier New',monospace;letter-spacing:0;",
        "img_sec": f"box-sizing:border-box;padding:0.5em 0;text-align:center;",
        "img": "max-width:100%;height:auto;border-radius:6px;vertical-align:middle;"
               "box-shadow:0 1px 4px rgba(0,0,0,0.08);",
        "codeblock_sec": f"padding:1.4em 18px;border-radius:8px;background-color:{colors['code_bg']};"
                         f"overflow-x:auto;-webkit-overflow-scrolling:touch;",
        "codeblock": f"margin:0;padding:0;color:{colors['code_fg']};font-size:14px;line-height:1.65;"
                     f"font-family:Consolas,'Courier New',monospace;white-space:pre-wrap;word-break:break-word;letter-spacing:0;",
        "ul_sec": f"box-sizing:border-box;padding:0.75em 0;",
        "ul": "margin:0;padding:0;list-style:none;",
        "li": f"margin:0;padding:0.35em 0 0.35em 1.4em;position:relative;{_txt(f, colors['text'])}font-size:16px;line-height:1.7;",
        "li_bullet_ul": f"position:absolute;left:2px;top:0.5em;color:{colors['accent']};font-weight:bold;font-size:16px;line-height:1;",
        "li_bullet_ol": f"position:absolute;left:0;top:0.1em;color:{colors['accent']};font-weight:bold;font-size:14px;line-height:1;",
        "hr_sec": f"box-sizing:border-box;padding:1em 0;text-align:center;",
        "hr_inner": f"display:inline-block;width:60px;height:1px;background-color:{colors['hr']};vertical-align:middle;",
        "hr_dot": f"display:inline-block;margin:0 12px;color:{colors['hr']};font-size:14px;vertical-align:middle;",
        "table_sec": f"box-sizing:border-box;padding:0.75em 0;overflow-x:auto;-webkit-overflow-scrolling:touch;",
        "table": f"border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;{_txt(f, colors['text'])}",
        "th": f"border:1px solid {colors['t_bd']};padding:8px 12px;background-color:{colors['th_bg']};"
              f"{_txt(f, colors['th_fg'])}font-weight:bold;text-align:left;",
        "td": f"border:1px solid {colors['t_bd']};padding:8px 12px;text-align:left;{_txt(f, colors['text'])};",
        "wrapper": f"box-sizing:border-box;width:100%;margin:0;background-color:{colors['body_bg']};padding:0.6em 16px;",
        "accent": colors["accent"],
        "inline_bg": colors["inline_bg"],
        "secdiv_sec": "box-sizing:border-box;padding:1.4em 0;text-align:center;",
        "secdiv_rule": f"display:inline-block;width:40px;height:1px;background-color:{colors['accent']};vertical-align:middle;",
        "secdiv_txt": f"display:inline-block;margin:0 14px;color:{colors['accent']};font-size:13px;letter-spacing:3px;font-weight:bold;font-family:{f};",
        "callout_sec": f"box-sizing:border-box;padding:1.2em 18px;border-radius:8px;border-left:4px solid {colors['accent']};background-color:{colors['inline_bg']};",
        "callout_label": f"display:block;font-size:13px;font-weight:bold;letter-spacing:2px;color:{colors['accent']};font-family:{f};margin:0 0 6px;",
        # 编号洞察卡：大号数字 + 标题 + 描述
        "insight_sec": f"box-sizing:border-box;padding:1.1em 16px;border-radius:10px;border-left:4px solid {colors['accent']};background-color:{colors['inline_bg']};",
        "insight_tbl": "border-collapse:collapse;width:100%;",
        "insight_num_cell": "vertical-align:top;width:56px;",
        "insight_num": f"display:block;font-family:{f};font-size:38px;line-height:1;font-weight:bold;color:{colors['accent']};",
        "insight_body": "vertical-align:top;",
        "insight_title": f"display:block;margin:0 0 5px;font-family:{f};font-size:17px;font-weight:bold;line-height:1.45;color:{colors['heading']};",
        "insight_desc": f"display:block;margin:0;{_txt(f, colors['text'])}font-size:15px;line-height:1.7;",
        # 对比双栏：两栏对照卡（左=主色 / 右=绿色，制造对照）
        "cmp_sec": f"box-sizing:border-box;padding:0.4em 0;",
        "cmp_card": f"box-sizing:border-box;padding:0;border-radius:10px;overflow:hidden;border:1px solid {colors['t_bd']};background-color:#ffffff;",
        "cmp_tbl": f"border-collapse:collapse;width:100%;font-size:15px;line-height:1.7;{_txt(f, colors['text'])}",
        "cmp_th": f"padding:10px 14px;text-align:center;font-family:{f};font-weight:bold;font-size:15px;color:{colors['accent']};background-color:{colors['inline_bg']};border-bottom:1px solid {colors['t_bd']};",
        "cmp_th2": f"padding:10px 14px;text-align:center;font-family:{f};font-weight:bold;font-size:15px;color:{colors['qg_bd']};background-color:{colors['qg_bg']};border-bottom:1px solid {colors['t_bd']};border-left:1px solid {colors['t_bd']};",
        "cmp_td": f"padding:10px 14px;vertical-align:top;width:50%;border-bottom:1px solid {colors['t_bd']};",
        "cmp_td2": f"padding:10px 14px;vertical-align:top;width:50%;border-bottom:1px solid {colors['t_bd']};border-left:1px solid {colors['t_bd']};",
    }
    base.update(_variant_overrides(colors, f, variant))
    base.update(_variant_overrides(colors, f, variant))
    return base


# 全部组合：(color, variant) -> 样式字典
STYLES = {(c, v): make_styles(COLORS[c], v) for c in COLOR_ORDER for v in VARIANT_ORDER}


# ----------------------------------------------------------------------------
# HTML 转义辅助
# ----------------------------------------------------------------------------
def esc_text(text):
    return html.escape(text, quote=False)


def esc_attr(text):
    return html.escape(text, quote=True)


# ----------------------------------------------------------------------------
# 行内解析：code > img > link > strong > em > del
# ----------------------------------------------------------------------------
def parse_inline(text, s):
    code_spans = []

    def stash_code(m):
        code_spans.append(m.group(1))
        return f"\x00CODE{len(code_spans)-1}\x00"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = esc_text(text)

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)",
        lambda m: (
            f'<section style="{s["img_sec"]}">'
            f'<img src="{esc_attr(m.group(2))}" alt="{esc_attr(m.group(1))}" style="{s["img"]}"></section>'
        ),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)",
        lambda m: f'<a href="{esc_attr(m.group(2))}" target="_blank" style="{s["a"]}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", f'<strong style="{s["strong"]}">\\1</strong>', text)
    text = re.sub(r"__(.+?)__", f'<strong style="{s["strong"]}">\\1</strong>', text)
    text = re.sub(r"~~(.+?)~~", f'<del style="{s["del"]}">\\1</del>', text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", f'<em style="{s["em"]}">\\1</em>', text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)_(?!_)", f'<em style="{s["em"]}">\\1</em>', text)

    def restore_code(m):
        idx = int(m.group(1))
        return f'<code style="{s["code"]}">{esc_text(code_spans[idx])}</code>'

    text = re.sub(r"\x00CODE(\d+)\x00", restore_code, text)
    return text


# ----------------------------------------------------------------------------
# 引用分类
# ----------------------------------------------------------------------------
def classify_quote(text):
    for kw in QUOTE_EDITOR_KEYWORDS:
        if kw in text:
            return "quote_orange"
    for kw in QUOTE_ANCIENT_KEYWORDS:
        if kw in text:
            return "quote_blue"
    return "quote_green"


# ----------------------------------------------------------------------------
# 块级渲染
# ----------------------------------------------------------------------------
def render_codeblock(lines, s):
    escaped = esc_text("\n".join(lines))
    return f'<section style="{s["codeblock_sec"]}"><code style="{s["codeblock"]}">{escaped}</code></section>'


def render_heading(level, text, s):
    key = f"h{level}" if level in (2, 3, 4, 5, 6) else "h4"
    inner = parse_inline(text, s)
    return f'<section style="{s["sec_head"]}"><h{level} style="{s[key]}">{inner}</h{level}></section>'


def render_paragraph(lines, s):
    inner = parse_inline(" ".join(lines).strip(), s)
    return f'<section style="{s["sec"]}"><p style="{s["p"]}">{inner}</p></section>'


def render_blockquote(lines, s):
    raw = "\n".join(l.strip() for l in lines)
    qkey = classify_quote(raw)
    parts = []
    for ln in lines:
        ln = ln.strip()
        parts.append("<br>" if ln == "" else parse_inline(ln, s))
    inner = "".join(parts)
    glyph = s.get("q_glyph", "")
    return f'<section style="{s[qkey]}">{glyph}{inner}</section>'


def render_list(items, ordered, s):
    tag = "ol" if ordered else "ul"
    li_html = []
    for idx, it in enumerate(items, 1):
        content = parse_inline(it, s)
        if ordered:
            bullet = f'<span style="{s["li_bullet_ol"]}">{idx}.</span>'
        else:
            bullet = f'<span style="{s["li_bullet_ul"]}">•</span>'
        li_html.append(f'<li style="{s["li"]}">{bullet}{content}</li>')
    return (
        f'<section style="{s["ul_sec"]}"><{tag} style="{s["ul"]}">{"".join(li_html)}</{tag}></section>'
    )


def render_hr(s):
    return (
        f'<section style="{s["hr_sec"]}">'
        f'<span style="{s["hr_inner"]}"></span>'
        f'<span style="{s["hr_dot"]}">●</span>'
        f'<span style="{s["hr_inner"]}"></span></section>'
    )


def render_secdiv(num, label, s):
    if label:
        txt = esc_text(label)
    elif num:
        txt = f"SECTION {num}"
    else:
        txt = ""
    return (
        f'<section style="{s["secdiv_sec"]}">'
        f'<span style="{s["secdiv_rule"]}"></span>'
        f'<span style="{s["secdiv_txt"]}">{txt}</span>'
        f'<span style="{s["secdiv_rule"]}"></span></section>'
    )


def render_callout(label, lines, s):
    parts = []
    for ln in lines:
        ln = ln.strip()
        parts.append("<br>" if ln == "" else parse_inline(ln, s))
    inner = "".join(parts)
    return (
        f'<section style="{s["callout_sec"]}">'
        f'<span style="{s["callout_label"]}">{esc_text(label)}</span>'
        f'<p style="{s["p"]}">{inner}</p></section>'
    )


def render_insight(num, lines, s):
    title = parse_inline(" ".join(lines[0:1]).strip(), s) if lines else ""
    desc_parts = []
    for ln in lines[1:]:
        ln = ln.strip()
        desc_parts.append("<br>" if ln == "" else parse_inline(ln, s))
    desc = "".join(desc_parts)
    return (
        f'<section style="{s["insight_sec"]}">'
        f'<table style="{s["insight_tbl"]}"><tr>'
        f'<td style="{s["insight_num_cell"]}"><span style="{s["insight_num"]}">{esc_text(num)}</span></td>'
        f'<td style="{s["insight_body"]}">'
        f'<p style="{s["insight_title"]}">{title}</p>'
        + (f'<p style="{s["insight_desc"]}">{desc}</p>' if desc else "")
        + f'</td></tr></table></section>'
    )


def render_comparison(lines, s):
    head = (lines[0] if lines else "").strip()
    if "|" in head:
        lh, rh = head.split("|", 1)
    else:
        lh, rh = head, ""
    lh, rh = lh.strip(), rh.strip()
    rows = []
    for ln in lines[1:]:
        ln = ln.strip()
        if ln == "":
            continue
        if "|" in ln:
            a, b = ln.split("|", 1)
        else:
            a, b = ln, ""
        rows.append((a.strip(), b.strip()))
    out = [f'<section style="{s["cmp_sec"]}">', f'<section style="{s["cmp_card"]}">',
           f'<table style="{s["cmp_tbl"]}"><tr>',
           f'<td style="{s["cmp_th"]}">{parse_inline(lh, s)}</td>',
           f'<td style="{s["cmp_th2"]}">{parse_inline(rh, s)}</td>',
           "</tr>"]
    for a, b in rows:
        out.append("<tr>")
        out.append(f'<td style="{s["cmp_td"]}">{parse_inline(a, s)}</td>')
        out.append(f'<td style="{s["cmp_td2"]}">{parse_inline(b, s)}</td>')
        out.append("</tr>")
    out.append("</table></section></section>")
    return "".join(out)


def render_table(header, rows, s):
    th = "".join(f'<th style="{s["th"]}">{parse_inline(c.strip(), s)}</th>' for c in header)
    body = "".join(
        "<tr>" + "".join(f'<td style="{s["td"]}">{parse_inline(c.strip(), s)}</td>' for c in r) + "</tr>"
        for r in rows
    )
    return (
        f'<section style="{s["table_sec"]}">'
        f'<table style="{s["table"]}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></section>'
    )


def render_image_line(alt, url, s):
    return (
        f'<section style="{s["img_sec"]}">'
        f'<img src="{esc_attr(url)}" alt="{esc_attr(alt)}" style="{s["img"]}"></section>'
    )


# ----------------------------------------------------------------------------
# Markdown -> 块列表
# ----------------------------------------------------------------------------
def split_blocks(md_text):
    lines = md_text.split("\n")
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped == "":
            i += 1
            continue

        m = re.match(r"^(`{3,}|~{3,})(.*)$", line)
        if m:
            fence = m.group(1)[0]
            lang = m.group(2).strip()
            buf = []
            i += 1
            while i < n and not re.match(r"^[" + fence + r"]{3,}\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", lang, buf))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            blocks.append(("h", len(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        m = re.match(r"^(---|\*\*\*|___)\s+(.+)$", stripped)
        if m:
            blocks.append(("secdiv", None, m.group(2).strip()))
            i += 1
            continue

        if re.match(r"^(---|\*\*\*|___)\s*$", stripped):
            blocks.append(("hr", None, None))
            i += 1
            continue

        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]).rstrip())
                i += 1
            if buf and re.match(r"^\[!([^\]]+)\]\s*(.*)$", buf[0]):
                cm = re.match(r"^\[!([^\]]+)\]\s*(.*)$", buf[0])
                raw_label = cm.group(1).strip()
                rest = cm.group(2).strip()
                low = raw_label.lower()
                if low == "compare":
                    # 逐行两列：内容[0]=两列标题("左标题 | 右标题")，后续每行 "左 | 右" 为一行对照
                    content = ([rest] if rest else []) + buf[1:]
                    blocks.append(("compare", None, content))
                else:
                    content = ([rest] if rest else []) + buf[1:]
                    if re.fullmatch(r"\d{1,3}", raw_label):
                        blocks.append(("insight", raw_label, content))
                    else:
                        blocks.append(("callout", raw_label, content))
            else:
                blocks.append(("quote", None, buf))
            continue

        m = re.match(r"^SECTION\s+(\d{1,3})$", stripped, re.IGNORECASE)
        if m:
            blocks.append(("secdiv", m.group(1), None))
            i += 1
            continue

        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            header = [c for c in stripped.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i].strip() and lines[i].strip():
                rows.append([c for c in lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append(("table", header, rows))
            continue

        if re.match(r"^(\s*)([-*+]|\d+[.)])\s+", line):
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", line))
            buf = []
            while i < n and re.match(r"^(\s*)([-*+]|\d+[.)])\s+", lines[i]):
                buf.append(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", lines[i]).rstrip())
                i += 1
            blocks.append(("list", ordered, buf))
            continue

        m = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)$", stripped)
        if m:
            blocks.append(("img", (m.group(1), m.group(2)), None))
            i += 1
            continue

        buf = []
        while (
            i < n and lines[i].strip() != ""
            and not re.match(r"^(#{1,6})\s+", lines[i])
            and not re.match(r"^(\s*)([-*+]|\d+[.)])\s+", lines[i])
            and not lines[i].strip().startswith(">")
            and not re.match(r"^(`{3,}|~{3,})", lines[i])
            and not re.match(r"^(---|\*\*\*|___)\s*$", lines[i].strip())
        ):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(("p", None, buf))
    return blocks


def convert(md_text, s):
    """返回 (title, body_html)。首个 H1 作为标题，不进正文。"""
    blocks = split_blocks(md_text)
    title = None
    out = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h" and blk[1] == 1:
            if title is None:
                title = parse_inline(blk[2], s)
                continue
            out.append(render_heading(2, blk[2], s))
            continue
        if kind == "h":
            out.append(render_heading(blk[1], blk[2], s))
        elif kind == "p":
            out.append(render_paragraph(blk[2], s))
        elif kind == "quote":
            out.append(render_blockquote(blk[2], s))
        elif kind == "code":
            out.append(render_codeblock(blk[2], s))
        elif kind == "list":
            out.append(render_list(blk[2], blk[1], s))
        elif kind == "hr":
            out.append(render_hr(s))
        elif kind == "secdiv":
            out.append(render_secdiv(blk[1], blk[2], s))
        elif kind == "callout":
            out.append(render_callout(blk[1], blk[2], s))
        elif kind == "insight":
            out.append(render_insight(blk[1], blk[2], s))
        elif kind == "compare":
            out.append(render_comparison(blk[2], s))
        elif kind == "table":
            out.append(render_table(blk[1], blk[2], s))
        elif kind == "img":
            alt, url = blk[1]
            out.append(render_image_line(alt, url, s))
    return title, f'<section style="{s["wrapper"]}">\n' + "\n".join(out) + "\n</section>"


def build_blocks_json(md_text):
    """返回 (title_plain, blocks_json)。首个 H1 作为标题不进正文；后续 H1 降级为 H2。

    blocks_json 供页面内 JS 渲染器实时组合「配色 × 格式」使用。
    """
    blocks = split_blocks(md_text)
    title = None
    out = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h" and blk[1] == 1:
            if title is None:
                title = blk[2]
                continue
            out.append({"t": "h", "l": 2, "x": blk[2]})
            continue
        if kind == "h":
            out.append({"t": "h", "l": blk[1], "x": blk[2]})
        elif kind == "p":
            out.append({"t": "p", "x": " ".join(blk[2]).strip()})
        elif kind == "quote":
            out.append({"t": "q", "x": blk[2]})
        elif kind == "code":
            out.append({"t": "c", "lang": blk[1], "x": blk[2]})
        elif kind == "list":
            out.append({"t": "l", "o": blk[1], "x": blk[2]})
        elif kind == "hr":
            out.append({"t": "hr"})
        elif kind == "secdiv":
            out.append({"t": "sd", "n": blk[1], "label": blk[2]})
        elif kind == "callout":
            out.append({"t": "co", "label": blk[1], "x": blk[2]})
        elif kind == "insight":
            out.append({"t": "ins", "n": blk[1], "x": blk[2]})
        elif kind == "compare":
            out.append({"t": "cmp", "x": blk[2]})
        elif kind == "table":
            out.append({"t": "tb", "h": blk[1], "r": blk[2]})
        elif kind == "img":
            alt, url = blk[1]
            out.append({"t": "img", "a": alt, "u": url})
    return title, out


# ----------------------------------------------------------------------------
# 预览页面模板（配色选择器 + 结构格式选择器 + 复制按钮）
# 说明：默认组合由 Python 渲染为 __DEF_BODY__（保证复制内容正确）；其余组合由
#       页面内 JS 渲染器实时生成，无需在 Python 端预渲染 81 份正文。
# ----------------------------------------------------------------------------
PREVIEW_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>公众号排版预览</title>
<style>
  html,body{height:100%;margin:0;overflow:hidden;}
  body{display:flex;flex-direction:column;background:#f2f3f5;font-family:__SANS__;}
  .bar{flex:0 0 auto;z-index:10;display:flex;align-items:center;gap:12px;
       padding:12px 20px;background:#fff;border-bottom:1px solid #ececec;box-shadow:0 1px 6px rgba(0,0,0,0.04);}
  .bar .t{font-size:15px;font-weight:bold;color:#333;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .bar button.copy{border:none;background:#4a90d9;color:#fff;font-size:14px;padding:9px 18px;border-radius:20px;cursor:pointer;font-weight:bold;}
  .bar button.copy:active{transform:scale(0.97);}
  .selbar{flex:0 0 auto;z-index:9;background:#fff;border-bottom:1px solid #ececec;padding-bottom:6px;overflow:auto;}
  .sel-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:8px 20px 2px;}
  .sel-row .lab{font-size:12px;color:#999;min-width:48px;flex-shrink:0;}
  .sel-row button{border:1px solid #e0e0e0;background:#fafafa;color:#555;font-size:13px;padding:6px 12px;border-radius:14px;cursor:pointer;}
  .sel-row button.active{background:#4a90d9;border-color:#4a90d9;color:#fff;font-weight:bold;}
  .stage{max-width:740px;margin:0 auto;background:transparent;border-radius:10px;padding:16px 0 48px;box-shadow:none;}
  #wechat-body{font-size:16px;padding:0;border-radius:6px;overflow:hidden;}
  .toast{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.8);color:#fff;padding:12px 22px;border-radius:8px;font-size:14px;opacity:0;transition:opacity .25s;pointer-events:none;z-index:40;}
  .toast.show{opacity:1;}
  .bar button.mode{border:1px solid #e0e0e0;background:#fafafa;color:#555;font-size:14px;padding:8px 16px;border-radius:20px;cursor:pointer;}
  .bar button.mode:active{transform:scale(0.97);}
  /* 帮助：收到问号里，点击展开 */
  .help-wrap{position:relative;flex-shrink:0;}
  .help-btn{width:32px;height:32px;padding:0;border:1px solid #e0e0e0;background:#fafafa;color:#666;
    border-radius:50%;cursor:pointer;font-size:16px;font-weight:bold;line-height:1;display:inline-flex;align-items:center;justify-content:center;}
  .help-btn:hover,.help-btn[aria-expanded="true"]{background:#4a90d9;border-color:#4a90d9;color:#fff;}
  .help-pop{display:none;position:absolute;right:0;top:calc(100% + 8px);width:min(440px,calc(100vw - 32px));
    background:#fff;border:1px solid #ececec;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.14);
    padding:14px 16px;font-size:13px;color:#666;line-height:1.7;z-index:30;}
  .help-pop.open{display:block;}
  .help-pop strong{color:#333;}
  /* 默认即为左右布局：左编辑、右预览（各自独立滚动，不带动整页） */
  #mdInput{width:100%;height:100%;box-sizing:border-box;border:none;outline:none;resize:none;
    padding:18px 20px;font-family:Consolas,'Courier New',monospace;font-size:14px;line-height:1.7;color:#2b2b2b;background:#fbfbfd;tab-size:2;}
  #mdInput:focus{background:#fff;}
  .split{flex:1 1 auto;min-height:0;display:flex;align-items:stretch;gap:0;width:100%;margin:0;
    border:none;border-top:1px solid #ececec;background:#fff;--edit-w:44%;}
  .editor-pane{flex:0 0 var(--edit-w,44%);background:#fbfbfd;min-width:0;min-height:0;overflow:hidden;display:flex;flex-direction:column;}
  .preview-pane{flex:1 1 56%;min-width:0;min-height:0;overflow:auto;-webkit-overflow-scrolling:touch;}
  .resizer{flex:0 0 7px;width:7px;cursor:col-resize;background:#e6e6ea;position:relative;}
  .resizer:hover,.resizer.active{background:#4a90d9;}
  .resizer::after{content:"";position:absolute;left:2px;top:50%;transform:translateY(-50%);width:2px;height:30px;background:#b9b9c2;border-radius:1px;}
  /* 手机宽度模式：右侧预览锁定为手机宽度，编辑区取剩余空间 */
  body.phone .editor-pane{flex:1 1 auto;}
  body.phone .resizer{display:none;}
  body.phone .preview-pane{flex:0 0 390px;}
  body.phone .stage{max-width:375px;}
  /* 仅预览模式：隐藏编辑区与分隔条，预览占满并独立滚动 */
  body.preview-only .editor-pane{display:none;}
  body.preview-only .resizer{display:none;}
  body.preview-only .split{display:flex;max-width:none;margin:0;border:none;background:#f2f3f5;}
  body.preview-only .preview-pane{flex:1 1 auto;overflow:auto;}
  body.preview-only .stage{max-width:740px;padding-left:16px;padding-right:16px;}
  @media (max-width:899px){
    /* 窄屏：默认仅预览，点“编辑”切到全宽编辑；分隔条在窄屏隐藏；仍保持区域内滚动 */
    .split{display:flex;max-width:none;margin:0;border:none;background:#f2f3f5;}
    .editor-pane{display:none;}
    .preview-pane{display:block;flex:1 1 auto;overflow:auto;}
    body:not(.preview-only) .editor-pane{display:flex;flex:1 1 auto;}
    body:not(.preview-only) .preview-pane{display:none;}
    .resizer{display:none;}
    .stage{padding-left:12px;padding-right:12px;}
  }
</style>
</head>
<body>
  <div class="bar">
    <span class="t" id="titleText">__TITLE__</span>
    <button class="mode" id="phoneBtn">📱 手机</button>
    <button class="mode" id="editToggle">👁 仅预览</button>
    <button class="copy" id="copyBtn">📋 复制正文</button>
    __EXTRA_BTNS__
    <div class="help-wrap">
      <button type="button" class="help-btn" id="helpBtn" title="使用说明" aria-label="使用说明" aria-expanded="false" aria-controls="helpPop">?</button>
      <div class="help-pop" id="helpPop" role="dialog" aria-label="使用说明">
        <strong>使用说明</strong><br>
        标题请在公众号后台单独填写（本页标题不进入复制区）。页面默认为「左编辑 / 右预览」布局，左侧改稿右侧实时刷新；左右可分别滚动。中间分隔条可拖动调整左右宽度；点「📱 手机」可把右侧预览锁定为手机宽度；点「👁 仅预览」可隐藏编辑区只看排版。上方两组可分别选择「配色」与「结构格式」自由组合；点击「复制正文」会以当前组合复制，到后台 Ctrl/⌘+V 粘贴即可保留格式。
      </div>
    </div>
    <input id="fileInput" type="file" accept=".md,.markdown,.txt,text/markdown" style="display:none">
  </div>
  <div class="selbar">
    <div class="sel-row"><span class="lab">配色</span><span id="colorBtns">__COLOR_BTNS__</span></div>
    <div class="sel-row"><span class="lab">结构格式</span><span id="formatBtns">__FORMAT_BTNS__</span></div>
  </div>
  <div class="split" id="split">
    <div class="pane editor-pane" id="editorPane">
      <textarea id="mdInput" spellcheck="false"></textarea>
    </div>
    <div class="resizer" id="resizer" title="拖动调整左右宽度"></div>
    <div class="pane preview-pane" id="previewPane">
      <div class="stage">
        <section id="wechat-body" style="font-family:__DEF_FONT__;color:__DEF_TEXT__;background-color:__DEF_BG__;">
__DEF_BODY__
        </section>
      </div>
    </div>
  </div>
  <div class="toast" id="toast"></div>
<script>
var BLOCKS = __BLOCKS_JSON__;
var STYLES = __STYLES_JSON__;
var META = __META_JSON__;
var COLOR_ORDER = __COLOR_ORDER_JSON__;
var VARIANT_ORDER = __VARIANT_ORDER_JSON__;
var COLOR_LABELS = __COLOR_LABELS_JSON__;
var VARIANT_LABELS = __VARIANT_LABELS_JSON__;
var DEF_COLOR = __DEF_COLOR__;
var DEF_FORMAT = __DEF_FORMAT__;
var SOURCE = __MD_SOURCE_JSON__;
var curColor = DEF_COLOR, curFormat = DEF_FORMAT;

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function escAttr(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

var QUOTE_EDITOR = __Q_EDITOR_JSON__;
var QUOTE_ANCIENT = __Q_ANCIENT_JSON__;
function classifyQuote(text){
  for(var i=0;i<QUOTE_EDITOR.length;i++){ if(text.indexOf(QUOTE_EDITOR[i])>=0) return 'quote_orange'; }
  for(var j=0;j<QUOTE_ANCIENT.length;j++){ if(text.indexOf(QUOTE_ANCIENT[j])>=0) return 'quote_blue'; }
  return 'quote_green';
}

function parseInline(text, s){
  var codes=[];
  text = text.replace(/`([^`]+)`/g, function(m,p1){ codes.push(p1); return "\\u0000CODE"+(codes.length-1)+"\\u0000"; });
  text = esc(text);
  text = text.replace(/!\\[([^\\]]*)\\]\\(([^)\\s]+)(?:\\s+"([^"]*)")?\\)/g, function(m,alt,url){
    return '<section style="'+s.img_sec+'"><img src="'+escAttr(url)+'" alt="'+escAttr(alt)+'" style="'+s.img+'"></section>';
  });
  text = text.replace(/\\[([^\\]]+)\\]\\(([^)\\s]+)(?:\\s+"([^"]*)")?\\)/g, function(m,t,url){
    return '<a href="'+escAttr(url)+'" target="_blank" style="'+s.a+'">'+t+'</a>';
  });
  text = text.replace(/\\*\\*(.+?)\\*\\*/g, function(m,p1){ return '<strong style="'+s.strong+'">'+p1+'</strong>'; });
  text = text.replace(/__(.+?)__/g, function(m,p1){ return '<strong style="'+s.strong+'">'+p1+'</strong>'; });
  text = text.replace(/~~(.+?)~~/g, function(m,p1){ return '<del style="'+s.del+'">'+p1+'</del>'; });
  text = text.replace(/(?<!\\*)\\*(?!\\*)(.+?)\\*(?!\\*)/g, function(m,p1){ return '<em style="'+s.em+'">'+p1+'</em>'; });
  text = text.replace(/(?<!_)_(?!_)(.+?)_(?!_)/g, function(m,p1){ return '<em style="'+s.em+'">'+p1+'</em>'; });
  text = text.replace(/\\u0000CODE(\\d+)\\u0000/g, function(m,idx){ return '<code style="'+s.code+'">'+esc(codes[+idx])+'</code>'; });
  return text;
}

function stripPipes(s){ while(s.charAt(0)==='|') s=s.slice(1); while(s.charAt(s.length-1)==='|') s=s.slice(0,-1); return s; }

// 浏览器端 Markdown 解析器：忠实移植 Python split_blocks，输出与 build_blocks_json 同构的块数组。
// 首个 H1 作为标题（不进正文），后续 H1 降级为 H2。
function parseMarkdown(text){
  var lines = String(text==null?'':text).split("\\n");
  var blocks = [];
  var title = null;
  var i=0, n=lines.length;
  while(i<n){
    var line = lines[i];
    var stripped = line.replace(/^\\s+/,'').replace(/\\s+$/,'');
    if(stripped===""){ i++; continue; }

    var m = line.match(/^(`{3,}|~{3,})(.*)$/);
    if(m){
      var fence = m[1].charAt(0);
      var lang = m[2].replace(/^\\s+/,'').replace(/\\s+$/,'');
      var buf=[]; i++;
      var fenceRe = new RegExp("^["+fence+"]{3,}\\s*$");
      while(i<n && !fenceRe.test(lines[i])){ buf.push(lines[i]); i++; }
      i++;
      blocks.push({t:"c", lang:lang, x:buf}); continue;
    }

    m = line.match(/^(#{1,6})\\s+(.*)$/);
    if(m){
      var lvl = m[1].length;
      var c2 = m[2].replace(/^\\s+/,'').replace(/\\s+$/,'');
      if(lvl===1){ if(title===null){ title=c2; i++; continue; } lvl=2; }
      blocks.push({t:"h", l:lvl, x:c2}); i++; continue;
    }

    m = stripped.match(/^(---|\\*\\*\\*|___)\\s+(.+)$/);
    if(m){ blocks.push({t:"sd", n:null, label:m[2].replace(/^\\s+/,'').replace(/\\s+$/,'')}); i++; continue; }

    if(/^(---|\\*\\*\\*|___)\\s*$/.test(stripped)){ blocks.push({t:"hr"}); i++; continue; }

    if(stripped.charAt(0)===">"){
      var qbuf=[];
      while(i<n && lines[i].replace(/^\\s+/,'').replace(/\\s+$/,'')!=="" && lines[i].replace(/^\\s+/,'').charAt(0)===">"){
        qbuf.push(lines[i].replace(/^>\\s?/, "").replace(/\\s+$/,''));
        i++;
      }
      if(qbuf.length && /^\\[!([^\\]]+)\\]\\s*(.*)$/.test(qbuf[0])){
        var cm = qbuf[0].match(/^\\[!([^\\]]+)\\]\\s*(.*)$/);
        var rawLabel = cm[1].replace(/^\\s+/,'').replace(/\\s+$/,'');
        var rest = cm[2].replace(/^\\s+/,'').replace(/\\s+$/,'');
                if(rawLabel.toLowerCase()==="compare"){
          var cmpContent = (rest? [rest]:[]).concat(qbuf.slice(1));
          blocks.push({t:"cmp", x:cmpContent});
        } else {
          var content2 = (rest? [rest]:[]).concat(qbuf.slice(1));
          if(/^\\d{1,3}$/.test(rawLabel)){ blocks.push({t:"ins", n:rawLabel, x:content2}); }
          else { blocks.push({t:"co", label:rawLabel, x:content2}); }
        }
      } else {
        blocks.push({t:"q", x:qbuf});
      }
      continue;
    }

    m = stripped.match(/^SECTION\\s+(\\d{1,3})$/i);
    if(m){ blocks.push({t:"sd", n:m[1], label:null}); i++; continue; }

    if(stripped.indexOf("|")>=0 && i+1<n && /^\\s*\\|?[\\s:|-]+\\|?\\s*$/.test(lines[i+1])){
      var header = stripPipes(stripped).split("|");
      i+=2;
      var rows=[];
      while(i<n && lines[i].indexOf("|")>=0 && lines[i].replace(/^\\s+/,'').replace(/\\s+$/,'')!==""){
        rows.push(stripPipes(lines[i].replace(/^\\s+/,'').replace(/\\s+$/,'')).split("|"));
        i++;
      }
      blocks.push({t:"tb", h:header, r:rows}); continue;
    }

    if(/^(\\s*)([-*+]|\\d+[.)])\\s+/.test(line)){
      var ordered = /^\\s*\\d+[.)]\\s+/.test(line);
      var lbuf=[];
      while(i<n && /^(\\s*)([-*+]|\\d+[.)])\\s+/.test(lines[i])){
        lbuf.push(lines[i].replace(/^\\s*(?:[-*+]|\\d+[.)])\\s+/, "").replace(/\\s+$/,''));
        i++;
      }
      blocks.push({t:"l", o:ordered, x:lbuf}); continue;
    }

    m = stripped.match(/^!\\[([^\\]]*)\\]\\(([^)\\s]+)(?:\\s+"([^"]*)")?\\)$/);
    if(m){ blocks.push({t:"img", a:m[1], u:m[2]}); i++; continue; }

    var pbuf=[];
    while(i<n && lines[i].replace(/^\\s+/,'').replace(/\\s+$/,'')!==""
          && !/^(#{1,6})\\s+/.test(lines[i])
          && !/^(\\s*)([-*+]|\\d+[.)])\\s+/.test(lines[i])
          && lines[i].replace(/^\\s+/,'').charAt(0)!==">"
          && !/^(`{3,}|~{3,})/.test(lines[i])
          && !/^(---|\\*\\*\\*|___)\\s*$/.test(lines[i].replace(/^\\s+/,'').replace(/\\s+$/,''))){
      pbuf.push(lines[i].replace(/^\\s+/,'').replace(/\\s+$/,''));
      i++;
    }
    blocks.push({t:"p", x:pbuf.join(" ")});
  }
  return {title:title, blocks:blocks};
}

function renderBlock(b, s){
  if(b.t==='h'){
    var lv = (b.l>=2 && b.l<=6) ? b.l : 4;
    return '<section style="'+s.sec_head+'"><h'+lv+' style="'+s['h'+lv]+'">'+parseInline(b.x, s)+'</h'+lv+'></section>';
  }
  if(b.t==='p'){
    return '<section style="'+s.sec+'"><p style="'+s.p+'">'+parseInline(b.x, s)+'</p></section>';
  }
  if(b.t==='q'){
    var raw = b.x.join('\\n');
    var qkey = classifyQuote(raw);
    var parts = b.x.map(function(ln){ ln=ln.trim(); return ln==='' ? '<br>' : parseInline(ln, s); });
    var glyph = s.q_glyph || '';
    return '<section style="'+s[qkey]+'">'+glyph+parts.join('')+'</section>';
  }
  if(b.t==='c'){
    return '<section style="'+s.codeblock_sec+'"><code style="'+s.codeblock+'">'+esc(b.x.join('\\n'))+'</code></section>';
  }
  if(b.t==='l'){
    var tag = b.o ? 'ol' : 'ul';
    var li = b.x.map(function(it, idx){
      var content = parseInline(it, s);
      var bullet = b.o ? '<span style="'+s.li_bullet_ol+'">'+(idx+1)+'.</span>'
                       : '<span style="'+s.li_bullet_ul+'">•</span>';
      return '<li style="'+s.li+'">'+bullet+content+'</li>';
    });
    return '<section style="'+s.ul_sec+'"><'+tag+' style="'+s.ul+'">'+li.join('')+'</'+tag+'></section>';
  }
  if(b.t==='hr'){
    return '<section style="'+s.hr_sec+'"><span style="'+s.hr_inner+'"></span><span style="'+s.hr_dot+'">●</span><span style="'+s.hr_inner+'"></span></section>';
  }
  if(b.t==='sd'){
    var sdtxt = (b.label!=null && b.label!=='') ? b.label : (b.n!=null ? 'SECTION '+b.n : '');
    return '<section style="'+s.secdiv_sec+'"><span style="'+s.secdiv_rule+'"></span><span style="'+s.secdiv_txt+'">'+esc(sdtxt)+'</span><span style="'+s.secdiv_rule+'"></span></section>';
  }
  if(b.t==='co'){
    var parts = b.x.map(function(ln){ ln=ln.trim(); return ln==='' ? '<br>' : parseInline(ln, s); });
    return '<section style="'+s.callout_sec+'"><span style="'+s.callout_label+'">'+esc(b.label)+'</span><p style="'+s.p+'">'+parts.join('')+'</p></section>';
  }
  if(b.t==='ins'){
    var insTitle = b.x.length ? parseInline(b.x[0], s) : '';
    var insDesc = b.x.slice(1).map(function(ln){ ln=ln.trim(); return ln==='' ? '<br>' : parseInline(ln, s); }).join('');
    return '<section style="'+s.insight_sec+'"><table style="'+s.insight_tbl+'"><tr>'
      +'<td style="'+s.insight_num_cell+'"><span style="'+s.insight_num+'">'+esc(b.n)+'</span></td>'
      +'<td style="'+s.insight_body+'"><p style="'+s.insight_title+'">'+insTitle+'</p>'
      + (insDesc ? '<p style="'+s.insight_desc+'">'+insDesc+'</p>' : '')
      +'</td></tr></table></section>';
  }
  if(b.t==='cmp'){
    var x = b.x || [];
    var head = (x[0]||'').trim();
    var hp = head.indexOf('|')>=0 ? head.split('|') : [head, ''];
    var lh = hp[0].trim(), rh = hp.length>1 ? hp[1].trim() : '';
    var rows = [];
    for(var ri=1; ri<x.length; ri++){
      var ln = x[ri].trim(); if(ln==='') continue;
      var sp = ln.indexOf('|')>=0 ? ln.split('|') : [ln, ''];
      rows.push([sp[0].trim(), sp.length>1 ? sp[1].trim() : '']);
    }
    var o = '<section style="'+s.cmp_sec+'"><section style="'+s.cmp_card+'"><table style="'+s.cmp_tbl+'"><tr>'
      +'<td style="'+s.cmp_th+'">'+parseInline(lh, s)+'</td>'
      +'<td style="'+s.cmp_th2+'">'+parseInline(rh, s)+'</td></tr>';
    for(var rj=0; rj<rows.length; rj++){
      o += '<tr><td style="'+s.cmp_td+'">'+parseInline(rows[rj][0], s)+'</td>'
        +'<td style="'+s.cmp_td2+'">'+parseInline(rows[rj][1], s)+'</td></tr>';
    }
    o += '</table></section></section>';
    return o;
  }
  if(b.t==='tb'){
    var th = b.h.map(function(c){ return '<th style="'+s.th+'">'+parseInline(c.trim(), s)+'</th>'; }).join('');
    var body = b.r.map(function(r){ return '<tr>'+r.map(function(c){ return '<td style="'+s.td+'">'+parseInline(c.trim(), s)+'</td>'; }).join('')+'</tr>'; }).join('');
    return '<section style="'+s.table_sec+'"><table style="'+s.table+'"><thead><tr>'+th+'</tr></thead><tbody>'+body+'</tbody></table></section>';
  }
  if(b.t==='img'){
    return '<section style="'+s.img_sec+'"><img src="'+escAttr(b.u)+'" alt="'+escAttr(b.a)+'" style="'+s.img+'"></section>';
  }
  return '';
}

function renderAll(blocks, s){
  return '<section style="'+s.wrapper+'">'+blocks.map(function(b){ return renderBlock(b, s); }).join('\\n')+'</section>';
}

function toast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(function(){t.classList.remove('show');},1800);}

function applyCombo(color, variant){
  curColor = color; curFormat = variant;
  var s = STYLES[color][variant];
  var node = document.getElementById('wechat-body');
  node.innerHTML = renderAll(BLOCKS, s);
  var m = META[color];
  node.style.fontFamily = m.font; node.style.color = m.text; node.style.backgroundColor = m.bg;
  var cb = document.querySelectorAll('#colorBtns button');
  for(var i=0;i<cb.length;i++){ cb[i].classList.toggle('active', cb[i].getAttribute('data-color')===color); }
  var fb = document.querySelectorAll('#formatBtns button');
  for(var j=0;j<fb.length;j++){ fb[j].classList.toggle('active', fb[j].getAttribute('data-variant')===variant); }
}

function copyHTML(){
  var node=document.getElementById('wechat-body');
  var html=node.innerHTML, plain=node.innerText;
  function ok(m){toast(m);} function fail(){toast('复制失败，请手动框选复制');}
  if(navigator.clipboard && window.ClipboardItem){
    var item=new ClipboardItem({'text/html':new Blob([html],{type:'text/html'}),'text/plain':new Blob([plain],{type:'text/plain'})});
    navigator.clipboard.write([item]).then(function(){ok('✅ 已复制，去公众号后台粘贴吧');}).catch(function(){fallback();});
  } else { fallback(); }
  function fallback(){
    try{var r=document.createRange();r.selectNodeContents(node);var sel=window.getSelection();
      sel.removeAllRanges();sel.addRange(r);var ok2=document.execCommand('copy');sel.removeAllRanges();
      ok2?ok('✅ 已复制（兼容模式）'):fail();}catch(e){fail();}
  }
}
document.getElementById('copyBtn').addEventListener('click',copyHTML);
(function helpPop(){
  var btn=document.getElementById('helpBtn'), pop=document.getElementById('helpPop');
  if(!btn||!pop) return;
  function close(){ pop.classList.remove('open'); btn.setAttribute('aria-expanded','false'); }
  function toggle(e){ e.stopPropagation(); var on=!pop.classList.contains('open');
    pop.classList.toggle('open', on); btn.setAttribute('aria-expanded', on?'true':'false'); }
  btn.addEventListener('click', toggle);
  pop.addEventListener('click', function(e){ e.stopPropagation(); });
  document.addEventListener('click', close);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') close(); });
})();
document.getElementById('colorBtns').addEventListener('click',function(e){
  if(e.target && e.target.getAttribute('data-color')){ applyCombo(e.target.getAttribute('data-color'), curFormat); }
});
document.getElementById('formatBtns').addEventListener('click',function(e){
  if(e.target && e.target.getAttribute('data-variant')){ applyCombo(curColor, e.target.getAttribute('data-variant')); }
});
document.getElementById('editToggle').addEventListener('click',function(){
  document.body.classList.toggle('preview-only');
  if(document.body.classList.contains('preview-only')){ document.body.classList.remove('phone'); syncModeLabels(); }
  this.textContent = document.body.classList.contains('preview-only') ? '✏️ 编辑' : '👁 仅预览';
});
function syncModeLabels(){
  var ph=document.getElementById('phoneBtn'), tg=document.getElementById('editToggle');
  if(ph){ ph.textContent = document.body.classList.contains('phone') ? '💻 宽屏' : '📱 手机'; }
  if(tg){ tg.textContent = document.body.classList.contains('preview-only') ? '✏️ 编辑' : '👁 仅预览'; }
}
document.getElementById('phoneBtn').addEventListener('click',function(){
  var on=document.body.classList.toggle('phone');
  if(on){ document.body.classList.remove('preview-only'); }
  syncModeLabels();
});
(function resizer(){
  var split=document.getElementById('split');
  var rz=document.getElementById('resizer');
  if(!split||!rz) return;
  var dragging=false;
  function setPct(clientX){
    var rect=split.getBoundingClientRect();
    var pct=((clientX-rect.left)/rect.width)*100;
    if(pct<18) pct=18; if(pct>82) pct=82;
    split.style.setProperty('--edit-w', pct.toFixed(1)+'%');
  }
  function down(e){
    if(document.body.classList.contains('preview-only')||document.body.classList.contains('phone')) return;
    dragging=true; rz.classList.add('active');
    document.body.style.cursor='col-resize'; document.body.style.userSelect='none';
    if(e.cancelable) e.preventDefault();
  }
  function move(e){
    if(!dragging) return;
    var x = e.touches ? e.touches[0].clientX : e.clientX;
    setPct(x); if(e.cancelable) e.preventDefault();
  }
  function up(){ if(dragging){ dragging=false; rz.classList.remove('active'); document.body.style.cursor=''; document.body.style.userSelect=''; } }
  rz.addEventListener('mousedown',down);
  rz.addEventListener('touchstart',down,{passive:false});
  window.addEventListener('mousemove',move);
  window.addEventListener('touchmove',move,{passive:false});
  window.addEventListener('mouseup',up);
  window.addEventListener('touchend',up);
})();
function setTitle(t){ var el=document.getElementById('titleText'); if(el){ el.textContent = t ? t : '（未检测到标题，请在后台填写）'; } }
var editTimer=null;
document.getElementById('mdInput').addEventListener('input',function(){
  clearTimeout(editTimer);
  editTimer=setTimeout(function(){
    var ps=parseMarkdown(document.getElementById('mdInput').value);
    if(ps && ps.blocks){ BLOCKS=ps.blocks; }
    if(ps && ps.title){ setTitle(ps.title); }
    applyCombo(curColor, curFormat);
  },250);
});
(function init(){
  // 窄屏默认进入“仅预览”模式（编辑区在窄屏下单独全宽展示）
  if(window.innerWidth < 900){ document.body.classList.add('preview-only'); }
  if(typeof syncModeLabels==='function'){ syncModeLabels(); }
  var ta=document.getElementById('mdInput');
  if(ta){ ta.value = (SOURCE==null?'':SOURCE); }
  var ps=parseMarkdown(SOURCE==null?'':SOURCE);
  if(ps && ps.blocks && ps.blocks.length){ BLOCKS=ps.blocks; }
  if(ps && ps.title){ setTitle(ps.title); }
  applyCombo(DEF_COLOR, DEF_FORMAT);
})();
__EXTRA_JS__
</script>
</body>
</html>
"""


def _safe_json(obj):
    """转 JSON 并防止 </script> 截断页面。"""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# 独立编辑器（--app）内置的示例文档：覆盖全部块类型，作为首次打开的引导。
APP_SAMPLE_MD = """# 公众号排版编辑器（示例）

这是 **公众号排版** 的在线编辑器。左侧写 Markdown，右侧实时预览；顶部切换「配色 × 结构格式」自由组合，满意后点「📋 复制正文」到后台粘贴即可。

> [!核心判断] 本页 100% 在浏览器里完成转换，不依赖服务器，也可离线使用。

--- 怎么写分栏

单独一行写 `--- 任意文字` 就能插入一条带文字的分栏线，文字随便改（旧的 `SECTION 01` 也仍然可用）。

> [!01] 标签卡片
用 `> [!标签] 内容` 写带小标签的强调卡片，区别于普通引用。

> [!02] 编号洞察卡
用 `> [!01] 标题` 写「大号数字 + 标题 + 描述」的卡片。

> [!compare] 过去写法 | 现在写法
> 纯文字堆砌 | 结构化卡片
> 复制进后台对不齐 | 内联样式粘贴即所见

| 能力 | 说明 |
| --- | --- |
| 编辑 + 预览 | 左写右看，实时刷新 |
| 配色 × 格式 | 10×10 共 100 种组合 |
| 一键复制 | 内联样式，粘贴保格式 |

1. 支持有序列表
2. 支持 `行内代码`
3. 支持 [链接](https://example.com)

> 普通引用会自动按关键词分色（蓝 / 橙 / 绿）。

点顶部「📂 打开」可载入本地 .md 文件；你的草稿会自动保存在本机浏览器里。
"""

# 独立编辑器（--app）专属的前端逻辑：打开本地 .md、新建空白、草稿自动保存。
STANDALONE_JS = r"""
// ===== 独立编辑器专属：打开 / 新建 / 草稿自动保存 =====
var STANDALONE = true;
var STORAGE_KEY = 'wxmd_draft_v1';
function _saveDraft(){ try{ localStorage.setItem(STORAGE_KEY, document.getElementById('mdInput').value); }catch(e){} }
function _loadDraft(){ try{ var d=localStorage.getItem(STORAGE_KEY); return (d===null)?null:d; }catch(e){ return null; } }
// 打开本地文件
(function(){
  var fi=document.getElementById('fileInput'); if(!fi) return;
  fi.addEventListener('change', function(e){
    var f=e.target.files && e.target.files[0]; if(!f) return;
    var r=new FileReader();
    r.onload=function(){
      var ta=document.getElementById('mdInput'); ta.value=r.result;
      var ps=parseMarkdown(r.result); if(ps&&ps.blocks){ BLOCKS=ps.blocks; } if(ps&&ps.title){ setTitle(ps.title); }
      applyCombo(curColor, curFormat); _saveDraft(); toast('已载入 '+f.name);
    };
    r.readAsText(f);
    e.target.value='';
  });
})();
(function(){
  var ob=document.getElementById('openBtn'); if(ob){ ob.addEventListener('click', function(){ document.getElementById('fileInput').click(); }); }
  var nb=document.getElementById('newBtn'); if(nb){ nb.addEventListener('click', function(){
    if(!confirm('清空当前内容，新建空白文章？')) return;
    var ta=document.getElementById('mdInput'); ta.value=''; BLOCKS=[]; setTitle(''); applyCombo(curColor, curFormat); _saveDraft();
  }); }
})();
// 输入即自动保存（与已有 input 监听并行，不冲突）
(function(){
  var ta=document.getElementById('mdInput'); if(!ta) return;
  ta.addEventListener('input', function(){ _saveDraft(); });
})();
// 优先恢复上次草稿
(function(){
  var d=_loadDraft();
  if(d!==null && d!==''){
    var ta=document.getElementById('mdInput'); if(ta){ ta.value=d; }
    var ps=parseMarkdown(d); if(ps&&ps.blocks){ BLOCKS=ps.blocks; } if(ps&&ps.title){ setTitle(ps.title); } applyCombo(curColor, curFormat);
  }
})();
"""


def build_preview(title, blocks_json, styles_json, meta_json,
                  default_color, default_format, default_body, md_source,
                  standalone=False):
    color_btns = "".join(
        f'<button data-color="{c}" class="{"active" if c == default_color else ""}">'
        f'{COLOR_LABELS[c]}</button>'
        for c in COLOR_ORDER
    )
    format_btns = "".join(
        f'<button data-variant="{v}" class="{"active" if v == default_format else ""}">'
        f'{VARIANT_LABELS[v]}</button>'
        for v in VARIANT_ORDER
    )
    title_html = title if title else "（未检测到标题，请在后台填写）"

    if standalone:
        extra_btns = (
            '<button class="mode" id="openBtn">📂 打开</button>'
            '<button class="mode" id="newBtn">🆕 新建</button>'
        )
        extra_js = STANDALONE_JS
    else:
        extra_btns = ""
        extra_js = ""

    return (
        PREVIEW_TMPL
        .replace("__SANS__", SANS)
        .replace("__TITLE__", title_html)
        .replace("__COLOR_BTNS__", color_btns)
        .replace("__FORMAT_BTNS__", format_btns)
        .replace("__EXTRA_BTNS__", extra_btns)
        .replace("__DEF_FONT__", COLORS[default_color]["font"])
        .replace("__DEF_TEXT__", COLORS[default_color]["text"])
        .replace("__DEF_BG__", COLORS[default_color]["body_bg"])
        .replace("__DEF_BODY__", default_body)
        .replace("__BLOCKS_JSON__", _safe_json(blocks_json))
        .replace("__MD_SOURCE_JSON__", _safe_json(md_source))
        .replace("__STYLES_JSON__", _safe_json(styles_json))
        .replace("__META_JSON__", _safe_json(meta_json))
        .replace("__COLOR_ORDER_JSON__", _safe_json(COLOR_ORDER))
        .replace("__VARIANT_ORDER_JSON__", _safe_json(VARIANT_ORDER))
        .replace("__COLOR_LABELS_JSON__", _safe_json(COLOR_LABELS))
        .replace("__VARIANT_LABELS_JSON__", _safe_json(VARIANT_LABELS))
        .replace("__DEF_COLOR__", json.dumps(default_color))
        .replace("__DEF_FORMAT__", json.dumps(default_format))
        .replace("__Q_EDITOR_JSON__", _safe_json(QUOTE_EDITOR_KEYWORDS))
        .replace("__Q_ANCIENT_JSON__", _safe_json(QUOTE_ANCIENT_KEYWORDS))
        .replace("__EXTRA_JS__", extra_js)
    )


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Markdown -> 公众号排版 HTML（配色 × 格式 自由组合）")
    ap.add_argument("input", nargs="?", help="输入的 Markdown 文件路径")
    ap.add_argument("-o", "--output", help="输出预览 HTML 路径（默认: <输入名>.wechat.html）")
    ap.add_argument("--title", help="自定义标题（覆盖检测到的首个 H1）")
    ap.add_argument("--theme", default=DEFAULT_COLOR, choices=COLOR_ORDER,
                    help="默认配色方案（预览页可继续切换组合）")
    ap.add_argument("--format", default=DEFAULT_FORMAT, choices=VARIANT_ORDER,
                    help="默认结构格式（预览页可继续切换组合）")
    ap.add_argument("--list-themes", action="store_true", help="列出全部配色与格式并退出")
    ap.add_argument("--app", action="store_true",
                    help="生成独立编辑器（不绑定单篇文章：内置示例文档、支持打开本地 .md、草稿自动保存）")
    ap.add_argument("--serve", metavar="DIR",
                    help="在指定目录启动本地静态服务（用于托管独立编辑器，获得最佳剪贴板支持）")
    args = ap.parse_args()

    if args.serve:
        import http.server
        import socketserver
        d = os.path.abspath(args.serve)
        if not os.path.isdir(d):
            sys.exit(f"[错误] 目录不存在: {d}")
        os.chdir(d)
        port = 8000
        handler = http.server.SimpleHTTPRequestHandler
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"[服务] 已启动: http://localhost:{port}  (Ctrl+C 停止)")
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[服务] 已停止。")
        return

    if args.list_themes:
        print("配色方案（--theme）：")
        for c in COLOR_ORDER:
            print(f"  {c:8s} - {COLOR_LABELS[c]}")
        print("\n结构格式（--format）：")
        for v in VARIANT_ORDER:
            print(f"  {v:8s} - {VARIANT_LABELS[v]}  ({VARIANT_DESC[v]})")
        print(f"\n共 {len(COLOR_ORDER)}×{len(VARIANT_ORDER)} = {len(COLOR_ORDER)*len(VARIANT_ORDER)} 种组合。")
        return

    if args.app:
        md_text = APP_SAMPLE_MD
        default_style = STYLES[(args.theme, args.format)]
        title, default_body = convert(md_text, default_style)
        _, blocks_json = build_blocks_json(md_text)
        styles_json = {
            c: {v: STYLES[(c, v)] for v in VARIANT_ORDER}
            for c in COLOR_ORDER
        }
        meta_json = {
            c: {"font": COLORS[c]["font"], "text": COLORS[c]["text"], "bg": COLORS[c]["body_bg"]}
            for c in COLOR_ORDER
        }
        preview = build_preview(title, blocks_json, styles_json, meta_json,
                                args.theme, args.format, default_body, md_text,
                                standalone=True)
        out_path = args.output or "wechat-app.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(preview)
        print(f"[完成] 独立编辑器已生成: {out_path}")
        print(f"        默认组合: 配色 {args.theme}({COLOR_LABELS[args.theme]}) × "
              f"格式 {args.format}({VARIANT_LABELS[args.format]})")
        print(f"        用法: python3 build_wechat_html.py --serve .   然后浏览器打开 http://localhost:8000/{os.path.basename(out_path)}")
        return

    if not args.input:
        sys.exit("[错误] 未指定输入文件。用法: build_wechat_html.py input.md [选项]")
    if not os.path.exists(args.input):
        sys.exit(f"[错误] 找不到输入文件: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    default_style = STYLES[(args.theme, args.format)]
    title, default_body = convert(md_text, default_style)
    if args.title:
        title = esc_text(args.title)
    _, blocks_json = build_blocks_json(md_text)

    styles_json = {
        c: {v: STYLES[(c, v)] for v in VARIANT_ORDER}
        for c in COLOR_ORDER
    }
    meta_json = {
        c: {"font": COLORS[c]["font"], "text": COLORS[c]["text"], "bg": COLORS[c]["body_bg"]}
        for c in COLOR_ORDER
    }

    preview = build_preview(title, blocks_json, styles_json, meta_json,
                            args.theme, args.format, default_body, md_text)

    out_path = args.output or (os.path.splitext(args.input)[0] + ".wechat.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(preview)

    print(f"[完成] 预览文件已生成: {out_path}")
    print(f"        标题: {title or '(无)'}")
    print(f"        默认组合: 配色 {args.theme}({COLOR_LABELS[args.theme]}) × "
          f"格式 {args.format}({VARIANT_LABELS[args.format]})")
    print(f"        可组合总数: {len(COLOR_ORDER)}×{len(VARIANT_ORDER)} = "
          f"{len(COLOR_ORDER)*len(VARIANT_ORDER)}（预览页两组选择器实时切换）")


if __name__ == "__main__":
    main()
