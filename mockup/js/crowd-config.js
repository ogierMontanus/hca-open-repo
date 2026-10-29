/* crowd-config.js — where the crowd pages find their API.
 *
 *   apiBase ''                         same origin: scripts/crowdsource/server.py, or nothing (browser-local mode)
 *   apiBase 'https://….workers.dev'    the GitHub-login Worker (workers/crowd-api): contributions are
 *                                      stored in a private repository and people sign in with GitHub
 *
 * scripts/build_mockup/apply_csp.py reads this value for `connect-src`, so nothing else needs
 * changing. Left empty, the pages behave exactly as before.
 */
window.CROWD_CONFIG = { apiBase: '' };
