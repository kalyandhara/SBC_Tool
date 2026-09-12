from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text
import datetime

# The expert commentary is for the period around Aug 23 - Sep 7
# Let's generate for the week starting Monday Aug 24, 2026 (which covers Aug 23-29)
start = datetime.date(2026, 8, 24)  # Monday
commentary = generate_weekly_commentary(start)
print(format_commentary_text(commentary))