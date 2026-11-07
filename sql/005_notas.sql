-- Notas nas MEL (aparecem por baixo do MEL Item).
-- Correr uma vez no Supabase: SQL Editor > New query > colar > Run.
alter table public.mel_records add column if not exists notes text not null default '';
