"""Repair the transit pane splice: restore status div + closers, and
replace the mojibake button label."""
import io

path = "templates/index.html"
src = io.open(path, encoding="utf-8").read()
lines = src.splitlines()

# 1. find the mojibake generate-button line and rewrite it cleanly
for i, line in enumerate(lines):
    if 'id="transit-generate"' in line:
        lines[i] = ('          <button id="transit-generate" class="btn">'
                    "\u2b07\ufe0f Generate Excel</button>")
        btn_line = i
        break

# 2. the pane close comes right after the controls div's closing tag
#    (btn_line + 1 is '        </div>'); splice the missing pieces
#    before the TAB 2c comment that follows.
idx = btn_line + 2  # 0-based index of the line after '</div>'
assert lines[idx].strip().startswith("<!-- TAB 2c"), lines[idx]
splice = [
    '        <div id="transit-status" class="transit-status" '
    'aria-live="polite"></div>',
    "      </section>",
    "    </div>",
    "",
]
lines[idx:idx] = splice

io.open(path, "w", encoding="utf-8", newline="").write(
    "\n".join(lines) + "\n")
print("repaired at line", idx + 1)
