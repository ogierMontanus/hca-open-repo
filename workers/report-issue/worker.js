// Cloudflare Worker — receives bug reports from the "Indberet fejl" button
// (mockup/js/report-issue.js) and files them as GitHub issues.
//
// Why a Worker: the site is static (GitHub Pages), and a GitHub token must
// never be shipped to the browser. The token lives here as a secret.
// Setup and rationale: docs/report-issue.md.

const DEFAULTS = {
  GITHUB_REPO: 'ogierMontanus/hca-open-repo',
  ALLOWED_ORIGINS: 'https://ogiermontanus.github.io',
  SCREENSHOT_BRANCH: 'report-screenshots',
  ISSUE_LABEL: 'brugerrapport',
};

const LIMITS = {
  name: 100,
  email: 254,
  title: 120,
  titleMin: 3,
  description: 5000,
  descriptionMin: 10,
  url: 500,
  agent: 300,
  body: 4 * 1024 * 1024,        // whole JSON request
  screenshot: 2.5 * 1024 * 1024, // decoded image bytes
};

const EMAIL_RE = /^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[^\s@<>()[\]\\,;:"]{2,}$/;

// Image type -> [file extension, magic-byte check]. Never trust the declared
// type alone: the bytes must actually be that format.
const IMAGE_TYPES = {
  'image/png': ['png', (b) => b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47],
  'image/jpeg': ['jpg', (b) => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff],
  'image/webp': ['webp', (b) => b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46
    && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50],
};

class HttpError extends Error {
  constructor(status, code) {
    super(code);
    this.status = status;
    this.code = code;
  }
}

function str(v) {
  return typeof v === 'string' ? v : '';
}

/** Collapse whitespace to one line and trim. */
function oneLine(v) {
  return str(v).replace(/\s+/g, ' ').trim();
}

/** Stop `@user` from pinging people from a public form. */
function defangMentions(s) {
  return s.replace(/@(?=[A-Za-z0-9])/g, '@​');
}

/** Inline text for the issue body: no markdown/HTML injection, no pings. */
function inlineText(s) {
  return defangMentions(s).replace(/[\\`*_[\]<>|]/g, (c) => '\\' + c);
}

export function validate(input) {
  const data = input && typeof input === 'object' ? input : {};
  const out = {
    name: oneLine(data.name),
    email: oneLine(data.email),
    title: oneLine(data.title),
    description: str(data.description).replace(/\r\n?/g, '\n').trim(),
    pageUrl: oneLine(data.pageUrl).slice(0, LIMITS.url),
    userAgent: oneLine(data.userAgent).slice(0, LIMITS.agent),
    viewport: oneLine(data.viewport).slice(0, 30),
    lang: oneLine(data.lang).slice(0, 10),
    screenshot: null,
  };

  if (!out.name || out.name.length > LIMITS.name) throw new HttpError(400, 'invalid_name');
  if (out.email.length > LIMITS.email || !EMAIL_RE.test(out.email)) throw new HttpError(400, 'invalid_email');
  if (out.title.length < LIMITS.titleMin || out.title.length > LIMITS.title) throw new HttpError(400, 'invalid_title');
  if (out.description.length < LIMITS.descriptionMin || out.description.length > LIMITS.description) {
    throw new HttpError(400, 'invalid_description');
  }
  if (out.pageUrl && !/^https?:\/\//i.test(out.pageUrl)) out.pageUrl = '';

  const shot = data.screenshot;
  if (shot) {
    const kind = IMAGE_TYPES[str(shot.type)];
    if (!kind) throw new HttpError(400, 'invalid_screenshot');
    const base64 = str(shot.data);
    if (!/^[A-Za-z0-9+/]+={0,2}$/.test(base64)) throw new HttpError(400, 'invalid_screenshot');
    const approxBytes = Math.floor(base64.length * 3 / 4);
    if (approxBytes > LIMITS.screenshot) throw new HttpError(413, 'screenshot_too_large');
    const head = Uint8Array.from(atob(base64.slice(0, 32)), (c) => c.charCodeAt(0));
    if (!kind[1](head)) throw new HttpError(400, 'invalid_screenshot');
    out.screenshot = { ext: kind[0], base64 };
  }
  return out;
}

export function buildIssueBody(report, screenshotUrl, now = new Date()) {
  const lines = [];
  lines.push('## Beskrivelse', '', defangMentions(report.description), '');

  if (screenshotUrl) {
    lines.push('## Skærmbillede', '', `![Skærmbillede fra brugeren](${screenshotUrl})`, '');
  } else if (report.screenshot) {
    lines.push('## Skærmbillede', '', '_Brugeren vedhæftede et skærmbillede, men det kunne ikke gemmes._', '');
  }

  lines.push('## Indberetter', '');
  lines.push(`- **Navn:** ${inlineText(report.name)}`);
  lines.push(`- **E-mail:** \`${report.email}\``);
  lines.push('', '## Teknisk kontekst', '');
  if (report.pageUrl) lines.push(`- **Side:** <${report.pageUrl.replace(/[<>\s]/g, encodeURIComponent)}>`);
  if (report.viewport) lines.push(`- **Vindue:** ${inlineText(report.viewport)}`);
  if (report.userAgent) lines.push(`- **Browser:** ${inlineText(report.userAgent)}`);
  if (report.lang) lines.push(`- **Sprog:** ${inlineText(report.lang)}`);
  lines.push(`- **Indsendt:** ${now.toISOString()}`);
  lines.push('', '---', '_Oprettet automatisk via "Indberet fejl"-knappen på webstedet._');
  return lines.join('\n');
}

async function github(env, method, path, body) {
  const res = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'hca-report-issue-worker',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

/** Make sure the screenshot branch exists (created from the default branch). */
async function ensureBranch(env, repo, branch) {
  const ref = await github(env, 'GET', `/repos/${repo}/git/ref/heads/${encodeURIComponent(branch)}`);
  if (ref.ok) return;
  if (ref.status !== 404) throw new Error(`ref lookup failed: ${ref.status}`);

  const info = await github(env, 'GET', `/repos/${repo}`);
  if (!info.ok) throw new Error(`repo lookup failed: ${info.status}`);
  const { default_branch: base } = await info.json();
  const baseRef = await github(env, 'GET', `/repos/${repo}/git/ref/heads/${encodeURIComponent(base)}`);
  if (!baseRef.ok) throw new Error(`base ref lookup failed: ${baseRef.status}`);
  const { object } = await baseRef.json();

  const created = await github(env, 'POST', `/repos/${repo}/git/refs`, {
    ref: `refs/heads/${branch}`,
    sha: object.sha,
  });
  // 422 = someone created it between our GET and POST; that is fine.
  if (!created.ok && created.status !== 422) throw new Error(`branch create failed: ${created.status}`);
}

/** Commit the image to the screenshot branch; returns its raw URL, or null. */
async function storeScreenshot(env, repo, branch, shot, now) {
  try {
    await ensureBranch(env, repo, branch);
    const rand = crypto.randomUUID().slice(0, 8);
    const stamp = now.toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const path = `screenshots/${now.getUTCFullYear()}/${String(now.getUTCMonth() + 1).padStart(2, '0')}/${stamp}-${rand}.${shot.ext}`;
    const res = await github(env, 'PUT', `/repos/${repo}/contents/${path}`, {
      message: `Skærmbillede til brugerrapport (${stamp})`,
      content: shot.base64,
      branch,
    });
    if (!res.ok) throw new Error(`upload failed: ${res.status}`);
    const json = await res.json();
    return json.content?.download_url || `https://raw.githubusercontent.com/${repo}/${branch}/${path}`;
  } catch (err) {
    console.error('screenshot not stored:', err.message);
    return null;
  }
}

function corsHeaders(origin, allowed) {
  if (!origin || !allowed.includes(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function json(status, payload, headers) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...headers },
  });
}

async function handlePost(request, env, cfg, cors) {
  const origin = request.headers.get('Origin');
  if (!origin || !cfg.allowedOrigins.includes(origin)) throw new HttpError(403, 'origin_not_allowed');
  if (!env.GITHUB_TOKEN) throw new HttpError(500, 'not_configured');

  const declared = Number(request.headers.get('Content-Length') || 0);
  if (declared > LIMITS.body) throw new HttpError(413, 'too_large');
  const text = await request.text();
  if (text.length > LIMITS.body) throw new HttpError(413, 'too_large');

  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new HttpError(400, 'invalid_json');
  }

  // Honeypot: the form hides this field from people. Pretend success so bots
  // learn nothing, but file nothing.
  if (data && str(data.website).trim()) return json(200, { ok: true, number: 0, url: '' }, cors);

  const report = validate(data);
  const now = new Date();
  const shotUrl = report.screenshot
    ? await storeScreenshot(env, cfg.repo, cfg.branch, report.screenshot, now)
    : null;

  const res = await github(env, 'POST', `/repos/${cfg.repo}/issues`, {
    title: `[Fejlrapport] ${report.title}`,
    body: buildIssueBody(report, shotUrl, now),
    labels: [cfg.label],
  });
  if (!res.ok) {
    console.error('issue create failed:', res.status, await res.text());
    throw new HttpError(502, 'github_error');
  }
  const issue = await res.json();
  return json(201, { ok: true, number: issue.number, url: issue.html_url, screenshot: !report.screenshot || !!shotUrl }, cors);
}

export default {
  async fetch(request, env) {
    const cfg = {
      repo: env.GITHUB_REPO || DEFAULTS.GITHUB_REPO,
      branch: env.SCREENSHOT_BRANCH || DEFAULTS.SCREENSHOT_BRANCH,
      label: env.ISSUE_LABEL || DEFAULTS.ISSUE_LABEL,
      allowedOrigins: (env.ALLOWED_ORIGINS || DEFAULTS.ALLOWED_ORIGINS)
        .split(',').map((s) => s.trim()).filter(Boolean),
    };
    const cors = corsHeaders(request.headers.get('Origin'), cfg.allowedOrigins);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (request.method !== 'POST') return json(405, { ok: false, error: 'method_not_allowed' }, cors);

    try {
      return await handlePost(request, env, cfg, cors);
    } catch (err) {
      if (err instanceof HttpError) return json(err.status, { ok: false, error: err.code }, cors);
      console.error('unexpected:', err);
      return json(500, { ok: false, error: 'server_error' }, cors);
    }
  },
};
