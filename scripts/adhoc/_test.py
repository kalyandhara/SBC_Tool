import urllib.request, urllib.parse, json
params=urllib.parse.urlencode({'date':'2026-09-07','time':'09:15','tz':'Asia/Kolkata','anchor':'','school':'allthree'})
try:
    r=urllib.request.urlopen('http://localhost:8801/api/prediction?'+params)
    print(r.status)
    d=json.load(r)
    print(d)
except Exception as e:
    print('err',e)