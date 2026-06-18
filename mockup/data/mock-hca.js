/* Mock HCA dataset — structurally mirrors the real schema:
   Registry (Reg######) · Diary pages (Pag######) · RefInDiaryPage join
   Replace by running: scripts/normalization/csv_to_mock_js.py

   H1 registers: PERSON-REGISTER · STED-REGISTER · VÆRK-REGISTER
   VÆRK-REGISTER H2: BILLEDKUNST · MUSIK · H. C. ANDERSEN · ANDRE FORFATTERE
*/

const HCA = {

  /* ------------------------------------------------------------------ *
   * PERSON-REGISTER — 10,228 entities · 39,361 diary refs
   * ------------------------------------------------------------------ */
  persons: [
    { id: "Reg0048570", label: "Collin, Edvard",         refs: 767,  link: "persons.html" },
    { id: "Reg0069470", label: "Henriques, Martin R.",   refs: 462,  link: "persons.html" },
    { id: "Reg0090690", label: "Melchior, Moritz G.",    refs: 457,  link: "persons.html" },
    { id: "Reg0046040", label: "Collin, Henriette Oline",refs: 438,  link: "persons.html" },
    { id: "Reg0082540", label: "Koch, Ida f. Wulff",     refs: 419,  link: "persons.html" },
    { id: "Reg0046030", label: "Collin, Jonas",          refs: 412,  link: "persons.html" },
    { id: "Reg0161110", label: "Melchior, Dorothea",     refs: 398,  link: "persons.html" },
    { id: "Reg0169560", label: "Ørsted, Hans Christian", refs: 387,  link: "persons.html" },
    { id: "Reg0097310", label: "Lind, Jenny",            refs: 318,  link: "persons.html" },
    { id: "Reg0061810", label: "Hartmann, Johan Peter Emilius", refs: 312, link: "persons.html" },
    { id: "Reg0022240", label: "Bournonville, August",   refs: 298,  link: "persons.html" },
    { id: "Reg0030760", label: "Collin, Louise f. Lind", refs: 276,  link: "persons.html" },
    { id: "Reg0049710", label: "Dickens, Charles",       refs: 189,  link: "persons.html" },
    { id: "Reg0189100", label: "Thorvaldsen, Bertel",    refs: 176,  link: "persons.html" },
    { id: "Reg0159800", label: "Liszt, Franz",           refs: 142,  link: "persons.html" }
  ],

  /* ------------------------------------------------------------------ *
   * STED-REGISTER — 2,508 entities · 18,849 diary refs
   * ------------------------------------------------------------------ */
  places: [
    { id: "Reg0010880", label: "København",   refs: 1564, country: "Danmark",  lat: 55.6761, lon: 12.5683, link: "place.html" },
    { id: "Reg0015520", label: "Paris",       refs:  373, country: "Frankrig", lat: 48.8566, lon:  2.3522, link: "place.html" },
    { id: "Reg0161130", label: "Rolighed",    refs:  346, country: "Danmark",  lat: 55.7403, lon: 12.6047, link: "place.html" },
    { id: "Reg0017430", label: "Rom",         refs:  332, country: "Italien",  lat: 41.9028, lon: 12.4964, link: "place.html" },
    { id: "Reg0034900", label: "Dresden",     refs:  325, country: "Tyskland", lat: 51.0504, lon: 13.7373, link: "place.html" },
    { id: "Reg0128480", label: "Odense",      refs:  287, country: "Danmark",  lat: 55.4038, lon: 10.4024, link: "place.html" },
    { id: "Reg0012430", label: "München",     refs:  241, country: "Tyskland", lat: 48.1351, lon: 11.5820, link: "place.html" },
    { id: "Reg0013800", label: "Wien",        refs:  228, country: "Østrig",   lat: 48.2082, lon: 16.3738, link: "place.html" },
    { id: "Reg0018650", label: "Stockholm",   refs:  198, country: "Sverige",  lat: 59.3293, lon: 18.0686, link: "place.html" },
    { id: "Reg0119810", label: "Napoli",      refs:  184, country: "Italien",  lat: 40.8518, lon: 14.2681, link: "place.html" },
    { id: "Reg0019140", label: "London",      refs:  173, country: "England",  lat: 51.5074, lon: -0.1278, link: "place.html" }
  ],

  /* ------------------------------------------------------------------ *
   * VÆRK-REGISTER — H2: BILLEDKUNST (941 entities · 1,436 refs)
   * ------------------------------------------------------------------ */
  billedkunst: {
    h2: "BILLEDKUNST",
    entities: 941, refs: 1436,
    h3: [
      { label: "Malerier og Tegninger", entities: 587, refs: 758 },
      { label: "Skulptur",              entities: 315, refs: 489 },
      { label: "Museer og Samlinger",   entities:  39, refs: 189 }
    ],
    works: [
      { id: "Reg003004", label: "Sixtinske Madonna (Rafael, Dresden)",         h3: "Malerier og Tegninger", refs: 15, link: "work.html" },
      { id: "Reg000726", label: "Den hellige Nat (Correggio, Dresden)",         h3: "Malerier og Tegninger", refs:  6, link: "work.html" },
      { id: "Reg002506", label: "Niels Ebbesen og Grev Gert (Carl Bloch)",      h3: "Malerier og Tegninger", refs:  6, link: "work.html" },
      { id: "Reg000737", label: "Den mediceiske Venus (Uffizi, Firenze)",       h3: "Skulptur",              refs: 10, link: "work.html" },
      { id: "Reg002041", label: "Laokoon-Gruppen (Vatikanet, Rom)",             h3: "Skulptur",              refs:  7, link: "work.html" },
      { id: "Reg000248", label: "Apollo di Belvedere (Vatikanet, Rom)",         h3: "Skulptur",              refs:  6, link: "work.html" },
      { id: "Reg002700", label: "Schweizer-Løven (Thorvaldsen, Luzern)",       h3: "Skulptur",              refs:  5, link: "work.html" },
      { id: "Reg001822", label: "Louvre (Paris)",                               h3: "Museer og Samlinger",  refs: 18, link: "work.html" },
      { id: "Reg001004", label: "Uffizi (Firenze)",                             h3: "Museer og Samlinger",  refs: 14, link: "work.html" },
      { id: "Reg002280", label: "Dresden Gemäldegalerie",                      h3: "Museer og Samlinger",  refs: 12, link: "work.html" }
    ]
  },

  /* ------------------------------------------------------------------ *
   * VÆRK-REGISTER — H2: MUSIK + Skuespil H3s (1,260 entities · 3,711 refs)
   * Maps to navigation wing: Teater & Musik
   * ------------------------------------------------------------------ */
  teaterMusik: {
    label: "Teater & Musik",
    entities: 1260, refs: 3711,
    h3: [
      { h2: "MUSIK",             label: "Operaer og Syngestykker, Skuespil med Musik", entities: 241, refs: 1041 },
      { h2: "MUSIK",             label: "Vokal- og Instrumentalmusik",                entities: 135, refs:  218 },
      { h2: "MUSIK",             label: "Balletter",                                  entities:  80, refs:  292 },
      { h2: "ANDRE FORFATTERE",  label: "Skuespil",                                   entities: 747, refs: 1479 },
      { h2: "H. C. ANDERSEN",    label: "Skuespil og Operatekster",                   entities:  57, refs:  681 }
    ],
    works: [
      { id: "Reg001260", label: "Faust (C. Gounod)",                   h2: "MUSIK",            h3: "Operaer og Syngestykker", refs: 57, link: "work.html" },
      { id: "Reg002774", label: "Ravnen (J. P. E. Hartmann)",          h2: "MUSIK",            h3: "Operaer og Syngestykker", refs: 41, link: "work.html" },
      { id: "Reg000875", label: "Liden Kirsten (J. P. E. Hartmann)",   h2: "MUSIK",            h3: "Operaer og Syngestykker", refs: 34, link: "work.html" },
      { id: "Reg003479", label: "Waldemar (A. Bournonville)",          h2: "MUSIK",            h3: "Balletter",               refs: 30, link: "work.html" },
      { id: "Reg003242", label: "Thrymskviden (A. Bournonville)",      h2: "MUSIK",            h3: "Balletter",               refs: 29, link: "work.html" },
      { id: "Reg001521", label: "Hakon Jarl (A. Oehlenschlæger)",     h2: "ANDRE FORFATTERE", h3: "Skuespil",                refs: 16, link: "work.html" },
      { id: "Reg001790", label: "Jeppe paa Bjerget (L. Holberg)",     h2: "ANDRE FORFATTERE", h3: "Skuespil",                refs: 16, link: "work.html" },
      { id: "Reg000980", label: "Faust I (Goethe)",                    h2: "ANDRE FORFATTERE", h3: "Skuespil",                refs: 14, link: "work.html" },
      { id: "Reg000712", label: "Mulatten (H.C. Andersen)",           h2: "H. C. ANDERSEN",   h3: "Skuespil og Operatekster",refs: 22, link: "work.html" },
      { id: "Reg001140", label: "Fuglen i Pæretræet (H.C. Andersen)", h2: "H. C. ANDERSEN",   h3: "Skuespil og Operatekster",refs: 18, link: "work.html" }
    ]
  },

  /* ------------------------------------------------------------------ *
   * VÆRK-REGISTER — Bogsamling (1,516 entities · 5,048 refs)
   * H2: H. C. ANDERSEN + ANDRE FORFATTERE (excl. Skuespil)
   * ------------------------------------------------------------------ */
  bogsamling: {
    label: "Bogsamling",
    entities: 1516, refs: 5048,
    hca: {
      h2: "H. C. ANDERSEN",
      h3: [
        { label: "Eventyr",                      entities: 288, refs: 2784 },
        { label: "Digte",                        entities: 342, refs:  770 },
        { label: "Romaner og Noveller",          entities:  33, refs:  417 },
        { label: "Skuespil og Operatekster",     entities:  57, refs:  681 },
        { label: "Rejseskildringer",             entities:  21, refs:  245 },
        { label: "Afhandlinger, Artikler m.m.",  entities:  19, refs:  214 },
        { label: "Selvbiografier",               entities:  10, refs:  196 },
        { label: "Samlede og blandede Skrifter", entities:   5, refs:   45 }
      ]
    },
    andreForfattere: {
      h2: "ANDRE FORFATTERE",
      h3: [
        { label: "Digte",                        entities: 250, refs:  341 },
        { label: "Romaner, Noveller, Eventyr",   entities: 229, refs:  338 },
        { label: "Faglitteratur",                entities: 216, refs:  347 },
        { label: "Tidsskrifter og aarbøger (Periodica)", entities: 84, refs: 318 },
        { label: "Samlede og blandede Skrifter", entities:  19, refs:   33 }
      ]
    },
    works: [
      { id: "Reg000713", label: "Den grimme Ælling",           h2: "H. C. ANDERSEN", h3: "Eventyr",            refs: 59, link: "work.html" },
      { id: "Reg001003", label: "Dryaden",                     h2: "H. C. ANDERSEN", h3: "Eventyr",            refs: 58, link: "work.html" },
      { id: "Reg001119", label: "Tommelise",                   h2: "H. C. ANDERSEN", h3: "Eventyr",            refs: 47, link: "work.html" },
      { id: "Reg001622", label: "Snedronningen",               h2: "H. C. ANDERSEN", h3: "Eventyr",            refs: 44, link: "work.html" },
      { id: "Reg001000", label: "Den lille Havfrue",           h2: "H. C. ANDERSEN", h3: "Eventyr",            refs: 41, link: "work.html" },
      { id: "Reg000846", label: "Det døende Barn",             h2: "H. C. ANDERSEN", h3: "Digte",              refs: 14, link: "work.html" },
      { id: "Reg001520", label: "Improvisatoren",              h2: "H. C. ANDERSEN", h3: "Romaner og Noveller",refs: 28, link: "work.html" },
      { id: "Reg001370", label: "Mit Livs Eventyr",            h2: "H. C. ANDERSEN", h3: "Selvbiografier",     refs: 19, link: "work.html" },
      { id: "Reg001979", label: "La Divina Commedia (Dante)",  h2: "ANDRE FORFATTERE",h3: "Digte",             refs:  6, link: "work.html" },
      { id: "Reg002140", label: "Frithiofs Saga (Tegnér)",    h2: "ANDRE FORFATTERE",h3: "Digte",             refs:  5, link: "work.html" }
    ]
  },

  /* ------------------------------------------------------------------ *
   * Diary pages (Pag######) — mirrors Diary sheet
   * ------------------------------------------------------------------ */
  diary: [
    {
      id: "Pag100100", vol: "XII", page: 100, date: "1833-10-18", year: 1833,
      heading: "Rom, den 18. Oktober.",
      excerpt: "Tilbragt Formiddagen hos Thorvaldsen i hans Atelier; saae paa hans store Basrelief. Han talte om Hjemmet og syntes rørt. Gaaet til Colosseum om Aftenen — Maanen kastede et uvirkeligt Lys over Stenene.",
      link: "entry.html"
    },
    {
      id: "Pag100200", vol: "XII", page: 140, date: "1833-11-12", year: 1833,
      heading: "Napoli, den 12. November.",
      excerpt: "Besteg i Dag Vesuvius med to engelske Rejsende. Vejen er besværlig, men Udsigten fra Toppen overvælder Sindet. Lavaen gløder endnu i Revnerne nedenfor.",
      link: "entry.html"
    },
    {
      id: "Pag100300", vol: "XVI", page: 55, date: "1843-09-24", year: 1843,
      heading: "Paris, den 24. September.",
      excerpt: "Besøgte Heine i hans lille Lejlighed ved Rue d'Amsterdam. Han laa syg men var aandfuld som altid. Talte om Poesiens Vilkaar i Frankrig og i Tydskland.",
      link: "entry.html"
    },
    {
      id: "Pag100400", vol: "XVIII", page: 82, date: "1847-06-30", year: 1847,
      heading: "London, den 30. Juni.",
      excerpt: "Middag hos Dickens i Devonshire Terrace. Huset livligt og festligt. Han læste selv nogle Passager af sin nye Fortælling og lo hjertelig. Jenny Linds Triumph i Operaen taler hele London om.",
      link: "entry.html"
    },
    {
      id: "Pag100500", vol: "XX", page: 210, date: "1854-11-17", year: 1854,
      heading: "Weimar, den 17. November.",
      excerpt: "Liszt spillede for os om Aftenen — en Beethoven-Sonate og et eget Fantasistykke. Storhertuginden overøste ham med Ros. Jeg sad stille og lyttede.",
      link: "entry.html"
    },
    {
      id: "Pag100600", vol: "XXII", page: 44, date: "1860-07-15", year: 1860,
      heading: "Kjøbenhavn, den 15. Juli.",
      excerpt: "Tænkte paa Ørsted idag; hans Død er mig endnu som et Saar. Eduard Collin kom til Kaffe; vi talte om gamle Dage. Solen skinnede over Øresund.",
      link: "entry.html"
    },
    {
      id: "Pag100700", vol: "XXIV", page: 330, date: "1862-12-05", year: 1862,
      heading: "Nizza, den 5. December.",
      excerpt: "Vejret herligt, Havet stille og blaat. Læste i Avisen om Jenny Linds ny Koncertsæson i London. Det er Vinter i Danmark, mens jeg sidder her i Sol.",
      link: "entry.html"
    }
  ],

  /* ------------------------------------------------------------------ *
   * RefInDiaryPage — mirrors join table
   * ------------------------------------------------------------------ */
  refs: [
    { page_id: "Pag100100", reg_id: "Reg0017430", rel: "sted" },
    { page_id: "Pag100100", reg_id: "Reg0189100", rel: "person" },
    { page_id: "Pag100200", reg_id: "Reg0119810", rel: "sted" },
    { page_id: "Pag100200", reg_id: "Reg0017430", rel: "sted" },
    { page_id: "Pag100300", reg_id: "Reg0015520", rel: "sted" },
    { page_id: "Pag100400", reg_id: "Reg0019140", rel: "sted" },
    { page_id: "Pag100400", reg_id: "Reg0049710", rel: "person" },
    { page_id: "Pag100400", reg_id: "Reg0097310", rel: "person" },
    { page_id: "Pag100500", reg_id: "Reg0159800", rel: "person" },
    { page_id: "Pag100600", reg_id: "Reg0010880", rel: "sted" },
    { page_id: "Pag100600", reg_id: "Reg0169560", rel: "person" },
    { page_id: "Pag100600", reg_id: "Reg0048570", rel: "person" },
    { page_id: "Pag100700", reg_id: "Reg0097310", rel: "person" }
  ],

  refsFor(page_id) {
    return this.refs.filter(r => r.page_id === page_id).map(r => ({
      ...r,
      entity: this.persons.find(p => p.id === r.reg_id)
           || this.places.find(p => p.id === r.reg_id)
           || null
    }));
  }
};
