-- Impedir MEL duplicadas: não pode haver duas MEL ATIVAS na mesma frota com o mesmo MEL Item
-- E o mesmo impacto operacional. O mesmo MEL Item com impactos diferentes é permitido.
-- (As MEL apagadas, no Histórico, não contam. Maiúsculas/minúsculas e espaços a mais são ignorados.)
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.
--
-- Se já existirem duplicados, o script PÁRA e mostra quais são, sem alterar nada.
-- Nesse caso: apaga (na app) as cópias a mais e volta a correr este script.

create or replace function public.mel_impact_key(p text)
returns text
language sql
immutable
as $$
  select md5(lower(btrim(regexp_replace(replace(coalesce(p, ''), chr(160), ' '), '\s+', ' ', 'g'))));
$$;

do $$
declare
  lista text;
begin
  select string_agg(format('%s  %s  (%s registos com o mesmo impacto)', fleet, item, n), E'\n' order by fleet, item)
    into lista
  from (
    select fleet, upper(btrim(mel_item)) as item, count(*) as n
    from public.mel_records
    where is_active
    group by fleet, upper(btrim(mel_item)), public.mel_impact_key(operational_impact)
    having count(*) > 1
  ) d;

  if lista is not null then
    raise exception E'Existem MEL ativas duplicadas (mesmo item e mesmo impacto). Apaga as cópias na app e volta a correr o script:\n%', lista;
  end if;
end $$;

-- Regra antiga (só frota + MEL Item), caso tenha chegado a ser criada
drop index if exists public.mel_records_unique_active_item;

create unique index if not exists mel_records_unique_active_item_impact
  on public.mel_records (fleet, upper(btrim(mel_item)), public.mel_impact_key(operational_impact))
  where is_active;
