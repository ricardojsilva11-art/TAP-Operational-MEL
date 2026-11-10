-- Aeroportos favoritos no TAF (estrela na grelha do TAF e no Início): de cada utilizador, iguais em todos os aparelhos.
-- Cada pessoa só vê e altera os seus. Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create table if not exists public.taf_favorites (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  icao text not null check (icao ~ '^[A-Z]{4}$'),
  created_at timestamptz not null default now(),
  primary key (user_id, icao)
);

alter table public.taf_favorites enable row level security;
drop policy if exists taf_favorites_own_read on public.taf_favorites;
create policy taf_favorites_own_read on public.taf_favorites for select to authenticated
using (user_id = auth.uid() and public.current_user_role() is not null);
drop policy if exists taf_favorites_own_insert on public.taf_favorites;
create policy taf_favorites_own_insert on public.taf_favorites for insert to authenticated
with check (user_id = auth.uid() and public.current_user_role() is not null);
drop policy if exists taf_favorites_own_delete on public.taf_favorites;
create policy taf_favorites_own_delete on public.taf_favorites for delete to authenticated
using (user_id = auth.uid());
revoke all on public.taf_favorites from anon;
grant select, insert, delete on public.taf_favorites to authenticated;
