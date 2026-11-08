# Phase 4 final fix report

1. Era wording: era_window_info returns widened/clipped flags; era_note now reads "Era window X to Y: middle half of the analog dates, widened to 2 years where shorter, clipped to the available data. This window is N.N years (widened) (clipped to data)." NOTES line reworded. Tests for each case.
2. Short draws: summarize blanks both the all-eras and era-matched shares when any draw was short (or no outcomes), with random_note / era_random_note shown beside each in the UI.
3. Bank Nifty and sector end dates come from data_coverage_note(market).
4. navRandomSentence lost its unused note parameter; navigator.js?v=4.
5. /analogs checks the cache under _analog_cache_lock; _analog_lock is taken only to compute. New test: cached result served while a build is running.
