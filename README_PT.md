# TAP Operational Control (TAF · MEL)

Portal web partilhado com uma única entrada para duas ferramentas: o **TAF Monitor** (alertas dos TAF por aeroporto) e a **MEL operacional** da TAP (A320, A330, E190/E195, a partir do ficheiro original `TAP MELs.xlsx`). Os dados das MEL ficam numa base de dados Supabase; o portal é uma página estática publicada no GitHub Pages.

**Portal:** https://ricardojsilva11-art.github.io/TAP-Operational-MEL/ (o link antigo do TAF Monitor reencaminha para aqui, separador TAF)

## Antes de começar — segurança
Estes dados são de contexto operacional de aviação. Não publicar nem carregar dados em serviços externos sem aprovação formal de IT/Segurança/owner dos dados da TAP. Esta aplicação é uma ferramenta de apoio: não é uma aprovação operacional nem uma certificação. Confirmar sempre a documentação MEL aprovada e os procedimentos em vigor.

Este repositório tem **apenas o código**. As MEL nunca são guardadas aqui: estão no Supabase, protegidas por regras de acesso (RLS), e só utilizadores aprovados as conseguem ler.

## Conteúdo do repositório
- `index.html` — a aplicação: entrada e registo, pesquisa, filtros por frota, favoritas, criação/edição com formatação, histórico de MEL apagadas, gestão de utilizadores, exportação para Excel, atualização em tempo real e consulta offline.
- `taf/index.html` — o TAF Monitor, aberto dentro do portal (separador **TAF**). É gerado a partir de `tools/taf-monitor-original.html` com `python3 tools/build_taf.py` (ver "TAF" abaixo). Não editar à mão.
- `tools/` — fonte original do TAF Monitor e o script que o adapta ao portal.
- `config.js` — URL e chave pública (publishable/anon) do projeto Supabase. Nunca colocar aqui a `service_role`/secret key.
- `tests/` e `.github/workflows/` — testes automáticos (ver abaixo).
- `sql/` — scripts da base de dados, numerados pela ordem em que se correm. Ver `sql/LEIAME.md`.
- `vendor/` — biblioteca Supabase JS (versão 2.119.0 fixa, copiada do pacote oficial do npm, com licença MIT). Para atualizar: substituir o ficheiro por uma versão nova, mudar o nome no `index.html` e no `sw.js`, e recalcular o `integrity`.
- `img/` — fotografias das frotas (A320, A330, E190/E195).
- `sw.js`, `manifest.webmanifest`, `icon-192.png`, `icon-512.png` — permitem abrir a app sem rede e instalá-la no telemóvel ou no PC.
- `manifest.txt` — contagem dos 365 registos iniciais (A320 184, A330 98, E190/E195 83) e a sua origem.

## Como funciona o acesso
1. **Registo:** qualquer pessoa pode criar conta na própria app (separador "Criar conta", com nome, email e palavra-passe).
2. **Pendente:** a conta nova fica **Pendente** e sem acesso a nenhuma MEL até ser aprovada. Se a confirmação de email estiver ativa no Supabase, a pessoa tem também de confirmar o email.
3. **Aprovação:** um administrador abre a página **Utilizadores**, escolhe o tipo de acesso e carrega em **Aprovar**. Também pode **Recusar** (apaga um registo pendente), **Desativar** uma conta aprovada ou **Eliminar** uma conta de vez (as MEL e o histórico dessa pessoa mantêm-se, com o nome).
4. **Esqueci-me da palavra-passe:** o pedido é feito no ecrã de entrada e aparece ao administrador na página Utilizadores. O administrador define uma **palavra-passe temporária** e comunica-a; no início de sessão seguinte a pessoa é obrigada a escolher uma nova antes de continuar.

