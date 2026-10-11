# Math Blast Arcade — audio engine spec (`js/audio.js`)

Deliver ONE file: `/home/claude/mathblast-arcade/js/audio.js`, plain script (no modules, no
build step, no external files or libraries), exposing `window.MB.Audio`. The game must run by
double-clicking `index.html` (file://) as well as from a static web server, on desktop Chrome,
Firefox, Safari and on iOS/Android browsers. Everything is synthesised with the Web Audio API
at run time: original music and sound effects — no samples, no copyrighted melodies.

Audience: children aged 8–11. Tone: adventurous, bright, modern chiptune / synthwave hybrid
(think 16-bit console music with fuller bass and delay). Never harsh, never shrill; SFX must be
satisfying and short. Music must loop seamlessly and stay pleasant after 10 minutes.

## API (exact)

```js
MB.Audio.init()                    // safe to call many times; creates nothing audible. Does NOT throw if Web Audio is unavailable
MB.Audio.unlock()                  // call from a user gesture (pointerdown/keydown): creates/resumes the AudioContext
MB.Audio.isUnlocked()              // boolean
MB.Audio.setVolume(kind, v)        // kind: 'master' | 'music' | 'sfx' | 'voice'; v in 0..1 (smoothly ramped)
MB.Audio.getVolume(kind)
MB.Audio.playMusic(name, opts)     // name: 'title' | 'dock' | 'bridge' | 'reactor' | 'zerog' | 'boss' | 'victory' | null
                                   // opts.fade (seconds, default 0.6). Cross-fades; calling with the current track is a no-op.
                                   // If called before unlock(), remember it and start when unlocked.
MB.Audio.stopMusic(fade)
MB.Audio.setIntensity(level)       // 0 | 1 | 2 — boss track adds layers / drive as the fight escalates (other tracks may ignore)
MB.Audio.duck(amount, seconds)     // amount 0..1 = how much to lower music (0 = none). Used during dialogue / maths consoles
MB.Audio.sfx(name, opts)           // opts: { pitch: semitone offset, vol: 0..1, pan: -1..1 } all optional. Unknown names are ignored silently
MB.Audio.playVoice(id, onEnd)      // plays MB_ASSETS.audio['voice/' + id] (a base64 data: URI of an MP3) through the voice bus.
                                   // Decode with atob -> ArrayBuffer -> decodeAudioData (NOT fetch, NOT <audio>), cache decoded buffers.
                                   // Returns true if the clip exists and was started (or queued to decode), false otherwise.
                                   // onEnd(completed:boolean) is called once when it finishes or is stopped. Only one voice at a time.
MB.Audio.stopVoice()
MB.Audio.voiceDuration(id)         // seconds if known/decoded, else 0
MB.Audio.pauseAll() / resumeAll()  // suspend/resume the context (game pause, tab hidden). Also auto-handle document visibilitychange
MB.Audio.debugInfo()               // { state, track, activeVoices } for tests
```

## Music — 7 original loops

| name | mood | notes |
|---|---|---|
| title | heroic, inviting, memorable 8-bar hook | mid tempo ~112 bpm, major key |
| dock | upbeat, curious, "first day on the job" | ~120 bpm; this is the tutorial area |
| bridge | airy, open, hopeful, starlit (exterior of the station) | ~104 bpm, arps + pads |
| reactor | driving, mechanical, warm, a bit tense | ~126 bpm, syncopated bass, metallic percussion |
| zerog | floaty, dreamy, weightless | ~92 bpm, long pads, sparse bell melody, gentle |
| boss | urgent and exciting but still fun, minor key | ~140 bpm; intensity 0 = base, 1 adds counter-melody/extra percussion, 2 adds octave lead + faster hats |
| victory | triumphant fanfare then relaxed loop | ~120 bpm, major; first 4 bars are the fanfare, then loop a calmer section |

Each track: at least lead, harmony/arp, bass and drums; 16–32 bars before looping; real melodic
writing with phrases, not random notes. A shared leitmotif across title/dock/victory is a plus
(and a minor-key variant for the Phantom in `boss`). Use a look-ahead scheduler (setInterval/
setTimeout ~25 ms, schedule ~120 ms ahead by `ctx.currentTime`) so timing survives frame drops;
keep node counts modest for phones (free nodes after notes end). Master chain: music bus, sfx
bus, voice bus → master gain → gentle compressor/limiter → destination. A light feedback delay
on leads is welcome. Avoid clicks (short attack/release envelopes on every note).

## Sound effects (all names must exist)

Movement: `jump`, `land`, `step` (very quiet), `spring`, `hurt`, `stomp`, `enemyPop`, `gravityFlip`
Collecting: `chip` (use opts.pitch to climb for streaks), `whole` (jingle: four quarters made a whole),
`secret`, `heart`, `checkpoint`, `qkey`
Doors/UI: `doorOpen`, `doorLocked`, `uiMove`, `uiSelect`, `uiBack`, `pause`, `unpause`,
`textBlip` (tiny dialogue tick; opts.pitch varies per speaker), `hintOpen`, `irisOut`, `irisIn`
Maths machines: `cellPlace`, `cellRemove`, `bridgeExtend` (rising energy hum ~0.6 s), `bridgeSolid`
(satisfying lock-in), `bridgeFail` (soft fizzle, never punishing), `blockBump` (add), `blockBumpMinus`
(take away, lower pitched), `lever`, `reactorFill` (liquid glug), `reactorOnline` (power-up swell ~1.2 s),
`reactorVent` (steam hiss), `correct` (bright success jingle ~0.8 s), `wrong` (gentle "bloop-down",
friendly), `podStep` (opts.pitch climbs with each correct pod), `podWrong`, `gateOpen`, `gateWrong`
Hazards: `zap`, `steam`, `mineBeep`
Boss: `bossAppear`, `bossLaugh` (synthetic glitchy chuckle), `bossTelegraph`, `bossShoot`,
`bossBeam`, `cannonCharge`, `cannonFire`, `cannonFizzle`, `shieldBreak`, `bossHit`, `bossStun`,
`bossDefeat` (2–3 s cascading glitch-explosion), `quarterGet` (the big prize sting ~1.5 s)
Misc: `victory` (short 2 s fanfare sting usable anywhere), `transition`

## Testing you must do (report results honestly)

You cannot hear the output. Test objectively with headless Chromium via Playwright
(`require('/opt/npm-tools/node_modules/playwright')`, launch with
`executablePath: '/opt/pw-browsers/chromium'` if needed, args `['--autoplay-policy=no-user-gesture-required']`):
1. Page with `audio.js` loads with zero console errors; calling every API function and every SFX
   name throws nothing, before and after `unlock()`.
2. Render each music track for ≥ 20 s and each SFX through an `OfflineAudioContext` code path
   (design the engine so the scheduler/synth can target any BaseAudioContext for this) and report
   per-track peak and RMS: no clipping (peak < 1.0 before the limiter), no silence, SFX peak
   levels consistent with one another, music RMS comparable across tracks.
3. Loop seam: confirm note scheduling at the loop point is continuous (no gap/overlap).
4. Run each track in the realtime context for ~10 s while sampling `debugInfo()` to confirm the
   scheduler keeps running and node counts do not grow without bound.
5. `playVoice` works with a small test MP3 data URI and calls onEnd; returns false for unknown ids.
Do not claim anything "sounds good" — say what was measured and what was not verifiable.
