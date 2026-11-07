-- Impedir MEL duplicadas: não pode haver duas MEL ATIVAS com o mesmo MEL Item na mesma frota.
-- (As MEL apagadas, no Histórico, não contam. Maiúsculas/minúsculas e espaços nas pontas são ignorados.)
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.
--
-- Se já existirem duplicados, o script PÁRA e mostra quais são, sem alterar nada.
-- Nesse caso: apaga (na app) as MEL a mais, ou corrige o MEL Item, e volta a correr este script.

do $$
declare
  lista text;
begin
  select string_agg(format('%s  %s  (%s registos)', fleet, item, n), E'\n' order by fleet, item)
    into lista
  from (
    select fleet, upper(btrim(mel_item)) as item, count(*) as n
    from public.mel_records
    where is_active
    group by fleet, upper(btrim(mel_item))
    having count(*) > 1
  ) d;

  if lista is not null then
    raise exception E'Existem MEL ativas duplicadas. Resolve-as primeiro na app e volta a correr o script:\n%', lista;
  end if;
end $$;

create unique index if not exists mel_records_unique_active_item
  on public.mel_records (fleet, upper(btrim(mel_item)))
  where is_active;
