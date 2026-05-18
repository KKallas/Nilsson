from datetime import date, timedelta


@scenario("as-is")
def as_is(data, out):
    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        max_end = str(date.today())

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": "#3b82f6"},
        }],
        "layout": {
            "title": {"text": "As-Is"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end)
    out.list("blockers", blockers if blockers else ["none"])

    return data


@scenario("start 2 weeks from now")
def start_2_weeks_from_now(data, out):
    new_start = str(date(2026, 4, 15) + timedelta(weeks=2))  # 2026-04-29
    transformed = shift_start(data, new_start)

    issues = transformed["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        max_end = new_start

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": "#f59e0b"},
        }],
        "layout": {
            "title": {"text": f"Start 2 Weeks From Now ({new_start})"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end)
    out.list("blockers", blockers if blockers else ["none"])

    return transformed


@scenario("4 devs not 2")
def four_devs_not_two(data, out):
    # Doubling dev count from 2 to 4 halves task durations
    transformed = scale_durations(data, 0.5)

    issues = transformed["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)

        if max_end is None or end > max_end:
            max_end = end
        if min_start is None or start < min_start:
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        max_end = str(date.today())

    figure = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": bars_x,
            "y": bars_y,
            "base": bars_base,
            "marker": {"color": "#10b981"},
        }],
        "layout": {
            "title": {"text": "4 Devs Instead of 2 (0.5× durations)"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end)
    out.list("blockers", blockers if blockers else ["none"])

    return transformed