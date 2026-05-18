from datetime import date, timedelta


@scenario("as-is")
def as_is(data, out):
    issues = data["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    colors = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_x.append(dur)
        bars_y.append(label)
        bars_base.append(start)
        colors.append("#10b981" if iss["state"] == "CLOSED" else "#3b82f6")

        if end and (max_end is None or end > max_end):
            max_end = end
        if start and (min_start is None or start < min_start):
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0

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
            "title": {"text": "As-Is Schedule"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
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
    colors = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_x.append(dur)
        bars_y.append(label)
        bars_base.append(start)
        colors.append("#10b981" if iss["state"] == "CLOSED" else "#3b82f6")

        if end and (max_end is None or end > max_end):
            max_end = end
        if start and (min_start is None or start < min_start):
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0

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
            "title": {"text": f"Start Shifted to {new_start}"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return transformed


@scenario("4 devs not 2")
def four_devs_not_two(data, out):
    # Doubling capacity from 2 → 4 devs halves durations
    transformed = scale_durations(data, 0.5)

    issues = transformed["issues"]

    bars_x = []
    bars_y = []
    bars_base = []
    colors = []
    max_end = None
    min_start = None
    blockers = []

    for iss in issues:
        f = iss["fields"]
        start = f["start_date"]["value"]
        end = f["end_date"]["value"]
        dur = f["duration_days"]["value"] or 0
        label = f"#{iss['number']} {iss['title']}"

        bars_x.append(dur)
        bars_y.append(label)
        bars_base.append(start)
        colors.append("#10b981" if iss["state"] == "CLOSED" else "#3b82f6")

        if end and (max_end is None or end > max_end):
            max_end = end
        if start and (min_start is None or start < min_start):
            min_start = start

        if iss["depends_on_parsed"]:
            blockers.append(label)

    if min_start and max_end:
        d0 = date.fromisoformat(min_start)
        d1 = date.fromisoformat(max_end)
        total_days = (d1 - d0).days
    else:
        total_days = 0

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
            "title": {"text": "4 Devs (durations halved)"},
            "xaxis": {"type": "date"},
            "yaxis": {"automargin": True, "autorange": "reversed"},
        },
    }

    out.chart(figure)
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max_end or "N/A")
    out.list("blockers", blockers if blockers else ["none"])

    return transformed