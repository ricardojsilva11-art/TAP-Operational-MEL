-- TAF novos/AMD já vistos: por aeroporto, a emissão mais recente que cada utilizador já abriu.
-- Assim, um TAF visto no computador não volta a aparecer como novo no telemóvel (e vice-versa).
-- Cada pessoa só vê e altera os seus. Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create table if not exists public.taf_seen (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  icao text not null check (icao ~ '^[A-Z]{4}$'),
  issue timestamptz not null,
  seen_at timestamptz not null default now(),
  primary key (user_id, icao)
);

alter table public.taf_seen enable row level security;
drop policy if exists taf_seen_own_read on public.taf_seen;
create policy taf_seen_own_read on public.taf_seen for select to authenticated
using (user_id = auth.uid() and public.current_user_role() is not null);
drop policy if exists taf_seen_own_insert on public.taf_seen;
create policy taf_seen_own_insert on public.taf_seen for insert to authenticated
with check (user_id = auth.uid() and public.current_user_role() is not null);
drop policy if exists taf_seen_own_update on public.taf_seen;
create policy taf_seen_own_update on public.taf_seen for update to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.taf_seen from anon;
grant select, insert, update on public.taf_seen to authenticated;
