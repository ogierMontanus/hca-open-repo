# crowd-api — GitHub-login og bidragslager for crowd-siderne

En Cloudflare Worker der gør to ting for `mockup/crowd*.html`
(design: [`docs/crowdsourcing-login-plan.md`](../../docs/crowdsourcing-login-plan.md)):

1. **OAuth-proxy.** Siderne er statiske og kan ikke holde GitHubs `client secret`;
   Workeren gør det. Bidragydere og redaktører logger ind med en GitHub-konto.
2. **API** med samme ruter som `scripts/crowdsource/server.py` (`/api/crowd/…`),
   men lagret er et **privat GitHub-repo**: én JSON-fil pr. bidrag, ét commit pr. ændring.

```
crowd.html (Pages) ──► GET  worker/auth/login ──► github.com (login)
                  ◄── 302 crowd.html#hca_session=<signeret token> ◄── worker/auth/callback
crowd.html ──► fetch worker/api/crowd/…  Authorization: Bearer <token>
                  └─► privat repo  <org>/hca-crowd-data  (submissions/*.json, contributors/*.json)
```

* **Ingen adgang til repoet kræves** af bidragydere eller redaktører — kun Workerens
  token skriver dér. (Grenene i et offentligt repo er altid offentlige; derfor et separat privat repo.)
* **Roller:** redaktør = GitHub-konto i `ADMINS`. Rollen slås op ved *hvert* kald, ikke læses fra
  tokenet — at fjerne en redaktør virker med det samme.
* **GitHubs eget token gemmes ikke.** Det bruges én gang til `GET /user` og kasseres.
  Sessionen (7 dage) indeholder kun id, brugernavn, navn og udløb.
* Reglerne (validering, review, optælling) er de samme filer som i browseren
  (`mockup/js/crowd-validate.js`, `crowd-store.js`) — ingen tredje kopi.

## Opsætning (PowerShell)

Kræver en gratis Cloudflare-konto og Node 22+.

**1. Privat datarepo** (med et første commit, så `main` findes):

```powershell
gh repo create ogierMontanus/hca-crowd-data --private --add-readme
```

**2. Adgangstoken til repoet.** GitHub → Settings → Developer settings → Fine-grained tokens:
kun dette repo, *Repository permissions → Contents: Read and write*. Udløber senest efter 1 år —
sæt en påmindelse.

**3. OAuth App.** GitHub → Settings → Developer settings → OAuth Apps → New:
*Homepage URL* = siden på Pages; *Authorization callback URL* =
`https://hca-crowd-api.<dit-subdomæne>.workers.dev/auth/callback`. Notér *Client ID*, generér *Client secret*.

**4. Redaktørernes id.** Brug det numeriske id (brugernavne kan omdøbes og overtages af andre):

```powershell
(Invoke-RestMethod https://api.github.com/users/<brugernavn>).id
```

**5. Konfigurér og udgiv:**

```powershell
cd workers/crowd-api
npm install
# redigér wrangler.toml: GITHUB_CLIENT_ID, ADMINS, DATA_REPO (ALLOWED_ORIGINS/RETURN_PATH_PREFIX passer til Pages)
npx wrangler login
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put DATA_TOKEN
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(36)) | npx wrangler secret put SESSION_SECRET
npx wrangler deploy
```

**6. Peg siderne på Workeren** — `mockup/js/crowd-config.js`:

```js
window.CROWD_CONFIG = { apiBase: 'https://hca-crowd-api.<dit-subdomæne>.workers.dev' };
```

Commit og push. CI's `apply_csp.py` læser værdien og tilføjer netop denne https-origin til
`connect-src` på de tre crowd-sider (intet andet ændres). Med `apiBase: ''` virker siderne som før.

**7. Lokal afprøvning** (uden at udgive): opret `workers/crowd-api/.dev.vars` (git-ignoreret) med
de samme nøgler som secrets + `ALLOWED_ORIGINS=http://127.0.0.1:8765`, og `RETURN_PATH_PREFIX=/`; kør
`npx wrangler dev` (port 8787) i ét vindue og `python -m http.server 8765 --directory mockup` i et andet.
Sæt midlertidigt `apiBase: 'http://127.0.0.1:8787'` — og kun der: CSP'en accepterer kun https.
Uden `DATA_REPO` bruger Workeren et lager i hukommelsen (tabes ved genstart).
Callback-URL'en i OAuth-appen skal så være `http://127.0.0.1:8787/auth/callback` (brug en separat dev-app).

## Prøv det af

1. Åbn `crowd.html` → **Log ind med GitHub** → du lander tilbage på siden som »Logget ind som …«.
2. Bidrag til en person → i det private repo dukker `submissions/CS-….json` op som et commit.
3. En anden konto kan ikke se eller rette bidraget (`Mine bidrag`, direkte kald → 403).
4. Åbn `crowd-review.html` som redaktør: kør afgørelsen → bidragyderen ser udfaldet under `Mine bidrag`.
5. *Hent alle bidrag og afgørelser (JSON)* → `python scripts/crowdsource/export_approved.py --import-json fil.json --write`.

## Test

```powershell
cd workers/crowd-api
node --test test/worker.test.js            # eller: python -m pytest tests/test_crowd_worker.py
python scripts/sync_taxonomy.py            # efter ændringer i scripts/crowdsource/taxonomy.py
```

Testene dækker login-flowet (state, nonce-cookie, åben-redirect), forfalskede/udløbne tokens, roller,
hele bidragyder→redaktør-forløbet, CORS og GitHub-lagerets forespørgsler (mod en falsk GitHub).
De kører ikke mod rigtige GitHub eller Cloudflare — det gør trin 1–5 ovenfor.

## Drift og kendte grænser

* **Udløb:** `DATA_TOKEN` (højst 1 år), OAuth-secret. Rotér med `wrangler secret put`; alle sessioner
  ugyldiggøres ved at skifte `SESSION_SECRET`.
* **Persondata** i det private repo: GitHub-id, brugernavn, navn og (valgfri) e-mail fra formularen.
  `public_credit` styrer, om navnet vises offentligt. E-mail vises kun for redaktører.
* **Ikke med her:** vedhæftede filer (angiv filnavn/placering i stedet), TSV/Excel-eksport (hent JSON og kør
  `export_approved.py --import-json`), kontrol af at `person_id` findes i registret (Python-serveren gør det;
  Workeren tjekker kun formatet), serverside-opslag af `register_snapshot` (kommer fra klienten, jf.
  `crowdsourcing.md` §9).
* **Misbrug:** højst 30 åbne bidrag pr. konto, 256 kB pr. forespørgsel. Ingen IP-begrænsning — tilføj
  Cloudflare Rate Limiting-regel på `/api/crowd/submissions` før offentlig udrulning.
* **Skala:** hver liste-forespørgsel læser alle filer med ét GraphQL-kald. Fint til hundredvis af bidrag;
  derover (eller ved samtidig skrivning) skift lageret til Cloudflare D1/PostgreSQL — `service.js` kender
  kun grænsefladen i `store-memory.js`.
* **Én identitetsudbyder:** GitHub. ORCID eller Microsoft kan føjes til som flere `/auth/…`-ruter uden at røre resten.
