// FLH publication watchdog: separate Worker, separate cron, separate secrets from the clock.
// At 7:05 and 7:35 a.m. Eastern it checks the LIVE SITE (not the build), checks that the clock is still ticking,
// attempts one recovery dispatch, and alerts only when something is wrong.
import {
  runEvidence, boundedFetch, easternNow, dueItem, getManifest, verifyLive, recentRuns, runInFlight, dispatchWorkflow, getJson, putJson, ping, alert,
} from '../../shared/flh.mjs';

const CHECK_HOUR_ET = 7;
const CLOCK_STALE_MIN = 30;

export async function runWatchdog(env, deps = {}) {
  const fetchFn = boundedFetch(deps.fetch ?? fetch);
  const now = deps.now ?? new Date();
  const et = easternNow(now);
  const rec = { at: now.toISOString(), et_date: et.date, et_time: et.hhmm, action: '', problems: [] };
  try {
    if (et.hour !== CHECK_HOUR_ET) {
      rec.action = 'outside-window';
    } else {
      const second = et.minute >= 30;
      const dayKey = `day:${et.date}`;
      const day = (await getJson(env.FLH_STATE, dayKey)) ?? { date: et.date, attempts: 0 };

      const last = await getJson(env.FLH_STATE, 'clock:last_tick');
      const ageMin = last ? (now - Date.parse(last.at)) / 60000 : Infinity;
      if (ageMin > CLOCK_STALE_MIN) rec.problems.push(`clock Worker silent for ${Number.isFinite(ageMin) ? Math.round(ageMin) + ' min' : 'ever'}`);

      const item = dueItem(await getManifest(env, fetchFn), et.date);
      if (!item) {
        rec.problems.push(`no approved queue entry for ${et.date}`);
      } else {
        const runs = await recentRuns(env, fetchFn);
        day.workflow_runs = runEvidence(runs, et.date);
        const v = await verifyLive(item, fetchFn);
        day.watchdog_checked_at = rec.at;
        day.article_slug = item.live_file;
        if (v.ok) {
          day.last_verified_at = rec.at;
          day.live_at ??= rec.at;
          day.live_et ??= et.hhmm;
          rec.action = 'verified-live';
        } else {
          rec.problems.push(`NOT LIVE: ${v.failures.join('; ')}`);
          if (!runInFlight(runs, now)) {
            await dispatchWorkflow(env, fetchFn, 'cloudflare-watchdog');
            day.attempts += 1;
            day.last_dispatch_at = rec.at;
            day.last_dispatch_source = 'cloudflare-watchdog';
            day.recovery_attempts = (day.recovery_attempts || 0) + 1;
            rec.problems.push('recovery dispatch sent');
          }
        }
      }
      await putJson(env.FLH_STATE, dayKey, day);
      if (rec.problems.length) {
        rec.action = rec.action || 'problem';
        const level = second ? 'second' : 'first';
        const dedupe = `alert:${et.date}:${level}`;
        const onlyPublicationMissing = rec.problems.every(x => x.startsWith('NOT LIVE:') || x === 'recovery dispatch sent');
        if ((second || !onlyPublicationMissing) && !(await env.FLH_STATE.get(dedupe))) {
          const sent = await alert(env, `FLH: ${second ? 'STILL ' : ''}problem at ${et.hhmm} ET`, rec.problems.join('\n'), second ? 'urgent' : 'high', fetchFn);
          rec.alert_sent = sent;
          if (sent) await env.FLH_STATE.put(dedupe, '1', { expirationTtl: 3 * 24 * 3600 });
        }
      }
    }
    await ping(env.HC_WATCHDOG_URL, '', `${rec.action} ${rec.et_date} ${rec.et_time}`, fetchFn);
  } catch (err) {
    rec.action = 'error';
    rec.problems.push(String(err.message || err));
    await ping(env.HC_WATCHDOG_URL, '/fail', rec.problems.join('; '), fetchFn);
    await alert(env, 'FLH watchdog error', rec.problems.join('\n'), 'high', fetchFn);
  }
  try { await putJson(env.FLH_STATE, `watchdog:${rec.at}`, rec, { expirationTtl: 90 * 24 * 3600 }); } catch { /* best-effort */ }
  return rec;
}

// Authenticated read-only reliability report: GET /status with "Authorization: Bearer <STATUS_TOKEN>".
export async function statusReport(env) {
  const allKeys = [];
  let cursor;
  do {
    const page = await env.FLH_STATE.list({ prefix: 'day:', ...(cursor ? { cursor } : {}) });
    allKeys.push(...page.keys.map(k => k.name));
    cursor = page.list_complete === false ? page.cursor : undefined;
  } while (cursor);
  const keys = allKeys.sort().slice(-30);
  const days = [];
  for (const k of keys) days.push(await getJson(env.FLH_STATE, k));
  const live = days.filter((d) => d.live_at);
  const byHour = (d) => d.live_et && d.live_et < '07:00';
  return {
    acceptance_verified: false,
    acceptance_note: 'Live observation times alone do not prove trigger attribution; correlate GitHub run summaries and IDs.',
    days_recorded: days.length,
    live_days: live.length,
    live_before_0700_et: live.filter(byHour).length,
    days,
  };
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runWatchdog(env));
  },
  async fetch(request, env) {
    const auth = request.headers.get('Authorization') || '';
    if (!env.STATUS_TOKEN || auth !== `Bearer ${env.STATUS_TOKEN}`) return new Response('Not found', { status: 404 });
    return Response.json(await statusReport(env));
  },
};