### Tipos de acesso
| Tipo | Pode |
|------|------|
| **Só consulta** (`reader`) | Ver o TAF e as MEL, pesquisar, copiar, exportar e marcar favoritas. Não pode adicionar, alterar ou apagar MEL. |
| **Supervisor** (`operator`) | O mesmo, mais adicionar, editar, apagar e reativar MEL. |
| **Administrador** (`admin`) | O mesmo, mais alterar as **Definições do TAF**, aprovar/recusar/desativar contas, definir palavras-passe temporárias e apagar definitivamente MEL do Histórico. |

Todas as contas aprovadas têm acesso ao TAF; não é preciso aprovar nada à parte.

As permissões são aplicadas pela base de dados, não só pela app: uma conta pendente, desativada, só de consulta ou com palavra-passe temporária por mudar é recusada pelo servidor mesmo que tente aceder sem passar pela app.

## Montar tudo de raiz

### Passo 1 — criar o projeto Supabase
1. Criar um projeto Supabase dedicado, idealmente numa organização controlada pela empresa.
2. Guardar o Project URL e a publishable key (ou anon key legada).
3. No SQL Editor, correr os scripts da pasta `sql/` por ordem, um de cada vez, como explicado em `sql/LEIAME.md`. Os registos iniciais importam-se logo a seguir ao `001` (passo 3).

### Passo 2 — configurar a autenticação
Em **Authentication > Sign In / Providers**:
1. Manter **Email** ativo.
2. Manter **Allow new users to sign up** ligado — é o que permite criar conta na app. A segurança vem da aprovação: nenhuma conta nova tem acesso sem um administrador a aprovar.
3. **Confirm email:** recomendado ligado. Nesse caso, configurar um SMTP de domínio autorizado em **Authentication > Emails**; o envio de email incluído no Supabase é muito limitado e não serve para uso real.

Em **Authentication > URL Configuration**, pôr o endereço publicado da app (o link do topo deste ficheiro) como **Site URL** e em **Redirect URLs**, para o link de confirmação de email voltar à app.

### Passo 3 — importar os registos iniciais
1. No Table Editor, abrir `mel_records` e usar **Import data from CSV** com o ficheiro `mel_seed.csv` (guardado fora deste repositório).
2. Mapear `legacy_id`, `fleet`, `mel_item`, `operational_impact`, `is_active`. Deixar `id`, `created_by`, `updated_by`, `created_at` e `updated_at` vazios.
3. Confirmar 365 linhas (184 / 98 / 83). Estes registos aparecem como "Importado" até alguém os editar.
4. Importar uma única vez, num projeto vazio.

### Passo 4 — criar o primeiro administrador
1. Abrir a app e criar conta normalmente (fica Pendente, como todas).
2. No SQL Editor, substituindo o email:
   ```sql
   update public.user_profiles
      set role = 'admin', active = true, approved_at = now()
    where user_id = (select id from auth.users where email = 'ADMIN_EMAIL');
   ```
3. Entrar na app. A partir daqui, todas as aprovações fazem-se na página **Utilizadores**.

### Passo 5 — configurar e publicar a app
1. Editar `config.js` com o `SUPABASE_URL` e a `SUPABASE_ANON_KEY` do projeto.
2. Para testar localmente, usar um servidor web local (não abrir como `file://`).
3. Publicar no GitHub Pages (ou outro alojamento estático aprovado pela TAP).
4. Testar registo e aprovação, entrada, leitura, criação, edição, exportação e sincronização em dois browsers/dispositivos.

## Funcionalidades

### Início
Ecrã dividido a meio. **À esquerda, TAF:** TAF novos ou emendados (AMD) na última hora e **destinos** em alerta agora e nas próximas 6 h; clicar num número abre o TAF já com esse filtro, e clicar num aeroporto abre o painel lateral desse aeroporto. **À direita, MEL:** as MEL adicionadas, alteradas ou apagadas nas últimas 24 horas (mais recentes primeiro), com o texto todo do impacto operacional e as notas, quem alterou e quando; separadores por frota e pesquisa que filtra logo. O botão **MEL** de cada uma abre-a na página MEL (copiar, anexos, editar).

