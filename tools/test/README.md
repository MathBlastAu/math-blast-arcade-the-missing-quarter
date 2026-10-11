# Automated tests

These scripts drive the real game in headless Chromium through [Playwright](https://playwright.dev)
(`npm i playwright` once, then run from the project root).

| command | what it does |
|---|---|
| `node tools/test/run.js tools/test/full.js` | Complete start-to-finish playthrough with real physics and inputs: all 5 areas, every maths machine (including deliberate wrong answers), the three-phase boss and the victory screen. `START=3 node ...` begins at a later area. |
| `node tools/test/run.js tools/test/s_ui.js` | Title, how-to-play, options, opening cinematic, pause/resume, save and reload. |
| `node tools/test/run.js tools/test/s_mouse.js` | Mouse/pointer operation of menus and the fraction console. |
| `node tools/test/run.js tools/test/s_touch.js` | Phone-sized viewport with real multi-touch events on the on-screen buttons. |
| `node tools/test/run.js tools/test/s_hazard.js` | Damage, stomping, pits, checkpoints, losing all hearts, relaxed mode. |
| `node tools/test/run.js tools/test/s_hint.js` | Optional hint button. |
| `node tools/test/run.js tools/test/s_physics.js` | Measures jump height and distance. |
| `node tools/test/run.js tools/test/s_overview.js` | Zoomed-out maps of every area (`tools/test/out/map_*.png`). |
| `node tools/test/realtime.js` | Real-time smoke test (no frame stepping), including the audio engine state. |
| `node tools/audio_test/run_tests.js` | Audio engine checks (levels, loop seams, API safety). |

`run.js` stops Phaser's real-time loop and advances the game one 60 Hz frame at a time, so runs are
deterministic and fast. `bot.js` is a small player bot that steers Jake by setting the same flags the
on-screen touch buttons set; consoles, levers and dialogue use real key presses.
Screenshots are written to `tools/test/out/`.
