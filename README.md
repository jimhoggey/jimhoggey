<div align="center">

<img src="./profile.svg" alt="jimhoggey on GitHub — a terminal window showing a contribution heatmap, an about blurb, an ASCII-art portrait of the avatar, and a neofetch-style summary of repos, stars and languages" />

<a href="https://www.fynnjammer.com"><b>fynnjammer.com</b></a> &nbsp;·&nbsp;
<a href="https://jimhoggey.github.io/jimhoggey/"><b>this page, larger</b></a> &nbsp;·&nbsp;
<a href="https://github.com/jimhoggey/Runsheetpilot"><b>Runsheetpilot</b></a> &nbsp;·&nbsp;
<a href="https://github.com/jimhoggey/service-visuals"><b>service-visuals</b></a> &nbsp;·&nbsp;
<a href="https://github.com/jimhoggey/SelfdrivingcarForza"><b>SelfdrivingcarForza</b></a>

</div>

---

<details>
<summary><b>How this page is built</b></summary>

One self-contained SVG. GitHub strips JavaScript from rendered markdown but
happily renders SMIL animation inside an `<img>`, so all the motion lives in the
SVG itself — no GIFs, no external services, nothing to rate-limit.

It is deliberately a *single* file rather than one image per section. Four
separate images cannot sit flush in a README: GitHub puts each in its own block
with margins, and each would carry its own window chrome, so the page reads as
four floating cards instead of one terminal session.

| Section | Animation | Source of truth |
|---|---|---|
| `./contributions.sh` | 53×7 grid, cells sweep in diagonally | scraped from the public contributions calendar |
| `cat about.txt` | each line typed character by character | hand-written in `scripts/about.py` |
| `whoami` (portrait) | avatar as density-ramp art, **retyped every 15s** | `github.com/jimhoggey.png` |
| `whoami` (card) | neofetch summary, staggered fade-in | GitHub REST API |

### Generating it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt

python scripts/fetch_contributions.py   # -> data/contributions.json
python scripts/make_profile_svg.py      # -> profile.svg
python scripts/check_svgs.py            # validates it
```

`scripts/make_profile_svg.py` is the composer; each section lives in its own
module (`heatmap.py`, `about.py`, `ascii_art.py`, `infocard.py`) and returns a
positionable fragment plus its height, so the composer just stacks them and
draws one window frame around the lot.

It reads `GITHUB_TOKEN` if set, purely to avoid the unauthenticated API rate
limit. Only public endpoints are used, so nothing from a private repo can reach
the card. To use a photo instead of the avatar:

```bash
python scripts/make_profile_svg.py some-photo.png
```

### Three details worth knowing

**Whitespace.** SVG collapses runs of whitespace, so ASCII art built as `<text>`
rows with space padding falls apart — the surviving glyphs bunch up and the grid
shears. `ascii_art.py` drops spaces entirely and gives every remaining glyph an
explicit `x`, which also pins the art to an exact grid no matter which monospace
font the renderer picks.

**Graceful degradation.** The usual way to stagger an entrance is `opacity="0"`
plus an animation that freezes at `1`. Anything that renders SVG *without*
running SMIL then shows a permanently blank image. Here every element already
holds its final value, and the animation runs from `t=0`, sitting on the hidden
value for its stagger before easing to the visible one — and deliberately does
not freeze, so it falls back to the element's own value. No SMIL means no
animation and a fully visible page. `check_svgs.py` enforces this by stripping
every animation and asserting nothing is left hidden.

**The looping portrait.** The ASCII rows animate on a 15-second cycle with
`repeatCount="indefinite"`: wipe in, hold, clear, repeat. Because the loop never
freezes either, the no-SMIL fallback is still the finished portrait.

### Staying fresh

[`update-profile-art.yml`](.github/workflows/update-profile-art.yml) re-renders
`profile.svg` daily at 06:17 UTC and commits it if anything changed. GitHub
proxies README images through its own cache, so an update can take a little
while to appear.

</details>
