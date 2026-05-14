CREATE TABLE IF NOT EXISTS portfolios (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id text NOT NULL,
  coin_id text NOT NULL,
  amount numeric NOT NULL,
  buy_price numeric DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id);
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for now" ON portfolios FOR ALL USING (true);
