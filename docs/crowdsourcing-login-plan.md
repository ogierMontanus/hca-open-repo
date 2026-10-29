# Crowdsourcing — testplan for minimal brugerhåndtering (GitHub som identitet)

Status: **OAuth-proxy bygget (ikke udgivet)** · 2026-10-29 · udvider [`crowdsourcing.md`](crowdsourcing.md) §8 og §11

## Beslutning (2026-10-29): OAuth-proxy + privat datarepo

Issues-løsningen nedenfor er **ikke** valgt. Skrevet: [`workers/crowd-api/`](../workers/crowd-api/README.md).
Årsagen er spørgsmålet *kan bidrag ligge på en ikke-offentlig gren?* — **nej**: grenene i et offentligt repo
er altid offentlige, og Issues i et offentligt repo ligeså. Bidrag (navne, ikke-godkendte påstande) skal ligge
i et **separat privat repo**, som kun en Worker skriver til. Det kræver en server-side hemmelighed (OAuth
`client secret` og repo-token), og den kan en statisk Pages-side ikke holde — derfor en lille Cloudflare Worker.

| | Issues-planen (nedenfor) | **Valgt: Worker + privat repo** |
|---|---|---|
| Bidrag synlige for andre | ja, offentligt repo | nej — kun Worker og redaktører |
| Bidragyder skal bruge | GitHub-konto + github.com-grænseflade | GitHub-konto, men logger ind **på siden** |
| Redaktør | repo-collaborator, kommandoer i kommentarer | `ADMINS`-liste; den eksisterende `crowd-review.html` |
| Uden for GitHub/Pages | nej | Cloudflare Workers (gratis niveau) |

Det eneste, der forlader GitHub, er Workeren. Bidragene er dog stadig almindelige filer i et git-repo
(commit pr. ændring = revisionsspor). Testtrinnene T1–T5 nedenfor gælder fortsat, med den ændring at
»issue« læses som »fil i datarepoet« og »label« som `status`; trin-for-trin-test: se Workerens README.

## Mål og rammer

* Flere bidragydere kan indsende, uden at nogen mailer en fil (i dag: *Mine bidrag → Hent som fil*).
* Roller: **bidragyder** og **administrator** (godkender, afviser, kommenterer).
* Alt bliver i GitHub; frontenden forbliver statisk på GitHub Pages og `file://`.
* Registerfelterne røres aldrig; godkendt data går fortsat via `export_approved.py` → `data/curated/person_crowd_approved.tsv` (CLAUDE.md: *bidrag er et lag*).

## Hvorfor ikke »rigtigt« login på Pages

Pages kan ikke holde en hemmelighed, og GitHubs OAuth-token-endpoint kan ikke kaldes direkte fra en browser (CORS — **verificeres i T0**). Rigtigt login på siden kræver derfor en lille proxy (fx Cloudflare Worker) uden for GitHub. Egne passwordkonti er udelukket (ingen server).

## Anbefalet løsning: GitHub-konto = identitet, Issues = indbakke, Actions = valideringsserver

```
bidragyder                         GitHub                                administrator
crowd-contribute.html
  validerer (crowd-validate.js)
  åbner github.com/<org>/<inbox>/issues/new?template=bidrag.yml&body=<JSON>
  (login sker på github.com, ikke hos os)
        │ Issue = bidrag, forfatter = GitHub-handle
        ▼
                          Action `on: issues.opened`
                          validate.py → label submitted | invalid
                          + kommentar med fejl ved invalid
                                                                    crowd-review.html (som i dag)
                                                                    læser bidrag, producerer afgørelser
                                                                    poster kommentar `/review {json}`
                          Action `on: issue_comment`
                          kun hvis author_association ∈ OWNER|MEMBER|COLLABORATOR
                          store.py-regler → label approved | needs_changes | rejected
                          ved approved: kører export_approved.py → PR mod main  ◄── admin merger (anden port)
bidragyder får GitHub-notifikation ved hver admin-kommentar (ingen mail fra os)
"Mine bidrag": fetch api.github.com/search/issues?q=repo:…+author:<handle>
```

| Krav | Løses af |
|---|---|
| Brugerhåndtering | GitHub-konti (ingen egen brugertabel) |
| Administratorrolle | repo-collaborators med skriveadgang; tjekkes i Action via `author_association` |
| Kommentering | Issue-kommentarer (bidragyder kan svare → *needs_changes*-flowet) |
| Gemme bidrag fra flere | ét issue pr. bidrag; kanonisk JSON i issue-body |
| Undgå mail | GitHub-notifikationer + »Mine bidrag«-listen |
| Godkendelse | label-tilstandsmaskine + PR som endelig port |

