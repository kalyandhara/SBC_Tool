# eVector.io ingest + REA (2026-10-26)

What eVector is, what its shipped artifacts reveal about how it works,
and which features are worth adopting into SBC_Tool.

## 1. What it is

A consumer market-intelligence product: each day's news becomes "events";
every event fans out into a graph of the assets it should touch (its
sector, industry, theme, peers, macro backdrop); each affected asset
carries a momentum-engine reading; and users make one-tap directional
calls that the market "grades" at a resolution date. Free tier is
metered (2 events, 1 stock); a $19.99/mo "Research Desk" opens the full
map, full picks list, an AI analyst and state-change alerts. Next.js
App Router (Turbopack), server-rendered, i18n (EN/HE), NY-time trading
day snapshots.

## 2. REA method + evidence (passive, static only)

No REA MCP server in this session; analysis is static inspection of
what the site publicly ships. No login, no locked-content access, no
runtime probing.

| evidence | source | what it showed |
|---|---|---|
| E1 | `https://evector.io/` HTML (283 KB SSR) | full page surface: hero event card, events-today list, market map tiles, picks, prediction cards, pricing, disclaimers |
| E2 | chunk `0_w-2fsvfnzic.js` (i18n dictionary, module 90012) | the complete domain vocabulary: node kinds, momentum states, measurement fields, scenario/analog copy, prediction + track-record copy, freemium funnel taxonomy, MCP integration copy, 61-indicator chart docs |
| E3 | chunk `2l8x4o7bgo21s.js` (event explorer) | graph component model: nodes/parent/touches, edge types, locked-node blur, scenario picker, crowd consensus reveal threshold, prediction-market odds |
| E4 | remaining chunks + `/robots.txt` (404), client API grep | client API surface is just `/api/session`, `/api/signout`, `/api/logo` — data is server-rendered; the engine internals are NOT observable from static evidence (recorded as unknowns) |

Unknowns (not inferable from shipped artifacts): the event-detection
pipeline, the momentum state-machine's exact sequence rules, the graph
edge measurement method beyond what the UI copy states, and the data
vendor. Everything below cites only what IS observable.

## 3. The reverse-engineered model (from E1-E3)

**Nodes.** kinds: `event, macro, asset_class, sector, theme, stock,
crypto`; categories: Macro, Crypto, Earnings, Technology, Energy,
Sector, Attention, Geopolitics, Commodities. Node fields observed:
`label, symbol, kind, parent, locked, measured, rationale ("Why it's
on the map"), strength (Strong/Moderate/Mild/Expected)`.

