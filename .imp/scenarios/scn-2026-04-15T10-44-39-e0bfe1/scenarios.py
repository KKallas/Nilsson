from datetime import date, timedelta


def _build_chart(data, title):
    """Build a Plotly-compatible Gantt dict from enriched issues."""
    xs, ys, bases, colors = [], [], [], []
    for issue in data["issues"]:
        dur = get_field(issue, "duration_days", default=3)
        start = get_field(issue, "start_date")
        end = get_field(issue, "end_date")
        if start is None and end is None:
            continue
        if start is None:
            start = str(date.fromisoformat(end) - timedelta(days=dur))
        if end is None:
            end = str(date.fromisoformat(start) + timedelta(days=dur))
        label = f"#{issue['number']}  {issue['title'][:48]}"
        bases.append(start)
        xs.append(dur)
        ys.append(label)
        color = "#10b981" if issue.get("state") == "CLOSED" else "#3b82f6"
        colors.append(color)

    figure = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": xs,
                "y": ys,
                "base": bases,
                "marker": {"color": colors},
            }
        ],
        "layout": {
            "title": {"text": title},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    return figure


def _compute_metrics(data, out):
    """Derive duration / finish-date / blockers from the issue set."""
    earliest = None
    latest = None
    blockers = []

    for issue in data["issues"]:
        start = get_field(issue, "start_date")
        end = get_field(issue, "end_date")
        dur = get_field(issue, "duration_days", default=3)

        if start is not None:
            sd = date.fromisoformat(start)
            if earliest is None or sd < earliest:
                earliest = sd
        if end is not None:
            ed = date.fromisoformat(end)
        elif start is not None:
            ed = date.fromisoformat(start) + timedelta(days=dur)
        else:
            continue

        if latest is None or ed > latest:
            latest = ed

        deps = issue.get("depends_on_parsed") or []
        if deps and issue.get("state") != "CLOSED":
            blockers.append(f"#{issue['number']} blocked by {deps}")

    if earliest and latest:
        total_days = (latest - earliest).days
        out.metric("duration", f"{total_days} days")
        out.metric("finish date", str(latest))
    else:
        out.metric("duration", "unknown")
        out.metric("finish date", "unknown")

    out.list("blockers", blockers if blockers else ["none"])


# ── Scenario 1: As-Is ───────────────────────────────────────────────


@scenario("as-is")
def as_is(data, out):
    """Baseline — current plan with no changes."""
    _compute_metrics(data, out)
    out.chart(_build_chart(data, "As-Is (baseline)"))
    return data


# ── Scenario 2: Start 2 weeks from now ──────────────────────────────


@scenario("start 2 weeks from now")
def start_two_weeks(data, out):
    """Shift the entire project start to 2026-04-29 (today + 14 d)."""
    new_start = str(date(2026, 4, 15) + timedelta(days=14))  # 2026-04-29
    result = shift_start(data, new_start)
    _compute_metrics(result, out)
    out.chart(_build_chart(result, f"Start shifted to {new_start}"))
    return result


# ── Scenario 3: 4 devs instead of 2 ────────────────────────────────


@scenario("4 devs not 2")
def four_devs(data, out):
    """Double the team size (2→4 devs) ⇒ halve every duration."""
    result = scale_durations(data, 0.5)
    _compute_metrics(result, out)
    out.chart(_build_chart(result, "4 devs (durations × 0.5)"))
    return result