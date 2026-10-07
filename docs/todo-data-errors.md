# TODO — datafejl

Genereret af `scripts/build_mockup/report_untranscribed_pages.py`. Ret kilden (eller transskriber siderne) og kør scriptet igen.

## FEJL: registerhenvisninger til sider uden transskriberet dagbogstekst

`data/normalized/references.csv` peger på **137 sider** (**212 henvisninger**), der ikke findes i `data/normalized/diary.csv`. Webstedet viser kun de **4.413 sider** med transskriberet tekst (bind I–X); de øvrige er udeladt fra dagbogslisten, dagbogssiderne, kurven, søgeindekset og alle henvisningstal.

Mulige årsager at undersøge pr. række: (a) sidetal uden for dagbogsteksten (kommentar-/registerdel bag teksten i bind I–X, fx VIII s. 704+), (b) bind XI (Personregister) er ikke en dagbog og skal ikke have dagbogssider, (c) OCR-/indlæsningsfejl i sidetallet i registeret.

| Bind | Sider | Henvisninger |
|---|---|---|
| I | 1 | 1 |
| II | 4 | 4 |
| III | 5 | 5 |
| IV | 2 | 73 |
| V | 5 | 5 |
| VI | 10 | 11 |
| VII | 2 | 2 |
| VIII | 25 | 26 |
| IX | 22 | 23 |
| X | 3 | 4 |
| XI | 56 | 56 |

Desuden har **117 henvisningsrækker** hverken bind eller side (registerets «se:»-krydshenvisninger). De er ikke dagbogssider, tælles som før og er ikke ændret.

### Alle sider

