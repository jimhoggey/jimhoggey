# OneReel

A birthday-present parody feed: it looks and swipes like a reels app, but serves
exactly one clip per day. Swipe for the next one and you get a countdown instead.

Clips are YouTube Shorts played through the official embedded player.

## How the one-a-day limit works

`netlify/functions/today.mjs` works out today's date in `REEL_TZ` and returns a
single video id from `data/reels.mjs`. The list is bundled into the function and
never sent to the browser, so a private window or cleared cache gets the same
reel back. No database, no login.

## Deploy on Netlify

1. Add new site, import this repository.
2. Base directory: `one-reel`. Leave the build command empty. Publish directory: `public`.
3. Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `REEL_NAME` | `Sally` | Shows "Made for NAME" on the opening screen |
| `REEL_TZ` | `Australia/Sydney` | Timezone that decides when midnight is |
| `REEL_START` | `2026-11-10` | Date that plays the first reel in the list |

## Preview locally

```bash
node dev.mjs   # http://localhost:8888
```

## Changing the clips

Edit `data/reels.mjs`. Each line is the id from a `youtube.com/shorts/<id>` link.
Add new ones at the end so earlier days keep their reel. If a clip is deleted or
has embedding switched off, the player quietly swaps in a stand-in for that day.
