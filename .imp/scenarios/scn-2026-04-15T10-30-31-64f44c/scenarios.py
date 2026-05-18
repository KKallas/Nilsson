from datetime import date, timedelta


@scenario("as-is")
def as_is(data, out):
    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    finish = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if finish is None or end > finish:
            finish = end

    start_date = min(
        (iss["fields"]["start_date"]["value"] for iss in issues), default="2026-04-15"
    )
    total_days = (
        date.fromisoformat(finish) - date.fromisoformat(start_date)
    ).days if finish else 0

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

    figure = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": bars_x,
                "y": bars_y,
                "base": bars_base,
                "marker": {"color": "#3b82f6"},
            }
        ],
        "layout": {
            "title": {"text": "As-Is"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", finish or "N/A")
    out.list("blockers", blockers or ["none"])

    return data


@scenario("start 2 weeks from now")
def start_2_weeks_from_now(data, out):
    new_start = (date(2026, 4, 15) + timedelta(weeks=2)).isoformat()
    data = shift_start(data, new_start)

    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    finish = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if finish is None or end > finish:
            finish = end

    earliest = min(
        (iss["fields"]["start_date"]["value"] for iss in issues), default=new_start
    )
    total_days = (
        date.fromisoformat(finish) - date.fromisoformat(earliest)
    ).days if finish else 0

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

    figure = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": bars_x,
                "y": bars_y,
                "base": bars_base,
                "marker": {"color": "#f59e0b"},
            }
        ],
        "layout": {
            "title": {"text": "Start 2 Weeks From Now"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", finish or "N/A")
    out.list("blockers", blockers or ["none"])

    return data


@scenario("4 devs not 2")
def four_devs_not_two(data, out):
    # Doubling team from 2 → 4 devs halves individual task durations
    data = scale_durations(data, factor=0.5)

    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    finish = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if finish is None or end > finish:
            finish = end

    earliest = min(
        (iss["fields"]["start_date"]["value"] for iss in issues), default="2026-04-15"
    )
    total_days = (
        date.fromisoformat(finish) - date.fromisoformat(earliest)
    ).days if finish else 0

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

    figure = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": bars_x,
                "y": bars_y,
                "base": bars_base,
                "marker": {"color": "#10b981"},
            }
        ],
        "layout": {
            "title": {"text": "4 Devs Not 2 (0.5× durations)"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", finish or "N/A")
    out.list("blockers", blockers or ["none"])

    return data