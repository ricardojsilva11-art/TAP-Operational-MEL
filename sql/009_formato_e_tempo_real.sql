-- 1) Validar o formato do MEL Item na base de dados (igual à app):
--    M-00-00-00 (com mais grupos, se for preciso) ou C-00 (C-00-00, …), com até 2 letras no fim.
--    Ex.: M-21-26-01, M-21-26-01-02, M-21-26-01A, C-21, C-21-01.
-- 2) Tempo real nos perfis: quando o administrador muda o tipo de acesso, desativa a conta
--    ou define uma palavra-passe temporária, a pessoa vê a mudança sem recarregar a página.
--    (Cada utilizador só recebe a sua própria linha; o administrador recebe todas.)
--
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.
-- Se houver MEL com o formato errado, o script PÁRA e mostra quais são, sem alterar nada.
-- Nesse caso: corrige o MEL Item dessas MEL na app (Editar) e volta a correr o script.

do $$
declare
  lista text;
begin
  select string_agg(format('%s  "%s"%s', fleet, mel_item, case when is_active then '' else '  (no Histórico)' end),
                    E'\n' order by fleet, mel_item)
    into lista
  from public.mel_records
  where mel_item !~ '^(M-[0-9]{2}-[0-9]{2}-[0-9]{2}(-[0-9]+)*|C-[0-9]{2}(-[0-9]+)*)[A-Z]{0,2}$';

  if lista is not null then
    raise exception E'Há MEL com o MEL Item fora do formato. Corrige-as na app e volta a correr o script:\n%', lista;
  end if;
end $$;

alter table public.mel_records drop constraint if exists mel_item_format;
alter table public.mel_records add constraint mel_item_format
  check (mel_item ~ '^(M-[0-9]{2}-[0-9]{2}-[0-9]{2}(-[0-9]+)*|C-[0-9]{2}(-[0-9]+)*)[A-Z]{0,2}$');

do $$ begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'user_profiles'
  ) then
    alter publication supabase_realtime add table public.user_profiles;
  end if;
end $$;