**Momentum engine (per node).** Seven states with plain-language
readings: Neutral ("No active trend"), Ignition ("Just broke out"),
Acceleration ("Speeding up"), Expansion ("Trend holding"),
HealthyPullback ("Resting, trend intact"), Weakening ("Losing steam"),
Breakdown ("Trend broken"). Fields: `state, previousState,
transitionReason ("From Weakening: ..."), score (0-100)`. Sector tiles
add honest guardrails ("broadening but has not yet met the minimum
sequence length for Expansion"; "early evidence present; persistence
not yet established").

**Measurement (per node).** `change` (over `windowLabel`, e.g. "in the
last 20 trading days"), `excess` (vs S&P over the SAME period), `z`
("for this name" — the move normalised by the name's own volatility,
shown as "±N.Nσ"), `price`. Impact: a 0-100 score rendered as 5 bars +
High/Medium/Low.

**Edges.** Three visual classes: measured (solid), hypothesis (dashed,
"waiting for the market"), second-order (finer dash). Status lifecycle:
`live` → `upcoming` ("Upcoming · Oct 28", "Awaiting reaction") with the
rule stated in the UI: "A hypothesis until {date}. The reaction is
measured from the close before the event."

**Scenarios ("Read the map as").** One event, several interpretations;
each maps to prediction buckets. Per node, a frozen-method analog card:
"On the day of {n} past decisions like this one ({range}): {subject}
moved {mean}% on average, ranging from {min}% to {max}%. Method: close
before the announcement to the close that day."

**Predictions.** Two question kinds: `categorical` ("confirmed
outcome") and `basket_return` ("Resolves {date} · from closing prices",
buckets include a flat centre). One tap, final: "the record only counts
what you said before the market did". Anti-herding: the crowd split is
hidden until a call threshold ("You're caller #2"; "the crowd's split
appears at N calls"), and there is a "prediction markets" cross-reference
row with external odds per bucket. Consensus history over time. Personal
track record: accuracy, streak, by-category, rank (Top N%), verdicts
Correct / Close / Missed / Open — with "Close — but outside your range...
the record counts it as a miss".

**Stock page.** Momentum reading + "N events reach it today" with
relation types: On the map / Through its industry / Through its sector /
Macro backdrop; a bottom line that weights momentum + event directions
("N linked events point up, M down" → "Leaning higher").

**Picks.** "#1 of 5,619 screened · score 77 · Expansion · Oil & Gas
Integrated", with explainability bullets: "5 consecutive gaps; new
highs in 40% of sessions; accelerating price discovery. (trend
holding)".

**Markets page.** Chart with 61 indicators (grouped MA / bands & channels
/ trend / momentum & oscillators / volatility / volume), each with
docs ("the formulas are the ones the chart runs"), drawing tools,
two engines (Lightweight Charts vs an own canvas engine), event markers
on the chart, compare-by-role (market/sector/industry/theme/peer),
"vs sector, 20d".

**MCP integration.** "Connect your AI to eVector" — a Streamable-HTTP +
OAuth MCP server (Research Desk tier) exposing "momentum states, the
day's world and market events and how they reach each stock, daily
bars, the 61 indicators computed exactly as on the chart, and the
technical read", plus watchlist and pre-configured charts.

**Growth mechanics (for completeness).** Metered free tier, blurred
locked nodes, conversion modals keyed to trigger
(`deep_node, locked_pick, ai_question, research_desk, stock_search`),
and a dev-analytics desk with an action taxonomy (event_opened,
node_expanded, prediction_made, resolution_viewed, locked_pick_clicked,
blur_shown, ...) and DAU/WAU/MAU/retention curves.

## 4. Features worth adopting (ranked, mapped to SBC_Tool)

| # | adopt | lands in | why | effort |
|---|-------|----------|-----|--------|
| 1 | **Auto-graded call ledger with a frozen-method track record** — one-tap pre-registered calls, resolved from settled closes, verdicts Correct/Close/Missed (close counts as a miss), accuracy/streak/by-category | `forecast_ledger.db` + `reports/astroz_calls_ledger.md` | the ledger is already SBC's epistemic core (B-70 pre-registration, D3 calls); eVector shows the completion: a resolution job + cumulative score. "The record only counts what you said before the market did" is exactly SBC's culture — automate the grading | M |
| 2 | **Expected-direction + measured-move per event→asset edge, with the hypothesis→measured lifecycle** ("the arrow is what we expect; the number is what the price actually did"; "a hypothesis until {date}; measured from the close before the event") | `sbc/forward_calendar.py` | the forward calendar already lists events; add per-affected-asset expected direction (from the matching event study) and a measured `change` once the close settles, with an observed/hypothesis badge. Upgrades B4 directly | M |
| 3 | **Scenario analog cards** — "on N past decisions like this one, X moved mean% (range), method: close-before to close-that-day" | `sbc/analogs.py` + forward calendar | SBC has the analog machinery; eVector shows the presentation that makes it decision-useful. For FOMC/RBI/ingress events this is one query away | L-M |
| 4 | **7-state momentum machine with transition reasons and honest guardrails** | NSE Momentum Screener | richer than up/down: Ignition → Acceleration → Expansion → HealthyPullback → Weakening → Breakdown, each with a plain-language reason and "persistence not yet established" style honesty. Fits the screener's existing scoring | M |
| 5 | **Explainable picks** — "why it matters" bullets from measured features (consecutive gaps, share of new-high sessions, price-discovery acceleration) | Screener output | every pick carries its own evidence; cheap to generate from features the screener already computes | L-M |
| 6 | **Relative-strength everywhere** — "vs benchmark · 20 sessions" and "vs sector, 20d" on every tile/node | Screener, charts | one division; makes every absolute number self-calibrating | L |
| 7 | **Crowding/theme detector** — "12 of the 40 strongest names are software — a story, not a coincidence; the sector ETF moved −6.6% — an industry move, not a sector one" | Screener | top-N concentration by sector/industry + the "industry vs sector" disambiguation is a genuine insight generator on Indian universes (e.g. PSU banks crowding) | M |
| 8 | **MCP server for SBC itself** — expose events (forward calendar), factor states, freshness, the call ledger, daily bars and the technical read over MCP | new `sbc/mcp_server.py` | eVector's own pitch proves the pattern; the user's Claude workflow would read the tool directly ("what does the tool say about today?") — high leverage for a single-user system | M |
| 9 | **State-change alerts** — "know the session a trend ignites — or breaks" | alerts + forward calendar | momentum `previousState → state` transitions and node-ingress/egress days are already computed; wire them to the alert surface | L-M |
| 10 | **Chart event markers + formula docs** — events as clickable markers on the price chart ([ and ] to step), and per-indicator "how it's computed" docs | SBC chart | astro events plotted on the chart the way eVector plots news; and the docs culture ("the formulas are the ones the chart runs") matches SBC's reproducibility ethos | M |
| 11 | **Event-weighted bottom line** — combine momentum state + today's event directions into one lean ("Leaning higher: momentum points up, 3 of 4 linked events point up") | stock/prediction view | a measured way to combine the two signal families SBC already has; the weighting must come from SBC's own validation studies, not vibes | M |
| 12 | **Verdict strictness for the ledger** — "Close — but outside your range... counts as a miss" | call grading | adopt the three-verdict taxonomy with strict misses; prevents soft-grading drift | L |

**Worth knowing, not adopting:** the metered free tier, blur-locks and
conversion funnels (consumer-growth mechanics, not analysis); the
"prediction game" as a product (SBC's ledger is single-user epistemics —
steal the grading, not the game); and the AI-analyst copy style
("get research, not a guess") is already SBC's report voice.

**Sequencing suggestion:** 1 + 2 + 3 form one coherent build ("the
forward calendar becomes an event map with expected arrows, analog
cards, and self-grading calls"); 4-7 are one screener upgrade; 8 is the
highest-novelty standalone piece.
