-- Recusar emails com caracteres escondidos ou símbolos estranhos (ex.: "jplemos@◘tap.pt",
-- que o Supabase grava como "jplemos@xn--tap-uh5a.pt" e depois ninguém consegue usar para entrar).
-- A app já limpa e valida o email; esta regra garante o mesmo na base de dados.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create or replace function public.check_auth_email()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  if new.email is not null and (
       new.email !~ '^[a-z0-9._%+''-]+@[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$'
       or split_part(new.email, '@', 2) ~ '(^|\.)xn--'
     ) then
    raise exception 'Email inválido: tem caracteres especiais ou escondidos. Escreve-o à mão, sem copiar e colar.';
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_email_check on auth.users;
create trigger on_auth_email_check before insert or update of email on auth.users
for each row execute function public.check_auth_email();
