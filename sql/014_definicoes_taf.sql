-- Definições do TAF partilhadas: o Administrador altera no portal (separador TAF > Definições)
-- e passam logo a valer para todos (aeroportos, destinos/alternativos, limites, fenómenos, horas, atualização).
-- Todos os utilizadores ativos leem; só administradores alteram. Vazio = definições de origem do TAF Monitor.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create table if not exists public.taf_settings (
  id int primary key default 1 check (id = 1),
  cfg jsonb,
  updated_at timestamptz,
  updated_by_name text
);
insert into public.taf_settings (id) values (1) on conflict (id) do nothing;

create or replace function public.taf_settings_stamp()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  new.id := 1;
  new.updated_at := now();
  select display_name into new.updated_by_name from public.user_profiles where user_id = auth.uid();
  return new;
end;
$$;
drop trigger if exists taf_settings_stamp on public.taf_settings;
create trigger taf_settings_stamp before update on public.taf_settings
for each row execute function public.taf_settings_stamp();

alter table public.taf_settings enable row level security;
drop policy if exists taf_settings_read on public.taf_settings;
create policy taf_settings_read on public.taf_settings for select to authenticated
using (public.current_user_role() is not null);
drop policy if exists taf_settings_admin_update on public.taf_settings;
create policy taf_settings_admin_update on public.taf_settings for update to authenticated
using (public.is_admin()) with check (public.is_admin());
revoke all on public.taf_settings from anon;
grant select, update on public.taf_settings to authenticated;

-- Tempo real: quando o Administrador grava, o TAF de todos atualiza sem recarregar
do $$
begin
  if not exists (select 1 from pg_publication_tables
                 where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'taf_settings') then
    alter publication supabase_realtime add table public.taf_settings;
  end if;
end $$;
