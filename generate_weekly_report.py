"""
Generate weekly commentary report - can be run as standalone script
or imported. Usage: python generate_weekly_report.py [YYYY-MM-DD]
"""
import sys
import datetime
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).parent))

from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text


def main():
    if len(sys.argv) > 1:
        try:
            date = datetime.date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"Invalid date format: {sys.argv[1]}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        date = datetime.date.today()

    # Find Monday of that week
    start = date - datetime.timedelta(days=date.weekday())

    print(f"Generating weekly commentary for week of {start}...")
    commentary = generate_weekly_commentary(start)
    text = format_commentary_text(commentary)
    print(text)

    # Also save to file
    output_file = f"weekly_commentary_{start.isoformat()}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()