// Serves exactly one reel per calendar day. The list never reaches the
// browser: the client only ever learns today's video id, so clearing the
// cache or opening a private window gets the same reel back.
import reels from '../../data/reels.mjs';

const DAY_MS = 86_400_000;

function localParts(now, tz) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz, hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).formatToParts(now);
  const p = Object.fromEntries(parts.map((x) => [x.type, Number(x.value)]));
  return p;
}

// Whole days since 1970-01-01 for the calendar date in the given timezone.
export function dayNumber(now, tz) {
  const p = localParts(now, tz);
  return Math.floor(Date.UTC(p.year, p.month - 1, p.day) / DAY_MS);
}

export function secondsToMidnight(now, tz) {
  const p = localParts(now, tz);
  return Math.max(1, 86_400 - (p.hour * 3600 + p.minute * 60 + p.second));
}

export function pick({ now = new Date(), tz, start, alt = 0, list = reels }) {
  const today = dayNumber(now, tz);
  const startDay = Math.floor(Date.parse(`${start}T00:00:00Z`) / DAY_MS);
  const n = list.length;
  const offset = today - startDay;
  // alt = 1 or 2 is a same-day stand-in for a reel that refuses to play.
  const step = Math.max(1, Math.floor(n / 3));
  const index = (((offset + alt * step) % n) + n) % n;
  return { id: list[index], day: offset + 1, secondsToNext: secondsToMidnight(now, tz) };
}

export default async (req) => {
  const url = new URL(req.url);
  const alt = Math.min(2, Math.max(0, Number.parseInt(url.searchParams.get('alt') ?? '0', 10) || 0));
  const tz = process.env.REEL_TZ || 'Australia/Sydney';
  const start = process.env.REEL_START || '2026-11-10';
  const body = { ...pick({ tz, start, alt }), name: process.env.REEL_NAME || '' };
  return new Response(JSON.stringify(body), {
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
};

export const config = { path: '/api/today' };
