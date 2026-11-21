import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

fm.fontManager.addfont("/System/Library/Fonts/AppleSDGothicNeo.ttc")
plt.rcParams["font.family"] = "Apple SD Gothic Neo"
INK, MUTE, SURF, LINE = "#0b0b0b", "#52514e", "#fcfcfb", "#9a9994"
KIND = {"code": ("#f0efec", "#8a8a85", "코드"),
        "llm": ("#dcebfc", "#2a78d6", "LLM (Claude Sonnet 4.6)"),
        "rerank": ("#fde6da", "#eb6834", "Reranker (Cohere Rerank 3.5)")}
steps = [
    ("공고 읽기", "공고 문장과 역량 목록", "code", "공고 1건", False),
    ("검색어 만들기", "역량마다 논문·저장소 검색어 1개씩", "llm", "검색어 55~70개", True),
    ("넓게 모으기", "BM25 키워드 검색", "code", "11만 → 1,000개", False),
    ("역량별로 다시 고르기", "역량 문장과 뜻이 맞는 차례로", "rerank", "1,000 → 100개", True),
    ("판정", "있음·일부·없음 + 근거 구절 (저장소는 README 까지)", "llm", "100개 × 역량", True),
    ("샘플 고르기", "필수를 다 덮는 후보 중 1위 (필수 → 우대 → 나머지)", "code", "샘플 1개", True),
    ("응용", "보완 프로젝트에서 빌려 우대·나머지를 더함", "llm", "프로젝트 1개", True),
]
ROW, BOX_H, X0, BW = 1.5, 1.12, 0.9, 6.6
fig, ax = plt.subplots(figsize=(10, 12.2), facecolor=SURF)
n = len(steps)
ax.set_xlim(0, 10)
ax.set_ylim(-0.25, n * ROW + 1.5)
ax.axis("off")
ax.text(0.1, n * ROW + 1.35, "공고 → 따라 만들 프로젝트 하나", fontsize=24, color=INK, fontweight="bold", va="top")
lx = 0.1
for kind, step in (("code", 1.3), ("llm", 3.6), ("rerank", 0)):
    fill, edge, label = KIND[kind]
    ax.add_patch(FancyBboxPatch((lx, n * ROW + 0.32), 0.34, 0.26, boxstyle="round,pad=0.01,rounding_size=0.05", fc=fill, ec=edge, lw=1.8))
    ax.text(lx + 0.46, n * ROW + 0.45, label, fontsize=13, color=INK, va="center")
    lx += step
for i, (title, body, kind, count, changed) in enumerate(steps):
    y = (n - 1 - i) * ROW
    fill, edge, _ = KIND[kind]
    ax.add_patch(FancyBboxPatch((X0, y), BW, BOX_H, boxstyle="round,pad=0.02,rounding_size=0.14", fc=fill, ec=edge, lw=2.2))
    ax.text(0.42, y + BOX_H / 2, str(i + 1), fontsize=22, color=edge, fontweight="bold", ha="center", va="center")
    ax.text(X0 + 0.25, y + BOX_H - 0.2, title, fontsize=19, color=INK, fontweight="bold", va="top")
    if changed:
        ax.text(X0 + BW - 0.2, y + BOX_H - 0.22, "연구로 바꿈", fontsize=12, color=edge, fontweight="bold", va="top", ha="right")
    ax.text(X0 + 0.25, y + BOX_H - 0.66, body, fontsize=14, color=MUTE, va="top", linespacing=1.35)
    ax.text(X0 + BW + 0.3, y + BOX_H / 2, count, fontsize=16, color=INK, fontweight="bold", va="center")
    if i < n - 1:
        ax.annotate("", xy=(X0 + BW / 2, y - (ROW - BOX_H) + 0.04), xytext=(X0 + BW / 2, y - 0.04),
                    arrowprops=dict(arrowstyle="-|>", color=LINE, lw=2, mutation_scale=18))
ax.text(X0 + BW + 0.3, n * ROW - 0.1, "남는 것", fontsize=13, color=MUTE, va="bottom")
fig.tight_layout(pad=0.5)
fig.savefig("m2_project/assets/fig_pipeline.png", dpi=150, facecolor=SURF)
