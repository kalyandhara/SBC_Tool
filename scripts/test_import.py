from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text
import datetime

start = datetime.date(2026, 8, 24)
c = generate_weekly_commentary(start)
print('OK - commentary generated')
print(f'Week: {c["week"]}')
print(f'Bias: {c["market_bias"]}')