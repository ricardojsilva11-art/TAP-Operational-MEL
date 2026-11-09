-- Anexos PDF nas MEL.
--  • Os ficheiros ficam num espaço privado do Supabase Storage ("mel-pdfs"), só PDF, até 20 MB cada.
--  • Todos os utilizadores ativos podem abrir os anexos; operadores e administradores podem anexar e apagar.
--  • Os ficheiros só se abrem com um link temporário gerado pela app para quem tem sessão iniciada.
-- Correr uma vez no Supabase: SQL Editor > New query > colar tudo > Run.

-- 1) Espaço de armazenamento privado
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('mel-pdfs', 'mel-pdfs', false, 20971520, array['application/pdf'])
on conflict (id) do update
  set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists mel_pdfs_read on storage.objects;
create policy mel_pdfs_read on storage.objects for select to authenticated
using (bucket_id = 'mel-pdfs' and public.current_user_role() is not null);

drop policy if exists mel_pdfs_insert on storage.objects;
create policy mel_pdfs_insert on storage.objects for insert to authenticated
with check (bucket_id = 'mel-pdfs' and public.current_user_can_edit());

drop policy if exists mel_pdfs_delete on storage.objects;
create policy mel_pdfs_delete on storage.objects for delete to authenticated
using (bucket_id = 'mel-pdfs' and public.current_user_can_edit());

-- 2) Lista de anexos de cada MEL
create table if not exists public.mel_attachments (
  id uuid primary key default gen_random_uuid(),
  record_id uuid not null references public.mel_records(id) on delete cascade,
  file_name text not null check (length(file_name) between 1 and 200),
  storage_path text not null unique,
  size_bytes bigint not null default 0,
  uploaded_by uuid default auth.uid(),
  uploaded_by_name text,
  uploaded_at timestamptz not null default now()
);
create index if not exists mel_attachments_record_idx on public.mel_attachments (record_id);

create or replace function public.mel_attachments_stamp()
returns trigger language plpgsql security definer set search_path = public
as $$
begin
  new.uploaded_by := auth.uid();
  new.uploaded_at := now();
  select display_name into new.uploaded_by_name from public.user_profiles where user_id = auth.uid();
  return new;
end;
$$;
drop trigger if exists mel_attachments_stamp on public.mel_attachments;
create trigger mel_attachments_stamp before insert on public.mel_attachments
for each row execute function public.mel_attachments_stamp();

alter table public.mel_attachments enable row level security;
drop policy if exists attachments_read on public.mel_attachments;
create policy attachments_read on public.mel_attachments for select to authenticated
using (public.current_user_role() is not null);
drop policy if exists attachments_insert on public.mel_attachments;
create policy attachments_insert on public.mel_attachments for insert to authenticated
with check (public.current_user_can_edit());
drop policy if exists attachments_delete on public.mel_attachments;
create policy attachments_delete on public.mel_attachments for delete to authenticated
using (public.current_user_can_edit());
revoke all on public.mel_attachments from anon;
grant select, insert, delete on public.mel_attachments to authenticated;

-- 3) Tempo real: anexos novos ou apagados aparecem logo aos outros utilizadores
do $$ begin
  if not exists (select 1 from pg_publication_tables
                 where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'mel_attachments') then
    alter publication supabase_realtime add table public.mel_attachments;
  end if;
end $$;
