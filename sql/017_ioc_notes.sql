-- IOC Notes nas MEL, independentes das Dispatch Notes (o antigo «Impacto operacional»).
-- Enquanto estiverem vazias (null), a aplicação mostra nas IOC Notes o texto das Dispatch Notes.
-- Correr uma vez no Supabase: SQL Editor > New query > colar > Run.
alter table public.mel_records add column if not exists ioc_notes text;
alter table public.mel_records add column if not exists ioc_notes_html text;
