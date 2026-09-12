import datetime
from sbc.planets import positions
import swisseph as swe
from zoneinfo import ZoneInfo

date = datetime.date(2020, 1, 1)
last_sign = None
while date <= datetime.date(2035, 12, 31):
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.timezone.utc)
    jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
    planets, _ = positions(jd)
    saturn = next(p for p in planets if p['name'] == 'Saturn')
    if saturn['sign'] != last_sign:
        print(f'{date}: Saturn entered {saturn["sign"]} at {saturn["degree"]:.2f} deg')
        last_sign = saturn['sign']
    date += datetime.timedelta(days=7)