-- 1) Validar o formato do MEL Item na base de dados (igual à app):
--    M-00-00 ou C-00, com mais grupos se for preciso, e até 2 letras no fim, juntas ou depois de hífen.
--    Ex.: M-34-50, M-21-26-01, M-21-26-01-02, M-21-26-01A, M-21-51-00-A, M-23-51-00-03-B, C-21, C-21-01.
--    Antes de criar a regra, um MEL Item com um comentário entre parênteses no fim
--    (ex.: "M-34-50-09F (ver MEL, varia com o avião)") fica só com o número, e o comentário passa para as Notas.
-- 2) Tempo real nos perfis: quando o administrador muda o tipo de acesso, desativa a conta
--    ou define uma palavra-passe temporária, a pessoa vê a mudança sem recarregar a página.
--    (Cada utilizador só recebe a sua própria linha; o administrador recebe todas.)
--
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.
-- Se ainda houver MEL com o formato errado, o script PÁRA e mostra quais são, sem alterar nada.
-- Nesse caso: corrige o MEL Item dessas MEL na app (Editar) e volta a correr o script.

-- 1a) Comentário entre parênteses no MEL Item -> Notas
--     A função que regista quem alterou recusa alterações sem utilizador com sessão (como no SQL Editor);
--     por isso desliga-se só durante esta correção e volta a ligar-se logo a seguir, no mesmo passo.
do $$
declare
  t record;
  trigs text[] := '{}';
begin
  for t in
    select tg.tgname from pg_trigger tg join pg_proc pr on pr.oid = tg.tgfoid
    where tg.tgrelid = 'public.mel_records'::regclass and not tg.tgisinternal
      and pr.proname = 'set_mel_audit_fields' and tg.tgenabled <> 'D'
  loop
    trigs := trigs || t.tgname::text;
    execute format('alter table public.mel_records disable trigger %I', t.tgname);
  end loop;

  update public.mel_records
     set notes = concat_ws(E'\n', nullif(btrim(coalesce(notes, '')), ''), btrim(substring(mel_item from '\((.*)\)\s*$'))),
         mel_item = btrim(substring(mel_item from '^([^(]+)\('))
   where mel_item ~ '^[MC]-[0-9][^(]*\(.*\)\s*$'
     and btrim(substring(mel_item from '^([^(]+)\(')) ~ '^(M-[0-9]{2}-[0-9]{2}(-[0-9]+)*|C-[0-9]{2}(-[0-9]+)*)(-?[A-Z]{1,2})?$';

  for i in 1 .. coalesce(array_length(trigs, 1), 0) loop
    execute format('alter table public.mel_records enable trigger %I', trigs[i]);
  end loop;
end $$;

-- 1b) Verificar o que ainda está fora do formato
do $$
declare
  lista text;
begin
  select string_agg(format('%s  "%s"%s', fleet, mel_item, case when is_active then '' else '  (no Histórico)' end),
                    E'\n' order by fleet, mel_item)
    into lista
  from public.mel_records
  where mel_item !~ '^(M-[0-9]{2}-[0-9]{2}(-[0-9]+)*|C-[0-9]{2}(-[0-9]+)*)(-?[A-Z]{1,2})?$';

  if lista is not null then
    raise exception E'Há MEL com o MEL Item fora do formato. Corrige-as na app e volta a correr o script:\n%', lista;
  end if;
end $$;

-- 1c) A regra
alter table public.mel_records drop constraint if exists mel_item_format;
alter table public.mel_records add constraint mel_item_format
  check (mel_item ~ '^(M-[0-9]{2}-[0-9]{2}(-[0-9]+)*|C-[0-9]{2}(-[0-9]+)*)(-?[A-Z]{1,2})?$');

-- 2) Tempo real nos perfis
do $$ begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'user_profiles'
  ) then
    alter publication supabase_realtime add table public.user_profiles;
  end if;
end $$;
