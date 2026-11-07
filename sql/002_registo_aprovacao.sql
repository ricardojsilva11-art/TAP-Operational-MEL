-- Registo de utilizadores com aprovação do administrador
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

-- 1) Guardar quando a conta foi aprovada (para distinguir "Pendente" de "Desativado")
alter table public.user_profiles add column if not exists approved_at timestamptz;
update public.user_profiles set approved_at = coalesce(approved_at, created_at) where active = true;

-- 2) Contas novas ficam pendentes (inativas) até um administrador aprovar
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_profiles(user_id, display_name, role, active)
  values (new.id,
          coalesce(nullif(new.raw_user_meta_data->>'name',''), split_part(new.email,'@',1)),
          'operator',
          false)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- 3) Funções do administrador
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.user_profiles
                 where user_id = auth.uid() and active = true and role = 'admin');
$$;

drop function if exists public.admin_list_users();
create function public.admin_list_users()
returns table(user_id uuid, email text, display_name text, role text, active boolean,
              approved_before boolean, created_at timestamptz, last_sign_in_at timestamptz)
language plpgsql
stable
security definer
set search_path = public
as $$
#variable_conflict use_column
begin
  if not public.is_admin() then
    raise exception 'Só administradores.';
  end if;
  return query
    select u.id, u.email::text,
           coalesce(p.display_name, nullif(u.raw_user_meta_data->>'name',''), split_part(u.email,'@',1)),
           coalesce(p.role, 'operator'),
           coalesce(p.active, false),
           (p.approved_at is not null),
           u.created_at, u.last_sign_in_at
    from auth.users u
    left join public.user_profiles p on p.user_id = u.id
    order by coalesce(p.active, false), (p.approved_at is not null), u.created_at desc;
end;
$$;

create or replace function public.admin_set_user(p_user uuid, p_active boolean, p_role text)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin() then
    raise exception 'Só administradores.';
  end if;
  if p_role not in ('operator','reader','admin') then
    raise exception 'Tipo de acesso inválido.';
  end if;
  if p_user = auth.uid() and (not p_active or p_role <> 'admin') then
    raise exception 'Não podes retirar o teu próprio acesso de administrador.';
  end if;
  insert into public.user_profiles(user_id, display_name, role, active, approved_at)
  select u.id, coalesce(nullif(u.raw_user_meta_data->>'name',''), split_part(u.email,'@',1)),
         p_role, p_active, case when p_active then now() end
  from auth.users u where u.id = p_user
  on conflict (user_id) do update
    set role = excluded.role,
        active = excluded.active,
        approved_at = coalesce(public.user_profiles.approved_at, excluded.approved_at);
end;
$$;

create or replace function public.admin_delete_user(p_user uuid)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  if not public.is_admin() then
    raise exception 'Só administradores.';
  end if;
  if p_user = auth.uid() then
    raise exception 'Não podes eliminar a tua própria conta.';
  end if;
  if exists (select 1 from public.user_profiles where user_id = p_user and (active or approved_at is not null)) then
    raise exception 'Só se podem recusar registos pendentes. Para tirar o acesso, usa Desativar.';
  end if;
  delete from auth.users where id = p_user;
end;
$$;

revoke all on function public.is_admin() from public;
revoke all on function public.admin_list_users() from public;
revoke all on function public.admin_set_user(uuid, boolean, text) from public;
revoke all on function public.admin_delete_user(uuid) from public;
grant execute on function public.is_admin() to authenticated;
grant execute on function public.admin_list_users() to authenticated;
grant execute on function public.admin_set_user(uuid, boolean, text) to authenticated;
grant execute on function public.admin_delete_user(uuid) to authenticated;
