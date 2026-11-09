-- Eliminar contas a partir da app (página Utilizadores), também contas já aprovadas.
--  • Só administradores; ninguém se pode eliminar a si próprio.
--  • As MEL e o histórico de alterações dessa pessoa ficam intactos: o nome continua a aparecer
--    ("Criado por", "Alterado por"), só deixa de estar ligado a uma conta que já não existe.
--  • As favoritas e o perfil da pessoa são apagados com a conta.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

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
  if not exists (select 1 from auth.users where id = p_user) then
    raise exception 'Utilizador não encontrado.';
  end if;

  -- Desligar as MEL e o histórico da conta, sem mexer em quem alterou nem quando
  -- (as regras automáticas da tabela são suspensas só durante este passo).
  alter table public.mel_records disable trigger user;
  update public.mel_records set created_by = null where created_by = p_user;
  update public.mel_records set updated_by = null where updated_by = p_user;
  alter table public.mel_records enable trigger user;
  update public.mel_audit_log set changed_by = null where changed_by = p_user;

  delete from auth.users where id = p_user;
end;
$$;

revoke all on function public.admin_delete_user(uuid) from public;
grant execute on function public.admin_delete_user(uuid) to authenticated;
