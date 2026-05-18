
@scenario('as-is')
def s1(data, out):
    total_dur = 0
    missing_dates = 0
    for issue in data['issues']:
        dur = get_field(issue, 'duration_days', default=0)
        if dur:
            total_dur += dur
        if get_field(issue, 'start_date') is None:
            missing_dates += 1
    out.metric('total duration', f'{total_dur} days')
    out.metric('issues without start_date', missing_dates)
    return data

@scenario('delayed')
def s2(data, out):
    shifted = delay_all(data, 14)
    total_dur = sum(get_field(i, 'duration_days', 0) for i in shifted['issues'])
    out.metric('total duration', f'{total_dur} days')
    out.metric('shifted', '+14 days')
    return shifted
