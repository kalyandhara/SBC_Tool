-- A score backtest and a rule backtest may run together for one profile.
ALTER TABLE backtest_run ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'score';
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'backtest_run_kind_check') THEN
    ALTER TABLE backtest_run ADD CONSTRAINT backtest_run_kind_check CHECK (kind IN ('score','rule'));
  END IF;
END $$;
DROP INDEX IF EXISTS one_active_run;
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_kind ON backtest_run(profile_id, kind)
  WHERE status IN ('queued','running');
