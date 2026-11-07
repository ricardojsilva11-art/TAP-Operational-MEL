-- "Esqueci-me da palavra-passe" sem email: o utilizador faz o pedido na app
-- e o administrador define uma nova palavra-passe na página Utilizadores.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

-- 1) Guardar quando alguém pediu nova palavra-passe
alter table public.user_profiles add column if not exists reset_requested_at timestamptz;

-- 2) Pedido feito no ecrã de entrada (funciona sem sessão iniciada).
--    Não revela se o email existe ou não.
create or replace function public.request_password_reset(p_email text)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  update public.user_profiles p
     set reset_requested_at = now()
    from auth.users u
   where u.id = p.user_id
     and lower(u.email) = lower(trim(p_email))
     and (p.reset_requested_at is null or p.reset_requested_at < now() - interval '2 minutes');
end;
$$;

-- 3) Administrador define uma nova palavra-passe
create or replace function public.admin_set_password(p_user uuid, p_pass text)
returns void
language plpgsql
security definer
set search_path = public, extensions, auth
as $$
begin
  if not public.is_admin() then
    raise exception 'Só administradores.';
  end if;
  if p_pass is null or length(p_pass) < 8 then
    raise exception 'A palavra-passe tem de ter pelo menos 8 caracteres.';
  end if;
  update auth.users
     set encrypted_password = extensions.crypt(p_pass, extensions.gen_salt('bf')),
         updated_at = now()
   where id = p_user;
  if not found then
    raise exception 'Utilizador não encontrado.';
  end if;
  update public.user_profiles set reset_requested_at = null where user_id = p_user;
end;
$$;

-- 4) Lista de utilizadores passa a indicar quem pediu nova palavra-passe
drop function if exists public.admin_list_users();
create function public.admin_list_users()
returns table(user_id uuid, email text, display_name text, role text, active boolean,
              approved_before boolean, reset_requested boolean,
              created_at timestamptz, last_sign_in_at timestamptz)
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
           (p.reset_requested_at is not null),
           u.created_at, u.last_sign_in_at
    from auth.users u
    left join public.user_profiles p on p.user_id = u.id
    order by coalesce(p.active, false), (p.approved_at is not null),
             (p.reset_requested_at is null), u.created_at desc;
end;
$$;

revoke all on function public.request_password_reset(text) from public;
revoke all on function public.admin_set_password(uuid, text) from public;
revoke all on function public.admin_list_users() from public;
grant execute on function public.request_password_reset(text) to anon, authenticated;
grant execute on function public.admin_set_password(uuid, text) to authenticated;
grant execute on function public.admin_list_users() to authenticated;