### TAF
- É o TAF Monitor tal como era, com a mesma grelha, filtros e painel lateral, agora dentro do portal e com a mesma entrada das MEL. Aberto diretamente (`/taf/`) reencaminha para o portal.
- O número vermelho no separador **TAF** conta os TAF novos ou emendados (AMD) que ainda não viste; limpa quando abres o separador TAF e só volta a aparecer quando chega outro TAF novo ou emenda.
- **Definições do TAF:** só Administradores do portal (deixou de haver PIN). Ficam guardadas no Supabase (`sql/014_definicoes_taf.sql`) e valem para todos; quando o Administrador grava, o TAF de todos atualiza logo. Só o modo (ao vivo / exemplo / manual) fica no navegador do Administrador, para testes não afetarem ninguém; os outros veem sempre ao vivo. As definições que um Administrador tinha no site antigo do TAF Monitor são trazidas para o portal na primeira vez que abre o link antigo.
- Os TAF/METAR vêm do Worker `taf` (Cloudflare). Esse Worker tem de aceitar pedidos do endereço do portal (variável `ALLOWED_ORIGIN` = `https://ricardojsilva11-art.github.io`).
- **Atualizar o TAF Monitor:** substituir `tools/taf-monitor-original.html` pela versão nova e correr `python3 tools/build_taf.py`; o script avisa se alguma parte que adapta deixou de existir.

### MEL
- **MEL Item** tem de seguir o formato `M-00-00` ou `C-00`, com mais grupos se for preciso e até 2 letras no fim, juntas ou depois de hífen (ex.: `M-34-50`, `M-21-26-01-02`, `C-21-01`, `M-21-26-01A`, `M-21-51-00-A`). Comentários vão nas Notas, não no MEL Item. Fora disto não grava — a regra é aplicada também pela base de dados.
- Ao adicionar, pode escolher-se mais de uma frota de uma vez.
- **Notas** opcionais, que aparecem por baixo do MEL Item.
- **Duplicados:** não pode haver duas MEL ativas na mesma frota com o mesmo MEL Item e o mesmo impacto operacional. O mesmo item com impactos diferentes é permitido. As MEL do Histórico não contam.
- **Histórico:** apagar uma MEL só a desativa. Pode ser **reativada** no separador Histórico; um administrador pode apagá-la definitivamente.
- Quem fez cada registo e quando é definido pelo servidor, não pelo browser. A tabela `mel_audit_log` guarda o estado antes e depois de cada alteração.
- **Ver alterações** (ícone do relógio em cada MEL, também no Histórico): mostra quem mudou, quando e o quê, com o texto retirado a vermelho e o acrescentado a verde. Supervisores e administradores podem **repor** uma versão anterior; a reposição fica também registada.

### Tempo real
- Quando outra pessoa adiciona, altera, apaga ou reativa uma MEL, aparece um aviso discreto no canto do ecrã ("Ana alterou M-21-26-01 (A320)"). Carregar no aviso leva à MEL, que fica realçada por instantes.
- Se um administrador mudar o tipo de acesso de alguém, a app dessa pessoa ajusta-se logo, sem recarregar. Se a conta for desativada, a sessão termina; se for definida uma palavra-passe temporária, a pessoa tem de a mudar.

### Anexos PDF
- Botão do clipe em cada MEL (também no Histórico), com o número de anexos. Abre a lista de PDFs dessa MEL: abrir, descarregar e, para supervisores e administradores, anexar (escolher ou arrastar) e apagar.
- Também se anexam no próprio formulário **Adicionar/Editar MEL** (secção "Anexos PDF"): os ficheiros novos e os retirados só são enviados/apagados ao carregar em **Guardar**; **Cancelar** não altera nada. Ao adicionar para várias frotas, o PDF fica anexado a cada uma.
- Só PDF, até 20 MB cada. Os ficheiros ficam num espaço privado do Supabase Storage e só abrem com um link temporário (5 minutos) gerado para quem tem sessão iniciada.
- Ao apagar definitivamente uma MEL do Histórico, os anexos são apagados também. Os anexos não estão disponíveis em modo offline nem entram no Excel.

