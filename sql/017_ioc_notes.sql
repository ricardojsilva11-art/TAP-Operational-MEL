-- IOC Notes nas MEL (o «Impacto operacional» passa a chamar-se Dispatch Notes; a coluna mantém-se).
-- Correr uma vez no Supabase: SQL Editor > New query > colar > Run.
alter table public.mel_records add column if not exists ioc_notes text not null default '';
