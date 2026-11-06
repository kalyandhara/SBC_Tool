CREATE TABLE IF NOT EXISTS natal_profile (
  id BIGSERIAL PRIMARY KEY, label TEXT NOT NULL, is_sample BOOLEAN NOT NULL,
  birth_date DATE NOT NULL, birth_time TIME NOT NULL, tz TEXT NOT NULL,
  lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS daily_score (
  profile_id BIGINT NOT NULL REFERENCES natal_profile(id) ON DELETE CASCADE,
  day DATE NOT NULL, weights_version TEXT NOT NULL, data_asof DATE NOT NULL,
  engine_version TEXT NOT NULL, chart_hash TEXT NOT NULL,
  score NUMERIC NOT NULL, band TEXT NOT NULL, action TEXT NOT NULL, lineage JSONB NOT NULL,
  PRIMARY KEY (profile_id, day, weights_version, data_asof, engine_version, chart_hash));
CREATE TABLE IF NOT EXISTS backtest_run (
  id BIGSERIAL PRIMARY KEY,
  profile_id BIGINT NOT NULL REFERENCES natal_profile(id) ON DELETE CASCADE,
  instrument TEXT NOT NULL, weights_version TEXT NOT NULL, data_asof DATE NOT NULL,
  engine_version TEXT NOT NULL, chart_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
  heartbeat_at TIMESTAMPTZ, error TEXT, params JSONB NOT NULL, folds JSONB, results JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON backtest_run(profile_id)
  WHERE status IN ('queued','running');
