
import copy
from datetime import timedelta, date

@scenario('uses copy')
def s1(data, out):
    d = copy.deepcopy(data)
    out.metric('count', len(d['issues']))
    return d

@scenario('uses date math')
def s2(data, out):
    tomorrow = date.today() + timedelta(days=1)
    out.metric('tomorrow', tomorrow.isoformat())
    return data
