import test from 'node:test';
import assert from 'node:assert/strict';
import { easternNow, dueItem, unescapeHtml, runInFlight, verifyLive } from '../shared/flh.mjs';
import { runClock } from '../clock/src/index.mjs';
import watchdog, { runWatchdog, statusReport } from '../watchdog/src/index.mjs';

const ITEM = { publish_date: '2026-10-10', display_date: 'October 10', status: 'Approved for Publication',
  title: "Hurricane Michael's Landfall", link_title: 'x', summary: 's', staged_file: 'a.html', live_file: 'today-october-10-michael.html' };
const MANIFEST = { entries: [ITEM] };

class KV { m = new Map();
  async get(k) { return this.m.get(k) ?? null; }
  async put(k, v) { this.m.set(k, v); }
  async list({ prefix }) { return { keys: [...this.m.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })) }; } }

// Fake network. `live` controls whether the site shows today's entry; `runs` is the workflow-run list.
function net({ live = false, runs = [], dispatchStatus = 204, manifest = MANIFEST } = {}) {
  const calls = [];
  const fn = async (url, init = {}) => {
    calls.push({ url: String(url), method: init.method || 'GET' });
    const u = String(url);
    if (u.includes('/contents/today-history-queue/manifest.json')) return Response.json(manifest);
    if (u.includes('/actions/workflows/') && u.includes('/runs')) return Response.json({ workflow_runs: runs });
    if (u.includes('/dispatches')) return new Response(null, { status: dispatchStatus });
    if (u.includes('ntfy.sh') || u.includes('hc-ping')) return new Response('ok');
    if (u.startsWith('https://floridalearninghub.org')) {
      if (!live) return new Response('old page', { status: 200 });
      const body = u.includes('sitemap') ? `https://floridalearninghub.org/${ITEM.live_file}`
        : u.includes('today-in-florida-history') ? `Featured Entry — October 10 href="${ITEM.live_file}"`
        : u.includes(ITEM.live_file) ? '<h1>Hurricane Michael&#39;s Landfall</h1>'
        : `Today in Florida History · October 10 href="${ITEM.live_file}"`;
      return new Response(body);
    }
    return new Response('?', { status: 404 });
  };
  fn.calls = calls; return fn;
}
const mkEnv = () => ({ FLH_STATE: new KV(), GITHUB_TOKEN: 't', HC_CLOCK_URL: 'https://hc-ping.com/c', HC_WATCHDOG_URL: 'https://hc-ping.com/w', NTFY_TOPIC: 'topic' });
const at = (iso) => new Date(iso);
const dispatches = (f) => f.calls.filter((c) => c.url.includes('/dispatches')).length;
const alerts = (f) => f.calls.filter((c) => c.url.includes('ntfy.sh')).length;

test('Eastern time handles EDT and EST', () => {
  assert.equal(easternNow(at('2026-10-10T08:05:00Z')).hhmm, '04:05');
  assert.equal(easternNow(at('2026-11-02T09:05:00Z')).hhmm, '04:05');
  assert.equal(easternNow(at('2026-11-01T04:30:00Z')).date, '2026-11-01');
});
test('dueItem requires approval and rejects duplicates', () => {
  assert.equal(dueItem({ entries: [{ ...ITEM, status: 'Draft' }] }, '2026-10-10'), null);
  assert.throws(() => dueItem({ entries: [ITEM, ITEM] }, '2026-10-10'));
});
test('HTML entities are unescaped like Python html.unescape', () => {
  assert.equal(unescapeHtml('Michael&#39;s &amp; &#x27;x&#x27; &quot;'), `Michael's & 'x' "`);
});
test('runInFlight ignores stale queued runs', () => {
  const now = at('2026-10-10T09:00:00Z');
  assert.equal(runInFlight([{ status: 'queued', created_at: '2026-10-10T08:50:00Z' }], now), true);
  assert.equal(runInFlight([{ status: 'queued', created_at: '2026-10-10T06:00:00Z' }], now), false);
  assert.equal(runInFlight([{ status: 'completed', created_at: '2026-10-10T08:59:00Z' }], now), false);
});
test('verifyLive passes only when all four checks pass', async () => {
  assert.equal((await verifyLive(ITEM, net({ live: true }))).ok, true);
  const bad = await verifyLive(ITEM, net({ live: false }));
  assert.equal(bad.ok, false); assert.equal(bad.failures.length, 4);
});

