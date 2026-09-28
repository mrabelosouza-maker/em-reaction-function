# EM Reaction Functions — design

Spec de desenho. 2026-09-28. Decisões do analista tomadas em sessão de brainstorming.

---

## 1. Objetivo

Um site no GitHub Pages, no molde de `Modelagem\fomc_reaction_functions`, que mostre a
postura hawk-dove dos BCs emergentes acompanhados (Banxico, BCCh, BanRep, SARB) em
duas trilhas:

- **colegiado** — comunicado, ata (futuramente RTI): a voz oficial do Board;
- **membro** — falas públicas e calls privados de membros individuais.

A pergunta central: *qual o nível do Board ao longo do tempo, e qual membro está
descolado dele?*

## 2. Escopo da v1

| dentro | fora (depois) |
|---|---|
| Banxico | BCCh, BanRep, SARB |
| Comunicados e atas desde **jan/2025** (~14 comunicados, ~13 atas) | RTI / Informe Trimestral |
| Integração da skill `bc-hawk-dove` para membros daqui em diante | Backfill do histórico de calls do Notion (37 notas em `Vault\raw\calls\MX\`) |
| Página de metodologia | Backfill antes de 2025 |
| | Decomposição em drivers (dado gravado, sem visualização) |
| | Incorporar o `Modelagem\bc_comunicacao` (Chile) |

O código nasce multi-país: uma aba por BC aparece quando houver dado do BC.

## 3. Decisões do analista

| decisão | valor |
|---|---|
| Publicação | **Tudo público**, inclusive calls privados com texto. O analista sabe que GitHub Pages é público mesmo com repo privado. |
| Série do Board | **Linha única em degrau**, atualizada por qualquer documento colegiado (comunicado ou ata); marcador indica o tipo. |
| Estrutura do site | **Um site, uma aba por BC** (+ Metodologia). |
| Repositório | **Novo**, separado do `bc_comunicacao`; a convergência fica para depois. |
| Rubrica | `1.0-generic` da skill `bc-hawk-dove` (a do piloto Banxico). |

Risco conhecido e aceito da série única: o salto comunicado → ata pode refletir
diferença de gênero (a ata é mais longa e explicita divisões) e não só mudança de
postura. A página de metodologia declara isso; o marcador por tipo permite ao leitor
separar visualmente.

## 4. Arquitetura

Repositório em `R:\Macro EMs\Modelagem\em_reaction_functions`, mesma costura do FOMC:

```
agente Claude (claude -p / skill)  ->  data/<bc>/extracted/*.json  ->  emrf/ (Python)  ->  index.html
         não determinístico                   contrato                  determinístico
```

`emrf/` nunca chama modelo nem rede. Remontar o site a partir dos JSON é grátis e
reproduzível.

```
em_reaction_functions/
  registry/rubric.json                 # cópia da 1.0-generic da skill
  registry/<bc>/roster.json            # membros, mandato, vota?
  registry/<bc>/calendar.json          # reuniões: data decisão, data ata
  data/<bc>/raw/                       # textos-fonte (txt), nunca editados
  data/<bc>/extracted/<doc_id>.json    # um registro por documento
  agents/10_classificar_colegiado.md   # prompt do classificador de comunicado/ata
  emrf/{schema,board,build,html}.py
  scripts/atualizar.py                 # coleta -> classifica -> valida -> build
  tests/
  index.html                           # gerado, servido pelo Pages
```

Publicação: GitHub Pages a partir da raiz de `main`, com o mesmo contorno do FOMC
para o truncamento do R: (`git hash-object -w` do HTML gerado como blob do
`index.html`).

## 5. Contrato de dados

Um registro por documento, schema de fala do FOMC acrescido de:

| campo | valores |
|---|---|
| `bc` | `banxico` \| `bcch` \| `banrep` \| `sarb` |
| `track` | `colegiado` \| `membro` |
| `doc_type` | `comunicado` \| `ata` \| `rti` \| `fala_publica` \| `call_privado` |
| `member_id` | slug do membro; `board` no colegiado |
| `meeting_date` | só colegiado — reunião a que o documento se refere |
| `decision` | só colegiado — `{action, rate, vote, dissents}`, extraídos do texto |

Demais campos iguais ao FOMC: `doc_id`, `date` (data de publicação), `url`, `summary`,
`key_quotes`, `llm_scores` (5 dimensões + `near_term_bias` + `theme_flags`), `drivers`,
`extractor_model`, `extracted_at`, `rubric_version`. `null` = dimensão não coberta,
nunca `0`.

`doc_id` = `<bc>-<member_id>-<doc_type>-YYYYMMDD`.

## 6. Série do Board e desvio

- **Nível do Board em t** = `composite_hawk_dove` do último documento colegiado com
  `date <= t`. Documento com composto `null` não move o degrau.
- **Desvio do membro** = composto da fala/call − nível do Board vigente na data dela.

## 7. Páginas (aba Banxico)

1. **KPIs** — taxa atual, última decisão e votação, nível do Board, Δ vs documento anterior.
2. **Board + membros** — degrau do Board com marcadores (● comunicado, ■ ata) e
   pontos dos membros; filtro por tipo de documento.
3. **Heatmap** — linhas Board + membros, colunas = ciclos de reunião
   `[reunião k, reunião k+1)`; toggle nível ↔ desvio vs Board. Célula do Board = nível
   no fim do ciclo (já incorpora a ata). Célula do membro = média das falas no ciclo;
   no modo desvio, média dos desvios individuais (§6). Ciclo sem fala = vazio.
4. **Cards por membro** — último score, Δ vs fala anterior, desvio vs Board, quote
   principal, tag pública/privada.
5. **Base pesquisável** — todos os documentos, filtro por trilha/tipo, texto expansível.

Aba **Metodologia**: rubrica, construção da série do Board, cálculo do desvio, risco
de gênero comunicado×ata, calibração da escala, escopo e datas cobertas.

Na v1 não há registros de membros no início: as visões 2–4 renderizam só o Board e
mostram os membros assim que o primeiro registro entrar.

Fora: decomposição por drivers, contrafactual ex-petróleo, votantes × não votantes,
cross-check por léxico, dots.

## 8. Fluxos

**Carga inicial (uma vez).**
1. Comunicados de `Mexico\4. Política Monetária\Comunicados\_historico\2025-*.txt` e
   `2026-*.txt` → copiados para `data/banxico/raw/`.
2. Atas 2025–2026 baixadas do banxico.org.mx → `data/banxico/raw/`.
3. Classificação com `agents/10_classificar_colegiado.md`, um documento por chamada.
   Os 5 comunicados do piloto (`hawk_dove_rubrica/extracted/`) são **reclassificados**
   pelo mesmo prompt, não migrados, para calibração homogênea.
4. Validação de schema → build → push.

**Rotina colegiada.** Gatilho manual ("atualiza o Banxico") após cada decisão ou ata:
coleta, classifica, valida, build, push. Sem agendamento na v1.

**Rotina de membros.** Skill `bc-hawk-dove`, ajustada para gravar em
`em_reaction_functions/data/<bc>/extracted/` (hoje aponta para
`Modelagem\bc_hawk_dove`, inexistente), preencher `track`/`doc_type` e publicar
este site. Call privado: `doc_type=call_privado`, fonte "notas próprias".

## 9. Erros e verificação

- JSON que não passa no schema não entra no build; o build falha nomeando o arquivo.
- Documento sem texto legível (PDF de ata que não extrai) é reportado, nunca descartado
  em silêncio.
- Testes: validação de schema; construção da série do Board e do desvio com casos
  sintéticos (degrau, `null` não move, desvio com Board vigente); smoke test do HTML
  (aba Banxico, todos os documentos presentes).
- Após cada push: conferência visual do site publicado.
