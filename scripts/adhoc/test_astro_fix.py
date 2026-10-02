import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test astro_plot with empty date
    resp = client.get('/api/astro_plot?date=')
    print('Astro Plot API (empty date):', resp.status_code)
    import json
    if resp.status_code == 200:
        data = json.loads(resp.data)
        print('Keys:', list(data.keys()))
    else:
        print('Error:', resp.get_data(as_text=True))

    # Test astro_plot without date param
    resp = client.get('/api/astro_plot')
    print('\nAstro Plot API (no date param):', resp.status_code)
    if resp.status_code == 200:
        data = json.loads(resp.data)
        print('Keys:', list(data.keys()))
    else:
        print('Error:', resp.get_data(as_text=True))
