-- "Só consulta": utilizadores com tipo de acesso reader podem ver e copiar,
-- mas a base de dados recusa qualquer alteração (adicionar, editar, apagar, reativar).
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

create or replace function public.current_user_can_edit()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from public.user_profiles
                 where user_id = auth.uid() and active = true and role in ('operator','admin'));
$$;
revoke all on function public.current_user_can_edit() from public;
grant execute on function public.current_user_can_edit() to authenticated;

-- Substituir as regras de escrita na tabela das MEL
drop policy if exists mel_insert on public.mel_records;
drop policy if exists mel_update on public.mel_records;
drop policy if exists mel_deactivate on public.mel_records;
drop policy if exists mel_team_insert on public.mel_records;
drop policy if exists mel_team_update on public.mel_records;

create policy mel_insert on public.mel_records
for insert to authenticated
with check (public.current_user_can_edit());

create policy mel_update on public.mel_records
for update to authenticated
using (public.current_user_can_edit())
with check (public.current_user_can_edit());
