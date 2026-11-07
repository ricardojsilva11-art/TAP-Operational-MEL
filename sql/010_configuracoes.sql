-- Configurações (só administradores alteram; todos os utilizadores ativos leem):
--  • Registos de novas contas: abrir/fechar a criação de conta na app (a base de dados recusa registos fechados).
--  • Duração da sessão: ao fim de quantas horas sem atividade a sessão termina (0 = sem limite).
--  • Cópia de segurança: data e autor da última cópia descarregada.
--  • Revisão da MEL por frota: número e data da revisão em vigor (aparece nas frotas e no Excel).
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

-- 1) Definições gerais (uma única linha)
create table if not exists public.app_settings (
  id int primary key default 1 check (id = 1),
  signups_open boolean not null default true,
  session_hours int not null default 12 check (session_hours between 0 and 72),
  last_backup_at timestamptz,
  last_backup_by text,
  updated_at timestamptz,
  updated_by text
);
insert into public.app_settings (id) values (1) on conflict (id) do nothing;

create or replace function public.app_settings_stamp()
returns trigger language plpgsql security definer set search_path = public
as $$
declare nm text;
begin
  select display_name into nm from public.user_profiles where user_id = auth.uid();
  new.id := 1;
  if new.last_backup_at is distinct from old.last_backup_at then
    new.last_backup_at := now();
    new.last_backup_by := nm;
  end if;
  if new.signups_open is distinct from old.signups_open or new.session_hours is distinct from old.session_hours then
    new.updated_at := now();
    new.updated_by := nm;
  else
    new.updated_at := old.updated_at;
    new.updated_by := old.updated_by;
  end if;
  return new;
end;
$$;
drop trigger if exists app_settings_stamp on public.app_settings;
create trigger app_settings_stamp before update on public.app_settings
for each row execute function public.app_settings_stamp();

alter table public.app_settings enable row level security;
drop policy if exists settings_read on public.app_settings;
create policy settings_read on public.app_settings for select to authenticated
using (public.current_user_role() is not null);
drop policy if exists settings_admin_update on public.app_settings;
create policy settings_admin_update on public.app_settings for update to authenticated
using (public.is_admin()) with check (public.is_admin());
revoke all on public.app_settings from anon;
grant select, update on public.app_settings to authenticated;

-- 2) Registos de novas contas: o ecrã de entrada pergunta se estão abertos (também sem sessão)
create or replace function public.signups_open()
returns boolean language sql stable security definer set search_path = public
as $$ select coalesce((select signups_open from public.app_settings where id = 1), true) $$;
revoke all on function public.signups_open() from public;
grant execute on function public.signups_open() to anon, authenticated;

-- ... e a base de dados recusa contas criadas pela app quando estão fechados.
-- (Só afeta registos feitos na app; o administrador continua a poder criar utilizadores no painel do Supabase.)
create or replace function public.block_closed_signups()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  if coalesce(new.raw_user_meta_data, '{}'::jsonb) ? 'name' and not public.signups_open() then
    raise exception 'Os registos de novas contas estão fechados.';
  end if;
  return new;
end;
$$;
drop trigger if exists on_auth_signup_check on auth.users;
create trigger on_auth_signup_check before insert on auth.users
for each row execute function public.block_closed_signups();

-- 3) Revisão da MEL por frota
create table if not exists public.fleet_revisions (
  fleet text primary key check (fleet in ('A320','A330','E190/E195')),
  revision text not null default '',
  effective_date date,
  updated_at timestamptz,
  updated_by_name text
);
insert into public.fleet_revisions (fleet) values ('A320'), ('A330'), ('E190/E195') on conflict (fleet) do nothing;

create or replace function public.fleet_revisions_stamp()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  new.fleet := old.fleet;
  new.revision := btrim(coalesce(new.revision, ''));
  new.updated_at := now();
  select display_name into new.updated_by_name from public.user_profiles where user_id = auth.uid();
  return new;
end;
$$;
drop trigger if exists fleet_revisions_stamp on public.fleet_revisions;
create trigger fleet_revisions_stamp before update on public.fleet_revisions
for each row execute function public.fleet_revisions_stamp();

alter table public.fleet_revisions enable row level security;
drop policy if exists revisions_read on public.fleet_revisions;
create policy revisions_read on public.fleet_revisions for select to authenticated
using (public.current_user_role() is not null);
drop policy if exists revisions_admin_update on public.fleet_revisions;
create policy revisions_admin_update on public.fleet_revisions for update to authenticated
using (public.is_admin()) with check (public.is_admin());
revoke all on public.fleet_revisions from anon;
grant select, update on public.fleet_revisions to authenticated;

-- 4) Tempo real: mudanças nas configurações chegam logo a todos
do $$
declare t text;
begin
  foreach t in array array['app_settings', 'fleet_revisions'] loop
    if not exists (select 1 from pg_publication_tables
                   where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;
