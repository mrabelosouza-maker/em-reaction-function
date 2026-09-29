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
- `C:\Users\mrabelo\.claude\skills\bc-hawk-dove\references\calibracao.md` — régua da escala.
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

**Régua para comunicados do Banxico** (use como ordem de grandeza, reavalie pelo texto;
a régua cobre a escala inteira — não comprima tudo em torno de −1.5 a +0.5):
- corte grande ou aceleração do ritmo (ex.: 50bp) sinalizando novos cortes de magnitude
  similar: **−3**
- corte grande, sem sinalizar repetição, ou corte de 25bp com guidance claramente
  de continuidade e maioria folgada: **−2 a −2.5**
- corte com porta aberta para mais cortes, maioria dividida: **−1.5**
- corte sinalizado como último / pausa à frente: **−0.5**
- manutenção neutra, dependente de dados: **0**
- manutenção com balanço de riscos inclinado para cima e ênfase em inflação: **+0.5**
- alta ou viés explícito de alta: **+2 ou mais**

**Saída — `data/<bc>/extracted/<speech_id>.json`:**
```json
{
  "speech_id": "<do cabeçalho>",
  "bc": "banxico",
  "track": "colegiado",
  "doc_type": "comunicado | ata",
  "member_id": "board",
  "title": "Comunicado <meeting_date> | Minuta <meeting_date>",
  "date": "<do cabeçalho>",
  "meeting_date": "<do cabeçalho>",
  "url": "<do cabeçalho>",
  "source": "banxico",
  "non_policy": false,
  "decision": {"action": "cut|hold|hike", "rate": "6.50%", "vote": "4-1", "dissents": ["Heath (hold)"]},
  "summary": "Um parágrafo em inglês, 3-5 frases: a mensagem de política e o que mudou vs o documento anterior do mesmo tipo.",
  "key_quotes": [{"quote": "verbatim em espanhol", "context": "...", "dimension": "<id>"}],
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
