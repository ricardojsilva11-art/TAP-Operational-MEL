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
| **Line OPS** (`reader`, só consulta) | Ver o TAF e as MEL, pesquisar, copiar, exportar e marcar favoritas. Não pode adicionar, alterar ou apagar MEL. |
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
Ecrã dividido a meio. **À esquerda, TAF:**
- **TAF novos / AMD com alerta, por ver:** só contam TAF novos ou emendados que cumprem os critérios de alerta da análise de TAF; um TAF emendado sem alerta não aparece. Cada um sai da lista e do contador quando abres esse aeroporto (no Início, no aviso do canto ou na grelha do TAF); os outros continuam por ver. "Marcar todos como vistos" limpa tudo de uma vez.
- **Em alerta agora / próximas 8 h:** só destinos; clicar no número abre o TAF já com esse filtro.
- **Meteorologia nos destinos – resumo:** (agora e próximas 8 h) todos os destinos em alerta (primeiro os que estão agora; a lista tem scroll próprio no PC), uma linha cada: o período em formato TAF, dia e hora UTC (ex.: 1102/1115; vermelho = já em alerta, laranja = a começar; → = continua para lá do TAF), todas as categorias de alerta nesse período (LVO, Thunderstorm, Wind / gust…) e os valores do TAF que as causam (ex.: VIS400m FG BKN002 TSRA G35); "Ver todos" abre o TAF filtrado. Carregar numa linha abre o painel lateral desse aeroporto.

**À direita, Voos afetados** (por cima da MEL): arrastar o PDF da lista de voos para a faixa tracejada (ou carregar nela para escolher o ficheiro). Conta só a meteorologia no **destino, à hora de chegada** (ETA ou STA). Mostra quantos voos têm **restrição** (LVO, abaixo dos mínimos, RVAC, fora dos limites de vento / aterragem não permitida) e quantos têm **alerta** (trovoada, vento, teto baixo…), e a lista dos voos afetados: voo, rota, hora de chegada, alerta e condição do TAF. Carregar num voo abre esse aeroporto no TAF; "Copiar tabela" cola no Outlook/Teams. Ver "Voos" em TAF.

**À direita, MEL:** as MEL adicionadas, alteradas ou apagadas nas últimas 24 horas (mais recentes primeiro), com o texto todo do impacto operacional e as notas, quem alterou e quando; separadores por frota e pesquisa que filtra logo.

