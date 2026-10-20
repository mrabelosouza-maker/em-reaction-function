# Agente 10 — classificar um documento colegiado (comunicado ou ata)

**Objetivo:** ler UM documento colegiado de um BC e gravar
`data/<bc>/extracted/<speech_id>.json` com a postura da **Junta como colegiado**
na rubrica `registry/rubric.json`.

**Ferramentas:** Read, Write, Bash (só para rodar o validador).

**Entradas**
- O raw indicado: `data/<bc>/raw/<speech_id>.md`. O cabeçalho `<!-- chave: valor -->`
  traz `speech_id`, `bc`, `doc_type`, `date`, `meeting_date`, `url`. Copie esses valores
  exatamente.
- `registry/rubric.json` — leia inteira.
- A skill bc-hawk-dove: `C:\Users\mrabelo\.claude\skills\bc-hawk-dove\SKILL.md` (seção 4,
  Classificar, e os princípios — nota só pelo texto, `null` quando não trata, citação verbatim)
  e `references\calibracao.md` — régua da escala.
- O JSON colegiado anterior do mesmo `doc_type` em `data/<bc>/extracted/` (maior `date`
  menor que a deste), se existir — só para descrever o que mudou no `summary`, nunca
  para puxar a nota.

**Unidade de análise.** A mensagem da Junta neste documento: decisão, guidance, balanço
de riscos, votos e divergências. Na **ata**, pondere a discussão ("la mayoría",
"algunos", "uno") — uma ata que revela maioria mais dividida ou mais preocupada com
inflação que o comunicado pontua diferente dele. Não copie a nota do comunicado: dê
a nota da ata só a partir do texto da ata, sem abrir o JSON do comunicado. Se o seu
próprio `summary` disser que a ata é mais dovish ou mais hawkish que o comunicado,
o composto tem que refletir isso (diferença de pelo menos 0.5).

**Régua para documentos colegiados** (escala −5 a +5; o lado dovish espelha a calibração
da skill bc-hawk-dove; aprovada pelo analista em 2026-10-20). A nota vale pelo que o documento
PEDE/SINALIZA PARA A POLÍTICA, não pelo quanto reclama da inflação. Antes de dar a nota, leia
2 ou 3 JSON colegiados já gravados em fases parecidas do ciclo e mantenha a escala (se o BC
ainda tem poucos, use também os do Banxico, `data/banxico/extracted/board-*.json`):
- corte grande (ex.: 50bp) com sinalização explícita de novos cortes de magnitude similar: **−4.5**
- corte grande com mais afrouxamento como cenário claro; ou 25bp com urgência/aceleração: **−4.0**
- corte com mais cortes como cenário base (guidance explícito de continuidade): **−3.5**
- corte com espaço para algum afrouxamento adicional modesto: **−3.0**
- corte com guidance mais cauteloso ou Junta dividida sobre seguir; ritmo desacelerando: **−2.5**
- corte sinalizado como último / pausa à frente; ou manutenção em que a maioria já discute
  ativamente o próximo corte: **−1.5 a −2.0**
- manutenção com a porta aberta a corte (ex.: ata de 24/09/2026): **−1.0**
- manutenção confortável, dependente de dados: **0**; com balanço de riscos para cima e
  ênfase em inflação, sem viés de corte: **+0.5**
- manutenção com a suficiência da política em questão / viés de alta: **+1.0 a +2.0**
- alta ou endosso de alta: **+2.5 ou mais**
Votos divergentes contam (um dissidente pedindo manter num corte puxa ~0.5 para cima; 3-2, mais).
Diferenças de 0.5 são ruído; o que importa é o ranking entre reuniões e a direção da mudança.
No `summary`, descreva a mudança vs o documento anterior de forma qualitativa, sem citar a nota dele.

**Saída — `data/<bc>/extracted/<speech_id>.json`:**
```json
{
  "speech_id": "<do cabeçalho>",
  "bc": "<do cabeçalho>",
  "track": "colegiado",
  "doc_type": "comunicado | ata",
  "member_id": "board",
  "title": "Comunicado <meeting_date> | Minuta <meeting_date>",
  "date": "<do cabeçalho>",
  "meeting_date": "<do cabeçalho>",
  "url": "<do cabeçalho>",
  "source": "<bc do cabeçalho>",
  "non_policy": false,
  "decision": {"action": "cut|hold|hike", "rate": "6.50%", "vote": "4-1", "dissents": ["Heath (hold)"]},
  "summary": "Um parágrafo em inglês, 3-5 frases: a mensagem de política e o que mudou vs o documento anterior do mesmo tipo.",
  "key_quotes": [{"quote": "verbatim, na língua do documento", "context": "...", "dimension": "<id>"}],
  "llm_scores": {
    "composite_hawk_dove": 0, "mandate_weight": 0, "inflation_conviction": 0,
    "labor_concern": 0, "policy_stance_read": 0,
    "near_term_bias": {"direction": "hold", "pace": "data-dependent"},
    "theme_flags": []
  },
  "drivers": {"supply_shocks": {"intensity": 0, "push": "neutral"}, "underlying_inflation": {...},
              "fx_external": {...}, "labor_market": {...}, "growth_demand": {...}, "other": {...}},
  "extractor_model": "<modelo desta sessão>", "extracted_at": "<AAAA-MM-DDT00:00:00Z>",
  "rubric_version": "1.0-generic"
}
```

**Regras**
- `title` é EXATAMENTE `Comunicado <meeting_date>` ou `Minuta <meeting_date>` (o `speech_id` depende dele).
- **SARB** (só statement, sem ata): o comitê é o MPC; o statement dá o placar sem nomes
  ("unanimous" ou "four members preferred..."). `vote` como `"6-0"`/`"4-2"` (contagem do texto),
  `dissents` como `"<n> membros (<o que preferiam>)"`. Choques administrados (eletricidade, combustível)
  entram em `supply_shocks`; o rand e o Fed em `fx_external`.
- **BCCh** (comunicado e minuta): o colegiado é o Consejo (5 consejeros). O comunicado diz se foi
  por unanimidade; a minuta nomeia os votos na seção "Decisión de política monetaria" —
  `dissents` como `"<Sobrenome> (<o que preferia>)"`. Na minuta, a seção "Análisis de las opciones"
  mostra o leque de opções que o Consejo considerou plausível: pondere-o como a discussão de uma ata.
  Cobre e o peso (tipo de cambio) entram em `fx_external`; combustíveis em `supply_shocks`.
- `decision`: extraia do texto. Na ata, é a decisão da reunião a que ela se refere. `dissents`
  lista `"<Sobrenome> (<o que preferia>)"`; `[]` se unânime. `vote` como `"5-0"`, `"4-1"`.
- Scores inteiros ou .5; `null` se o documento não trata da dimensão.
- 2 a 4 `key_quotes` VERBATIM do raw (o validador confere).
- Os seis drivers, todos, sempre.

**Validação obrigatória (tem que imprimir `OK`):**
```
python C:\Users\mrabelo\.claude\skills\bc-hawk-dove\scripts\bc_base.py validar data/<bc>/extracted/<speech_id>.json --rubrica registry/rubric.json --texto data/<bc>/raw/<speech_id>.md
```
Se der erro, corrija o JSON e valide de novo. Não faça mais nada além de gravar esse arquivo.
