# Scripts SQL — correr por ordem

Para criar a base de dados do zero, no Supabase (SQL Editor > New query), correr **um de cada vez, por esta ordem**:

| # | Ficheiro | O que faz | Depende de |
|---|----------|-----------|------------|
| 1 | `001_setup.sql` | Tabelas, perfis, auditoria, carimbos temporais do servidor, RLS, Realtime, apagar definitivamente | — |
| 2 | `002_registo_aprovacao.sql` | Contas novas ficam pendentes até aprovação; funções de administrador (listar, aprovar, recusar) | 001 |
| 3 | `003_palavra_passe.sql` | Pedido de nova palavra-passe e definição pelo administrador | 002 |
| 4 | `004_so_consulta.sql` | Utilizadores `reader` só podem consultar (a base de dados recusa alterações) | 001 |
| 5 | `005_notas.sql` | Coluna de notas nas MEL | 001 |
| 6 | `006_duplicados.sql` | Impede MEL ativas iguais (frota + MEL Item + impacto operacional) | 001 |
| 7 | `007_favoritos.sql` | Favoritas, por utilizador | 001 |
| 8 | `008_mudar_palavra_passe.sql` | Palavra-passe definida pelo administrador é temporária: obriga a mudar no próximo início de sessão | 003, 004 |
| 9 | `009_formato_e_tempo_real.sql` | Valida o formato do MEL Item na base de dados; tempo real nos perfis (mudanças de acesso sem recarregar) | 001 |
| 10 | `010_configuracoes.sql` | Configurações: registos de novas contas, duração da sessão, cópia de segurança e revisão da MEL por frota | 002, 008 |
| 11 | `011_anexos_pdf.sql` | Anexos PDF nas MEL (espaço privado `mel-pdfs` no Storage e tabela `mel_attachments`) | 001, 008 |
| 12 | `012_email_valido.sql` | Recusa emails com caracteres escondidos ou símbolos estranhos no registo | — |
| 13 | `013_eliminar_utilizador.sql` | Eliminar contas (também aprovadas) na página Utilizadores, mantendo as MEL e o histórico | 002 |
| 14 | `014_definicoes_taf.sql` | Definições do TAF partilhadas: o Administrador altera e valem para todos, em tempo real | 002, 008 |
| 15 | `015_taf_favoritos.sql` | Aeroportos favoritos no TAF (estrela), de cada utilizador | 002 |
| 16 | `016_taf_vistos.sql` | TAF novos/AMD já vistos, iguais em todos os aparelhos de cada utilizador | 002 |

Depois do `001`, importar os registos iniciais (`mel_seed.csv`) para a tabela `mel_records`, antes de continuar com os restantes.

Todos os scripts podem ser corridos outra vez sem estragar nada.

**Regra para alterações futuras:** cada alteração à base de dados é um ficheiro novo com o número seguinte (`007_…`, `008_…`). Não se editam os ficheiros já corridos.
