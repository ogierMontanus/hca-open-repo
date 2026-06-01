# Onboarding til GitHub og Codex — for Ole

## Side 1: Adgang til repo'et og GitHub Desktop

### Trin 1 — Opret en GitHub-konto
Gå til **github.com** og opret en gratis konto. Brug den e-mailadresse du vil have
tilknyttet dit arbejde. Send dit brugernavn til mig, så tilføjer jeg dig som
*collaborator* på repo'et **ogiermontanus/hca-open-repo**.

### Trin 2 — Installer GitHub Desktop
GitHub Desktop er den visuelle klient der giver dig fuld kontrol over repo'et uden
at bruge kommandolinjen.

**Download:** https://desktop.github.com

Når du starter programmet første gang, logger du ind med din GitHub-konto og vælger
**"Clone a repository"** → søg på `ogiermontanus/hca-open-repo`. Vælg en lokal
mappe på din computer, f.eks. `Dokumenter/hca-repo`.

**Officielle videogennemgange (GitHub Desktop Getting Started):**
- Åbn GitHub Desktop → menuen **Help → GitHub Desktop on YouTube**
- Alternativt: søg på YouTube efter *"GitHub Desktop tutorial"* — kanalen **GitHub**
  har korte officielle videoer om clone, commit, push og branches.

---

### De tre begreber du skal kende

| Begreb | Hvad det er | Hverdagsmetafor |
|--------|-------------|-----------------|
| **Repository** (repo) | Det fælles arkiv med alle filer og hele historikken | En delt mappe med fuldstændig versionskontrol |
| **Branch** | En parallel arbejdsstrøm — du arbejder isoleret uden at påvirke andres arbejde | Et arbejdsbord ved siden af det fælles bord |
| **Commit** | Et navngivet snapshot af dine ændringer | Ctrl+S med en beskrivende besked |

---

### Den daglige arbejdsgang — pull, arbejd, push

```
1. PULL   — hent de seneste ændringer fra GitHub (andres arbejde)
2. ARBEJD — rediger filer lokalt på din computer
3. COMMIT — gem et snapshot med en kort beskrivelse
4. PUSH   — send dine ændringer op til GitHub
```

I **GitHub Desktop** ser det sådan ud:

- **Pull:** Klik **"Fetch origin"** øverst, derefter **"Pull origin"** — gør dette
  *altid* inden du begynder at arbejde for at hente det seneste.
- **Commit:** Skriv en kort besked i feltet *"Summary"* nederst til venstre,
  klik **"Commit to [branchnavn]"**.
- **Push:** Klik **"Push origin"** øverst til højre.

---

## Side 2: Branches og Codex

### Branches — parallelle arbejdsstrømme

En **branch** er en isoleret kopi af repo'et, hvor du kan eksperimentere frit.
Ændringer på din branch påvirker ikke `main`-branchen (den godkendte version)
eller andres arbejde, før du eksplicit beder om det via en **Pull Request**.

**Skift branch i GitHub Desktop:**
1. Klik på dropdown-menuen **"Current Branch"** øverst i midten.
2. Vælg en eksisterende branch fra listen — eller klik **"New Branch"** for at
   oprette din egen.
3. Giv den et sigende navn, f.eks. `ole/stedregister-facetter`.

> **Tommelfingerregel:** Opret en ny branch til hvert afgrænset arbejdsopgave.
> Hold `main` ren — kun velfungerende og godkendt kode lander der.

**Skift til en andens branch** (f.eks. for at se mit arbejde): Klik
**"Current Branch"** → vælg branchen → filerne på din computer opdateres
automatisk.

---

### Arbejde med Codex (ChatGPT Pro)

Codex er en coding agent der kan læse og skrive kode på baggrund af
natursprogsinstruktioner.

**Sådan forbinder du Codex til repo'et:**
1. Åbn **ChatGPT** → vælg **Codex** i agentpanelet.
2. Tilknyt repo'et via **GitHub-integrationen**
   (Settings → Integrations → GitHub) — giv Codex adgang til
   `ogiermontanus/hca-open-repo`.
3. Codex arbejder på sin egen branch og laver automatisk commits — du kan se og
   godkende ændringerne i GitHub Desktop eller på github.com.

**Praktisk arbejdsgang med Codex:**
1. Formulér opgaven på naturligt dansk — f.eks. *"Tilføj et filter på
   stedregister-siden der kun viser steder i Italien"*.
2. Codex opretter en branch, skriver koden og åbner en **Pull Request** på GitHub.
3. Du gennemgår ændringerne på github.com (klik **"Files changed"** i
   Pull Request'en).
4. Godkend ved at klikke **"Merge pull request"** — eller bed Codex justere.

**Hvis noget går galt:** Codex' ændringer er altid på en separat branch —
`main` er beskyttet. Du kan trygt afvise en Pull Request uden konsekvenser.

---

### Hurtigreference

| Situation | Handling i GitHub Desktop |
|-----------|--------------------------|
| Starte dagen | Fetch origin → Pull origin |
| Skifte til en anden branch | Current Branch → vælg branch |
| Gemme et checkpoint | Summary-felt → Commit |
| Sende til GitHub | Push origin |
| Noget gik galt | History → højreklik commit → Revert |

**Spørgsmål?** Skriv til mig — eller spørg ChatGPT:
*"Forklar Git pull og push som om jeg ikke har kodet i 20 år."*
