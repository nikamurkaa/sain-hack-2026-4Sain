"""Независимая проверка правил сна по сохранённому расписанию (только для тестов)."""
from datetime import timedelta
from backend.core import default_state, moment


def audit(stay, expected, steps, devices):
    start, wake = moment(stay['check_in_at']), moment(stay['target_wake_at'])
    bed = moment(expected['resolved_bedtime_at'])
    pref = expected['resolved_preferences']
    ordered = sorted(steps, key=lambda s: moment(s['at']))
    def state(at):
        current = default_state(devices)
        for step in ordered:
            if moment(step['at']) <= at:
                current[step['device_id']].update(step['values'])
        return current
    def throughout(begin, end, predicate):
        if end < begin: return True
        probes = {begin, end}
        probes.update(moment(s['at']) for s in ordered if begin <= moment(s['at']) <= end)
        return all(predicate(state(t)) for t in probes)
    failures = []
    evening = max(start, bed-timedelta(minutes=60))
    if not throughout(evening, bed-timedelta(minutes=5), lambda s:10 <= s['light']['brightness'] <= 30 and s['light']['color_temperature_k'] <= 2700):
        failures.append('R1')
    previous = default_state(devices)
    rises = []
    brightness_rises = []
    for step in ordered:
        when = moment(step['at']);dev=step['device_id'];values=step['values']
        bright = dev=='light' and values.get('brightness',previous['light']['brightness'])>previous['light']['brightness']
        curtain = dev=='curtains' and values.get('position',previous['curtains']['position'])>previous['curtains']['position']
        if bed < when <= wake:
            if bright or curtain:rises.append(when)
            if bright:brightness_rises.append(when)
        previous[dev].update(values)
    dawn=min(rises) if rises else wake
    night=max(start,bed+timedelta(minutes=5))
    if not throughout(night,dawn-timedelta(microseconds=1),lambda s:s['light']['brightness']==0 and s['curtains']['position']<=10):
        failures.append('R2')
    lo,hi={'normal':(19,20),'cool':(17,18),'warm':(21,22)}[pref['temperature']]
    if not throughout(night,wake,lambda s:lo<=s['climate']['temperature_c']<=hi):failures.append('R3')
    # Official R4 requires the favorite sound at bedtime, not five minutes later.
    sound=state(max(start,bed))['sound'];tracks=pref['favorite_track_ids']
    if tracks:
        sound_ok=sound['track_id'] in tracks and 1<=sound['volume']<=30 and 1<=sound['timer_minutes']<=45
    else:sound_ok=sound['volume']==0
    if not sound_ok:failures.append('R4')
    alarm=state(wake-timedelta(minutes=31))['alarm']
    if alarm['at'] is None or abs((moment(alarm['at'])-wake).total_seconds())>300 or (pref['gentle_alarm'] and alarm['mode']!='light'):
        failures.append('R5')
    if not rises or not timedelta(minutes=15)<=wake-dawn<=timedelta(minutes=30) or not (len(set(brightness_rises))>=3 or state(wake)['curtains']['position']-state(night)['curtains']['position']>=50):
        failures.append('R6')
    if not throughout(night,wake-timedelta(microseconds=1),lambda s:s['dnd']['enabled']):failures.append('R7')
    return failures
