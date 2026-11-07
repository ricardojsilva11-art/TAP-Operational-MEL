-- Obrigar a mudar a palavra-passe definida pelo administrador.
-- Quando o administrador define uma palavra-passe, a conta fica marcada como "tem de mudar".
-- No próximo início de sessão a app só deixa continuar depois de o utilizador escolher uma nova.
-- Enquanto a marca estiver ativa, a base de dados também não mostra nem deixa alterar MEL.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

-- 1) A marca
alter table public.user_profiles add column if not exists must_change_password boolean not null default false;

-- 2) Quando a palavra-passe muda (pelo próprio utilizador), a marca é retirada automaticamente
create or replace function public.clear_must_change_password()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.encrypted_password is distinct from old.encrypted_password then
    update public.user_profiles set must_change_password = false where user_id = new.id;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_password_changed on auth.users;
create trigger on_auth_password_changed after update of encrypted_password on auth.users
for each row execute function public.clear_must_change_password();

-- 3) O administrador define a palavra-passe e a conta fica marcada
--    (a marca é posta depois da alteração, por isso o passo 2 não a retira)
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
  if p_user = auth.uid() then
    raise exception 'Para mudares a tua própria palavra-passe usa o botão da chave, no topo.';
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
  update public.user_profiles
     set reset_requested_at = null,
         must_change_password = true
   where user_id = p_user;
end;
$$;
revoke all on function public.admin_set_password(uuid, text) from public;
grant execute on function public.admin_set_password(uuid, text) to authenticated;

-- 4) Enquanto a marca estiver ativa, a conta não tem acesso aos dados
create or replace function public.current_user_role()
returns text language sql stable security definer set search_path = public
as $$ select role from public.user_profiles
      where user_id = auth.uid() and active = true and not must_change_password $$;

create or replace function public.current_user_can_edit()
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.user_profiles
                     where user_id = auth.uid() and active = true and not must_change_password
                       and role in ('operator','admin')) $$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.user_profiles
                     where user_id = auth.uid() and active = true and not must_change_password
                       and role = 'admin') $$;
