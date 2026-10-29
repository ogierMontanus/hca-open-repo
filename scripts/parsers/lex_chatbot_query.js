// lex_chatbot_query.js — asks Lex's chatbot (https://spoerg.lex.dk/) about people, one
// fresh conversation each, and stores the cited SOURCE-CARD links (href + short card
// text) as JSON lines. Companion to scripts/parsers/lex_link_candidates.py, which
// verifies and filters them. Read docs/data-model/lex-dk-links.md first.
//
// Politeness / terms: the service is a public test version ("AI kan lave fejl"),
// lex.dk's robots.txt disallows AI crawlers and asks for approval before bulk AI use
// of its content. This script is therefore (1) sequential with a pause between
// conversations, (2) declines all non-essential cookies, (3) meant for SMALL runs
// (the trial was 100 persons). Do not scale it up to the full register without
// asking the Lex editors (chatbot@lex.dk).
//
//   node scripts/parsers/lex_chatbot_query.js QUERIES.json OUT.jsonl [start end]
//   QUERIES.json: [{ "rid": "Reg…", "label": "…", "name": "Adam Oehlenschläger (1779–1850)" }, …]
//
// Needs Playwright (npm i playwright). Raw output quotes lex.dk text: keep it out of git.
// Sequential, polite queries to https://spoerg.lex.dk/ (new conversation each). Keeps links + short card text.
const { chromium } = require('playwright');
const fs = require('fs');
const [,, qfile, outfile, startArg, endArg] = process.argv;
const Q = JSON.parse(fs.readFileSync(qfile, 'utf8'));
const start = +startArg || 0, end = Math.min(+endArg || Q.length, Q.length);
const done = new Set(fs.existsSync(outfile) ? fs.readFileSync(outfile, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l).rid) : []);
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launch();
  for (let i = start; i < end; i++) {
    const q = Q[i];
    if (done.has(q.rid)) continue;
    const ctx = await b.newContext({ locale: 'da-DK', viewport: { width: 1100, height: 1000 } });
    const p = await ctx.newPage();
    let rec = { rid: q.rid, label: q.label, name: q.name, ok: false };
    try {
      await p.goto('https://spoerg.lex.dk/', { waitUntil: 'domcontentloaded', timeout: 45000 });
      await p.waitForTimeout(2000);
      const decl = p.locator('#declineButton'); if (await decl.count()) await decl.first().click({ timeout: 3000 }).catch(() => {});
      await p.waitForTimeout(500);
      const prompt = `Hvem var ${q.name}? Giv link til artiklen i Dansk Biografisk Leksikon og til andre udførlige leksikonartikler om personen.`;
      await p.fill('#input-message', prompt);
      await p.keyboard.press('Enter');
      // wait for streaming to finish: body text stable for 8s, max 100s
      let last = -1, stable = 0;
      for (let t = 0; t < 50; t++) {
        await sleep(2000);
        const len = (await p.innerText('body')).length;
        if (len === last && len > 400) { if (++stable >= 4) break; } else stable = 0;
        last = len;
      }
      rec.text = (await p.innerText('body'));
      rec.links = await p.evaluate(() => {
        const out = [];
        for (const a of document.querySelectorAll('a[href]')) {
          const h = a.href; if (!/^https:\/\/[a-z0-9.-]*lex\.dk\//.test(h) || /mere\.lex\.dk|\/\.|^https:\/\/lex\.dk\/$/.test(h) || /spoerg\.lex\.dk/.test(h)) continue;
          let el = a, txt = a.innerText.trim();
          for (let k = 0; k < 4 && txt.length < 80 && el.parentElement; k++) { el = el.parentElement; txt = el.innerText.trim(); }
          out.push({ href: h, anchor: a.innerText.trim().slice(0, 80), card: txt.slice(0, 380) });
        }
        return out;
      });
      rec.ok = true;
    } catch (e) { rec.error = String(e).slice(0, 200); }
    fs.appendFileSync(outfile, JSON.stringify(rec) + '\n');
    console.log(i, q.rid, rec.ok ? 'ok' : 'ERR', (rec.links || []).length);
    await ctx.close();
    await sleep(6000);   // be polite: pause between conversations
  }
  await b.close();
})();
