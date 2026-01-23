-- 20260122064332_init_schema.sql
-- 1. UUID生成関数の有効化（念の為）
create extension if not exists "uuid-ossp";

-- ==========================================
-- Table: mobile_suits (機体データの保存)
-- ==========================================
create table public.mobile_suits (
  id uuid not null default gen_random_uuid() primary key,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  
  -- 所有者 (将来的にAuthと紐付けるため。一時はNULL許可)
  user_id uuid references auth.users,
  
  -- 基本ステータス
  name text not null,
  max_hp int not null default 1000,
  armor int not null default 0,
  mobility float not null default 1.0,
  
  -- 装備データ (List[Weapon] をJSONとしてそのまま保存)
  -- 例: [{"id": "w1", "name": "Rifle", "power": 300, ...}]
  weapons jsonb not null default '[]'::jsonb
);

-- ==========================================
-- Table: battle_logs (戦闘結果の履歴)
-- ==========================================
create table public.battle_logs (
  id uuid not null default gen_random_uuid() primary key,
  created_at timestamptz default now(),
  
  -- 戦闘に参加した機体ID
  ms1_id uuid references public.mobile_suits(id),
  ms2_id uuid references public.mobile_suits(id),
  
  -- 勝者ID (引き分けならNULL)
  winner_id uuid,
  
  -- バトルログ本体 (巨大なJSON配列)
  logs jsonb not null
);

-- ==========================================
-- Security: RLS (Row Level Security) 設定
-- ==========================================

-- RLSを有効化
alter table public.mobile_suits enable row level security;
alter table public.battle_logs enable row level security;

-- ポリシー設定 (開発フェーズ用: 誰でも読み書き自由)
-- ※ 本番運用時は「自分のデータしか編集できない」ように修正が必要です

-- mobile_suits: 全公開
create policy "Public read access for mobile_suits"
  on public.mobile_suits for select
  using (true);

create policy "Public insert access for mobile_suits"
  on public.mobile_suits for insert
  with check (true);

create policy "Public update access for mobile_suits"
  on public.mobile_suits for update
  using (true);

-- battle_logs: 全公開
create policy "Public read access for battle_logs"
  on public.battle_logs for select
  using (true);

create policy "Public insert access for battle_logs"
  on public.battle_logs for insert
  with check (true);
