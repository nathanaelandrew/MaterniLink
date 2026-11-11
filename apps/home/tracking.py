"""Server-side SVG chart geometry for the mother's trends page.

Everything is returned as pre-formatted strings so that templates never
have to do arithmetic (and a comma-decimal locale can never break an SVG).
"""
import math

W, H = 640, 260
PL, PR, PT, PB = 46, 18, 18, 34          # plot-area padding


def _f(v):
    return f"{v:.1f}"


def _label(v):
    return f"{v:g}"


def _nice_ticks(lo, hi, n=4):
    raw = max(hi - lo, 1e-9) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    end = math.ceil(hi / step) * step
    ticks, v = [], start
    while v <= end + 1e-9:
        ticks.append(round(v, 6))
        v += step
    return ticks


def _x_labels(positions, texts, max_labels=5):
    n = len(texts)
    if n == 0:
        return []
    if n <= max_labels:
        idx = range(n)
    else:
        idx = sorted({round(i * (n - 1) / (max_labels - 1)) for i in range(max_labels)})
    return [{'x': _f(positions[i]), 'text': texts[i]} for i in idx]


def _frame(ticks, sy, W, H):
    return {
        'w': W, 'h': H,
        'pl': _f(PL), 'pr': _f(W - PR), 'pt': _f(PT), 'pb': _f(H - PB),
        'tick_x': _f(PL - 8), 'label_y': _f(H - 10),
        'yticks': [{'y': _f(sy(t)), 'text': _label(t)} for t in ticks],
    }


def line_chart(dates, series, refs=(), min_span=10, area=False, W=W, H=H):
    """dates: list[date]; series: [{'name','cls','values','flags'(optional)}];
    refs: [(y_value, text)] dashed reference lines."""
    PW, PH = W - PL - PR, H - PT - PB
    values = [v for s in series for v in s['values']] + [r[0] for r in refs]
    lo, hi = min(values), max(values)
    if hi - lo < min_span:
        mid = (hi + lo) / 2
        lo, hi = mid - min_span / 2, mid + min_span / 2
    ticks = _nice_ticks(lo, hi)
    ymin, ymax = ticks[0], ticks[-1]

    def sy(v):
        return PT + PH * (1 - (v - ymin) / (ymax - ymin))

    n = len(dates)
    span = (dates[-1] - dates[0]).days if n > 1 else 0
    if n == 1:
        xs = [PL + PW / 2]
    elif span == 0:
        xs = [PL + PW * i / (n - 1) for i in range(n)]
    else:
        xs = [PL + PW * (d - dates[0]).days / span for d in dates]

    chart = _frame(ticks, sy, W, H)
    chart['xlabels'] = _x_labels(xs, [d.strftime('%b %d').replace(' 0', ' ') for d in dates])
    chart['refs'] = [{'y': _f(sy(v)), 'text': t, 'text_y': _f(sy(v) - 5)} for v, t in refs]
    chart['series'] = []
    for s in series:
        ys = [sy(v) for v in s['values']]
        flags = s.get('flags') or [False] * n
        path = ' '.join(f"{'M' if i == 0 else 'L'}{_f(x)} {_f(y)}" for i, (x, y) in enumerate(zip(xs, ys)))
        area_path = ''
        if area and n > 1:
            area_path = f"{path} L{_f(xs[-1])} {_f(H - PB)} L{_f(xs[0])} {_f(H - PB)} Z"
        chart['series'].append({
            'name': s['name'], 'cls': s['cls'], 'path': path, 'area': area_path,
            'points': [{
                'x': _f(x), 'y': _f(y), 'flag': flag,
                'tip': f"{d.strftime('%b %d, %Y')}: {_label(v)} {s.get('unit', '')}".strip(),
            } for x, y, v, d, flag in zip(xs, ys, s['values'], dates, flags)],
        })
    return chart


def bar_chart(items, goal=None, W=W, H=H):
    """items: [(label, value, tooltip)]; goal draws a dashed line and colours bars that reach it."""
    PW, PH = W - PL - PR, H - PT - PB
    top = max([v for _, v, _ in items] + [goal or 0, 5])
    ticks = _nice_ticks(0, top)
    ymax = ticks[-1]

    def sy(v):
        return PT + PH * (1 - v / ymax)

    n = len(items)
    slot = PW / n
    bw = min(38, slot * 0.6)
    bars, centers = [], []
    for i, (label, v, tip) in enumerate(items):
        cx = PL + slot * (i + 0.5)
        centers.append(cx)
        top_y = sy(v)
        bars.append({
            'x': _f(cx - bw / 2), 'y': _f(top_y), 'w': _f(bw),
            'h': _f(max(0, (H - PB) - top_y)), 'tip': tip,
            'met': goal is not None and v >= goal,
        })
    chart = _frame(ticks, sy, W, H)
    chart['bars'] = bars
    chart['xlabels'] = _x_labels(centers, [i[0] for i in items], max_labels=10)
    chart['goal'] = (
        {'y': _f(sy(goal)), 'text_y': _f(sy(goal) - 5), 'text': f"Goal: {goal}"}
        if goal is not None else None
    )
    return chart