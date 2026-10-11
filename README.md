# Math Blast Arcade — The Missing Quarter

Space Arc, Level 1 as a 2D pixel-art platformer for ages 8–11 (Year 4 fractions).
Jake Nova, Junior Fuel Inspector, chases the Fraction Phantom through five areas of Kepler Station.
The fractions are the game mechanics: nothing is a multiple-choice question and no maths is timed.

## Play it

- **Simplest:** unzip and double-click `index.html`. No server, no install, no internet needed.
- **On a website:** upload the whole folder to any static host (GitHub Pages, Netlify, your own site)
  and link to `index.html`. For GitHub Pages: push the folder to a repository, then
  Settings → Pages → deploy from the branch root.
- Works with keyboard, mouse and touch. On phones, hold the device sideways.

| | Keyboard | Touch |
|---|---|---|
| Move | ← → or A / D | left / right buttons |
| Jump (hold for higher) | Space, ↑ or W | jump button |
| Use console / lever, continue story | E or Enter | hand button, or tap the screen in dialogue |
| Hint (near a maths machine) | H | light-bulb button |
| Pause | Esc or P | pause button |

Progress saves automatically in the browser (checkpoints, solved machines, collected items, options).
Options include music and sound volume, **Relaxed mode** (no heart loss), screen shake on/off and an
optional read-aloud that uses the device's own voice.

## What is in the level

| Area | Play | Maths |
|---|---|---|
| 1 Docking Bay | movement, jumping, robots, springs | collect quarters (4 quarters = 1 whole, shown as a pie and a mixed number); find 4 quarter cells to make 1 whole power cell |
| 2 Fraction Bridge | three energy bridges, moving platform | add cells so a bridge is exactly 1 whole: same denominator, then equivalent fractions (2/8 = 1/4), then several cells (1/8 + 1/2 + 1/4 + 1/8) |
| 3 Reactor Core | lift, steam, electric arcs | bump + and − blocks to fill a reactor to an exact level: 1/4 + 2/4 = 3/4, 7/8 − 2/8 = 5/8, 3/8 + 3/8 = 6/8 = 3/4 |
| 4 Zero-Gravity Sector | low gravity, gravity-flip pads | only the larger fraction's gate opens (3/4 v 1/4, 1/2 v 3/8, 3/4 v 5/8); hop number-line pods smallest to largest |
| 5 Showdown | three-phase boss, dodge then think | charge the cannon to match the shield exactly (add, equivalent, take away), then stomp the Phantom |

Every machine shows a bar model next to the numerals, reacts physically to wrong answers (a bridge
that is too short, a reactor that vents) and explains the comparison in words. Hints are optional.

## Folder map

```
index.html            the game page
lib/phaser.min.js     Phaser 3.90 game engine (MIT licence, see lib/PHASER-LICENSE.md)
js/                   game code (plain scripts, no build step)
  areas.js            the five areas, written as readable level code
  puzzles.js boss.js  the maths machines and the boss
  story.js            every line of dialogue, with ids
  audio.js            music and sound effects, synthesised live with the Web Audio API
  assets-embedded.js  GENERATED: every image and font as base64 (lets index.html run from disk)
assets/               the real asset files: sprite sheets, tiles, backgrounds, UI, fonts, manifests
art/                  Python scripts that draw every asset (shared palette in art/pix.py)
tools/build.py        rebuilds js/assets-embedded.js from assets/
tools/test/           automated playthrough and UI tests (see tools/test/README.md)
docs/                 the art and audio production specs used to build the game
```

### Changing things

- **Dialogue:** edit `js/story.js`.
- **Levels and puzzle numbers:** edit `js/areas.js` (and `PHASES` in `js/boss.js`).
- **Art:** edit a script in `art/`, run it (`python3 art/jake.py`, needs Pillow), then run
  `python3 tools/build.py`. Jake's colours are a palette block at the top of `art/jake.py`.
- **Voice recordings:** the dialogue box already plays a clip per line when one exists.
  Save recordings as `assets/voice/<line id>.mp3` (ids are in `js/story.js`, e.g. `n01.mp3`), list them in
  `assets/manifest/voice.json` as `{"voice": {"n01": {"file": "voice/n01.mp3"}}}` and run
  `python3 tools/build.py`. A voice-volume option then appears automatically.

## Honest notes

- **No voiced narration ships in this build.** All story lines are on-screen text; voice slots are wired
  and tested with a dummy clip only. The optional read-aloud uses the device's speech voice.
- **Music and sound effects are synthesised by code**, not audio files. They were checked by measurement
  (levels, loop seams, no errors), not by ear.
- **Art is original pixel art drawn by scripts** from the written character descriptions. It was not matched
  to the existing Math Blast illustrations, which could not be downloaded during production.
- **Tested in headless Chromium only** (keyboard, mouse and emulated multi-touch). Not yet run on real
  phones, tablets, Safari or Firefox.
- Adding and subtracting fractions with the same denominator is in the brief and in this level; in the
  Australian Curriculum v9 that content descriptor sits in Year 5, so some Year 4 classes may meet it here first.

## Credits and licences

- Engine: Phaser 3 (MIT).
- Fonts: Fredoka and Press Start 2P (SIL Open Font Licence, texts in `assets/fonts/src/`).
- Game code, pixel art, music and sound design: produced for Math Blast for this demonstration.
