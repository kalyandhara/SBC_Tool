# VedAstro ingest (2026-10-31)

Source: https://github.com/VedAstro/VedAstro, shallow clone of `master` at
`4d14da8` (2026-10-05). MIT licence (c) 2014-2022 VedAstro. C# (.NET) on
SwissEphNet, plus a website, a REST/MCP API and HuggingFace datasets.

## 1. What it is

A consumer Vedic-astrology platform: horoscope, life predictor, match
checker, horary, panchang, numerology, an LLM "AI astrologer", and an
"earthquake predictor". Nothing in it is market- or finance-specific; the
only "stock exchange" mentions are natal-reading text (e.g. Ketu in 11th).

## 2. The important caveat: the core math is not in the public repo

`Library/Logic/Calculate/*.cs` declares `public partial class Calculate`, but
the part that does the actual astronomy and strength math is absent. These
are called throughout but defined nowhere in the tree:

| called | defined? |
|---|---|
| `Calculate.PlanetRasiD1Sign(...)` | no |
| `Calculate.PlanetNirayanaLongitude(...)` | no |
| `Calculate.IsPlanetGocharaBindu(...)` (all 63 Ashtakavarga-transit events) | no |
| `Calculate.PlanetShadbalaPinda` / `IsPlanetStrongInShadbala(...)` | no |

So the repo does not build from source, and there is no Shadbala code to port.
Treat it as a **rule catalogue + reference tables**, not as an engine.

## 3. What is there, and how it compares with SBC_Tool

| VedAstro piece | file | SBC_Tool today | worth it? |
|---|---|---|---|
| Ashtakavarga benefic-place tables (BAV per planet, SAV) | `Ashtakavarga.cs` (`PlanetBeneficAshtakaHouse`, `SarvashtakavargaChart`) | none (0 hits for ashtakavarga) | **Yes.** Small, classical (BPHS) tables; easy to port to Python on our own `sbc.natal` longitudes. Enables bindu-scored transits of an index natal chart. |
| Ashtakavarga-transit (gochara bindu) events, 0-8 bindus x 7 planets | `Muhurtha.cs` 4915-5110, text in `EventDataListStatic.cs` | none | **Yes, as a study candidate**, after the tables above. The calculator itself is missing (sec. 2), so we write our own. |
| Tarabala (9 taras x strong/middling/weak) and Chandrabala | `Core.cs` `Tarabala`, `Chandrabala`; `Muhurtha.cs` 662-1060 | partial: `kota_chakra.py` scores Vipat/Pratyak/Naidhana only | **Maybe.** Full tara table vs index natal Moon nakshatra is cheap to add; low prior. |
| Muhurta "Selling for profit" / buying rules (Moon and Mercury free of Mars; Moon in Taurus/Cancer/Pisces; Mercury kendra or aspected by Jupiter; Mon/Wed/Thu best, Tue avoid) | `Muhurtha.cs` 4027 `IsGoodSellingForProfitOccuring`, `EventTag.BuyingSelling` (9 rules) | `muhurta.py` has Guru/Ravi Pushya only | **Yes, as a pre-registered falsification test.** Concrete, rule-defined, daily-resolvable; same treatment as the other event studies. |
| Pancha Pakshi (5-bird time-of-day activity tables) | `PanchaPakshi.cs` (1144 lines, tables only) | none | **Low.** Needs a birth nakshatra and a Moon-phase split; intraday-timing claim with no published evidence. Park it. |
| Vargas (D1-D60) | `Vargas.cs` | navamsa only (`navamsa_pipeline/`) | **Low.** Divisional charts amplify birth-time error; our index anchors are 00:00 IST by convention. |
| Vimshottari dasa | `VimshottariDasa.cs` | referenced in 2 files | **Low.** Dasa on an exchange "birth" is decade-scale, untestable in our sample. |
| Golden test values from B.V. Raman, *Manual of Hindu Astrology* (1935): standard horoscope 14:20 16/10/1918 Bangalore | `LibraryTests/Logic/Calculate/ManualOfHinduAstrologyTests.cs`, `CalculateAshtakvargaTests.cs` | our ephemeris checks use Drik Panchang | **Yes, cheap.** Use as extra fixtures for `sbc.natal` / house / ashtakavarga ports. Check which ayanamsa the expected values assume (Raman vs Lahiri) before asserting. |
| Datasets: 15k famous births, marriage data, "100 years London" | `HuggingFace/` | n/a | **No.** Person-level; the London CSV is just a time grid. |
| KP | `CalculateKP-ORI.cs` | full KP stack | **No.** The file is a single empty line. |
| LLM chat, numerology, match/kuta, earthquake predictor | various | n/a | **No.** Off-domain. |

## 4. Recommendation (in order)

1. **Ashtakavarga module** (`sbc/ashtakavarga.py`): port the BAV/SAV tables,
   compute on index natal charts, test against Raman's fixtures. Descriptive
   only until validated.
2. **Pre-register an Ashtakavarga-transit study**: e.g. does Jupiter/Saturn
   transiting a high-SAV sign of the Nifty chart change forward returns vs a
   decile-matched control. Follow the existing event-study lessons (cluster
   rules, event counts not day counts, frozen fixture, transaction costs).
3. **Pre-register the "selling for profit" muhurta rule** as a daily
   classifier against next-day returns. Expect null; it is cheap and the
   rule is fully specified.
4. Optionally extend `kota_chakra.py`'s Tara Balam to the full 9-tara table.

Nothing here replaces existing SBC_Tool components; it fills the
Ashtakavarga gap and supplies a few classical, testable rules.
