# Ad-hoc scripts

One-off backtests, extraction and analysis scripts that used to live at the
repository root. They are not imported by the app or the tests.

Run them from the repository root so `sbc` is importable:

    PYTHONPATH=. python scripts/adhoc/<name>.py

Several still reference the old `D:/SBC_Tool/` folder and were already
broken before the move; fix the path when you next need one.
