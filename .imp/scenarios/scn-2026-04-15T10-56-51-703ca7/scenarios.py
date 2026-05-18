from datetime import date, timedelta


@scenario("as-is")
def as_is(data, out):
    """Baseline — no changes."""
    issues = data["issues"]

    bars_x, bars_y, bars_base, colors = [], [], [], []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        start = get_field(iss, "start_date")
        end = get_field(iss, "end_date")
        dur = get_field(iss, "duration_days", default=1)
        if not start or not end:
            continue
        label = f'#{iss["number"]} {iss["title"]}'
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        colors.append("#22c55e" if iss["state"] == "CLOSED" else "#3b82f6")

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss.get("depends_on_parsed"):
            blockers.append(label)

    total_days = (date.fromisoformat(max_end) - date.fromisoformat(min_start)).days if max_end and min_start else 0

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": colors},
        }],
        "layout": {
            "title": {"text": "As-Is"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return data


@scenario("start-2-weeks-later")
def start_2_weeks_later(data, out):
    """Shift the entire plan to start 2 weeks from today."""
    new_start = (date(2026, 4, 15) + timedelta(weeks=2)).isoformat()
    data = shift_start(data, new_start)

    issues = data["issues"]
    bars_x, bars_y, bars_base, colors = [], [], [], []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        start = get_field(iss, "start_date")
        end = get_field(iss, "end_date")
        dur = get_field(iss, "duration_days", default=1)
        if not start or not end:
            continue
        label = f'#{iss["number"]} {iss["title"]}'
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        colors.append("#22c55e" if iss["state"] == "CLOSED" else "#3b82f6")

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss.get("depends_on_parsed"):
            blockers.append(label)

    total_days = (date.fromisoformat(max_end) - date.fromisoformat(min_start)).days if max_end and min_start else 0

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": colors},
        }],
        "layout": {
            "title": {"text": f"Start shifted to {new_start}"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return data


@scenario("4-devs-not-2")
def four_devs_not_two(data, out):
    """Double the team from 2 to 4 devs — halve open-issue durations."""
    data = scale_durations(data, 0.5)

    issues = data["issues"]
    bars_x, bars_y, bars_base, colors = [], [], [], []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        start = get_field(iss, "start_date")
        end = get_field(iss, "end_date")
        dur = get_field(iss, "duration_days", default=1)
        if not start or not end:
            continue
        label = f'#{iss["number"]} {iss["title"]}'
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        colors.append("#22c55e" if iss["state"] == "CLOSED" else "#3b82f6")

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss.get("depends_on_parsed"):
            blockers.append(label)

    total_days = (date.fromisoformat(max_end) - date.fromisoformat(min_start)).days if max_end and min_start else 0

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": colors},
        }],
        "layout": {
            "title": {"text": "4 devs instead of 2 (durations halved)"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return data