### TAF
- É o TAF Monitor tal como era, com a mesma grelha, filtros e painel lateral, agora dentro do portal e com a mesma entrada das MEL. Aberto diretamente (`/taf/`) reencaminha para o portal.
- O número vermelho no separador **Início** conta os TAF novos ou emendados (AMD) **com alerta** que ainda não viste; cada um conta como visto quando abres esse aeroporto, e o número só volta a subir quando chega outro TAF novo ou emenda com alerta. Passar o rato por cima do número mostra quais os aeroportos. Quando chega um TAF novo ou emenda aparece um aviso no canto a dizer qual o aeroporto (ex.: "TAF emendado (AMD): LPMA Madeira"); carregar no aviso abre o TAF nesse aeroporto. No Início, os que ainda não viste ficam destacados.
- **Definições do TAF:** só Administradores do portal (deixou de haver PIN). Ficam guardadas no Supabase (`sql/014_definicoes_taf.sql`) e valem para todos; quando o Administrador grava, o TAF de todos atualiza logo. Só o modo (ao vivo / exemplo / manual) fica no navegador do Administrador, para testes não afetarem ninguém; os outros veem sempre ao vivo. As definições que um Administrador tinha no site antigo do TAF Monitor são trazidas para o portal na primeira vez que abre o link antigo.
- Os TAF/METAR vêm do Worker `taf` (Cloudflare). Esse Worker tem de aceitar pedidos do endereço do portal (variável `ALLOWED_ORIGIN` = `https://ricardojsilva11-art.github.io`).
- **METAR e TAF anteriores:** no painel de cada aeroporto aparecem o último METAR e o anterior, com o que mudou assinalado a azul claro; no painel, o TAF atual também assinala o que mudou em relação ao TAF anterior (que aparece por baixo). "Esconder anterior" esconde o METAR/TAF anterior (fica lembrado no browser). O Worker `taf` devolve os METAR das últimas 2 h (`&hours=2`); sem isso, o anterior é o último que este browser viu.
- **Aeroportos favoritos:** a estrela (☆/★) ao lado do código na grelha do TAF e em cada linha de "Meteorologia nos destinos – resumo" marca o aeroporto como favorito. É de cada utilizador e fica igual em todos os aparelhos (`sql/015_taf_favoritos.sql`; sem essa tabela fica só no browser). No Início e na grelha do TAF, os favoritos aparecem no topo (na vista por regiões, num grupo "★ Favoritos").
- **Voos:** botão **Voos** no TAF (ou o cartão "Voos afetados" do Início). O PDF da lista de voos é lido **só no browser** (pdf.js 3.11.174 em `vendor/`, licença Apache-2.0) e a lista fica **só nesse browser** (`localStorage`, apagada ao terminar sessão): não vai para o Supabase nem para outro serviço. De cada linha com um voo TP tira origem e destino (IATA ou ICAO da lista do TAF) e as horas. Na Flight List do sistema de operações (STD e ETD em dia-hora-minuto, ex.: 220850 / 220945E, sem hora de chegada) a **ETA é estimada**: ETD (ou STD) + tempo de voo. O tempo de voo vem da **tabela de tempos de bloco partilhada**: um Administrador arrasta uma vez o Excel com as colunas voo, DEP, DEST e BLOCK em minutos para o cartão "Voos afetados" e a tabela fica nas definições do TAF no Supabase (`taf_settings.cfg.blocks`, só utilizadores com sessão; não vai para o repositório, que é público), já carregada para todos; para atualizar, o Administrador arrasta o Excel novo. Os outros utilizadores só carregam o PDF do dia. O tempo é procurado **só pela rota** (origem e destino), sem olhar ao número do voo, por isso voos extra e renumerados também usam a tabela; se a rota tiver vários voos, usa o tempo mediano dessa rota. Se a rota de um voo do PDF não estiver na tabela, o cartão mostra um aviso com esses voos e a ETA é estimada pela distância (43 min + distância a 453 kt, até +6 % para oeste; coordenadas OurAirports). O alerta no destino conta **da ETA até 1 h depois** (a ETA aparece com ~), com as horas exatas dos grupos do TAF (um BECMG em curso mantém a condição anterior até ao fim do período); intensidade (+/−) e MIST não contam como impacto nos voos. Noutros formatos usa STD, STA, ETD e ETA (UTC) se existirem, e cruza com o TAF do destino à hora de chegada (só o destino), com todas as categorias de alerta e todos os aeroportos do TAF Monitor (não depende das escolhas do Relatório). O número do voo repetido noutra coluna não conta como hora; "Todos os voos lidos" mostra as horas e o destino lidos de cada voo, para conferir. Na grelha, cada voo com alerta à chegada aparece como um **✈** no canto da célula da hora em que fica afetado (com o número de voos se houver mais de um, ex.: ✈2); passar o rato mostra os voos (rota, ETA, período afetado e alerta) e carregar na célula abre o aeroporto: meteorologia na lateral e o quadro Voos afetados por baixo da grelha. Ao selecionar um aeroporto com voos afetados, o painel lateral continua só com a meteorologia e aparece **por baixo da grelha** o quadro **Voos afetados**: tabela com voo, rota, ETD → ETA, a hora em que o voo está afetado, o alerta e a condição; o TAF com a parte que afeta cada voo sublinhada e a etiqueta do voo e da hora; e uma linha do tempo com os alertas, o voo no ar e a hora seguinte à chegada. Carregar num voo da tabela mostra só esse voo no TAF sublinhado e na linha do tempo (abre no primeiro voo; "ver todos" mostra todos). O quadro e o painel lateral fecham cada um no seu ×, independentemente; o painel lateral muda de largura pela pega à esquerda e o quadro muda de altura pela pega no topo (duplo clique repõe). Os voos que já aterraram (chegada antes da hora atual) deixam de contar. No **Relatório** do TAF, com uma lista de voos carregada, aparece a coluna **VOOS** na mesma linha de cada aeroporto: os voos por aterrar cuja chegada cai no período do alerta (da ETA até 1 h depois), só o número do voo (4 por linha dentro da célula), também na faixa Personalizada; vai também no "Copiar tabela" e no .txt. Voos para aeroportos fora da lista do TAF aparecem como "fora da lista". Os voos são recalculados sempre que os TAF atualizam. Em "Texto lido do PDF" pode ver-se e corrigir o que foi lido (ou colar a lista à mão). O formato do PDF real ainda tem de ser confirmado: o leitor procura voo, aeroportos e horas em cada linha, sem depender de colunas fixas.
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

