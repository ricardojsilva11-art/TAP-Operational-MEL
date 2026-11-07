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
| 7 | `007_favoritos.sql` | Favoritas e usadas recentemente, por utilizador | 001 |

Depois do `001`, importar os registos iniciais (`mel_seed.csv`) para a tabela `mel_records`, antes de continuar com os restantes.

Todos os scripts podem ser corridos outra vez sem estragar nada.

**Regra para alterações futuras:** cada alteração à base de dados é um ficheiro novo com o número seguinte (`007_…`, `008_…`). Não se editam os ficheiros já corridos.
