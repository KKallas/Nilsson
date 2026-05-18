from datetime import date, timedelta


def _reschedule_parallel(data, num_devs):
    """Serialize issues onto `num_devs` parallel tracks, respecting deps."""
    issues_sorted = sorted(
        data["issues"],
        key=lambda it: get_field(it, "start_date") or "9999-12-31",
    )
    result = data
    tracks = [None] * num_devs
    new_ends = {}

    def _priority(t):
        return t if t is not None else "0000-00-00"

    for issue in issues_sorted:
        start = get_field(issue, "start_date")
        dur = get_field(issue, "duration_days", default=1)
        if not start:
            continue

        dep_end = None
        for dep_num in issue.get("depends_on_parsed") or []:
            end = new_ends.get(dep_num)
            if end is not None and (dep_end is None or end > dep_end):
                dep_end = end

        best_idx = min(range(num_devs), key=lambda k: _priority(tracks[k]))
        track_free = tracks[best_idx]

        candidates = [start]
        if track_free is not None:
            candidates.append(track_free)
        if dep_end is not None:
            candidates.append(dep_end)
        target_start = max(candidates)

        if target_start > start:
            delay = (date.fromisoformat(target_start) - date.fromisoformat(start)).days
            if delay > 0:
                result = delay_issue(result, issue["number"], delay)

        new_end = (date.fromisoformat(target_start) + timedelta(days=dur)).isoformat()
        tracks[best_idx] = new_end
        new_ends[issue["number"]] = new_end

    return result


def _emit_metrics(result, out):
    starts = [get_field(i, "start_date") for i in result["issues"]]
    ends = [get_field(i, "end_date") for i in result["issues"]]
    starts = [s for s in starts if s]
    ends = [e for e in ends if e]

    if starts and ends:
        total = (date.fromisoformat(max(ends)) - date.fromisoformat(min(starts))).days
        out.metric("duration", f"{total} days")
        out.metric("finish date", max(ends))
    else:
        out.metric("duration", "n/a")
        out.metric("finish date", "n/a")

    blocked = [f"#{i['number']}" for i in result["issues"] if i.get("depends_on_parsed")]
    out.list("blockers", blocked if blocked else ["none"])


@scenario("1 developer - only 1 issue can be solved in parallel at a time")
def s_one_dev(data, out):
    result = _reschedule_parallel(data, 1)
    out.chart(build_gantt_figure(result, title="1 developer (fully serialized)"))
    _emit_metrics(result, out)
    return result


@scenario("2 developers - up to 2 issues can be solved in parallel at a time")
def s_two_devs(data, out):
    result = _reschedule_parallel(data, 2)
    out.chart(build_gantt_figure(result, title="2 developers (up to 2 in parallel)"))
    _emit_metrics(result, out)
    return result