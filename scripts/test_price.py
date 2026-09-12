import urllib.request, urllib.error
try:
    urllib.request.urlopen('http://localhost:8801/api/price').close()
    print('ok')
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode()[:500])
