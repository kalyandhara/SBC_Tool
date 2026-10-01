import app
c = app.app.test_client()
r = c.get('/api/rahu_ketu_trap_calendar?start=2025-08-01&end=2025-08-03')
print(r.status_code)
print(r.data[:500])
