-- seed.sql
-- ガンダム (RX-78-2)
INSERT INTO public.mobile_suits (id, name, max_hp, armor, mobility, weapons)
VALUES (
  '00000000-0000-0000-0000-000000000001', -- 固定UUID
  'ガンダム',
  1000,
  100,
  1.5,
  '[{"id": "br", "name": "ビームライフル", "power": 300, "range": 600, "accuracy": 80}]'::jsonb
);

-- ザクII (MS-06)
INSERT INTO public.mobile_suits (id, name, max_hp, armor, mobility, weapons)
VALUES (
  '00000000-0000-0000-0000-000000000002', -- 固定UUID
  'ザクII',
  800,
  50,
  1.0,
  '[{"id": "mg", "name": "ザクマシンガン", "power": 100, "range": 400, "accuracy": 60}]'::jsonb
);
