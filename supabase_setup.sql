-- TAP Operational MEL - cloud schema (Supabase PostgreSQL)
-- Execute in Supabase SQL Editor in a dedicated project approved by TAP IT/Security.
create extension if not exists pgcrypto;

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  role text not null default 'operator' check (role in ('operator','admin','reader')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.mel_records (
  id uuid primary key default gen_random_uuid(),
  legacy_id text unique,
  fleet text not null check (fleet in ('A320','A330','E190/E195')),
  mel_item text not null,
  operational_impact text not null default '',
  operational_impact_html text not null default '',
  is_active boolean not null default true,
  created_by uuid references auth.users(id),
  created_by_name text,
  updated_by uuid references auth.users(id),
  updated_by_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);
create index if not exists mel_records_fleet_idx on public.mel_records(fleet);
create index if not exists mel_records_mel_item_idx on public.mel_records(mel_item);
create index if not exists mel_records_active_idx on public.mel_records(is_active);

create table if not exists public.mel_audit_log (
  id bigint generated always as identity primary key,
  record_id uuid not null references public.mel_records(id) on delete restrict,
  action text not null check (action in ('INSERT','UPDATE','DEACTIVATE')),
  changed_by uuid references auth.users(id),
  changed_at timestamptz not null default now(),
  old_record jsonb,
  new_record jsonb
);
create index if not exists mel_audit_record_idx on public.mel_audit_log(record_id, changed_at desc);

-- Automatically create a profile for each invited Auth user.
create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  insert into public.user_profiles(user_id, display_name, role, active)
  values (new.id, coalesce(nullif(new.raw_user_meta_data->>'name',''), split_part(new.email,'@',1)), 'operator', true)
  on conflict (user_id) do nothing;
  return new;
end;
$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_auth_user();

create or replace function public.current_user_role()
returns text language sql stable security definer set search_path = public
as $$ select role from public.user_profiles where user_id = auth.uid() and active = true $$;

-- Server-side timestamps and identity. Browser cannot forge creator/editor fields.
create or replace function public.set_mel_audit_fields()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  if tg_op = 'INSERT' then
    new.created_by := auth.uid();
    select display_name into new.created_by_name from public.user_profiles where user_id = auth.uid();
    new.created_at := now();
    new.updated_by := null;
    new.updated_by_name := null;
    new.updated_at := null;
  elsif tg_op = 'UPDATE' then
    new.created_by := old.created_by;
    new.created_at := old.created_at;
    new.created_by_name := old.created_by_name;
    new.updated_by := auth.uid();
    select display_name into new.updated_by_name from public.user_profiles where user_id = auth.uid();
    new.updated_at := now();
  end if;
  return new;
end;
$$;
drop trigger if exists mel_set_audit_fields on public.mel_records;
create trigger mel_set_audit_fields before insert or update on public.mel_records
for each row execute function public.set_mel_audit_fields();

create or replace function public.write_mel_audit_log()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  if tg_op = 'INSERT' then
    insert into public.mel_audit_log(record_id,action,changed_by,new_record)
    values(new.id,'INSERT',auth.uid(),to_jsonb(new));
    return new;
  elsif tg_op = 'UPDATE' then
    insert into public.mel_audit_log(record_id,action,changed_by,old_record,new_record)
    values(new.id,case when old.is_active and not new.is_active then 'DEACTIVATE' else 'UPDATE' end,auth.uid(),to_jsonb(old),to_jsonb(new));
    return new;
  end if;
  return null;
end;
$$;
drop trigger if exists mel_audit_trigger on public.mel_records;
create trigger mel_audit_trigger after insert or update on public.mel_records
for each row execute function public.write_mel_audit_log();

alter table public.user_profiles enable row level security;
alter table public.mel_records enable row level security;
alter table public.mel_audit_log enable row level security;

-- Profiles: users can read their own profile; admins can read/manage all.
drop policy if exists profile_read on public.user_profiles;
create policy profile_read on public.user_profiles for select to authenticated
using (user_id = auth.uid() or public.current_user_role() = 'admin');
drop policy if exists profile_admin_update on public.user_profiles;
create policy profile_admin_update on public.user_profiles for update to authenticated
using (public.current_user_role() = 'admin') with check (public.current_user_role() = 'admin');

-- Every active team member can read; operator/admin can add and edit; reader is read-only.
drop policy if exists mel_team_read on public.mel_records;
create policy mel_team_read on public.mel_records for select to authenticated
using (public.current_user_role() in ('operator','admin','reader'));
drop policy if exists mel_team_insert on public.mel_records;
create policy mel_team_insert on public.mel_records for insert to authenticated
with check (public.current_user_role() in ('operator','admin'));
drop policy if exists mel_team_update on public.mel_records;
create policy mel_team_update on public.mel_records for update to authenticated
using (public.current_user_role() in ('operator','admin'))
with check (public.current_user_role() in ('operator','admin'));
drop policy if exists mel_admin_delete on public.mel_records;
create policy mel_admin_delete on public.mel_records for delete to authenticated
using (public.current_user_role() = 'admin');

drop policy if exists audit_team_read on public.mel_audit_log;
create policy audit_team_read on public.mel_audit_log for select to authenticated
using (public.current_user_role() in ('operator','admin','reader'));

-- Restrict table privileges as well as applying RLS.
revoke all on public.user_profiles, public.mel_records, public.mel_audit_log from anon;
grant select on public.user_profiles to authenticated;
grant update (display_name, role, active) on public.user_profiles to authenticated;
grant select, insert, update, delete on public.mel_records to authenticated;
grant select on public.mel_audit_log to authenticated;
grant usage, select on sequence public.mel_audit_log_id_seq to authenticated;

-- Realtime: add mel_records to supabase_realtime publication if not already present.
do $$ begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'mel_records'
  ) then
    alter publication supabase_realtime add table public.mel_records;
  end if;
end $$;

-- After the first invited user exists, promote that user deliberately:
-- update public.user_profiles set role='admin' where user_id=(select id from auth.users where email='ADMIN_EMAIL');
-- Never put Supabase service_role/secret keys in browser code.