Teknisk: en tredje bagende `js/crowd-store-github.js` bag samme Promise-API som `local`/`api` i `crowd-store.js` (§8) — siderne ændres ikke.

## Alternativer (fravalgt til testen)

| | Fordel | Hvorfor ikke først |
|---|---|---|
| Pages + OAuth-proxy (Worker) | Login på siden, ingen synlig GitHub-UI | Infrastruktur uden for GitHub; senere trin hvis T5 viser behov |
| Firebase/Supabase | Rigtige konti, mail-login | Forlader GitHub |
| Bruger indsætter PAT | Intet backend | Usikkert; ikke-teknikere |
| giscus/Discussions | Kun kommentarer | Løser ikke indsendelse/godkendelse |

## Testtrin (hvert med bestå-kriterium)

**T0 — Gennemførlighed (½ dag, ingen produktionskode).** Med to egne GitHub-konti i et privat testrepo:
1. Maks. længde på forududfyldt `issues/new?body=` — bestå: realistisk bidrag (5 felter, 3 kilder) kommer igennem; ellers fallback »kopiér JSON → indsæt i formularfelt«.
2. `fetch` fra `file://` og Pages til `api.github.com` (CORS, uautentificeret rate limit 60/t, søgning 10/min) — bestå: »Mine bidrag« kan hentes ≥ 3 gange i træk.
3. Bekræft at OAuth-token-exchange fra browser ikke er mulig (afgør, at denne løsning er den simple).
4. `author_association` for en ikke-collaborator i `issue_comment`-payload.

**T1 — Bidragyderstien.** Inbox-repo (offentligt), issue-form `bidrag.yml`, Action `validate`. Bestå: gyldigt bidrag → label *submitted*; ugyldigt (testsættet `tests/fixtures/crowd_cases.json`) → *invalid* + læsbare fejl; Action bruger samme `validate.py` som serveren.

**T2 — Administratorstien.** `/review`-kommando i kommentar; Action bruger `store.py`-reglerne. Bestå: collaborator kan godkende/afvise/bede om uddybning; **ikke-collaborator med samme kommentar ændrer intet**; status følger afgørelserne som i §5.

**T3 — Kommentarer og »Mine bidrag«.** `crowd-store-github.js` med `mine()` og `reply()`. Bestå: bidragyder ser admin-kommentar og *needs_changes* på siden og kan svare uden at forlade flowet; GitHub-notifikation modtaget.

**T4 — Overdragelse.** Ved *approved* åbner Action en PR med rækker i `person_crowd_approved.tsv`. Bestå: genkørsel skaber ikke dubletter (nøgle `(submission_id, field)`); `guard`/`register_changed` blokerer som i dag.

**T5 — Brugertest med 3–5 rigtige slægtsforskere** (ikke-udviklere). Mål: gennemfører de en indsendelse uden hjælp? Bestå: ≥ 4 af 5. Falder ≥ 2 fra ved oprettelse af GitHub-konto → skift til Worker-løsningen (OAuth på siden).

## Beslutninger der skal tages først

1. **Offentlige, ikke-godkendte påstande.** Issues i et offentligt repo er synlige for alle; i dag er `data/crowdsource/` bevidst `.gitignore`'et (`crowdsourcing.md` §9). Personerne er omtalt 1825–1875 (afdøde), bidragyderens persondata er kun et allerede offentligt GitHub-handle — men Centret skal godkende, og bidragsformularen skal sige det højt (samtykke i stedet for kontaktoplysninger). Privat inbox fungerer ikke (bidragydere skal så være collaborators).
2. **Ingen vedhæftninger i T1–T5** (issue-billeder er offentlige; ophavsret jf. åben beslutning 4).
3. **Misbrug:** slå GitHubs *interaction limits* til; Action lukker automatisk *invalid* efter 14 dage.
4. **CSP:** `connect-src` skal udvides med `https://api.github.com` (kun på `crowd*.html`); opdatér `docs/security.md` og `tests/test_csp_ready.py`.
5. **Administratorer:** hvem er collaborators? Kræv to godkendelser for *Sikker* (åben beslutning 1) — i PR-trinnet via *required reviews* uden ekstra kode.

## Ikke med i testen

Engelsk grænseflade, mærker/statistik på tværs af brugere (`contributor_stats()` kan beregnes af en Action til `stats.json` bagefter), e-mailbekræftelse, PostgreSQL (§11).
