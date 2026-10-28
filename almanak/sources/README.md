# Kilder til almanakprojektet

Originalkilderne ligger **ikke** i git. Denne fil registrerer, hvor de findes,
hvilken version analysen bygger på (sha256), og hvordan de bruges. Ingen
almanakscript må skrive til disse filer.

| ID | Kilde | Placering (lokal) | sha256 | Rolle |
|---|---|---|---|---|
| `SRC-DB` | MySQL-dump `hca_db.sql`, tabel `almanak` (phpMyAdmin 5.1.2, dumpet 29.06.2023) | `raw/hca_db.sql` (gitignoreret, findes ikke i cloud-sessioner) | `56f01944e4cd73208e4e3cad39c3e9699f69d19be9a494573135b4fce8441af3` | Kontrolvidne: indtastning af 1990-udgaven (importeret 2006). Rettelserne 2007–2019 er rettelser af indtastningsfejl efter 1990-udgaven, ikke efter håndskriftet (afklaret 2026-10-27). Nøglen `Dato` er den eksisterende webadresse-nøgle på andersen.sdu.dk/liv/almanak |
| `SRC-PDF` | *H. C. Andersens Almanakker 1833–1873*, udg. Helga Vang Lauridsen og Kirsten Weber, DSL/Gad 1990. Digitaliseret af Claus Rønlev; ABBYY FineReader 15, 28.03.2023 | `C:\Users\nh\Syddansk Universitet\HCA-MS - Documents\forskning_HCA\1990 HCAs almanak\andersen-hc_almanakker.pdf` | `9e80b7fa87a1f5d22112d3e431ae856d740193d3967abcfb20585302e8e05a0c` | Tekstgrundlag: sidebilledet er facit; tekstlaget er OCR. **Erstattes af `SRC-PDF2`**, når den foreligger |
| `SRC-PDF2` | Ny OCR-scanning af samme udgave (bestilt 2026-10-27) | — | — | Forventet nyt tekstgrundlag; måles mod basislinjen i [`baseline-2026-10-27.json`](baseline-2026-10-27.json) før den tages i brug |
| `SRC-JPG` | 404 sidebilleder `almanak001.jpg`–`almanak404.jpg` (marts 2022) | samme mappe som `SRC-PDF` | ikke beregnet | Ikke undersøgt. Sandsynligvis scanningerne bag PDF'en (404 billeder mod 400 PDF-sider — forskellen er uafklaret) |
| `SRC-OCRTEST` | `testOCR-15pages-almanak.pdf` + Google Docs-HTML (juni 2022) | samme mappe | ikke beregnet | Ældre OCR-forsøg; ikke brugt |
| `SRC-KB` | Det Kgl. Biblioteks digitale almanakudgave 2006 med faksimiler af originalerne (Collinske Samling 10, 4to; 1854: UB Oslo Ms. 8vo 2156) | **Offline** (bekræftet 2026-10-27); intet at linke til | — | Ikke tilgængelig. Spørgsmål, der kun håndskriftet kan afgøre (fx trykkets forkerte ugedage), forbliver uafgjorte og markeres som sådan |

## Sideforskydning i `SRC-PDF`

Trykt side = PDF-side − 12. PDF-siderne 13–339 er almanakteksten (trykt s. 1–327),
340–350 Værkregister (s. 328–338), 351–400 Personregister (s. 339–388).
Forord s. vii (PDF 6), Introduktion s. ix–xiii (PDF 8–12) med de redaktionelle
principper.

## Sådan peger scripts på kilderne

```powershell
# DB: standard er raw/hca_db.sql; ellers
python almanak/scripts/analysis/extract_db.py --sql D:\sti\hca_db.sql

# PDF: angiv stien eller sæt miljøvariablen én gang pr. session
$env:HCA_ALMANAK_PDF = "C:\Users\nh\Syddansk Universitet\HCA-MS - Documents\forskning_HCA\1990 HCAs almanak\andersen-hc_almanakker.pdf"
python almanak/scripts/analysis/extract_pdf_entries.py --cache almanak/data/cache/lines.json
```

Kontrollér sha256 før en ny kørsel (`Get-FileHash <fil> -Algorithm SHA256`).
Ændres en kilde, skal tallene i [`../docs/kildeanalyse.md`](../docs/kildeanalyse.md)
genberegnes.

## Rettigheder

Teksten er 1990-udgavens (© DSL 1990). **Den må publiceres i repoet**
(afklaret 2026-10-27). Maskinelle udtræk holdes alligevel ude af git
(`almanak/.gitignore`), fordi de kan genskabes og ikke er autoritative; den
etablerede tekst i `almanak/data/build/` og beslutningerne i
`almanak/data/review/` committes.

## Status for afklaringer (2026-10-27)

| Spørgsmål | Svar |
|---|---|
| Hvad bygger DB's ≈950 rettelser på? | Rettelser af indtastningsfejl; højst efter 1990-udgaven, ikke efter håndskriftet |
| Må 1990-teksten publiceres? | Ja |
| Er »Sørens Almanak« (`docs/data-model/star-schema.md`) dette materiale? | Uvist |
| KB's faksimileudgave? | Offline; intet at linke til |
| De 404 JPG'er i forhold til PDF'ens 400 sider? | Ikke undersøgt |
| Ny OCR | Bestilt; erstatter `SRC-PDF`s tekstlag |
