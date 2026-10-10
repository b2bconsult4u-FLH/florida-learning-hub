// FLH publication clock: the primary trigger for Today in Florida History.
// Cron fires every 10 minutes (UTC) between 07:00 and 13:59; DST is handled here by reading Eastern time.
// Each tick reconciles reality: if today's approved entry is not live, dispatch the GitHub workflow.
import {
  runEvidence, boundedFetch, easternNow, dueItem, getManifest, verifyLive, recentRuns, runInFlight, dispatchWorkflow, getJson, putJson, ping,
} from '../../shared/flh.mjs';

const START_HOUR_ET = 4; // begin recovery attempts at 4:00 a.m. Eastern

export async function runClock(env, deps = {}) {
  const fetchFn = boundedFetch(deps.fetch ?? fetch);
  const now = deps.now ?? new Date();
  const et = easternNow(now);
  const rec = { tick: now.toISOString(), et_date: et.date, et_time: et.hhmm, action: '', detail: '' };
  try {
    await putJson(env.FLH_STATE, 'clock:last_tick', { at: rec.tick });
    const dayKey = `day:${et.date}`;
    const day = (await getJson(env.FLH_STATE, dayKey)) ?? { date: et.date, attempts: 0 };
    if (et.hour < START_HOUR_ET) {
      rec.action = 'before-window';
    } else {
      const item = dueItem(await getManifest(env, fetchFn), et.date);
      if (!item) {
        rec.action = 'no-approved-entry';
        day.no_entry = true;
        throw new Error(`No approved entry for ${et.date}`);
      } else {
        day.title = item.title;
        day.article_slug = item.live_file;
        const runs = await recentRuns(env, fetchFn);
        day.workflow_runs = runEvidence(runs, et.date);
        const v = await verifyLive(item, fetchFn);
        if (v.ok) {
          rec.action = 'verified-live';
          day.live_at ??= rec.tick;
          day.live_et ??= et.hhmm;
          day.last_verified_at = rec.tick;
        } else {
          day.first_missing_at ??= rec.tick;
          rec.detail = v.failures.join('; ');
          if (runInFlight(runs, now)) {
            rec.action = 'waiting-for-run';
          } else {
            await dispatchWorkflow(env, fetchFn);
            rec.action = 'dispatched';
            day.attempts += 1;
            day.first_dispatch_at ??= rec.tick;
            day.last_dispatch_at = rec.tick;
            day.last_dispatch_source = 'cloudflare-clock';
          }
        }
      }
    }
    await putJson(env.FLH_STATE, dayKey, day);
    await ping(env.HC_CLOCK_URL, '', `${rec.action} ${rec.et_date} ${rec.et_time}`, fetchFn);
  } catch (err) {
    rec.action = 'error';
    rec.detail = String(err.message || err);
    await ping(env.HC_CLOCK_URL, '/fail', rec.detail, fetchFn);
  }
  const keep = { expirationTtl: 90 * 24 * 3600 };
  try { await putJson(env.FLH_STATE, `tick:${rec.tick}`, rec, keep); } catch { /* record is best-effort */ }
  return rec;
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runClock(env));
  },
};
