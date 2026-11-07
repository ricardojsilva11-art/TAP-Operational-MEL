-- Favoritas, por utilizador (as mesmas no PC e no telemóvel).
-- Cada utilizador só vê e altera as suas. Funciona para todos os tipos de acesso, incluindo "só consulta".
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create table if not exists public.mel_user_prefs (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  record_id uuid not null references public.mel_records(id) on delete cascade,
  is_favorite boolean not null default false,
  last_used_at timestamptz,
  primary key (user_id, record_id)
);

alter table public.mel_user_prefs enable row level security;

drop policy if exists prefs_own on public.mel_user_prefs;
create policy prefs_own on public.mel_user_prefs
for all to authenticated
using (user_id = auth.uid() and public.current_user_role() is not null)
with check (user_id = auth.uid() and public.current_user_role() is not null);

revoke all on public.mel_user_prefs from anon;
grant select, insert, update, delete on public.mel_user_prefs to authenticated;
