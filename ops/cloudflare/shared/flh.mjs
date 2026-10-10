// Shared logic for the FLH publication clock and watchdog Workers.
// Mirrors scripts/publish_today_history.py (due_item) and scripts/verify_today_history.py (checks).

export function boundedFetch(fetchFn) {
  return (url, init = {}) => fetchFn(url, { ...init, signal: AbortSignal.timeout(15000) });
}

export const REPO = 'b2bconsult4u-FLH/florida-learning-hub';
export const WORKFLOW = 'publish-today-history.yml';
export const ORIGIN = 'https://floridalearninghub.org';
const GH = 'https://api.github.com';
const UA = 'FLH-Publication-Ops/1.0';

export function easternNow(date = new Date()) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(date).map((x) => [x.type, x.value]),
  );
  return { date: `${p.year}-${p.month}-${p.day}`, hour: Number(p.hour), minute: Number(p.minute), hhmm: `${p.hour}:${p.minute}` };
}

export function dueItem(manifest, today) {
  const items = (manifest.entries || []).filter((x) => x.publish_date === today && x.status === 'Approved for Publication');
  if (items.length > 1) throw new Error(`Multiple approved entries for ${today}`);
  return items[0] || null;
}

export function unescapeHtml(s) {
  return s
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

export function liveChecks(item) {
  return [
    ['article', `${ORIGIN}/${item.live_file}`, [`<h1>${item.title}</h1>`]],
    ['homepage', `${ORIGIN}/`, [`Today in Florida History · ${item.display_date}`, `href="${item.live_file}"`]],
    ['archive', `${ORIGIN}/today-in-florida-history.html`, [`Featured Entry — ${item.display_date}`, `href="${item.live_file}"`]],
    ['sitemap', `${ORIGIN}/sitemap.xml`, [`${ORIGIN}/${item.live_file}`]],
  ];
}

// Same four checks as the GitHub verification step, run from outside GitHub.
export async function verifyLive(item, fetchFn = fetch) {
  const failures = [];
  for (const [name, url, needles] of liveChecks(item)) {
    try {
      const res = await fetchFn(`${url}?flh_verify=${Date.now()}`, { headers: { 'Cache-Control': 'no-cache', 'User-Agent': UA } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = unescapeHtml(await res.text());
      if (!needles.every((n) => body.includes(n))) failures.push(`${name}: expected publication content missing`);
    } catch (e) {
      failures.push(`${name}: ${e.message}`);
    }
  }
  return { ok: failures.length === 0, failures };
}

const ghHeaders = (env, extra = {}) => ({
  Authorization: `Bearer ${env.GITHUB_TOKEN}`, 'User-Agent': UA, 'X-GitHub-Api-Version': '2022-11-28', ...extra,
});

export async function getManifest(env, fetchFn = fetch) {
  const res = await fetchFn(`${GH}/repos/${REPO}/contents/today-history-queue/manifest.json?ref=main`, {
    headers: ghHeaders(env, { Accept: 'application/vnd.github.raw+json' }),
  });
  if (!res.ok) throw new Error(`manifest fetch failed: HTTP ${res.status}`);
  return res.json();
}

export async function recentRuns(env, fetchFn = fetch) {
  const res = await fetchFn(`${GH}/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=100`, {
    headers: ghHeaders(env, { Accept: 'application/vnd.github+json' }),
  });
  if (!res.ok) throw new Error(`run list failed: HTTP ${res.status}`);
  return (await res.json()).workflow_runs || [];
}

// A queued/in-progress run created in the last 30 minutes means a publish is already under way.
// Older "queued" runs do not block: a GitHub backlog must not stop recovery.
export function runInFlight(runs, now = new Date(), windowMs = 30 * 60 * 1000) {
  return runs.some((r) => ['queued', 'in_progress', 'waiting', 'pending', 'requested'].includes(r.status)
    && now - Date.parse(r.created_at) < windowMs);
}

export async function dispatchWorkflow(env, fetchFn = fetch, source = 'cloudflare-clock') {
  const res = await fetchFn(`${GH}/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: ghHeaders(env, { Accept: 'application/vnd.github+json', 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ref: 'main', inputs: { trigger_source: source } }),
  });
  if (res.status !== 204) throw new Error(`dispatch failed: HTTP ${res.status}`);
}

export async function getJson(kv, key) {
  const v = await kv.get(key);
  return v ? JSON.parse(v) : null;
}
export const putJson = (kv, key, obj, opts) => kv.put(key, JSON.stringify(obj), opts);

// Dead-man's-switch ping (Healthchecks.io). Missing pings are what raise the alarm, so errors are swallowed here.
export async function ping(url, suffix = '', body = '', fetchFn = fetch) {
  if (!url) return;
  try { await fetchFn(url + suffix, { method: 'POST', body: String(body).slice(0, 5000) }); } catch { /* ignore */ }
}

export async function alert(env, title, message, priority = 'high', fetchFn = fetch) {
  if (!env.NTFY_TOPIC) return false;
  try {
    const res = await fetchFn(`https://ntfy.sh/${env.NTFY_TOPIC}`, {
      method: 'POST', body: message, headers: { Title: title, Priority: priority, Tags: 'warning' },
    });
    return res.ok;
  } catch { return false; }
}

export function runEvidence(runs, date) {
  return runs.filter(r => r.created_at && easternNow(new Date(r.created_at)).date === date).map(r => ({
    run_id: r.id, event: r.event, actor: r.actor?.login, created_at: r.created_at,
    started_at: r.run_started_at, status: r.status, conclusion: r.conclusion, url: r.html_url,
  }));
}
