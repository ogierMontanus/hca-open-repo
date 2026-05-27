/* Mock HCA dataset — structurally mirrors the real schema:
   Registry (Reg######) · Diary pages (Pag######) · RefInDiaryPage join
   Replace by running: scripts/normalization/csv_to_mock_js.py
*/

const HCA = {

  institutions: [
    {
      id: "inst_rdl",
      name: "The Royal Danish Library",
      type: "Library",
      city: "Copenhagen", country: "Denmark",
      desc: "National library of Denmark, holding the primary HCA manuscript collections.",
      collections: ["col_diaries", "col_letters"],
      works_count: 1842, entities_count: 312
    }
  ],

  collections: [
    {
      id: "col_diaries", institution_id: "inst_rdl",
      name: "H.C. Andersen Diaries", type: "Manuscript / Diary",
      desc: "Handwritten travel and personal diaries, 1825–1875, documenting European journeys and encounters with cultural figures.",
      date_start: 1825, date_end: 1875, works_count: 38,
      link: "diaries.html"
    },
    {
      id: "col_letters", institution_id: "inst_rdl",
      name: "H.C. Andersen Letters", type: "Correspondence",
      desc: "Over 1,000 letters written and received by Andersen, documenting lifelong friendships and professional contacts.",
      date_start: 1820, date_end: 1875, works_count: 1042,
      link: "#"
    }
  ],

  /* Diary entries — mirrors Diary sheet (VolRef, Date, PageRef, DiaryTextLines) */
  works: [
    {
      id: "Pag100100", vol: "XII", page: 100, date: "1833-10-18",
      year: 1833, month: "Oktober", heading: "Rom, den 18. Oktober.",
      title: "Diary: Rome, October–November 1833",
      location: "Rome, Italy",
      excerpt: "Tilbragt Formiddagen hos Thorvaldsen i hans Atelier; saae paa hans store Basrelief. Han talte om Hjemmet og syntes rørt. Gaaet til Colosseum om Aftenen — Maanen kastede et uvirkeligt Lys over Stenene.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100200", vol: "XII", page: 140, date: "1833-11-12",
      year: 1833, month: "November", heading: "Napoli, den 12. November.",
      title: "Diary: Naples, November–December 1833",
      location: "Naples, Italy",
      excerpt: "Besteg i Dag Vesuvius med to engelske Rejsende. Vejen er besværlig, men Udsigten fra Toppen overvælder Sindet. Lavaen gløder endnu i Revnerne nedenfor.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100300", vol: "XVI", page: 55, date: "1843-09-24",
      year: 1843, month: "September", heading: "Paris, den 24. September.",
      title: "Diary: Paris, September–October 1843",
      location: "Paris, France",
      excerpt: "Besøgte Heine i hans lille Lejlighed ved Rue d'Amsterdam. Han laa syg men var aandfuld som altid. Talte om Poesiens Vilkaar i Frankrig og i Tydskland.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100400", vol: "XVIII", page: 82, date: "1847-06-30",
      year: 1847, month: "Juni", heading: "London, den 30. Juni.",
      title: "Diary: London, June 1847",
      location: "London, United Kingdom",
      excerpt: "Middag hos Dickens i Devonshire Terrace. Huset livligt og festligt. Han læste selv nogle Passager af sin nye Fortælling og lo hjertelig. Jenny Linds Triumph i Operaen taler hele London om.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100500", vol: "XX", page: 210, date: "1854-11-17",
      year: 1854, month: "November", heading: "Weimar, den 17. November.",
      title: "Diary: Weimar, November–December 1854",
      location: "Weimar, Germany",
      excerpt: "Liszt spillede for os om Aftenen — en Beethoven-Sonate og et eget Fantasistykke. Storhertuginden overøste ham med Ros. Jeg sad stille og lyttede.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100600", vol: "XXII", page: 44, date: "1860-07-15",
      year: 1860, month: "Juli", heading: "Kjøbenhavn, den 15. Juli.",
      title: "Diary: Copenhagen, July–August 1860",
      location: "Copenhagen, Denmark",
      excerpt: "Tænkte paa Ørsted idag; hans Død er mig endnu som et Saar. Eduard Collin kom til Kaffe; vi talte om gamle Dage. Solen skinnede over Øresund.",
      collection_id: "col_diaries", link: "entry.html"
    },
    {
      id: "Pag100700", vol: "XXIV", page: 330, date: "1862-12-05",
      year: 1862, month: "December", heading: "Nizza, den 5. December.",
      title: "Diary: Nice, December 1862–January 1863",
      location: "Nice, France",
      excerpt: "Vejret herligt, Havet stille og blaat. Læste i Avisen om Jenny Linds ny Koncertsæson i London. Det er Vinter i Danmark, mens jeg sidder her i Sol.",
      collection_id: "col_diaries", link: "entry.html"
    }
  ],

  /* Registry persons (PERSON-REGISTER) — mirrors Registry sheet with H1 = PERSON-REGISTER */
  persons: [
    {
      id: "Reg000001", label: "Andersen, Hans Christian",
      birth: 1805, death: 1875, nationality: "Danish",
      role: "Author, Poet, Playwright",
      desc: "Danish author of fairy tales, novels, and travel writing. One of the most translated authors in world literature.",
      viaf: "4932746", wikidata: "Q9648",
      link: "person.html"
    },
    {
      id: "Reg000042", label: "Lind, Jenny",
      birth: 1820, death: 1887, nationality: "Swedish",
      role: "Opera singer (soprano)",
      desc: "The 'Swedish Nightingale'. A close personal acquaintance; Andersen is believed to have held romantic feelings for her.",
      viaf: "32167", wikidata: "Q153626",
      link: "person.html"
    },
    {
      id: "Reg000083", label: "Dickens, Charles",
      birth: 1812, death: 1870, nationality: "British",
      role: "Novelist",
      desc: "English novelist whose work Andersen admired greatly. They met during Andersen's London visits in 1847 and 1857.",
      viaf: "95150359", wikidata: "Q5686",
      link: "person.html"
    },
    {
      id: "Reg000124", label: "Liszt, Franz",
      birth: 1811, death: 1886, nationality: "Hungarian",
      role: "Composer, Pianist",
      desc: "Met at the Weimar court; Andersen recorded admiring descriptions of his performances.",
      viaf: "32083", wikidata: "Q41309",
      link: "person.html"
    },
    {
      id: "Reg000156", label: "Heine, Heinrich",
      birth: 1797, death: 1856, nationality: "German",
      role: "Poet",
      desc: "German lyric poet living in Paris. Andersen visited him in 1843 and recorded their conversations.",
      viaf: "29626265", wikidata: "Q44403",
      link: "person.html"
    },
    {
      id: "Reg000189", label: "Thorvaldsen, Bertel",
      birth: 1770, death: 1844, nationality: "Danish",
      role: "Sculptor",
      desc: "Danish neoclassical sculptor based in Rome. Andersen visited him frequently during Italian sojourns.",
      viaf: "4938880", wikidata: "Q313723",
      link: "person.html"
    },
    {
      id: "Reg000211", label: "Ørsted, Hans Christian",
      birth: 1777, death: 1851, nationality: "Danish",
      role: "Physicist, Chemist",
      desc: "Discoverer of electromagnetism. A close family friend of Andersen and important intellectual influence.",
      viaf: "57430936", wikidata: "Q182004",
      link: "person.html"
    },
    {
      id: "Reg000234", label: "Collin, Édouard",
      birth: 1808, death: 1886, nationality: "Danish",
      role: "Civil servant, Friend",
      desc: "Andersen's closest lifelong friend. The most extensive surviving correspondence is with Collin.",
      viaf: "100905617", wikidata: "Q16239278",
      link: "person.html"
    }
  ],

  /* Registry places (STED-REGISTER) */
  places: [
    {
      id: "Reg001001", label: "Rom", label_en: "Rome",
      country: "Italy", region: "Lazio",
      lat: 41.9028, lon: 12.4964,
      link: "place.html"
    },
    {
      id: "Reg001002", label: "Napoli", label_en: "Naples",
      country: "Italy", region: "Campania",
      lat: 40.8518, lon: 14.2681,
      link: "place.html"
    },
    {
      id: "Reg001003", label: "Paris",
      country: "France", region: "Île-de-France",
      lat: 48.8566, lon: 2.3522,
      link: "place.html"
    },
    {
      id: "Reg001004", label: "London",
      country: "United Kingdom", region: "England",
      lat: 51.5074, lon: -0.1278,
      link: "place.html"
    },
    {
      id: "Reg001005", label: "Weimar",
      country: "Germany", region: "Thuringia",
      lat: 50.9795, lon: 11.3236,
      link: "place.html"
    },
    {
      id: "Reg001006", label: "Kjøbenhavn", label_en: "Copenhagen",
      country: "Denmark", region: "Sjælland",
      lat: 55.6761, lon: 12.5683,
      link: "place.html"
    },
    {
      id: "Reg001007", label: "Nizza", label_en: "Nice",
      country: "France", region: "Provence-Alpes-Côte d'Azur",
      lat: 43.7102, lon: 7.262,
      link: "place.html"
    }
  ],

  /* RefInDiaryPage — mirrors join table */
  refs: [
    { page_id: "Pag100100", reg_id: "Reg001001", relation: "located_in" },
    { page_id: "Pag100100", reg_id: "Reg000189", relation: "mentions" },
    { page_id: "Pag100100", reg_id: "Reg001002", relation: "mentions" },
    { page_id: "Pag100200", reg_id: "Reg001002", relation: "located_in" },
    { page_id: "Pag100200", reg_id: "Reg001001", relation: "mentions" },
    { page_id: "Pag100300", reg_id: "Reg001003", relation: "located_in" },
    { page_id: "Pag100300", reg_id: "Reg000156", relation: "meets" },
    { page_id: "Pag100400", reg_id: "Reg001004", relation: "located_in" },
    { page_id: "Pag100400", reg_id: "Reg000083", relation: "meets" },
    { page_id: "Pag100400", reg_id: "Reg000042", relation: "mentions" },
    { page_id: "Pag100500", reg_id: "Reg001005", relation: "located_in" },
    { page_id: "Pag100500", reg_id: "Reg000124", relation: "meets" },
    { page_id: "Pag100600", reg_id: "Reg001006", relation: "located_in" },
    { page_id: "Pag100600", reg_id: "Reg000211", relation: "mentions" },
    { page_id: "Pag100600", reg_id: "Reg000234", relation: "corresponds_with" },
    { page_id: "Pag100700", reg_id: "Reg001007", relation: "located_in" },
    { page_id: "Pag100700", reg_id: "Reg000042", relation: "mentions" }
  ],

  /* Helper: get refs for a work */
  refsFor(page_id) {
    return this.refs.filter(r => r.page_id === page_id).map(r => ({
      ...r,
      entity: this.persons.find(p => p.id === r.reg_id)
           || this.places.find(p => p.id === r.reg_id)
           || null
    }));
  }
};