test('clock: before 4 a.m. ET does nothing but heartbeat', async () => {
  const f = net(); const env = mkEnv();
  const r = await runClock(env, { fetch: f, now: at('2026-10-10T07:10:00Z') }); // 3:10 EDT
  assert.equal(r.action, 'before-window'); assert.equal(dispatches(f), 0);
  assert.ok(f.calls.some((c) => c.url === 'https://hc-ping.com/c'));
});
test('clock: dispatches when not live, then waits while a run is in flight', async () => {
  const env = mkEnv(); const f = net();
  assert.equal((await runClock(env, { fetch: f, now: at('2026-10-10T08:10:00Z') })).action, 'dispatched');
  const f2 = net({ runs: [{ status: 'queued', created_at: '2026-10-10T08:10:30Z' }] });
  assert.equal((await runClock(env, { fetch: f2, now: at('2026-10-10T08:20:00Z') })).action, 'waiting-for-run');
  assert.equal(dispatches(f2), 0);
});
test('clock: rechecks recorded success and recovers a later regression', async () => {
  const env = mkEnv(); const f = net({ live: true });
  assert.equal((await runClock(env, { fetch: f, now: at('2026-10-10T08:10:00Z') })).action, 'verified-live');
  const f2 = net();
  assert.equal((await runClock(env, { fetch: f2, now: at('2026-10-10T08:20:00Z') })).action, 'dispatched');
  assert.equal(dispatches(f2), 1);
  assert.equal(JSON.parse(env.FLH_STATE.m.get('day:2026-10-10')).live_et, '04:10');
});
test('clock: dispatch failure pings /fail instead of success', async () => {
  const env = mkEnv(); const f = net({ dispatchStatus: 403 });
  const r = await runClock(env, { fetch: f, now: at('2026-10-10T08:10:00Z') });
  assert.equal(r.action, 'error');
  assert.ok(f.calls.some((c) => c.url === 'https://hc-ping.com/c/fail'));
  assert.ok(!f.calls.some((c) => c.url === 'https://hc-ping.com/c'));
});
test('clock: no approved entry is reported, not dispatched', async () => {
  const f = net({ manifest: { entries: [] } });
  assert.equal((await runClock(mkEnv(), { fetch: f, now: at('2026-10-10T08:10:00Z') })).action, 'error');
  assert.equal(dispatches(f), 0);
});

test('watchdog: silent and healthy when live and clock ticking', async () => {
  const env = mkEnv(); await env.FLH_STATE.put('clock:last_tick', JSON.stringify({ at: '2026-10-10T11:00:00Z' }));
  const f = net({ live: true });
  const r = await runWatchdog(env, { fetch: f, now: at('2026-10-10T11:05:00Z') });
  assert.equal(r.action, 'verified-live'); assert.equal(alerts(f), 0);
});
test('watchdog: not live -> recovery dispatch + one alert per level', async () => {
  const env = mkEnv(); await env.FLH_STATE.put('clock:last_tick', JSON.stringify({ at: '2026-10-10T11:00:00Z' }));
  const f = net();
  const r = await runWatchdog(env, { fetch: f, now: at('2026-10-10T11:05:00Z') });
  assert.equal(r.action, 'problem'); assert.equal(dispatches(f), 1); assert.equal(alerts(f), 0);
  const again = net(); await runWatchdog(env, { fetch: again, now: at('2026-10-10T11:07:00Z') });
  assert.equal(alerts(again), 0, 'first-level alert is deduplicated');
  const second = net(); await runWatchdog(env, { fetch: second, now: at('2026-10-10T11:35:00Z') });
  assert.equal(alerts(second), 1, 'second check escalates');
});
test('watchdog: stopped clock alerts even when article is live', async () => {
  const env = mkEnv(); const f = net({ live: true });
  await runWatchdog(env, { fetch: f, now: at('2026-10-10T11:05:00Z') });
  assert.equal(alerts(f), 1);
});
test('watchdog: acts only in the 7 a.m. Eastern hour (both DST states)', async () => {
  const env = mkEnv(); const f = net();
  assert.equal((await runWatchdog(env, { fetch: f, now: at('2026-10-10T12:05:00Z') })).action, 'outside-window'); // 8:05 EDT
  assert.notEqual((await runWatchdog(env, { fetch: net(), now: at('2026-11-02T12:05:00Z') })).action, 'outside-window'); // 7:05 EST
});
test('status report counts observed on-time days', async () => {
  const env = mkEnv();
  await env.FLH_STATE.put('day:2026-10-09', JSON.stringify({ date: '2026-10-09', live_at: 'x', live_et: '04:10' }));
  await env.FLH_STATE.put('day:2026-10-08', JSON.stringify({ date: '2026-10-08', live_at: 'x', live_et: '08:16' }));
  const s = await statusReport(env);
  assert.equal(s.live_days, 2); assert.equal(s.live_before_0700_et, 1);
});

test('status endpoint requires configured valid bearer token', async () => {
 const env = mkEnv(); env.STATUS_TOKEN = 'secret';
 assert.equal((await watchdog.fetch(new Request('https://test/status'),env)).status,404);
 assert.equal((await watchdog.fetch(new Request('https://test/status',{headers:{Authorization:'Bearer wrong'}}),env)).status,404);
 assert.equal((await watchdog.fetch(new Request('https://test/status',{headers:{Authorization:'Bearer secret'}}),env)).status,200);
});

test('status pagination retains newest days', async () => {
 const env = mkEnv();
 env.FLH_STATE.list = async ({cursor}) => cursor ? {keys:[{name:'day:2026-10-10'}],list_complete:true} : {keys:[{name:'day:2026-10-09'}],list_complete:false,cursor:'next'};
 for (const date of ['2026-10-09','2026-10-10']) await env.FLH_STATE.put('day:'+date,JSON.stringify({date}));
 assert.equal((await statusReport(env)).days_recorded,2);
});
