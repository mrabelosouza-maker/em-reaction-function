# CLAUDE.md — EM Reaction Functions

Site (GitHub Pages) com a escala hawk-dove de BCs emergentes: trilha colegiada
(comunicado, ata) e trilha de membros (falas, calls privados). v1: Banxico desde 2025.
Spec: docs/superpowers/specs/2026-09-28-em-reaction-functions-design.md.

## Costura
agentes (`claude -p`, skill bc-hawk-dove) -> data/<bc>/extracted/<speech_id>.json -> emrf/ -> results/index.html
`emrf/` nunca chama modelo nem rede. Remontar é grátis: `python scripts/build.py`.

## Rotinas
- **Atualizar o Banxico** (após decisão ou ata): `python scripts/coletar_banxico.py`
  -> `python scripts/classificar.py` -> `python -m pytest -q` -> `python scripts/build.py` -> publicar.
  - A coleta de comunicados lê o `_historico` de `Mexico\4. Política Monetária\Comunicados`;
    se o comunicado novo não aparecer, rode primeiro o coletor de lá.
  - O classificador é sequencial, com timeout de 15 min por documento, e só conta JSON
    que valida. JSON inválido vira `<id>.json.invalido` e é refeito na rodada seguinte.
- **Membro (fala/call):** skill `bc-hawk-dove`; grava em data/<bc>/raw e extracted com
  `track=membro`, `doc_type` fala_publica|call_privado, `bc`; `member_id` tem que estar em
  registry/<bc>/roster.json. Depois build + publicar.
- **Roster:** mandato de Heath termina em 2026-12-31 — revisar `registry/banxico/roster.json` em janeiro.

## Publicar
```powershell
python scripts/build.py
$blob = git hash-object -w results/index.html
git update-index --add --cacheinfo "100644,$blob,index.html"
git add <arquivos de dados novos>
git commit -m "<mensagem>"
git cat-file -s HEAD:index.html   # tem que bater com os bytes impressos por scripts/build.py
git push origin main
git update-index --skip-worktree index.html   # após o push
```
Compare `git cat-file -s HEAD:index.html` com a contagem de bytes impressa por
`python scripts/build.py` ("OK <path> (<n> bytes)"); o build já grava em LF e falha se a escrita truncar.

O `index.html` da raiz vive só no git: a cópia no working tree nunca é usada (o share R:
trunca arquivos grandes), por isso o `skip-worktree` acima. Nunca `git add index.html`
do working tree, nunca `git add -u` nem `git commit -a`, nunca `git add -A`/`git add .`.

### Remover um registro
Só a pedido explícito do analista (único caso em que um raw pode ser apagado):
```powershell
git rm -q data/<bc>/extracted/<id>.json data/<bc>/raw/<id>.md
python scripts/build.py
```
Depois siga os passos de "Publicar" (blob do `results/index.html`, commit, checagem de tamanho, push).

## Decisões (não repropor sem o analista)
- Tudo público, inclusive calls privados.
- Board = degrau único atualizado por comunicado OU ata (risco de gênero declarado na Metodologia).
- Colegiado: `member_id=board`, título canônico `Comunicado|Minuta <meeting_date>`.
- Rubrica 1.0-generic da skill; drivers gravados mas sem visualização na v1.
- Régua de comunicados em `agents/10_classificar_colegiado.md` (−3 a +2); calibrada no
  próprio Banxico 2025–26, sujeita a revisão do analista.
- Fora da v1: RTI, outros BCs, backfill de calls do Notion (Vault/raw/calls/MX), pré-2025,
  convergência com Modelagem/bc_comunicacao (Chile).
- Nunca editar/apagar raw gravado.
