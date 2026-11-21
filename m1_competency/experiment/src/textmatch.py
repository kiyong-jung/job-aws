"""이름 비교 도우미 (계산 기반, LLM 아님)."""
import re


def norm(t):
    return re.sub(r"[\s·・,()\-/]", "", str(t)).lower()


def bigrams(t):
    t = norm(t)
    return {t[i:i + 2] for i in range(len(t) - 1)} or {t}


def dice(a, b):
    x, y = bigrams(a), bigrams(b)
    return 2 * len(x & y) / (len(x) + len(y)) if (x or y) else 0.0


def cohen_kappa(a, b):
    """두 사람 라벨 목록의 Cohen's κ."""
    n = len(a)
    labels = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0
