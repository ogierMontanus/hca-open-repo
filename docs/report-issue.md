# "Indberet fejl" — fejlrapporter som GitHub-issues

Status: gældende · 2026-10-19

Alle sider har en lille knap nederst til højre. Den åbner en formular, og
indberetningen oprettes som et issue i GitHub-repoet med labelen
`brugerrapport` og titlen `[Fejlrapport] …`.

| Felt | Krav |
|------|------|
| Navn | påkrævet |
| E-mail | påkrævet, valideres |
| Overskrift + beskrivelse | påkrævet |
| Skærmbillede | valgfrit (fil eller Ctrl+V) |
| Samtykke | påkrævet — navn, e-mail og billede er offentlige |

Siden, browser og vinduesstørrelse tilføjes automatisk.

---

## Arkitektur

```
Browser (mockup/js/report-issue.js)
   │  POST JSON (navn, e-mail, tekst, evt. JPEG som base64)
   ▼
Cloudflare Worker (workers/report-issue/worker.js)   ← holder GitHub-tokenet
   │  1. commit skærmbillede til branchen `report-screenshots`
   │  2. opret issue med billedet indlejret
   ▼
GitHub: ogierMontanus/hca-open-repo
```

**Hvorfor en Worker?** Webstedet er statisk (GitHub Pages). Et GitHub-token i
JavaScript kan læses af alle og misbruges. Tokenet ligger derfor som *secret*
i Workeren. **Hvorfor en gren til skærmbilleder?** GitHub har ingen API til at
vedhæfte billeder til et issue; billedet committes i stedet til en separat
gren (så `main` og Pages-bygget ikke berøres) og indlejres via sin
raw-URL.

Uden Worker virker knappen stadig: formularen åbner da GitHubs egen
"nyt issue"-side forududfyldt i et nyt faneblad (kræver GitHub-login, og
skærmbillede skal trækkes ind manuelt).

---

## Opsætning (engangs)

### 1. Opret et token

GitHub → Settings → Developer settings → **Fine-grained personal access
tokens** → Generate new token:

- Repository access: *Only select repositories* → `hca-open-repo`
- Permissions: **Issues: Read and write**, **Contents: Read and write**
- Udløb: så langt, du er tryg ved (husk at forny)

Tokenet kan *kun* røre dette repo. Det er stadig en nøgle, der kan skrive
indhold — behandl den som en adgangskode.

### 2. Udgiv Workeren (PowerShell)

Kræver en gratis Cloudflare-konto og Node.js.

```
cd workers\report-issue
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

`secret put` beder om tokenet interaktivt; det gemmes ikke i filer eller git.
`deploy` printer Worker-adressen, fx
`https://hca-report-issue.<konto>.workers.dev`.

### 3. Peg knappen på Workeren

I `mockup/js/report-issue.js`, øverst:

```js
var REPORT_ENDPOINT = window.HCA_REPORT_ENDPOINT || 'https://hca-report-issue.<konto>.workers.dev';
```

Commit og merge til `main`; Pages-workflowet udgiver siden.

### 4. Prøv det

Åbn siden, indberet en testfejl med skærmbillede, og kontrollér at issuet
dukker op med labelen `brugerrapport`. Luk det bagefter.

---

## Indstillinger (`workers/report-issue/wrangler.toml`)

| Variabel | Standard | Betydning |
|----------|----------|-----------|
| `GITHUB_REPO` | `ogierMontanus/hca-open-repo` | Hvor issues oprettes |
| `ALLOWED_ORIGINS` | `https://ogiermontanus.github.io` | Hvilke sider må kalde Workeren fra en browser (kommasepareret). Tilføj dit eget domæne, hvis siden flytter |
| `SCREENSHOT_BRANCH` | `report-screenshots` | Gren til skærmbilleder (oprettes automatisk fra standardgrenen) |
| `ISSUE_LABEL` | `brugerrapport` | Label på nye issues (oprettes automatisk) |

---

## Privatliv — læs før I går live

Repoet er **offentligt**, så et issue er det også. Brugerens **navn og
e-mailadresse bliver derfor synlige for alle**, og e-mailen kan høstes af
spam-robotter. Formularen kræver et udtrykkeligt samtykke, men det er en
beslutning for projektet, om det er acceptabelt (GDPR). Alternativer:

- Opret issues i et **privat** repo (ret `GITHUB_REPO`). Skærmbilleder
  indlejres kun, hvis læseren er logget ind med adgang — i et privat repo
  vil raw-URL'en ikke kunne vises for andre end medlemmer.
- Fjern e-mailen fra issuet og send den i stedet et andet sted hen (kræver
  en mailtjeneste, fx Cloudflare Email Routing/Resend, i Workeren).

Skærmbilleder kan indeholde personoplysninger; de committes til en offentlig
gren og kan ikke fjernes fra git-historikken uden videre.

## Misbrugsbeskyttelse

Workeren er et åbent endpoint, der skriver i repoet. Nuværende værn:

- Kun JSON fra tilladte `Origin`s (stopper andre websteder, **ikke**
  scripts, der selv sætter headeren)
- Skjult honeypot-felt (bots får "succes", intet oprettes)
- Længdegrænser, e-mail-validering, billede højst 2,5 MB og kontrol af
  filens faktiske format (PNG/JPEG/WebP)
- `@navn` uskadeliggøres, så formularen ikke kan bruges til at pinge
  GitHub-brugere; markdown i navn og e-mail escapes
- GitHubs fejlbeskeder videregives aldrig til browseren

Der er **ingen rate limiting**. Bliver der spammet, så tilføj
[Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/) eller
Cloudflares rate-limit-regler foran Workeren.

---

## Test

Worker-logikken (validering, oprettelse af issue, skærmbilleder, afvisning af
fremmede origins, honeypot) er dækket af tests uden netværk:

```
cd workers\report-issue
node --test worker.test.mjs
```

## Filer

| Sti | Indhold |
|-----|---------|
| `mockup/js/report-issue.js` | Knap, dialog, billedkomprimering, afsendelse |
| `mockup/js/nav.js` | Indlæser knappen på alle indre sider |
| `mockup/css/style.css` | Sektionen `=== Report a problem ===` |
| `workers/report-issue/` | Worker, `wrangler.toml`, tests |
