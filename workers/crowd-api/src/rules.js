/* rules.js — the browser's own validation and review rules, reused as-is.
 *
 * mockup/js/crowd-validate.js and crowd-store.js are UMD modules with no DOM
 * dependency in the paths used here, and are tested against the Python
 * originals (tests/fixtures/crowd_cases.json, tests/js/crowd-store.test.js).
 * Importing them — instead of a third copy — keeps one set of rules for the
 * local mode, the Python reference server and this Worker.
 *
 * src/taxonomy.json is generated from scripts/crowdsource/taxonomy.py
 * (python workers/crowd-api/scripts/sync_taxonomy.py; tests fail on drift).
 */
import taxonomy from './taxonomy.json' with { type: 'json' };
import Validate from '../../../mockup/js/crowd-validate.js';
import Store from '../../../mockup/js/crowd-store.js';

globalThis.CROWD_TAXONOMY = taxonomy;
globalThis.CrowdValidate = Validate;

export { taxonomy, Validate, Store };
