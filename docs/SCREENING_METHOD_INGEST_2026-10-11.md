# Stock screening method (Finance With Prabhu reel) — ingest (2026-10-11)

**Source:** https://www.facebook.com/reel/1462340476099750 (Facebook reel, "Finance With Prabhu", 1.1K views, 348 reactions, 12 comments; original audio).
**What was read:** the caption and page metadata only. The video and audio were not accessible without a Facebook login, so the examples it discusses (Radico Khaitan, Solex Energy) and any on-screen detail are **not** verified.
**Status: ingested, not built, not tested.** This is a creator's public claim, not a validated method.

## The claimed screen (as stated in the caption)

| Filter | Threshold |
|---|---|
| Market capitalisation | ₹500 Cr – ₹20,000 Cr |
| Operating profit margin growth | > 25% over 10 years |
| Sales growth | > 25% over 5 years |
| Profit growth | > 25% over 5 years |
| Debt | prefer lower debt (no number given) |
| Altman Z-Score | > 3 (described as a distress screen) |
| Promoter holding | > 60% |

The caption says the filters narrow a large universe to a smaller research list, and that passing them "does not guarantee future returns". It names Screener as the tool.

## Gaps for any build

- **Debt has no threshold.** A rule would need a number, such as debt/equity below some value, chosen before testing.
- **"Over 10 years" growth** needs a definition: CAGR endpoints, or every year above 25%.
- **Universe and data.** Screener is a fundamentals source the repo doesn't have. Market cap and promoter holding would need a feed; the repo holds daily prices only (`data/market.db`).
- **Survivorship and look-ahead.** A screen run today on today's filings says nothing about past years unless fundamentals are stored as they were published.
- **Not astrology.** This sits outside the engine's research scope. Building it would be a new project, not a rule in `sbc/`.

## Recommendation

Log it as an idea, not a backlog item. Testing it needs point-in-time fundamentals, which the repo doesn't have. If you want it pursued, I'd first register the thresholds and the debt rule before pulling any data, the same way B-53 was handled.
