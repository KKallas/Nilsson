from datetime import date, timedelta


@scenario("as-is")
def s_as_is(data, out):
    out.chart(build_gantt_figure(data, title="As-is"))

    ends = [get_field(i, "end_date") for i in data["issues"]]
    ends = [e for e in ends if e]
    starts = [get_field(i, "start_date") for i in data["issues"]]
    starts = [s for s in starts if s]

    total_days = (date.fromisoformat(max(ends)) - date.fromisoformat(min(starts))).days if ends and starts else 0
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max(ends) if ends else "unknown")

    blocked = [f"#{i['number']}" for i in data["issues"] if i.get("depends_on_parsed")]
    out.list("blockers", blocked if blocked else ["none"])
    return data


@scenario("start 2 weeks from now")
def s_start_2w(data, out):
    new_start = (date.fromisoformat("2026-04-15") + timedelta(weeks=2)).isoformat()
    shifted = shift_start(data, new_start)

    out.chart(build_gantt_figure(shifted, title="Start 2 weeks from now"))

    ends = [get_field(i, "end_date") for i in shifted["issues"]]
    ends = [e for e in ends if e]
    starts = [get_field(i, "start_date") for i in shifted["issues"]]
    starts = [s for s in starts if s]

    total_days = (date.fromisoformat(max(ends)) - date.fromisoformat(min(starts))).days if ends and starts else 0
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max(ends) if ends else "unknown")

    blocked = [f"#{i['number']}" for i in shifted["issues"] if i.get("depends_on_parsed")]
    out.list("blockers", blocked if blocked else ["none"])
    return shifted


@scenario("4 devs not 2")
def s_4_devs(data, out):
    # Doubling the team from 2 → 4 devs halves each task's duration
    scaled = scale_durations(data, 0.5)

    out.chart(build_gantt_figure(scaled, title="4 devs not 2"))

    ends = [get_field(i, "end_date") for i in scaled["issues"]]
    ends = [e for e in ends if e]
    starts = [get_field(i, "start_date") for i in scaled["issues"]]
    starts = [s for s in starts if s]

    total_days = (date.fromisoformat(max(ends)) - date.fromisoformat(min(starts))).days if ends and starts else 0
    out.metric("duration", f"{total_days} days")
    out.metric("finish date", max(ends) if ends else "unknown")

    blocked = [f"#{i['number']}" for i in scaled["issues"] if i.get("depends_on_parsed")]
    out.list("blockers", blocked if blocked else ["none"])
    return scaled