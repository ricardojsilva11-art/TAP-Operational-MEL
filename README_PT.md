# TAP Operational MEL — pacote cloud multiutilizador

Este pacote contém a base inicial para migrar a aplicação local para uma aplicação partilhada. Foram extraídos **365 registos** do protótipo v21: A320 184, A330 98, E190/E195 83.

## Conteúdo
- `index.html` — interface web com login, pesquisa, filtros, criação/edição, formatação básica, exportação Excel e atualização em tempo real.
- `config.js` — preencher com o URL e a chave pública do projeto Supabase.
- `sql/` — scripts da base de dados, numerados pela ordem em que se correm (ver `sql/LEIAME.md`).
- `mel_seed.csv` — 365 registos iniciais para importação.

## Antes de começar — segurança
Como estes dados são de contexto operacional de aviação, não publicar nem carregar dados em serviços externos sem aprovação formal de IT/Segurança/owner dos dados da TAP. Este pacote é uma implementação técnica inicial, não uma aprovação operacional nem uma certificação.

## Passo 1 — criar Supabase
1. Criar um projeto Supabase dedicado, idealmente numa organização controlada pela empresa.
2. Guardar o Project URL e a publishable key (ou anon key legada). Nunca usar `service_role`/secret key no browser.
3. No SQL Editor, correr os scripts da pasta `sql/` por ordem (`001` a `008`), um de cada vez. Ver `sql/LEIAME.md`.
4. Em Authentication > Sign In / Providers, manter email/password ativo e desativar inscrições públicas. Utilizar convites apenas.
5. Configurar SMTP de domínio autorizado antes de convidar utilizadores reais.

## Passo 2 — criar administrador e convidar a equipa
1. Em Authentication > Users, convidar o primeiro utilizador administrador.
2. Após o trigger criar o perfil, executar no SQL Editor, substituindo o email: `update public.user_profiles set role='admin' where user_id=(select id from auth.users where email='ADMIN_EMAIL');`
3. Convidar cada operador em Authentication > Users. Os perfis são criados automaticamente com role `operator`.
4. Para utilizador só de consulta, mudar role para `reader`. Para desativar acesso, definir `active=false`.

## Passo 3 — importar os 365 registos
1. No Supabase Table Editor, abrir `mel_records` e usar Import data from CSV.
2. Importar `mel_seed.csv`. Mapear `legacy_id`, `fleet`, `mel_item`, `operational_impact`, `is_active`. Deixar `id`, `created_by`, `updated_by`, `created_at`, `updated_at` sem valor para usar defaults.
3. Confirmar 365 linhas e distribuição 184/98/83. Os registos importados não recebem um nome de criador fictício; são identificados como `Importado` até serem editados por um utilizador autenticado.

## Passo 4 — configurar e publicar a aplicação
1. Editar `config.js`: `SUPABASE_URL` e `SUPABASE_ANON_KEY` com os valores do projeto.
2. Testar primeiro localmente através de um servidor web local (não abrir como `file://`).
3. Publicar `index.html` e `config.js` num projeto GitHub Pages (ou outro alojamento estático aprovado pela TAP), ligado a repositório Git privado ou upload controlado.
4. Configurar o URL autorizado de redirecionamento no Supabase Auth para o domínio publicado.
5. Testar login, leitura, criação, edição, exportação e sincronização em dois browsers/dispositivos.

## Modelo de permissões
- `operator`: consultar, criar e editar registos.
- `admin`: o mesmo, mais gestão de perfis no Supabase e permissões administrativas.
- `reader`: apenas consultar e exportar.
- Utilizadores desativados (`active=false`) não conseguem ler/escrever.

## Notas técnicas e limitações desta primeira entrega
- A identificação do utilizador e os timestamps de criação/edição são definidos no PostgreSQL por trigger; não dependem do nome digitado nem do relógio do dispositivo.
- A tabela `mel_audit_log` guarda snapshots anteriores e posteriores das alterações.
- A aplicação usa Realtime para atualizar a lista nos outros clientes.
- A importação CSV deve ser feita uma única vez num projeto vazio. Não repetir sobre dados já carregados sem limpar/reconciliar os registos.
- Os nomes apresentados dependem do perfil criado a partir do email; o administrador deve corrigir `display_name` para o nome profissional correto.
- O protótipo é uma base de implementação. Antes de produção, fazer revisão de segurança, testes de concorrência, backups/restore, monitorização, política de retenção e validação documental/operacional com a TAP.
- O código carrega Supabase JS e SheetJS a partir de CDN; para produção, fixar versões e avaliar self-hosting conforme a política de IT.

## MEL duplicadas
Correr `sql/006_duplicados.sql` uma vez no SQL Editor. Impede duas MEL ativas na mesma frota com o mesmo MEL Item e o mesmo impacto operacional; o mesmo item com impactos diferentes é permitido (as do Histórico não contam). Se já houver duplicados, o script não altera nada e mostra a lista para resolver primeiro.

## Consulta offline
Se a internet ou o Supabase falharem, a app mostra a última cópia das MEL guardada no próprio dispositivo, em modo só de consulta, com o aviso "Sem ligação ao servidor… dados das HH:MM". Pesquisar, copiar e exportar continuam a funcionar.
- A cópia é atualizada sempre que a app carrega dados do servidor. É preciso ter aberto a app pelo menos uma vez com ligação nesse dispositivo.
- A app tenta voltar a ligar a cada minuto, ou quando se carrega em "Tentar ligar".
- "Terminar sessão" apaga a cópia do dispositivo. A cópia também é apagada se a sessão expirar e o servidor estiver disponível.
- `sw.js` (service worker) guarda a própria app para abrir sem rede; `manifest.webmanifest` e os ícones permitem instalá-la como app no telemóvel ou no PC.

## Pesquisa e favoritas
- A pesquisa ignora acentos e hífens: `212601`, `21-26` ou `m212601` encontram `M-21-26-01`; `pressao` encontra "pressão". Várias palavras têm de aparecer todas. O termo encontrado fica realçado.
- Atalho `/` para ir à caixa de pesquisa; `Esc` limpa a pesquisa.
- Estrela antes de cada MEL Item para a marcar como favorita. O filtro "Favoritas" mostra só essas.
- As favoritas são de cada utilizador e ficam guardadas no servidor (`sql/007_favoritos.sql`), por isso são as mesmas no PC e no telemóvel.

## Palavra-passe temporária
Quando o administrador define uma palavra-passe a alguém (página Utilizadores), essa palavra-passe é temporária. No próximo início de sessão a pessoa tem de escolher uma nova antes de ver a app; enquanto não o fizer, a base de dados também não lhe mostra MEL (`sql/008_mudar_palavra_passe.sql`). O administrador não pode usar esta função na própria conta; para isso usa o botão da chave, no topo.
