
@scenario('as-is')
def s1(data, out):
    dates = [(get_field(i, "start_date"), get_field(i, "end_date")) for i in data["issues"]]
    starts = [d[0] for d in dates if d[0]]
    ends = [d[1] for d in dates if d[1]]
    out.metric("first start", min(starts) if starts else "none")
    out.metric("last end", max(ends) if ends else "none")
    out.metric("issue count", len(data["issues"]))
    return data

@scenario('start 2 weeks from now')
def s2(data, out):
    shifted = delay_all(data, 14)
    starts = [get_field(i, "start_date") for i in shifted["issues"]]
    out.metric("first start", min(s for s in starts if s))
    return shifted
