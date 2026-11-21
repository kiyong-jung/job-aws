"""m2_project/assets/ 의 성능 그림. 숫자는 모두 research/ 의 result.md 에서 옮겼다 (출처는 그림마다 주석)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

fm.fontManager.addfont("/System/Library/Fonts/AppleSDGothicNeo.ttc")
plt.rcParams["font.family"] = "Apple SD Gothic Neo"
OUT = Path("m2_project/assets")
OUT.mkdir(exist_ok=True)
INK, MUTE, SURF, GRID, AXIS = "#0b0b0b", "#52514e", "#fcfcfb", "#ebebe7", "#d0d0cc"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"


def frame(ax, top, title=None):
    ax.set_facecolor(SURF)
    ax.set_ylim(0, top)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(axis="y", colors=MUTE, length=0, labelsize=9)
    ax.tick_params(axis="x", colors=INK, length=0, labelsize=10.5)
    ax.grid(axis="y", color=GRID, zorder=0)
    if title:
        ax.set_title(title, loc="left", fontsize=11.5, color=INK, fontweight="bold", pad=10)


def grouped(ax, groups, series, top, fmt, width=0.8):
    """series = [(이름, 값 목록, 색)]. 막대 사이 2px 틈, 값은 막대 위에 글 색으로."""
    x = np.arange(len(groups))
    n = len(series)
    w = width / n
    for j, (name, vals, color) in enumerate(series):
        pos = x - width / 2 + w * (j + 0.5)
        bars = ax.bar(pos, vals, w * 0.92, color=color, label=name, zorder=2)
        for b, v in zip(bars, vals):
            if v is not None:
                ax.text(b.get_x() + b.get_width() / 2, v + top * 0.012, fmt(v), ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(x, groups)
    frame(ax, top)


def human_line(ax, y, x0, x1, label):
    ax.plot([x0, x1], [y, y], ls=(0, (4, 3)), color=INK, lw=1.3, zorder=3)
    ax.text(x1, y + 0.015, label, ha="right", va="bottom", fontsize=9, color=INK)


def legend_below(ax, ncol):
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=ncol, labelcolor=INK)


def header(fig, title, sub):
    fig.text(0.012, 0.975, title, fontsize=14, color=INK, fontweight="bold", va="top")
    fig.text(0.012, 0.915, sub, fontsize=10, color=MUTE, va="top", linespacing=1.4)


def save(fig, name):
    fig.savefig(OUT / name, dpi=160, facecolor=SURF)
    plt.close(fig)


# 0. 한 페이지 요약 (rq4d/result.md v3 @50, rq5/result.md, rq4b/report_for_user.md, rq4b/gold/rubric.md)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), facecolor=SURF, gridspec_kw={"width_ratios": [1.25, 1]})
header(fig, "같은 판정 비용으로 역량을 더 찾고, 판정은 Human에 더 가까워졌다",
       "공고 4건 · DB 논문 7.6만 + 저장소 2.2만 (11/17 고정본) · 판정 모델 Claude Sonnet 4.6 · 두 방식 모두 지금 판정기(v3)로 다시 잼")
grouped(axes[0], ["50개 판정", "100개", "200개"],
        [("예전 방식 (검색어 8개 + BM25)", [68, 76, 80], BLUE), ("지금 방식 (역량별 검색어 + Cohere 다시 고르기)", [82, 85, 86], ORANGE)],
        100, lambda v: f"{v}")
axes[0].axhline(87, color=MUTE, lw=1, ls=":", zorder=1)
axes[0].text(-0.42, 88.5, "덮을 수 있는 87개", ha="left", fontsize=9, color=MUTE)
axes[0].set_title("① 찾은 역량 수 (판정한 후보 안에 '있음'이 하나라도)", loc="left", fontsize=11.5, color=INK, fontweight="bold", pad=10)
legend_below(axes[0], 1)
grouped(axes[1], ["논문 30쌍", "저장소 30쌍"],
        [("처음 판정기 (900자만 봄)", [0.44, 0.32], BLUE), ("지금 판정기 v3 (README + 조각별 검사)", [0.44, 0.67], ORANGE)],
        1.05, lambda v: f"{v:.2f}", width=0.6)
human_line(axes[1], 0.948, -0.38, 0.38, "Human A 대 B 0.95")
human_line(axes[1], 0.880, 0.62, 1.38, "Human A 대 B 0.88")
axes[1].set_title("② 판정이 Human 기준 답과 맞는 정도 (κ)", loc="left", fontsize=11.5, color=INK, fontweight="bold", pad=10)
legend_below(axes[1], 1)
fig.subplots_adjust(left=0.05, right=0.985, top=0.76, bottom=0.25, wspace=0.18)
save(fig, "fig0_summary.png")

# 1. 실험 1 역량별 검색어 (rq5/result.md, 판정기 v2, 덮을 수 있는 86)
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURF)
header(fig, "실험 1. 검색어를 역량마다 하나씩 만들면 놓치는 역량이 준다",
       "예전: 공고 전체를 보고 검색어 8개 → 자주 나오는 주제에 몰림 · 지금: 역량마다 논문·저장소 검색어 1개씩\n"
       "나머지(BM25, 판정)는 같음 · 공고 4건, 판정기 v2, 덮을 수 있는 86개 중 찾은 수")
grouped(ax, ["50개 판정", "100개", "200개"],
        [("예전 방식 (검색어 8개)", [68, 75, 80], BLUE), ("역량마다 검색어 (RQ1)", [74, 80, 84], AQUA)], 100, lambda v: f"{v}", width=0.6)
legend_below(ax, 2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.72, bottom=0.17)
save(fig, "fig1_queries.png")

# 2. 실험 2 다시 고르기 (rq2b/result.md, 판정기 v1, 덮을 수 있는 83, 200개 판정)
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURF)
header(fig, "실험 2. 넓게 모은 뒤 역량마다 다시 고르면 더 찾는다. 단, 1,000개까지 넓게",
       "BM25 키워드 순위 위 N개를 역량마다 다른 모델로 다시 줄 세운 뒤 합쳐 200개 판정\n"
       "공고 4건, 판정기 v1, 덮을 수 있는 83개 중 찾은 수 · 판정기 흔들림 약 ±3")
names = ["BM25 만\n(예전 방식)", "Titan 임베딩\n위 1,000개", "Cohere Rerank\n위 400개", "Cohere Rerank\n위 1,000개 (채택)"]
vals, cols = [75, 75, 76, 79], [BLUE, YELLOW, MAGENTA, ORANGE]
bars = ax.bar(range(4), vals, 0.56, color=cols, zorder=2)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v}", ha="center", va="bottom", fontsize=10, color=INK)
ax.set_xticks(range(4), names)
frame(ax, 90)
ax.axhline(83, color=MUTE, lw=1, ls=":", zorder=1)
ax.text(-0.3, 84, "덮을 수 있는 83개", ha="left", fontsize=9, color=MUTE)
fig.subplots_adjust(left=0.06, right=0.98, top=0.72, bottom=0.14)
save(fig, "fig2_rerank.png")

# 3. 실험 3 판정기에 무엇을 보여 주나 (rq4b/report_for_user.md, 각 단계 2회 실행)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), facecolor=SURF)
header(fig, "실험 3. 저장소는 README 를 보여 주면 판정이 크게 나아진다. 논문은 길게 보여 줘도 그대로",
       "같은 판정 모델(Sonnet 4.6)에 보여 주는 글만 바꿈 · 막대 = 두 번 실행 평균, 점 = 각 실행 · Human 기준 답 30쌍과의 κ")
for ax, groups, runs, top_h, title in (
        (axes[0], ["초록 앞 900자\n(지금)", "초록 전체", "초록 + 본문\n24,000자"], [(0.59, 0.29), (0.25, 0.44), (0.34, 0.30)], 0.948, "논문"),
        (axes[1], ["이름·설명\n(처음)", "+ README\n4,000자 (지금)", "+ 판정기가 파일을\n골라 읽음"], [(0.32, 0.32), (0.62, 0.58), (0.62, 0.44)], 0.880, "저장소")):
    means = [sum(r) / 2 for r in runs]
    colors = [BLUE, AQUA, YELLOW] if title == "논문" else [BLUE, ORANGE, YELLOW]
    if title == "논문":
        colors = [ORANGE, AQUA, YELLOW]
    bars = ax.bar(range(3), means, 0.55, color=colors, zorder=2)
    for i, (b, m, r) in enumerate(zip(bars, means, runs)):
        ax.scatter([i - 0.08, i + 0.08], r, s=26, color=INK, zorder=4, edgecolors=SURF, linewidths=1)
        ax.text(b.get_x() + b.get_width() / 2, max(r) + 0.03, f"{m:.2f}", ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(range(3), groups)
    frame(ax, 1.05, title)
    human_line(ax, top_h, -0.4, 2.4, f"Human A 대 B {top_h:.2f}")
fig.subplots_adjust(left=0.05, right=0.985, top=0.78, bottom=0.16, wspace=0.15)
save(fig, "fig3_shown.png")

# 4. 실험 4 조각별 근거 검사 (rq4d/result.md, 60쌍)
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURF)
header(fig, "실험 4. 근거 구절을 조각별로 확인하면 저장소 판정이 더 맞는다",
       "판정기는 긴 README 에서 구절을 '…' 로 줄여 인용한다. 예전 검사는 글자 그대로만 인정해 맞는 판정도 깎았다\n"
       "지금: 조각(3낱말 이상)이 원문에 차례대로 모두 있으면 인정 · 호출·비용 그대로 · Human 기준 답과의 κ")
grouped(ax, ["전체 60쌍", "논문 30쌍", "저장소 30쌍"],
        [("글자 그대로 검사 (v2)", [0.517, 0.440, 0.598], AQUA), ("조각별 검사 (v3, 지금)", [0.551, 0.440, 0.668], ORANGE)],
        1.05, lambda v: f"{v:.2f}", width=0.6)
for x, y in ((0, 0.918), (1, 0.948), (2, 0.880)):
    human_line(ax, y, x - 0.32, x + 0.32, f"Human A 대 B {y:.2f}")
legend_below(ax, 2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.72, bottom=0.17)
save(fig, "fig4_quote.png")

# 5. 합친 결과와 기각한 섞기 (rq5/result.md, 판정기 v2, 덮을 수 있는 86)
fig, ax = plt.subplots(figsize=(12, 5.2), facecolor=SURF)
header(fig, "합친 결과. 역량별 검색어와 Cohere 다시 고르기를 함께 쓰면 50개 판정에서 13개를 더 찾는다",
       "같은 판정기(v2)로 모든 방법을 다시 잼 · 공고 4건, 덮을 수 있는 86개 중 찾은 수 · 판정기 흔들림 약 ±5 (200개 기준)\n"
       "Titan 벡터 검색을 섞은 방법은 100개에서 하나 더 찾지만 흔들림 안이고 단계가 늘어 기각 (50개에서는 1개 적음)")
grouped(ax, ["50개 판정", "100개", "200개"],
        [("예전 방식", [68, 75, 80], BLUE), ("역량별 검색어", [74, 80, 84], AQUA), ("Cohere 다시 고르기", [77, 82, 83], MAGENTA),
         ("둘 다 (채택)", [81, 85, 86], ORANGE), ("BM25 + Titan 순위 합", [76, 78, 85], YELLOW), ("BM25·Titan 섞어 + Cohere", [80, 86, 86], VIOLET)],
        100, lambda v: f"{v}", width=0.86)
legend_below(ax, 6)
fig.subplots_adjust(left=0.045, right=0.985, top=0.75, bottom=0.15)
save(fig, "fig5_combined.png")

# 6. 판정 모델 비교 (judge/result.md, 옛 기준 답 40쌍, 95% 구간 = 2,000번 되뽑기)
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURF)
header(fig, "판정 모델 비교. Sonnet 4.6 을 뚜렷이 넘는 모델이 없어 그대로 쓴다",
       "같은 지시문으로 모델만 바꿈 · 회사 계정 Bedrock 에서 부를 수 있는 모델 · Human 기준 답 40쌍(짧은 글로 단 것)과의 κ\n"
       "선 = 95% 구간 (40쌍을 2,000번 되뽑음). 구간이 서로 크게 겹쳐, 차이는 대부분 우연 범위")
models = ["Sonnet 4.6\n(지금)", "Kimi K3", "Kimi K3.1", "Opus 4.6", "Haiku 4.5"]
k = [0.477, 0.471, 0.433, 0.361, 0.279]
lo = [0.24, 0.27, 0.22, 0.15, 0.10]
hi = [0.69, 0.66, 0.65, 0.57, 0.48]
cols = [ORANGE, AQUA, YELLOW, MAGENTA, VIOLET]
bars = ax.bar(range(5), k, 0.5, color=cols, zorder=2)
ax.vlines(range(5), lo, hi, color=MUTE, lw=1.4, zorder=3)
for b, v in zip(bars, k):
    ax.text(b.get_x() + b.get_width() + 0.03, v, f"{v:.2f}", ha="left", va="center", fontsize=9.5, color=INK)
ax.set_xticks(range(5), models)
frame(ax, 1.0)
human_line(ax, 0.85, -0.4, 4.4, "Human A 대 B 0.85")
fig.subplots_adjust(left=0.06, right=0.98, top=0.72, bottom=0.14)
save(fig, "fig6_judges.png")
print("ok")
