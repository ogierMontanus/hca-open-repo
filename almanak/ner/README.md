# almanak/ner — navnespænd i almanakken (»diary2almanac«)

Lille, lokal rangeringsmodel, der finder navnestrenge (Person, Sted, Lokalitet, Værk, Andet) i
almanakposterne og foreslår en registerpost. Baggrund, målinger og forbehold:
[`docs/plan-streng-grounding.md`](../../docs/plan-streng-grounding.md) §3.11.

| Fil | Rolle |
|---|---|
| `gold.py` | Sørens overlap-annotering (`../annotation/Opmærkning til Holger.json`) og kort mellem dagstekst og dagbogens rå sideoffsets |
| `eval_grounding.py` | måler `data/normalized/ner_page_grounding.csv` (dagbogens regler) mod Sørens dagbogsspans |
| `context.py` | alt modellen må vide om en dato: almanakpost, samme dags dagbog, almanakregistrets datohenvisninger, dagbogsregistret for dagens sider, regelforankringerne i dagbogen, navnelister, navneordsliste |
| `candidates.py` | kandidatspænd (1–5 ord, første og sidste med stort) |
| `features.py` | træk pr. kandidat, kildesymmetriske (så dagbogsdagene også kan bruges som træningsdata) |
| `model.py` | `eval` (blokvis krydsvalidering + to grundlinjer + bootstrap-interval), `ablate` (bidrag fra dagbog og registre), `train` |
| `predict.py` | `all`: annotér alle almanakposter, kobl til registerpost, mål dækning af almanakregistret |
| `build_lexicon.py`, `noun_filter.py` | fællesnavneliste fra moderniseringsrepoet og filter, der holder «Tænderne», «Fluen» ude af forslagene (§3.13) |
| `build_review_page.py` | gennemsynsside med maskinforslag til en ny stikprøve (blok E–H) |
| `eval_review.py` | mål modellen på en returneret gennemsyns-eksport pr. lag (sikre/usikre) og omtaleform; enighed mellem to gennemsyn |

Kør (PowerShell, fra repo-roden; kræver `numpy` og `scikit-learn`):

```powershell
python scripts/parsers/ner_page_grounding.py          # dagbogens regelforankring (bruges som træk)
python almanak/ner/eval_grounding.py data/normalized/ner_page_grounding.csv
python almanak/ner/model.py eval
python almanak/ner/model.py ablate
python almanak/ner/model.py tiers                     # gitter over HIGH/LOW (sikre/usikre); valgt i predict.py, se docs/plan-streng-grounding.md §3.14
python almanak/ner/model.py train
python almanak/ner/predict.py all
python almanak/ner/build_review_page.py --out mockup/almanak-gennemsyn.html
python almanak/ner/eval_review.py soren.json ole.json
```

`out/eval.json`, `out/ablation.json` og `out/coverage.json` committes; modellen (`model.pkl`) og
den fulde forudsigelse (`almanac_predictions.jsonl`) genskabes. Alt er deterministisk (fast seed,
sorterede opslag), uanset `PYTHONHASHSEED`.

**Modelvalg.** Logistisk regression på ~80 håndlavede træk (scikit-learn), trænet på begge kilder.
Gradient boosting blev afprøvet og var ikke bedre inden for usikkerheden. Ingen ekstern tjeneste
eller sprogmodel; teksten forlader ikke maskinen.

**Egennavn og omtale.** Gennemsynssiden arbejder i tre runder (egennavne → omtaler af endnu ikke dækkede registerposter →
usikre forslag, som ikke markeres, men tildeles fra en kø) og har et valgfrit felt *Omtaleform*. Se
[`docs/plan-streng-grounding.md`](../../docs/plan-streng-grounding.md) §3.12.
