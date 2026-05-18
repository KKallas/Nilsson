from datetime import date, timedelta


def _copy_data(data):
    new_issues = []
    for i in data["issues"]:
        new_fields = {}
        for k, v in i.get("fields", {}).items():
            new_fields[k] = dict(v) if isinstance(v, dict) else v
        new_i = dict(i)
        new_i["fields"] = new_fields
        new_issues.append(new_i)
    return {"issues": new_issues}


def _schedule_with_capacity(data, capacity):
    new_data = _copy_data(data)
    issues = new_data["issues"]

    starts = [get_field(i, "start_date") for i in issues]
    starts = [s for s in starts if s]
    base = date.fromisoformat(min(starts)) if starts else date.today()

    issues_sorted = sorted(
        issues,
        key=lambda i: (get_field(i, "start_date") or "9999-12-31", i.get("number", 0)),
    )
    by_num = {i["number"]: i for i in issues_sorted}
    finish_by_num = {}
    tracks = [base] * max(capacity, 1)
    remaining = list(issues_sorted)

    while remaining:
        progress = False
        for issue in list(remaining):
            deps = issue.get("depends_on_parsed") or []
            if not all((d in finish_by_num) or (d not in by_num) for d in deps):
                continue
            dur = get_field(issue, "duration_days", default=1) or 1
            dep_finish = max(
                (finish_by_num[d] for d in deps if d in finish_by_num),
                default=base,
            )
            t_idx = min(range(len(tracks)), key=lambda t: tracks[t])
            start = max(tracks[t_idx], dep_finish)
            end = start + timedelta(days=int(dur))
            tracks[t_idx] = end
            finish_by_num[issue["number"]] = end
            issue["fields"]["start_date"] = {
                "value": start.isoformat(),
                "source": "scenario:capacity",
            }
            issue["fields"]["end_date"] = {
                "value": end.isoformat(),
                "source": "scenario:capacity",
            }
            remaining.remove(issue)
            progress = True
        if not progress:
            # break dependency cycles by scheduling whatever's left
            for issue in list(remaining):
                dur = get_field(issue, "duration_days", default=1) or 1
                t_idx = min(range(len(tracks)), key=lambda t: tracks[t])
                start = tracks[t_idx]
                end = start + timedelta(days=int(dur))
                tracks[t_idx] = end
                finish_by_num[issue["number"]] = end
                issue["fields"]["start_date"] = {
                    "value": start.isoformat(),
                    "source": "scenario:capacity",
                }
                issue["fields"]["end_date"] = {
                    "value": end.isoformat(),
                    "source": "scenario:capacity",
                }
                remaining.remove(issue)
            break
    return new_data


def _emit(out, transformed, title):
    out.chart(build_gantt_figure(transformed, title=title))
    starts = [get_field(i, "start_date") for i in transformed["issues"]]
    ends = [get_field(i, "end_date") for i in transformed["issues"]]
    starts = [s for s in starts if s]
    ends = [e for e in ends if e]
    if starts and ends:
        span = (date.fromisoformat(max(ends)) - date.fromisoformat(min(starts))).days
        out.metric("duration", f"{span} days")
        out.metric("finish date", max(ends))
    else:
        out.metric("duration", "n/a")
        out.metric("finish date", "n/a")
    blocked = [f"#{i['number']}" for i in transformed["issues"] if i.get("depends_on_parsed")]
    out.list("blockers", blocked if blocked else ["none"])


@scenario("1 developer - only 1 issue solved in parallel at a time")
def s_one_dev(data, out):
    transformed = _schedule_with_capacity(data, 1)
    _emit(out, transformed, "1 developer (sequential)")
    return transformed


@scenario("2 developers - up to 2 issues solved in parallel at a time")
def s_two_devs(data, out):
    transformed = _schedule_with_capacity(data, 2)
    _emit(out, transformed, "2 developers (max 2 in parallel)")
    return transformed