### TAF em janela no Início

No Início, carregar num aeroporto de "TAF novos ou emendas com alerta" ou de "Meteorologia nos destinos – resumo" abre o TAF numa janela (sem sair do Início): o TAF com a condição sublinhada na cor do alerta. "Abrir no TAF Monitor" leva ao painel desse aeroporto. Abrir a janela conta como TAF visto.

Nas listas do Início (TAF novos/AMD e destinos em alerta), a bola tem a cor da condição mais penalizante que o TAF prevê e as listas vêm ordenadas por gravidade (fora dos limites/abaixo dos mínimos, LVO, trovoada, teto baixo/RVAC, neve/gelo, vento…); nos destinos, os favoritos ficam primeiro.

Filtro **✈ Com voos** (junto a Todos / Com alertas / Alerta agora): mostra só os aeroportos com voos afetados, com o número entre parênteses; só aparece quando há lista de voos carregada.

### Mínimos de aproximação (cartas Lido)

Um Administrador arrasta o ficheiro de mínimos (`.json`, preparado a partir das cartas Lido, categoria C) para o cartão "Voos afetados" do Início; fica nas definições do TAF no Supabase (`taf_settings.cfg.minima`, só utilizadores com sessão) e vale para todos. Por pista: **BELOW MIN** abaixo do DH/MDH ou do RVR/VIS da melhor aproximação (sem LPV); **RVAC** até ao CAT I + 200 ft / + 1000 m (pista sem ILS: a melhor aproximação); o **LVO** mantém os limites das Definições (fuel policy). A pista é a estimada pelo vento. Os mínimos de LIS, OPO, FAO, FNC, PDL, TER, BCN, MAD, SVQ, AGP, BIO e VLC (cartas Lido, Cat C) já vêm incluídos no site e valem para todos sem carregar nada; um ficheiro carregado pelo Administrador substitui-os. Os aeroportos que não estão no ficheiro mantêm os mínimos de origem. O painel lateral mostra a tabela dos mínimos de cada pista.

### Layout v2

Paleta: BMIN vermelho (o mais limitativo), LIM magenta, LVO laranja, TS roxo, RVAC amarelo, SN azul, WND verde-azulado, teto baixo oliva. As células da grelha mostram um código curto (BMIN, LVO, RVAC, TS, WND, SN, CIG…) e, por baixo, a pista ou a condição. Os controlos do TAF ficam numa só barra (contadores que filtram, zona e categorias em menus, pesquisa). O painel do aeroporto abre com o resumo do alerta (agora e a seguir), os mínimos da pista e o próximo voo afetado; depois pistas/mínimos e TAF; METAR, limites de vento, janelas e grupos ficam recolhidos por omissão. O Início tem uma faixa de turno (destinos em restrição, voos afetados, próximo voo afetado, TAF novos/AMD por ver). No telemóvel, o TAF mostra cartões dos aeroportos em alerta em vez da grelha.

No quadro **Voos afetados**, a coluna **Fonte** indica de onde vem o alerta: voos que já saíram (ETD/STD já passou) são lidos pelo **METAR** atual do destino (se tiver até 90 min; o METAR aparece com a condição sublinhada e "Afetado: agora"); voos que ainda não saíram, ou sem METAR recente, são lidos pelo **TAF** da ETA até 1 h depois. O ✈ da grelha, o Início e o relatório continuam pelo TAF.