| Bind | Side | Henv. | Poster |
|---|---|---|---|
| I | 586 | 1 | Frankrig, Napoléon I, Kejser af – (1769–1821) |
| II | 449 | 1 | Warszawa |
| II | 777 | 1 | Næstved |
| II | 827 | 1 | Don Pasquale (G. Donizetti) |
| II | 828 | 1 | Don Pasquale (G. Donizetti) |
| III | 431 | 1 | Scavenius, Henriette, f. Komtesse Moltke (1819–1898) |
| III | 445 | 1 | Scavenius, Henriette, f. Komtesse Moltke (1819–1898) |
| III | 446 | 1 | Scavenius, Henriette, f. Komtesse Moltke (1819–1898) |
| III | 449 | 1 | Scavenius, Henriette, f. Komtesse Moltke (1819–1898) |
| III | 779 | 1 | Odense |
| IV |  | 72 | Franske - Fantaisies danoises (Tr. par Jules F.-U. Jurgensen). (Genève 1861); Franske - Fantaisies danoises (Tr. par Jules F.-U. Jurgensen). (Genève 1861); Franske - Fantaisies danoises (Tr. par Jules F.-U. Jurgensen). (Genève 1861); Franske - Fantaisies danoises (Tr. par Jules F.-U. Jurgensen). (Genève 1861) … (+68) |
| IV | 766 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| V |  | 1 | auf der Maur, Agatha (1824–1872) |
| V | 476 | 1 | Moltke, Thusnelda (Nelly), Komtesse (1843–1928) |
| V | 756 | 1 | Collin, Hjalmar (1834–1897) |
| V | 760 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| V | 765 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 367 | 1 | Malmö |
| VI | 373 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 375 | 1 | Heiberg, Sara (1853–1941) |
| VI | 722 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 723 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 740 | 1 | Collin, Gottlieb (1806–1885) |
| VI | 750 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 755 | 2 | Collin, Henriette Oline, f.Thyberg (1813–1894); Ristori, Adelaide (1822–1906) |
| VI | 780 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VI | 782 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VII | 400 | 1 | Warburg, Karl (1852–1918) |
| VII | 413 | 1 | Montreux |
| VIII | 704 | 1 | Collin, Edvard (1808–1886) |
| VIII | 706 | 1 | Collin, Edvard (1808–1886) |
| VIII | 722 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| VIII | 728 | 1 | Collin, Edvard (1808–1886) |
| VIII | 729 | 1 | Collin, Edvard (1808–1886) |
| VIII | 733 | 1 | Collin, Edvard (1808–1886) |
| VIII | 736 | 1 | Collin, Edvard (1808–1886) |
| VIII | 743 | 1 | Collin, Edvard (1808–1886) |
| VIII | 744 | 1 | Collin, Edvard (1808–1886) |
| VIII | 746 | 1 | Collin, Edvard (1808–1886) |
| VIII | 747 | 1 | Collin, Edvard (1808–1886) |
| VIII | 748 | 1 | Collin, Edvard (1808–1886) |
| VIII | 749 | 1 | Collin, Edvard (1808–1886) |
| VIII | 754 | 1 | Collin, Edvard (1808–1886) |
| VIII | 759 | 1 | Collin, Hjalmar (1834–1897) |
| VIII | 765 | 1 | Collin, Edvard (1808–1886) |
| VIII | 767 | 1 | Collin, Edvard (1808–1886) |
| VIII | 769 | 1 | Collin, Edvard (1808–1886) |
| VIII | 775 | 2 | Haffner, Vilhelmine (Mine), f. Krieger (1807–1889); Haffner, Wolfgang (1810–1887) |
| VIII | 784 | 1 | Collin, Edvard (1808–1886) |
| VIII | 787 | 1 | Collin, Edvard (1808–1886) |
| VIII | 790 | 1 | Collin, Edvard (1808–1886) |
| VIII | 793 | 1 | Collin, Edvard (1808–1886) |
| VIII | 795 | 1 | Collin, Edvard (1808–1886) |
| VIII | 797 | 1 | Collin, Edvard (1808–1886) |
| IX | 400 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 403 | 1 | Øresund |
| IX | 415 | 1 | Øresund |
| IX | 422 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 425 | 1 | Meisling, Inger Cathrine, f. Hjarup (1793–1854) |
| IX | 437 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 452 | 1 | Barselstuen (L. Holberg) |
| IX | 453 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 454 | 1 | Bang, Oluf (Ole) (1788–1877) |
| IX | 455 | 1 | Uppsala |
| IX | 457 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 458 | 1 | Uppsala |
| IX | 466 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 468 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 471 | 1 | Bøgh, Nicolai (1843–1905) |
| IX | 738 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| IX | 739 | 1 | Collin, Gottlieb (1806–1885) |
| IX | 756 | 1 | Collin, Henriette Oline, f.Thyberg (1813–1894) |
| IX | 760 | 2 | Collin, Edvard (1808–1886); Collin, Henriette Oline, f.Thyberg (1813–1894) |
| IX | 764 | 1 | Collin, Edvard (1808–1886) |
| IX | 765 | 1 | Collin, Edvard (1808–1886) |
| IX | 222123 | 1 | Henriques, Martin R. (1825–1912) |
| X | 777 | 2 | Collin, Edvard (1808–1886); Collin, Henriette Oline, f.Thyberg (1813–1894) |
| X | 793 | 1 | Collin, Jonas d.Y. (1840–1905) |
| X | 795 | 1 | Collin, Edvard (1808–1886) |
| XI | 3 | 1 | Hornemann, Emil (1810–1890) |
| XI | 5 | 1 | Hornemann, Emil (1810–1890) |
| XI | 17 | 1 | Hornemann, Emil (1810–1890) |
| XI | 24 | 1 | Hornemann, Emil (1810–1890) |
| XI | 30 | 1 | Hornemann, Emil (1810–1890) |
| XI | 38 | 1 | Hornemann, Emil (1810–1890) |
| XI | 50 | 1 | Hornemann, Emil (1810–1890) |
| XI | 64 | 1 | Hornemann, Emil (1810–1890) |
| XI | 75 | 1 | Hornemann, Emil (1810–1890) |
| XI | 77 | 1 | Hornemann, Emil (1810–1890) |
| XI | 84 | 1 | Hornemann, Emil (1810–1890) |
| XI | 86 | 1 | Hornemann, Emil (1810–1890) |
| XI | 90 | 1 | Hornemann, Emil (1810–1890) |
| XI | 109 | 1 | Hornemann, Emil (1810–1890) |
| XI | 122 | 1 | Hornemann, Emil (1810–1890) |
| XI | 138 | 1 | Hornemann, Emil (1810–1890) |
| XI | 140 | 1 | Hornemann, Emil (1810–1890) |
| XI | 143 | 1 | Hornemann, Emil (1810–1890) |
| XI | 144 | 1 | Hornemann, Emil (1810–1890) |
| XI | 146 | 1 | Hornemann, Emil (1810–1890) |
| XI | 148 | 1 | Hornemann, Emil (1810–1890) |
| XI | 151 | 1 | Hornemann, Emil (1810–1890) |
| XI | 154 | 1 | Hornemann, Emil (1810–1890) |
| XI | 160 | 1 | Hornemann, Emil (1810–1890) |
| XI | 162 | 1 | Hornemann, Emil (1810–1890) |
| XI | 170 | 1 | Hornemann, Emil (1810–1890) |
| XI | 192 | 1 | Hornemann, Emil (1810–1890) |
| XI | 198 | 1 | Hornemann, Emil (1810–1890) |
| XI | 200 | 1 | Hornemann, Emil (1810–1890) |
| XI | 211 | 1 | Hornemann, Emil (1810–1890) |
| XI | 241 | 1 | Hornemann, Emil (1810–1890) |
| XI | 253 | 1 | Hornemann, Emil (1810–1890) |
| XI | 275 | 1 | Hornemann, Emil (1810–1890) |
| XI | 278 | 1 | Hornemann, Emil (1810–1890) |
| XI | 279 | 1 | Hornemann, Emil (1810–1890) |
| XI | 285 | 1 | Hornemann, Emil (1810–1890) |
| XI | 303 | 1 | Hornemann, Emil (1810–1890) |
| XI | 313 | 1 | Hornemann, Emil (1810–1890) |
| XI | 322 | 1 | Hornemann, Emil (1810–1890) |
| XI | 327 | 1 | Hornemann, Emil (1810–1890) |
| XI | 347 | 1 | Hornemann, Emil (1810–1890) |
| XI | 353 | 1 | Hornemann, Emil (1810–1890) |
| XI | 355 | 1 | Hornemann, Emil (1810–1890) |
| XI | 358 | 1 | Hornemann, Emil (1810–1890) |
| XI | 381 | 1 | Hornemann, Emil (1810–1890) |
| XI | 391 | 1 | Hornemann, Emil (1810–1890) |
| XI | 407 | 1 | Hornemann, Emil (1810–1890) |
| XI | 410 | 1 | Hornemann, Emil (1810–1890) |
| XI | 416 | 1 | Hornemann, Emil (1810–1890) |
| XI | 435 | 1 | Hornemann, Emil (1810–1890) |
| XI | 448 | 1 | Hornemann, Emil (1810–1890) |
| XI | 453 | 1 | Hornemann, Emil (1810–1890) |
| XI | 458 | 1 | Hornemann, Emil (1810–1890) |
| XI | 473 | 1 | Hornemann, Emil (1810–1890) |
| XI | 480 | 1 | Hornemann, Emil (1810–1890) |
| XI | 482 | 1 | Hornemann, Emil (1810–1890) |
|  | 20 | 1 | Bardenfleth, Johan Frederik (Fritz) (1835–1890) |
|  | 418 | 1 | Vernet, Joseph (1718–1789) |

## Fjernet pladsholderindhold (opgave udført)

Håndskrevet eksempelindhold med opfundne bind- og sidetal (bind XII–XXIV findes ikke) er fjernet:

- `mockup/entry.html` (opdigtet dagbogstekst, «Bind XVIII»; linkede til manglende `entry_en.html`)
- `mockup/search.html` / `search_en.html` (statisk demo-søgning på «Rom», «16 resultater»)
- `mockup/data/mock-hca.js` (ubrugt eksempeldatasæt)
- de 7 statiske eksempelkort i `diaries.html` / `diaries_en.html`
- «Søg»-kortet på `works.html` / `works_en.html` (nyt søgeresultatsside: se `docs/plan-fulltext-search.md`)
