from datetime import date, timedelta


@scenario("as-is")
def as_is(data, out):
    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    earliest = None
    latest = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"]
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if earliest is None or start < earliest:
            earliest = start
        if latest is None or end > latest:
            latest = end

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

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
            "title": {"text": "As-Is Schedule"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)

    if earliest and latest:
        d0 = date.fromisoformat(earliest)
        d1 = date.fromisoformat(latest)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        latest = "N/A"

    out.metric("duration", f"{total_days} days")
    out.metric("finish date", latest if latest else "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return data


@scenario("start 2 weeks from now")
def start_2_weeks_from_now(data, out):
    new_start = (date(2026, 4, 15) + timedelta(weeks=2)).isoformat()
    transformed = shift_start(data, new_start)

    issues = transformed["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    earliest = None
    latest = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"]
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if earliest is None or start < earliest:
            earliest = start
        if latest is None or end > latest:
            latest = end

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

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
            "title": {"text": f"Start shifted to {new_start}"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)

    if earliest and latest:
        d0 = date.fromisoformat(earliest)
        d1 = date.fromisoformat(latest)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        latest = "N/A"

    out.metric("duration", f"{total_days} days")
    out.metric("finish date", latest if latest else "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return transformed


@scenario("4 devs not 2")
def four_devs_not_two(data, out):
    # Doubling team from 2 → 4 devs halves durations
    transformed = scale_durations(data, 0.5)

    issues = transformed["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    earliest = None
    latest = None

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"]
        label = f"#{iss['number']} {iss['title']}"
        bars_y.append(label)
        bars_base.append(start)
        bars_x.append(dur)
        if earliest is None or start < earliest:
            earliest = start
        if latest is None or end > latest:
            latest = end

    blockers = []
    for iss in issues:
        if iss.get("depends_on_parsed"):
            blockers.append(f"#{iss['number']} blocked by {iss['depends_on_parsed']}")

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
            "title": {"text": "4 Devs (durations halved)"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }
    out.chart(figure)

    if earliest and latest:
        d0 = date.fromisoformat(earliest)
        d1 = date.fromisoformat(latest)
        total_days = (d1 - d0).days
    else:
        total_days = 0
        latest = "N/A"

    out.metric("duration", f"{total_days} days")
    out.metric("finish date", latest if latest else "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return transformed