### Pesquisa e favoritas
- A pesquisa ignora acentos e hífens: `212601`, `21-26` ou `m212601` encontram `M-21-26-01`; `pressao` encontra "pressão". Várias palavras têm de aparecer todas. O termo encontrado fica realçado.
- Atalho `/` para ir à caixa de pesquisa; `Esc` limpa a pesquisa.
- Estrela antes de cada MEL Item para a marcar como favorita; o filtro "Favoritas" mostra só essas. As favoritas são de cada utilizador e ficam no servidor, por isso são as mesmas no PC e no telemóvel.

### Consulta offline
Se a internet ou o Supabase falharem, a app mostra a última cópia das MEL guardada no próprio dispositivo, em modo só de consulta, com o aviso "Sem ligação ao servidor… dados das HH:MM". Pesquisar, copiar e exportar continuam a funcionar.
- A cópia é atualizada sempre que a app carrega dados do servidor. É preciso ter aberto a app pelo menos uma vez com ligação nesse dispositivo.
- A app tenta voltar a ligar a cada minuto, ou quando se carrega em "Tentar ligar".
- **Terminar sessão** apaga a cópia do dispositivo. Em PCs partilhados, terminar sempre a sessão no fim do turno.

### Configurações (só administradores)
- **Cópia de segurança:** descarrega um Excel com todas as MEL (ativas e do Histórico), notas, texto formatado e revisões. A página mostra a data e o autor da última cópia e avisa se já passaram mais de 7 dias.
- **Registos de novas contas:** abrir ou fechar a criação de conta na app. Fechados, o separador "Criar conta" desaparece e a base de dados recusa registos novos (o painel do Supabase continua a poder criar utilizadores).
- **Duração da sessão:** 4, 8, 12 ou 24 horas sem atividade, ou sem limite. Ao fim desse tempo, a sessão termina nesse dispositivo e a cópia offline é apagada.
- **Revisão da MEL por frota:** número e data da revisão em vigor. Aparece nos cartões das frotas e numa coluna do Excel exportado.
- **Atividade recente:** todas as alterações (últimas 24 h, 7, 30 ou 90 dias), filtráveis por frota e pessoa. Carregar numa linha abre o histórico dessa MEL.

## Testes automáticos
A pasta `tests/` tem testes que abrem a app num browser com um Supabase simulado (não tocam na base de dados real): modo offline, pesquisa, favoritas, palavra-passe temporária, tipos de acesso, nomes de utilizadores, histórico de alterações, exportação Excel e Configurações.
- Correm sozinhos no GitHub a cada alteração (separador **Actions** do repositório, ficheiro `.github/workflows/testes.yml`). Um ✓ verde ao lado do commit quer dizer que passaram; um ✗ vermelho quer dizer que alguma coisa se partiu.
- Para correr no próprio computador: `pip install -r tests/requirements.txt`, `python -m playwright install chromium` e `python -m pytest tests`.

## Notas técnicas e pendentes
- A app usa Realtime do Supabase para atualizar a lista nos outros utilizadores sem recarregar.
- O Supabase JS está alojado no próprio repositório (`vendor/`, versão 2.119.0 fixa, com verificação `integrity`). O SheetJS vem de `cdn.sheetjs.com`, a fonte oficial, fixado na versão 0.20.3.
- Os nomes apresentados vêm do nome dado no registo; o administrador pode corrigi-los na página **Utilizadores** (lápis ao lado do nome). As MEL já gravadas mantêm o nome que estava em uso quando foram alteradas.
- Antes de uso em produção: revisão de segurança, backups e reposição, monitorização, política de retenção e validação documental/operacional com a TAP.
