#!/usr/bin/env node
/* Objective tests for js/audio.js (see js/AUDIO_SPEC.md, "Testing you must do").
 *
 *   node tools/audio_test/run_tests.js              all tests, writes results.json
 *   node tools/audio_test/run_tests.js --calibrate  print the SFX_CAL table, the limiter trim and per-track levels
 *   node tools/audio_test/run_tests.js --calibrate --write   ...and write SFX_CAL and COMP_TRIM into js/audio.js
 *   node tools/audio_test/run_tests.js --wav        also write out/<name>.wav of every render, to listen to
 *   node tools/audio_test/run_tests.js --quick      skip the realtime section (about 2 minutes of waiting)
 *
 * The page is loaded from disk (file://) in headless Chromium. These tests
 * measure levels, spectra, timing and resource use; they cannot judge whether
 * the music is pleasant.
 */
'use strict';
const path = require('path');
const fs = require('fs');
const cp = require('child_process');
const { chromium } = require('/opt/npm-tools/node_modules/playwright');

const HERE = __dirname;
const PAGE = 'file://' + path.join(HERE, 'test.html');
const ARGV = process.argv.slice(2);
const CALIBRATE = ARGV.includes('--calibrate');
const WAV = ARGV.includes('--wav');
const QUICK = ARGV.includes('--quick');
const AUTOPLAY = ['--autoplay-policy=no-user-gesture-required'];

// the names the spec requires (kept here independently of the engine's own list)
const SPEC_TRACKS = ['title', 'dock', 'bridge', 'reactor', 'zerog', 'boss', 'victory'];
const SPEC_SFX = [
  'jump', 'land', 'step', 'spring', 'hurt', 'stomp', 'enemyPop', 'gravityFlip',
  'chip', 'whole', 'secret', 'heart', 'checkpoint', 'qkey',
  'doorOpen', 'doorLocked', 'uiMove', 'uiSelect', 'uiBack', 'pause', 'unpause', 'textBlip', 'hintOpen', 'irisOut', 'irisIn',
  'cellPlace', 'cellRemove', 'bridgeExtend', 'bridgeSolid', 'bridgeFail', 'blockBump', 'blockBumpMinus', 'lever',
  'reactorFill', 'reactorOnline', 'reactorVent', 'correct', 'wrong', 'podStep', 'podWrong', 'gateOpen', 'gateWrong',
  'zap', 'steam', 'mineBeep',
  'bossAppear', 'bossLaugh', 'bossTelegraph', 'bossShoot', 'bossBeam', 'cannonCharge', 'cannonFire', 'cannonFizzle',
  'shieldBreak', 'bossHit', 'bossStun', 'bossDefeat', 'quarterGet',
  'victory', 'transition'
];
const SPEC_API = ['init', 'unlock', 'isUnlocked', 'setVolume', 'getVolume', 'playMusic', 'stopMusic', 'setIntensity', 'duck',
  'sfx', 'playVoice', 'stopVoice', 'voiceDuration', 'pauseAll', 'resumeAll', 'debugInfo'];
// durations the spec gives for particular effects: [min, max] seconds of audible sound
const SPEC_LEN = {
  bridgeExtend: [0.5, 0.9], reactorOnline: [1.0, 1.6], correct: [0.6, 1.1], bossDefeat: [2.0, 3.0],
  quarterGet: [1.2, 1.9], victory: [1.7, 2.4]
};
const GENTLE = ['wrong', 'bridgeFail', 'gateWrong', 'podWrong'];

const results = { started: new Date().toISOString(), checks: [], music: {}, sfx: {}, seam: {}, realtime: {}, notes: [] };
let failed = 0;
function check(name, ok, detail) {
  results.checks.push({ name, ok: !!ok, detail: detail === undefined ? '' : detail });
  if (!ok) failed++;
  console.log((ok ? '  ok    ' : '  FAIL  ') + name + (detail !== undefined && detail !== '' ? '   [' + detail + ']' : ''));
}
const f3 = (x) => (typeof x === 'number' ? x.toFixed(3) : String(x));
const f1 = (x) => (typeof x === 'number' ? x.toFixed(1) : String(x));
const pct = (x) => (100 * x).toFixed(2) + '%';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function table(rows, cols) {
  const w = cols.map((c) => Math.max(c.length, ...rows.map((r) => String(r[c]).length)));
  console.log('  ' + cols.map((c, i) => c.padEnd(w[i])).join('  '));
  for (const r of rows) console.log('  ' + cols.map((c, i) => String(r[c]).padEnd(w[i])).join('  '));
}

async function launch(args) {
  try { return await chromium.launch({ args }); } catch (e) {
    return await chromium.launch({ args, executablePath: '/opt/pw-browsers/chromium' });
  }
}
// open the test page; console errors and uncaught errors are collected on page.__log
async function open(browser, query) {
  const page = await browser.newPage();
  page.__log = { errors: [], warnings: [] };
  page.on('console', (m) => {
    if (m.type() === 'error') page.__log.errors.push(m.text());
    if (m.type() === 'warning') page.__log.warnings.push(m.text());
  });
  page.on('pageerror', (e) => page.__log.errors.push('pageerror: ' + e.message));
  await page.goto(PAGE + (query || ''));
  await page.waitForFunction(() => !!(window.MB && window.MB.Audio && window.MBT));
  return page;
}
async function pageErrors(page) {
  const inPage = await page.evaluate(() => window.__errors.concat(window.MB.Audio.debugInfo().errors || []));
  return page.__log.errors.concat(inPage);
}

// ---------------------------------------------------------------------------
// code that runs inside the page
// ---------------------------------------------------------------------------
// call every API function with sensible and with silly arguments; returns what threw
function apiSweep(arg) {
  const A = window.MB.Audio, thrown = [];
  const weird = [undefined, null, 0, 1, -1, 2.5, NaN, Infinity, '', 'nope', {}, [], true, function () {}];
  const call = (label, f) => { try { return f(); } catch (e) { thrown.push(label + ': ' + e.message); } };
  const s = (v) => { try { return typeof v === 'function' ? 'fn' : JSON.stringify(v) || String(v); } catch (e) { return '?'; } };
  let calls = 0;
  const c = (label, f) => { calls++; return call(label, f); };
  c('init', () => { A.init(); A.init(); A.init(); });
  c('isUnlocked', () => A.isUnlocked());
  c('debugInfo', () => A.debugInfo());
  for (const k of ['master', 'music', 'sfx', 'voice', 'bogus', undefined, null, 7]) {
    for (const v of weird) c('setVolume ' + s(k) + ' ' + s(v), () => A.setVolume(k, v));
    c('getVolume ' + s(k), () => A.getVolume(k));
  }
  for (const k of ['master', 'music', 'sfx', 'voice']) c('restore ' + k, () => A.setVolume(k, arg.vols[k]));
  for (const n of arg.tracks.concat(weird)) {
    c('playMusic ' + s(n), () => A.playMusic(n));
    c('playMusic fade0 ' + s(n), () => A.playMusic(n, { fade: 0 }));
    c('playMusic badopts ' + s(n), () => A.playMusic(n, { fade: 'x' }));
    c('playMusic nullopts ' + s(n), () => A.playMusic(n, null));
  }
  for (const v of weird) c('stopMusic ' + s(v), () => A.stopMusic(v));
  for (const v of weird.concat([2, 3])) c('setIntensity ' + s(v), () => A.setIntensity(v));
  for (const v of weird) for (const w of [undefined, 0, 0.2, 'x', -1]) c('duck ' + s(v), () => A.duck(v, w));
  c('duck 0', () => A.duck(0, 0));
  c('setIntensity 0', () => A.setIntensity(0));
  for (const n of arg.sfx) {
    c('sfx ' + n, () => A.sfx(n));
    c('sfx opts ' + n, () => A.sfx(n, { pitch: 3, vol: 0.5, pan: -0.5 }));
  }
  for (const n of weird.concat(['__proto__', 'constructor', 'toString', 'hasOwnProperty'])) {
    c('sfx weird ' + s(n), () => A.sfx(n));
    c('sfx weird opts ' + s(n), () => A.sfx(n, { pitch: NaN, vol: 'x', pan: 9 }));
  }
  for (const o of weird) c('sfx jump opts ' + s(o), () => A.sfx('jump', o));
  c('sfx extreme', () => { A.sfx('chip', { pitch: 99 }); A.sfx('chip', { pitch: -99 }); A.sfx('chip', { vol: 0 }); A.sfx('chip', { vol: 5, pan: -3 }); });
  for (const v of weird.concat(['__proto__', 'test1'])) {
    for (const cb of [undefined, null, 5, function () {}]) c('playVoice ' + s(v), () => A.playVoice(v, cb));
    c('voiceDuration ' + s(v), () => A.voiceDuration(v));
  }
  c('stopVoice', () => { A.stopVoice(); A.stopVoice(); });
  c('pause/resume', () => { A.pauseAll(); A.pauseAll(); A.resumeAll(); A.resumeAll(); A.pauseAll(); A.resumeAll(); });
  c('stopMusic', () => A.stopMusic(0.05));
  const d = c('debugInfo', () => A.debugInfo());
  return { thrown, calls, state: d && d.state, track: d && d.track, errors: d ? d.errors : ['no debugInfo'], unlocked: A.isUnlocked() };
}

// loop seam measured on the scheduled events (three passes of the loop)
function seamEvents(arg) {
  const r = window.MB.Audio._test.events(arg.name, 3, arg.intensity || 0);
  const spb = r.spb, L = r.loopBeats, I = r.introBeats, eps = 1e-9;
  const passes = [[], [], []], intro = [];
  for (const e of r.events) (e.loop < 0 ? intro : passes[e.loop]).push(e);
  let maxDev = 0, mismatch = 0, outOfRange = 0, dup = 0;
  for (let k = 0; k < 2; k++) {
    if (passes[k].length !== passes[k + 1].length) mismatch += 1000;
    for (let i = 0; i < Math.min(passes[k].length, passes[k + 1].length); i++) {
      const a = passes[k][i], b = passes[k + 1][i];
      if (a.p !== b.p || a.k !== b.k || String(a.n) !== String(b.n) || Math.abs(a.d - b.d) > eps) mismatch++;
      maxDev = Math.max(maxDev, Math.abs(b.time - a.time - L * spb));
    }
  }
  for (let k = 0; k < 3; k++) for (const e of passes[k]) if (e.beat < I + k * L - eps || e.beat >= I + (k + 1) * L - eps) outOfRange++;
  for (const e of intro) if (e.beat < -eps || e.beat >= I - eps) outOfRange++;
  const seen = {};
  for (const e of r.events) { const key = [e.time.toFixed(6), e.p, e.k, String(e.n)].join('|'); if (seen[key]) dup++; seen[key] = 1; }
  // one-voice parts must never overlap themselves, including across the seam
  let maxOverlap = -Infinity, seamGap = {};
  for (const part of ['lead', 'lead2', 'counter', 'bass']) {
    const ev = r.events.filter((e) => e.p === part).sort((a, b) => a.time - b.time);
    for (let i = 1; i < ev.length; i++) {
      maxOverlap = Math.max(maxOverlap, ev[i - 1].time + ev[i - 1].d - ev[i].time);
      if (ev[i - 1].loop === 0 && ev[i].loop === 1) seamGap[part] = (ev[i].time - (ev[i - 1].time + ev[i - 1].d)) / spb;
    }
  }
  // pads: where does the last chord of a pass end and the next begin, relative to the loop point?
  const pads = r.events.filter((e) => e.p === 'pad');
  const lastPad = pads.filter((e) => e.loop === 0).pop(), firstPad = pads.filter((e) => e.loop === 1)[0];
  const seamT = (I + L) * spb;
  const first1 = passes[1][0], last0 = passes[0][passes[0].length - 1];
  // every 16th-note slot around the seam that has an onset in pass 2 must have one in pass 1 as well
  const grid = (k) => { const g = {}; for (const e of passes[k]) g[Math.round((e.beat - I - k * L) * 1000)] = 1; return Object.keys(g).length; };
  return {
    perPass: passes.map((p) => p.length), intro: intro.length, loopSeconds: L * spb,
    maxDeviation: maxDev, mismatch, outOfRange, duplicates: dup,
    maxMonoOverlap: maxOverlap, seamGapBeats: seamGap,
    firstOnsetAfterSeam: first1 ? first1.time - seamT : null, lastOnsetBeforeSeamBeats: last0 ? (seamT - last0.time) / spb : null,
    padEndsBeforeSeamBeats: lastPad ? (seamT - (lastPad.time + lastPad.d)) / spb : null,
    padStartsAfterSeam: firstPad ? firstPad.time - seamT : null,
    gridSlots: [grid(0), grid(1), grid(2)],
    introEndsBeforeLoopBeats: intro.length ? (I * spb - intro[intro.length - 1].time) / spb : null
  };
}

// one sample of the realtime engine: debugInfo + the level on the master bus
function rtSample() {
  const A = window.MB.Audio, d = A.debugInfo(), a = A._test.tap();
  let rms = 0;
  if (a) {
    const buf = new Float32Array(a.fftSize);
    a.getFloatTimeDomainData(buf);
    for (let i = 0; i < buf.length; i++) rms += buf[i] * buf[i];
    rms = Math.sqrt(rms / buf.length);
  }
  return { state: d.state, track: d.track, playing: d.playing, active: d.activeVoices, nodes: d.nodes, sfxLive: d.sfxLive,
    players: d.players, scheduled: d.scheduled, missed: d.missed, late: d.late, loop: d.loop, time: d.time, rms, errors: d.errors.length, dupEnded: d.dupEnded, wall: performance.now() };
}
// summarise the events recorded from the realtime scheduler
function rtEvents(name) {
  const A = window.MB.Audio, rec = (A._test.record(false) || []).filter((e) => e.track === name), info = A._test.trackInfo(name);
  if (!rec.length) return { count: 0 };
  const spb = 60 / info.bpm, t0 = rec[0].time - rec[0].beat * spb;
  let dev = 0, minLead = Infinity, maxLead = 0, backwards = 0;
  for (let i = 0; i < rec.length; i++) {
    dev = Math.max(dev, Math.abs(rec[i].time - (t0 + rec[i].beat * spb)));
    minLead = Math.min(minLead, rec[i].time - rec[i].at); maxLead = Math.max(maxLead, rec[i].time - rec[i].at);
    if (i && rec[i].time < rec[i - 1].time - 1e-9) backwards++;
  }
  // what the compiled track holds up to the last beat that was scheduled (intensity 0)
  const lastBeat = rec[rec.length - 1].beat;
  const all = A._test.events(name, Math.ceil(lastBeat / info.loopBeats) + 1, 0).events;
  let expected = 0;
  for (const e of all) if (e.beat <= lastBeat + 1e-9) expected++;
  return { count: rec.length, expected, maxGridDeviation: dev, minLead, maxLead, backwards, lastBeat, span: rec[rec.length - 1].time - rec[0].time };
}

// ---------------------------------------------------------------------------
async function testApi(browser) {
  console.log('\n[1] API safety');
  const sweepArg = { tracks: SPEC_TRACKS, sfx: SPEC_SFX, vols: { master: 0.8, music: 0.6, sfx: 0.8, voice: 1 } };

  // normal browser, autoplay allowed
  let page = await open(browser);
  const names = await page.evaluate(() => ({
    api: Object.keys(window.MB.Audio), tracks: window.MB.Audio._test.tracks(), sfx: window.MB.Audio._test.sfxNames(),
    warnings: window.MB.Audio._test.warnings(), state: window.MB.Audio.debugInfo().state
  }));
  check('window.MB.Audio has every API function', SPEC_API.every((k) => names.api.includes(k)), SPEC_API.filter((k) => !names.api.includes(k)).join(' '));
  check('all 7 tracks exist', SPEC_TRACKS.every((k) => names.tracks.includes(k)), names.tracks.join(' '));
  const missing = SPEC_SFX.filter((k) => !names.sfx.includes(k));
  check('all ' + SPEC_SFX.length + ' named sound effects exist', missing.length === 0, missing.length ? 'missing: ' + missing.join(' ') : names.sfx.length + ' defined');
  check('state before unlock is "locked" (no AudioContext created yet)', names.state === 'locked', names.state);
  let r = await page.evaluate(apiSweep, sweepArg);
  check('before unlock: ' + r.calls + ' API calls throw nothing', r.thrown.length === 0, r.thrown.slice(0, 3).join(' | '));
  check('before unlock: still locked, isUnlocked() false, no caught errors', r.state === 'locked' && !r.unlocked && r.errors.length === 0, r.state + ' ' + r.errors.slice(0, 2).join(' | '));
  // music asked for before unlock starts after unlock
  r = await page.evaluate(async () => {
    const A = window.MB.Audio, out = {};
    A.playMusic('title');
    out.pendingTrack = A.debugInfo().track; out.playingBefore = A.debugInfo().playing;
    out.voiceBefore = A.playVoice('x', () => {});
    out.unlockReturn = A.unlock();
    await new Promise((res) => setTimeout(res, 400));
    const d = A.debugInfo();
    out.state = d.state; out.unlocked = A.isUnlocked(); out.playing = d.playing; out.scheduled = d.scheduled; out.active = d.activeVoices;
    return out;
  });
  check('playMusic before unlock is remembered', r.pendingTrack === 'title' && r.playingBefore === null, JSON.stringify(r.pendingTrack));
  check('after unlock(): running, isUnlocked() true, remembered track started', r.state === 'running' && r.unlocked && r.playing === 'title' && r.scheduled > 0,
    'state ' + r.state + ', playing ' + r.playing + ', ' + r.scheduled + ' events scheduled');
  r = await page.evaluate(apiSweep, sweepArg);
  check('after unlock: ' + r.calls + ' API calls throw nothing', r.thrown.length === 0, r.thrown.slice(0, 3).join(' | '));
  check('after unlock: no errors caught inside the engine', r.errors.length === 0, r.errors.slice(0, 2).join(' | '));
  // every effect really starts in the realtime context
  await sleep(3500);
  r = await page.evaluate(async (list) => {
    const A = window.MB.Audio, notStarted = [];
    let peakLive = 0;
    for (const n of list) {
      const before = A.debugInfo().sfxLive;
      A.sfx(n, { pan: 0.3 });
      const after = A.debugInfo().sfxLive;
      if (after !== before + 1) notStarted.push(n);
      peakLive = Math.max(peakLive, after);
      await new Promise((res) => setTimeout(res, 70));
    }
    await new Promise((res) => setTimeout(res, 3600));
    const d = A.debugInfo();
    return { notStarted, peakLive, leftLive: d.sfxLive, leftActive: d.activeVoices, leftNodes: d.nodes, errors: d.errors };
  }, SPEC_SFX);
  check('every effect starts in the realtime context', r.notStarted.length === 0, r.notStarted.join(' ') || 'peak ' + r.peakLive + ' at once');
  check('all effect voices are freed afterwards', r.leftLive === 0 && r.leftActive === 0 && r.leftNodes === 0, 'live ' + r.leftLive + ', voices ' + r.leftActive + ', nodes ' + r.leftNodes);
  let errs = await pageErrors(page);
  check('zero console errors (normal page)', errs.length === 0, errs.slice(0, 3).join(' | '));
  results.notes.push('console warnings on the normal page: ' + page.__log.warnings.length);
  await page.close();

  // no Web Audio at all
  page = await open(browser, '?noctx');
  r = await page.evaluate(apiSweep, sweepArg);
  const r2 = await page.evaluate(() => { const A = window.MB.Audio; return { u: A.unlock(), s: A.debugInfo().state, un: A.isUnlocked(), v: A.playVoice('test1', () => {}) }; });
  check('no AudioContext: ' + r.calls + ' API calls throw nothing', r.thrown.length === 0 && r.errors.length === 0, r.thrown.concat(r.errors).slice(0, 3).join(' | '));
  check('no AudioContext: state "unavailable", unlock() false', r2.s === 'unavailable' && r2.u === false && r2.un === false && r2.v === false, JSON.stringify(r2));
  errs = await pageErrors(page);
  check('zero console errors (no AudioContext)', errs.length === 0, errs.slice(0, 3).join(' | '));
  await page.close();

  // webkitAudioContext only, and an old feature set
  for (const variant of ['?webkit', '?legacy']) {
    page = await open(browser, variant);
    r = await page.evaluate(async (arg) => {
      const A = window.MB.Audio;
      A.playMusic('dock'); A.unlock();
      await new Promise((res) => setTimeout(res, 500));
      const d = A.debugInfo();
      for (const n of arg.sfx.slice(0, 20)) A.sfx(n, { pan: -0.4, pitch: 2 });
      await new Promise((res) => setTimeout(res, 500));
      const d2 = A.debugInfo();
      return { state: d.state, playing: d.playing, scheduled: d.scheduled, later: d2.scheduled, errors: d2.errors };
    }, sweepArg);
    check(variant.slice(1) + ': unlocks and plays', r.state === 'running' && r.playing === 'dock' && r.later > r.scheduled && r.errors.length === 0,
      'state ' + r.state + ', scheduled ' + r.scheduled + ' -> ' + r.later + ' ' + r.errors.slice(0, 2).join(' | '));
    r = await page.evaluate(apiSweep, sweepArg);
    errs = await pageErrors(page);
    check(variant.slice(1) + ': API sweep throws nothing, zero console errors', r.thrown.length === 0 && errs.length === 0, r.thrown.concat(errs).slice(0, 3).join(' | '));
    await page.close();
  }
}

// Autoplay policy: unlock() without a gesture must leave things safe and a real click must start the music.
// Headless Chromium does not enforce the policy (new AudioContext() is "running" at once whatever
// --autoplay-policy says), so test.html?blocked imitates it; see the comment there.
async function testAutoplayPolicy(browser) {
  console.log('\n[1b] autoplay policy (imitated: context stays suspended until a real user gesture)');
  const page = await open(browser, '?blocked');
  let r = await page.evaluate(async (arg) => {
    const A = window.MB.Audio, thrown = [];
    A.playMusic('bridge');
    const ret = A.unlock();
    await new Promise((res) => setTimeout(res, 400));
    const d = A.debugInfo();
    try { for (const n of arg) A.sfx(n); A.duck(0.5, 0.2); A.setVolume('music', 0.5); A.setVolume('music', 0.6); A.duck(0, 0.1); A.setIntensity(1); A.setIntensity(0); } catch (e) { thrown.push(e.message); }
    const v = A.playVoice('test1', () => {});
    return { ret, state: d.state, unlocked: A.isUnlocked(), track: d.track, playing: d.playing, scheduled: d.scheduled, thrown, v, sfxLive: A.debugInfo().sfxLive, errors: d.errors };
  }, SPEC_SFX);
  check('unlock() outside a gesture: context stays suspended, nothing throws, nothing plays, the track stays remembered',
    r.state === 'suspended' && !r.unlocked && r.ret === false && r.track === 'bridge' && r.playing === null && r.thrown.length === 0 && r.sfxLive === 0 && r.v === false && r.errors.length === 0, JSON.stringify(r));
  await page.mouse.click(200, 300);                 // a real user gesture, not on any button
  await sleep(600);
  r = await page.evaluate(() => { const A = window.MB.Audio, d = A.debugInfo(); return { state: d.state, unlocked: A.isUnlocked(), playing: d.playing, scheduled: d.scheduled, sfxLive: d.sfxLive, errors: d.errors }; });
  check('the next real click resumes the context and starts the remembered track (effects asked for earlier are not replayed)',
    r.state === 'running' && r.unlocked && r.playing === 'bridge' && r.scheduled > 0 && r.sfxLive === 0, JSON.stringify(r));
  const errs = await pageErrors(page);
  check('zero console errors (autoplay page)', errs.length === 0, errs.slice(0, 3).join(' | '));
  await page.close();
}

async function testOffline(page) {
  console.log('\n[2] offline renders (OfflineAudioContext, default volumes, measured BEFORE the limiter)');
  if (WAV && !fs.existsSync(path.join(HERE, 'out'))) fs.mkdirSync(path.join(HERE, 'out'));
  const saveWav = (name, st) => { if (st.wav) { fs.writeFileSync(path.join(HERE, 'out', name + '.wav'), Buffer.from(st.wav, 'base64')); delete st.wav; } };

  const warnings = await page.evaluate(() => window.MB.Audio._test.warnings());
  check('track data compiles with no warnings (every bar adds up, all chords and notes parse)', warnings.length === 0, warnings.slice(0, 3).join(' | '));

  // ---- music: one continuous render per track = whole intro + loop + 4 bars of the second pass ----
  const jobs = SPEC_TRACKS.map((t) => ({ key: t, track: t, intensity: 0 }));
  jobs.push({ key: 'boss@1', track: 'boss', intensity: 1 });
  jobs.push({ key: 'boss@2', track: 'boss', intensity: 2 });
  const rows = [];
  for (const j of jobs) {
    const st = await page.evaluate((a) => window.MBT.trackFull(a.track, { intensity: a.intensity, wav: a.wav }), Object.assign({ wav: WAV }, j));
    saveWav('music_' + j.key.replace(/[^a-z0-9]/gi, '_'), st);
    const info = await page.evaluate((n) => Object.assign(window.MB.Audio._test.trackInfo(n), { lint: window.MB.Audio._test.lint(n) }), j.track);
    results.music[j.key] = Object.assign({}, st, { bpm: info.bpm, loopBars: info.loopBeats / 4, introBars: info.introBeats / 4, loopSeconds: info.loopSeconds, lint: info.lint });
    rows.push({ track: j.key, bpm: info.bpm, bars: (info.introBeats ? info.introBeats / 4 + '+' : '') + info.loopBeats / 4, 'rendered s': f1(st.seconds),
      peak: f3(st.peak), 'peak dB': f1(st.peakDb), rms: f3(st.rms), 'rms dB': f1(st.rmsDb), 'A-wtd dB': f1(st.aRmsDb), crest: f1(st.crestDb),
      '<150Hz': pct(st.lf150), '>5k': pct(st.hf5), '>8k': pct(st.hf8), centroid: Math.round(st.centroid), 'silent 100ms': st.silentWindows, events: st.scheduled });
  }
  table(rows, ['track', 'bpm', 'bars', 'rendered s', 'peak', 'peak dB', 'rms', 'rms dB', 'A-wtd dB', 'crest', '<150Hz', '>5k', '>8k', 'centroid', 'silent 100ms', 'events']);
  const M = results.music;
  const base = SPEC_TRACKS.map((t) => M[t]);
  const all = Object.keys(M).map((k) => M[k]);
  check('music: no clipping before the limiter (peak < 1.0 on every render)', all.every((s) => s.peak < 1.0), 'max peak ' + f3(Math.max(...all.map((s) => s.peak))));
  check('music: peaks leave headroom (< 0.75, i.e. 2.5 dB or more)', all.every((s) => s.peak < 0.75), 'max peak ' + f3(Math.max(...all.map((s) => s.peak))));
  check('music: no NaN samples, no DC offset', all.every((s) => s.nan === 0 && Math.abs(s.dc) < 0.002), '');
  check('music: every render is at least 20 s (the whole loop)', all.every((s) => s.seconds >= 20), f1(Math.min(...all.map((s) => s.seconds))) + ' .. ' + f1(Math.max(...all.map((s) => s.seconds))) + ' s');
  check('music: no silence (no 100 ms window below -60 dBFS anywhere in the loop)', all.every((s) => s.silentWindows === 0), Object.keys(M).filter((k) => M[k].silentWindows).join(' '));
  const rmsDb = base.map((s) => s.rmsDb), spread = Math.max(...rmsDb) - Math.min(...rmsDb);
  check('music: RMS comparable across the 7 tracks (spread <= 3 dB)', spread <= 3, 'spread ' + f1(spread) + ' dB, ' + f1(Math.min(...rmsDb)) + ' .. ' + f1(Math.max(...rmsDb)) + ' dBFS');
  const aDb = base.map((s) => s.aRmsDb), aSpread = Math.max(...aDb) - Math.min(...aDb);
  check('music: A-weighted RMS comparable across the 7 tracks (spread <= 3 dB)', aSpread <= 3, 'spread ' + f1(aSpread) + ' dB, ' + f1(Math.min(...aDb)) + ' .. ' + f1(Math.max(...aDb)) + ' dB');
  check('music: energy above 8 kHz stays low (< 1% of total on every render)', all.every((s) => s.hf8 < 0.01), 'max ' + pct(Math.max(...all.map((s) => s.hf8))));
  check('boss: each intensity level adds events', M['boss@1'].scheduled > M.boss.scheduled && M['boss@2'].scheduled > M['boss@1'].scheduled,
    M.boss.scheduled + ' < ' + M['boss@1'].scheduled + ' < ' + M['boss@2'].scheduled + ' events');
  check('boss: intensity raises the level only moderately (< 3 dB from 0 to 2)', M['boss@2'].rmsDb - M.boss.rmsDb < 3 && M['boss@2'].rmsDb >= M.boss.rmsDb, f1(M['boss@2'].rmsDb - M.boss.rmsDb) + ' dB');
  check('tempo and length follow the brief (16-32 bars, bpm within 2 of the brief)',
    SPEC_TRACKS.every((t) => M[t].loopBars >= 16 && M[t].loopBars <= 32) && [112, 120, 104, 126, 92, 140, 120].every((b, i) => Math.abs(base[i].bpm - b) <= 2) && M.victory.introBars === 4, '');
  const lintBad = SPEC_TRACKS.filter((t) => M[t].lint.chordTone !== M[t].lint.strong);
  check('melody: every lead note sounding on beats 1 and 3 is a chord tone', lintBad.length === 0,
    SPEC_TRACKS.map((t) => t + ' ' + M[t].lint.chordTone + '/' + M[t].lint.strong).join(', '));
  check('melody: lead stays at or below G#6 (1661 Hz)', SPEC_TRACKS.every((t) => M[t].lint.hi <= 92), SPEC_TRACKS.map((t) => t + ' ' + M[t].lint.lo + '-' + M[t].lint.hi).join(', '));

  // ---- the shared theme: so do re mi . so mi (+5 +2 +2 +3 -3 semitones), upside-down for the boss ----
  const motif = await page.evaluate((tracks) => {
    const find = (iv, pat) => { let n = 0; for (let i = 0; i + pat.length <= iv.length; i++) { let ok = true; for (let j = 0; j < pat.length; j++) if (iv[i + j] !== pat[j]) { ok = false; break; } if (ok) n++; } return n; };
    const out = {};
    for (const t of tracks) {
      const lead = window.MB.Audio._test.events(t, 1, 0).events.filter((e) => e.p === 'lead').sort((a, b) => a.time - b.time).map((e) => e.n);
      const iv = lead.slice(1).map((n, i) => n - lead[i]);
      out[t] = { notes: lead.length, first: lead.slice(0, 6), theme: find(iv, [5, 2, 2, 3, -3]), head: find(iv, [5, 2, 2]), inverted: find(iv, [-5, -2, -2, -3, 3]) };
    }
    return out;
  }, SPEC_TRACKS);
  results.motif = motif;
  console.log('  theme statements per pass (full / first four notes / inverted): ' + SPEC_TRACKS.map((t) => t + ' ' + motif[t].theme + '/' + motif[t].head + '/' + motif[t].inverted).join(', '));
  check('leitmotif: title opens with the theme; dock and victory restate it; boss carries its inversion in the minor key',
    JSON.stringify(motif.title.first) === '[67,72,74,76,79,76]' && motif.title.theme >= 3 && motif.dock.theme >= 3 && motif.victory.theme >= 1 && motif.boss.inverted >= 4 && motif.boss.theme === 0,
    'title ' + motif.title.theme + 'x, dock ' + motif.dock.theme + 'x, victory ' + motif.victory.theme + 'x, boss inverted ' + motif.boss.inverted + 'x');

  // ---- ten minutes, and another sample rate ----
  const soak = await page.evaluate(async () => {
    const A = window.MB.Audio._test, T = window.MBT, out = {};
    for (const [name, intensity] of [['zerog', 0], ['boss', 2]]) {
      const info = A.trackInfo(name), L = info.loopSeconds;
      const r = await A.render({ track: name, seconds: 600, intensity });
      const passes = [];
      for (let k = 1; (k + 1) * L <= 600; k++) passes.push(T.stats(r.buffer, 0.02 + k * L, 0.02 + (k + 1) * L));   // pass 2 onwards (pass 1 starts from silence)
      await new Promise((res) => setTimeout(res, 30));
      const c = r.counts();
      out[name] = { passes: passes.length + 1, rmsDb: passes.map((p) => p.rmsDb), peak: passes.map((p) => p.peak), whole: T.stats(r.buffer, 0.02).peak, active: c.active, nodes: c.nodes, scheduled: r.scheduled, missed: r.missed };
    }
    const a = await A.render({ track: 'title', seconds: 30 }), b = await A.render({ track: 'title', seconds: 30, sampleRate: 48000 });
    out.sr = { rms441: T.stats(a.buffer, 0.02).rmsDb, rms48: T.stats(b.buffer, 0.02).rmsDb, peak441: T.stats(a.buffer, 0.02).peak, peak48: T.stats(b.buffer, 0.02).peak };
    return out;
  });
  results.soak = soak;
  for (const k of ['zerog', 'boss']) {
    const s = soak[k], d = Math.max(...s.rmsDb) - Math.min(...s.rmsDb);
    console.log('  10-minute render of ' + k + ': ' + s.passes + ' passes, per-pass RMS ' + f1(Math.min(...s.rmsDb)) + ' .. ' + f1(Math.max(...s.rmsDb)) + ' dB, peak ' + f3(s.whole) + ', ' + s.scheduled + ' events, voices still sounding at the end: ' + s.active + ' (' + s.nodes + ' nodes)');
    check('10 minutes of ' + k + ': every pass of the loop has the same level (within 0.2 dB), nothing builds up, voices stay bounded',
      d <= 0.2 && Math.max(...s.peak) - Math.min(...s.peak) < 0.1 && s.whole < 0.8 && s.missed === 0 && s.active < 40 && s.nodes < 250,
      'RMS spread ' + d.toFixed(3) + ' dB, per-pass peak ' + f3(Math.min(...s.peak)) + ' .. ' + f3(Math.max(...s.peak)) + ', ' + s.active + ' voices / ' + s.nodes + ' nodes at the end');
  }
  check('same level at 48 kHz as at 44.1 kHz (title, 30 s: RMS within 0.3 dB)', Math.abs(soak.sr.rms441 - soak.sr.rms48) < 0.3, f1(soak.sr.rms441) + ' vs ' + f1(soak.sr.rms48) + ' dB, peak ' + f3(soak.sr.peak441) + ' vs ' + f3(soak.sr.peak48));

  // ---- sound effects ----
  console.log('\n  sound effects (peak is at the master output with default volumes: sfx 0.8 x master 0.8)');
  const srows = [];
  for (const n of SPEC_SFX) {
    const st = await page.evaluate((a) => window.MBT.sfx(a.n, null, { wav: a.wav }), { n, wav: WAV });
    saveWav('sfx_' + n, st);
    results.sfx[n] = st;
    srows.push({ sfx: n, target: f3(st.level * 0.64), peak: f3(st.peak), 'peak dB': f1(st.peakDb), 'rms dB': f1(st.activeRmsDb), 'A-wtd dB': f1(st.activeARmsDb), seconds: st.activeSeconds.toFixed(2), 'voices s': st.len.toFixed(2),
      '>8k': pct(st.hf8), '>5k': pct(st.hf5), centroid: Math.round(st.centroid) });
  }
  table(srows, ['sfx', 'target', 'peak', 'peak dB', 'rms dB', 'A-wtd dB', 'seconds', 'voices s', '>8k', '>5k', 'centroid']);
  const S = results.sfx, sl = SPEC_SFX.map((n) => S[n]);
  check('sfx: none silent, none clipping (0.03 < peak < 1.0)', sl.every((s) => s.peak > 0.03 && s.peak < 1.0), 'range ' + f3(Math.min(...sl.map((s) => s.peak))) + ' .. ' + f3(Math.max(...sl.map((s) => s.peak))));
  const off = SPEC_SFX.map((n) => ({ n, d: S[n].peakDb - 20 * Math.log10(S[n].level * 0.64) }));
  const worst = off.reduce((a, b) => (Math.abs(b.d) > Math.abs(a.d) ? b : a));
  check('sfx: every peak within 1 dB of its level class', off.every((o) => Math.abs(o.d) <= 1), 'worst ' + worst.n + ' ' + f1(worst.d) + ' dB');
  const loud = SPEC_SFX.filter((n) => S[n].level >= 0.3);
  const lp = loud.map((n) => S[n].peakDb);
  check('sfx: peaks consistent (all but the deliberately tiny ones within 6 dB of each other)', Math.max(...lp) - Math.min(...lp) <= 6, f1(Math.min(...lp)) + ' .. ' + f1(Math.max(...lp)) + ' dBFS over ' + loud.length + ' effects');
  check('sfx: all voices ended, all nodes freed and the tail is silent at the end of each render', sl.every((s) => s.leftActive === 0 && s.leftNodes === 0 && s.leftLive === 0 && s.tailPeak < 0.002),
    SPEC_SFX.filter((n) => S[n].leftActive || S[n].leftNodes || S[n].tailPeak >= 0.002).join(' ') || 'longest voice lifetime ' + Math.max(...sl.map((s) => s.len)).toFixed(2) + ' s');
  check('sfx: energy above 8 kHz stays low (< 2% of total for every effect)', sl.every((s) => s.hf8 < 0.02), 'max ' + pct(Math.max(...sl.map((s) => s.hf8))) + ' (' + SPEC_SFX.reduce((a, b) => (S[b].hf8 > S[a].hf8 ? b : a)) + ')');
  const lenBad = Object.keys(SPEC_LEN).filter((n) => S[n].activeSeconds < SPEC_LEN[n][0] || S[n].activeSeconds > SPEC_LEN[n][1]);
  check('sfx: durations the spec gives are met', lenBad.length === 0, Object.keys(SPEC_LEN).map((n) => n + ' ' + S[n].activeSeconds.toFixed(2) + 's').join(', '));
  check('sfx: short (every effect <= 3 s, movement/UI effects <= 0.6 s)', sl.every((s) => s.activeSeconds <= 3.0) &&
    ['jump', 'land', 'step', 'stomp', 'uiMove', 'uiSelect', 'uiBack', 'textBlip', 'cellPlace', 'cellRemove', 'chip'].every((n) => S[n].activeSeconds <= 0.6), '');
  const gentleMax = Math.max(...GENTLE.map((n) => S[n].peak)), correctPeak = S.correct.peak;
  check('sfx: wrong / bridgeFail / gateWrong / podWrong are quieter than "correct", low and dull (centroid < 1.2 kHz, < 0.5% above 5 kHz)',
    GENTLE.every((n) => S[n].peak < correctPeak * 0.75 && S[n].centroid < 1200 && S[n].hf5 < 0.005),
    GENTLE.map((n) => n + ' pk ' + f3(S[n].peak) + ' c ' + Math.round(S[n].centroid) + 'Hz').join(', '));
  check('sfx: step and textBlip are very quiet (peak < 0.12)', S.step.peak < 0.12 && S.textBlip.peak < 0.12, f3(S.step.peak) + ' ' + f3(S.textBlip.peak));

  // opts: pitch / vol / pan
  const o = await page.evaluate(async () => {
    const T = window.MBT, out = {};
    out.base = await T.sfx('chip'); out.up = await T.sfx('chip', { pitch: 12 }); out.down = await T.sfx('chip', { pitch: -12 });
    out.half = await T.sfx('chip', { vol: 0.5 });
    const r = await window.MB.Audio._test.render({ seconds: 0.8, sfx: [{ name: 'chip', at: 0, opts: { pan: 1 } }] });
    const L = r.buffer.getChannelData(0), R = r.buffer.getChannelData(1); let pl = 0, pr = 0;
    for (let i = 0; i < L.length; i++) { pl = Math.max(pl, Math.abs(L[i])); pr = Math.max(pr, Math.abs(R[i])); }
    out.panL = pl; out.panR = pr;
    const c = await window.MB.Audio._test.render({ seconds: 0.8, sfx: [{ name: 'chip', at: 0, opts: { pan: 0.001 } }] });
    out.panCentre = T.stats(c.buffer).peak;
    out.pod = []; for (const p of [0, 2, 4, 5, 7, 9, 11, 12]) out.pod.push((await T.sfx('podStep', { pitch: p })).centroid);
    return out;
  });
  check('sfx opts.pitch moves the spectrum up and down (chip centroid)', o.up.centroid > o.base.centroid * 1.3 && o.down.centroid < o.base.centroid * 0.8,
    Math.round(o.down.centroid) + ' < ' + Math.round(o.base.centroid) + ' < ' + Math.round(o.up.centroid) + ' Hz');
  check('sfx opts.pitch +12 stays tame (peak not above base, < 3% above 8 kHz)', o.up.peak <= o.base.peak * 1.05 && o.up.hf8 < 0.03, 'peak ' + f3(o.up.peak) + ', >8k ' + pct(o.up.hf8));
  check('sfx opts.vol 0.5 halves the peak', Math.abs(o.half.peak / o.base.peak - 0.5) < 0.03, f3(o.half.peak / o.base.peak));
  check('sfx opts.pan 1 is right-only and no louder than centre', o.panL < 0.002 && Math.abs(o.panR / o.base.peak - 1) < 0.06 && Math.abs(o.panCentre / o.base.peak - 1) < 0.06,
    'L ' + f3(o.panL) + ' R ' + f3(o.panR) + ' centre ' + f3(o.panCentre) + ' unpanned ' + f3(o.base.peak));
  check('podStep opts.pitch climbs monotonically', o.pod.every((c, i) => i === 0 || c > o.pod[i - 1]), o.pod.map(Math.round).join(' '));
  // jingles follow the key of the music; unpitched effects do not
  const k = await page.evaluate(async () => {
    const A = window.MB.Audio._test, T = window.MBT, out = { keys: {}, tonal: [], correct: [], jump: [] };
    for (const t of A.tracks()) out.keys[t] = A.trackInfo(t).key;
    for (const n of A.sfxNames()) if (A.sfxInfo(n).tonal) out.tonal.push(n);
    for (const key of [-5, -3, 0, 2, 4, 5]) {
      const c = T.stats((await A.render({ seconds: 1.6, key, sfx: [{ name: 'correct', at: 0 }] })).buffer);
      const j = T.stats((await A.render({ seconds: 0.6, key, sfx: [{ name: 'jump', at: 0 }] })).buffer);
      out.correct.push({ key, peak: c.peak, centroid: c.centroid, hf8: c.hf8 }); out.jump.push(j.centroid);
    }
    return out;
  });
  results.keys = k;
  check('tonal effects are transposed with the music key (centroid of "correct" rises with the key), peak stays within 1.5 dB, still tame',
    k.correct.every((c, i) => i === 0 || c.centroid > k.correct[i - 1].centroid) && k.correct.every((c) => Math.abs(20 * Math.log10(c.peak / k.correct[2].peak)) < 1.5 && c.hf8 < 0.02),
    k.correct.map((c) => (c.key > 0 ? '+' : '') + c.key + ': ' + Math.round(c.centroid) + ' Hz / ' + f3(c.peak)).join(', '));
  check('unpitched effects ignore the key (jump)', k.jump.every((c) => Math.abs(c - k.jump[0]) < 1), '');
  console.log('  track keys (semitones from C): ' + JSON.stringify(k.keys) + '; ' + k.tonal.length + ' tonal effects');

  // ---- limiter ----
  console.log('\n  limiter');
  const lim = await page.evaluate(async () => {
    const A = window.MB.Audio._test, T = window.MBT, out = {};
    out.makeup = await T.compGain(0.02);
    out.trim = A.defaults.trim;
    const quiet = { seconds: 2, sfx: [{ name: 'uiSelect', at: 1 }] };       // after the compressor has settled (it fades in over ~0.2 s)
    out.quietPre = T.stats((await A.render(quiet)).buffer).peak;
    out.quietPost = T.stats((await A.render(Object.assign({ limiter: true }, quiet))).buffer).peak;
    const typical = { seconds: 8, track: 'boss', intensity: 2, sfx: [{ name: 'bossHit', at: 2 }, { name: 'jump', at: 2.3 }, { name: 'cannonFire', at: 4 }, { name: 'correct', at: 6 }] };
    out.typPre = T.stats((await A.render(typical)).buffer, 0.02);
    out.typPost = T.stats((await A.render(Object.assign({ limiter: true }, typical))).buffer, 0.02);
    const loud = { seconds: 6, track: 'boss', intensity: 2, vols: { master: 1, music: 1, sfx: 1, voice: 1 }, sfx: [] };
    for (const n of ['cannonFire', 'bossDefeat', 'quarterGet', 'victory', 'bossHit', 'shieldBreak', 'reactorOnline', 'whole']) for (const at of [1, 1.02, 3]) loud.sfx.push({ name: n, at });
    out.loudPre = T.stats((await A.render(loud)).buffer, 0.02);
    out.loudPost = T.stats((await A.render(Object.assign({ limiter: true }, loud))).buffer, 0.02);
    return out;
  });
  results.limiter = lim;
  console.log('  compressor make-up gain in this browser: x' + f3(lim.makeup) + ' (' + f1(20 * Math.log10(lim.makeup)) + ' dB); COMP_TRIM = ' + lim.trim + ' -> x' + f3(lim.makeup * lim.trim) + ' for quiet material');
  console.log('  boss@2 + 4 effects, default volumes : before limiter peak ' + f3(lim.typPre.peak) + ' rms ' + f1(lim.typPre.rmsDb) + ' dB | after limiter peak ' + f3(lim.typPost.peak) + ' rms ' + f1(lim.typPost.rmsDb) + ' dB');
  console.log('  boss@2 + 24 big effects, all volumes 1.0 : before limiter peak ' + f3(lim.loudPre.peak) + ' | after limiter peak ' + f3(lim.loudPost.peak) + ' rms ' + f1(lim.loudPost.rmsDb) + ' dB');
  check('limiter is transparent for quiet material (within 0.5 dB of unity)', Math.abs(20 * Math.log10(lim.quietPost / lim.quietPre)) < 0.5, 'x' + f3(lim.quietPost / lim.quietPre));
  check('limiter trim cancels the compressor make-up gain (within 3%)', Math.abs(lim.makeup * lim.trim - 1) < 0.03, 'x' + f3(lim.makeup * lim.trim));
  check('typical busy scene: music + effects below 1.0 even before the limiter', lim.typPre.peak < 1.0, f3(lim.typPre.peak));
  check('worst case (everything at once, all volumes 1.0) cannot clip after the limiter', lim.loudPre.peak > 1.0 && lim.loudPost.peak < 0.95, 'before ' + f3(lim.loudPre.peak) + ', after ' + f3(lim.loudPost.peak));
}

async function testSeams(page) {
  console.log('\n[3] loop seams (events from three passes of the scheduler; audio from the continuous renders above)');
  const rows = [];
  const cases = SPEC_TRACKS.map((t) => ({ name: t, intensity: 0 })).concat([{ name: 'boss', intensity: 2 }]);
  for (const c of cases) {
    const key = c.name + (c.intensity ? '@' + c.intensity : '');
    const ev = await page.evaluate(seamEvents, c);
    const au = results.music[key].seam;
    results.seam[key] = { events: ev, audio: au };
    rows.push({ track: key, 'events/pass': ev.perPass.join(','), 'max dev s': ev.maxDeviation.toExponential(1), dup: ev.duplicates, 'mono overlap s': ev.maxMonoOverlap.toFixed(4),
      'last onset before (beats)': ev.lastOnsetBeforeSeamBeats.toFixed(3), 'first after (s)': ev.firstOnsetAfterSeam.toExponential(1),
      'pad gap (beats)': ev.padEndsBeforeSeamBeats === null ? '-' : ev.padEndsBeforeSeamBeats.toFixed(3),
      'rms 1s around seam': f3(au.nearMin) + '..' + f3(au.nearMax), 'whole track p5/med/max': f3(au.p05) + '/' + f3(au.median) + '/' + f3(au.max),
      'pass2 vs pass1 dB (beat 1 / beats 2-16)': f1(au.firstBeatDiffDb) + ' / ' + f1(au.maxBeatDiffDb) });
  }
  table(rows, ['track', 'events/pass', 'max dev s', 'dup', 'mono overlap s', 'last onset before (beats)', 'first after (s)', 'pad gap (beats)', 'rms 1s around seam', 'whole track p5/med/max', 'pass2 vs pass1 dB (beat 1 / beats 2-16)']);
  const R = Object.keys(results.seam).map((k) => results.seam[k]);
  check('seam: every pass of the loop schedules the same events, exactly one loop length apart (< 1 ns)', R.every((r) => r.events.mismatch === 0 && r.events.maxDeviation < 1e-9 && r.events.perPass[0] === r.events.perPass[2]), '');
  check('seam: no event falls outside its own pass, none is scheduled twice', R.every((r) => r.events.outOfRange === 0 && r.events.duplicates === 0), '');
  check('seam: the first event of the next pass is exactly on the loop point', R.every((r) => Math.abs(r.events.firstOnsetAfterSeam) < 1e-9), '');
  check('seam: the last onset before the loop point is at most one beat earlier (no gap)', R.every((r) => r.events.lastOnsetBeforeSeamBeats <= 1.0 + 1e-9), R.map((r) => r.events.lastOnsetBeforeSeamBeats.toFixed(2)).join(' '));
  check('seam: lead / bass / counter-melody never overlap themselves (no doubled notes at the loop point)', R.every((r) => r.events.maxMonoOverlap <= 1e-9), R.map((r) => r.events.maxMonoOverlap.toFixed(3)).join(' '));
  check('seam: pad chords meet at the loop point (ends within 0.1 beat before it, next starts on it)', R.every((r) => r.events.padEndsBeforeSeamBeats >= 0 && r.events.padEndsBeforeSeamBeats <= 0.1 && Math.abs(r.events.padStartsAfterSeam) < 1e-9), '');
  check('seam: same number of occupied 16th-note slots in every pass', R.every((r) => r.events.gridSlots[0] === r.events.gridSlots[1] && r.events.gridSlots[1] === r.events.gridSlots[2]), '');
  check('seam (audio): no hole at the loop point (no 50 ms window within 1 s of it below half the 5th percentile of the whole track)', R.every((r) => r.audio.nearMin >= r.audio.p05 * 0.5), '');
  check('seam (audio): no pile-up at the loop point (no 50 ms window within 1 s of it above the loudest window elsewhere x 1.1)', R.every((r) => r.audio.nearMax <= r.audio.max * 1.1), '');
  check('seam (audio): the second pass starts like the first (per-beat RMS of bars 1-4 within 3 dB after the first beat)', R.every((r) => r.audio.maxBeatDiffDb <= 3),
    R.map((r) => f1(r.audio.maxBeatDiffDb)).join(' ') + ' dB');
  const v = results.seam.victory.events;
  check('victory: 4-bar fanfare intro leads straight into the loop (16 beats, last intro onset < 1 beat before)', v.intro > 0 && v.introEndsBeforeLoopBeats > 0 && v.introEndsBeforeLoopBeats <= 1, v.intro + ' intro events, ' + (v.introEndsBeforeLoopBeats || 0).toFixed(2) + ' beats');
}

async function testRealtime(page) {
  console.log('\n[4] realtime scheduler (10 s per track, sampled every 250 ms)');
  await page.evaluate(() => { window.MB.Audio.unlock(); });
  await sleep(300);
  const rows = [];
  const plans = SPEC_TRACKS.map((t) => ({ name: t })).concat([{ name: 'boss', ramp: true }]);
  for (const p of plans) {
    const key = p.name + (p.ramp ? ' 0>1>2' : '');
    await page.evaluate((n) => { const A = window.MB.Audio; A.setIntensity(0); A._test.record(true); A.playMusic(n, { fade: 0.2 }); }, p.name);
    const samples = [];
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) {
      await sleep(250);
      if (p.ramp) await page.evaluate((lv) => window.MB.Audio.setIntensity(lv), Date.now() - t0 > 6500 ? 2 : (Date.now() - t0 > 3000 ? 1 : 0));
      samples.push(await page.evaluate(rtSample));
    }
    const ev = await page.evaluate(rtEvents, p.name);
    await page.evaluate(() => { window.MB.Audio.stopMusic(0.2); window.MB.Audio.setIntensity(0); });
    await sleep(1800);
    const after = await page.evaluate(rtSample);
    const half = Math.floor(samples.length / 2);
    const mx = (arr, k) => Math.max(...arr.map((s) => s[k]));
    const first = samples[0], last = samples[samples.length - 1];
    const audioSpan = last.time - first.time, wallSpan = (last.wall - first.wall) / 1000;
    const r = { samples: samples.length, activeMaxA: mx(samples.slice(0, half), 'active'), activeMaxB: mx(samples.slice(half), 'active'),
      nodesMaxA: mx(samples.slice(0, half), 'nodes'), nodesMaxB: mx(samples.slice(half), 'nodes'),
      scheduled: last.scheduled, ramp: !!p.ramp, dupEnded: last.dupEnded,
      missed: last.missed, late: last.late, clockRatio: audioSpan / wallSpan, rmsMin: Math.min(...samples.slice(2).map((s) => s.rms)), rmsMax: mx(samples, 'rms'),
      states: Array.from(new Set(samples.map((s) => s.state))).join(','), ev, after };
    results.realtime[key] = r;
    rows.push({ track: key, events: ev.count + (p.ramp ? '' : '/' + ev.expected), 'span s': ev.span.toFixed(2), 'grid dev s': ev.maxGridDeviation.toExponential(1), 'lead ms': (ev.minLead * 1000).toFixed(0) + '..' + (ev.maxLead * 1000).toFixed(0),
      missed: r.missed, late: r.late, 'voices 1st/2nd half': r.activeMaxA + '/' + r.activeMaxB, 'nodes 1st/2nd half': r.nodesMaxA + '/' + r.nodesMaxB,
      'clock': r.clockRatio.toFixed(3), 'tap rms': f3(r.rmsMin) + '..' + f3(r.rmsMax), 'after stop v/n/p': after.active + '/' + after.nodes + '/' + after.players });
  }
  table(rows, ['track', 'events', 'span s', 'grid dev s', 'lead ms', 'missed', 'late', 'voices 1st/2nd half', 'nodes 1st/2nd half', 'clock', 'tap rms', 'after stop v/n/p']);
  const R = Object.keys(results.realtime).map((k) => results.realtime[k]);
  check('realtime: context stays running and its clock advances in real time (ratio 0.97-1.03)', R.every((r) => r.states === 'running' && r.clockRatio > 0.97 && r.clockRatio < 1.03), R.map((r) => r.clockRatio.toFixed(3)).join(' '));
  check('realtime: the scheduler keeps running for the whole 10 s and schedules every event of the track, in order (count = compiled data, none skipped)',
    R.every((r) => r.ev.span > 9 && r.ev.backwards === 0 && (r.ramp || r.ev.count === r.ev.expected)), R.map((r) => r.ev.count + (r.ramp ? '' : '/' + r.ev.expected)).join(' '));
  check('realtime: every event sits exactly on the beat grid (deviation < 1 ns: no drift)', R.every((r) => r.ev.maxGridDeviation < 1e-9), '');
  check('realtime: every event was scheduled ahead of the audio clock, by no more than the look-ahead + one tick', R.every((r) => r.ev.minLead > 0 && r.ev.maxLead < 0.2 && r.missed === 0 && r.late === 0),
    R.map((r) => (r.ev.minLead * 1000).toFixed(0) + '-' + (r.ev.maxLead * 1000).toFixed(0)).join(' ') + ' ms');
  check('realtime: voice and node counts do not grow (2nd half max <= 1.3 x 1st half max + 4; under 250 nodes)', R.every((r) => r.activeMaxB <= r.activeMaxA * 1.3 + 4 && r.nodesMaxB <= r.nodesMaxA * 1.3 + 12 && r.nodesMaxB < 250),
    'max voices ' + Math.max(...R.map((r) => Math.max(r.activeMaxA, r.activeMaxB))) + ', max nodes ' + Math.max(...R.map((r) => Math.max(r.nodesMaxA, r.nodesMaxB))));
  check('realtime: signal is present on the master bus while playing', R.every((r) => r.rmsMax > 0.02), R.map((r) => f3(r.rmsMax)).join(' '));
  check('realtime: after stopMusic everything is freed (0 voices, 0 nodes, 0 players, silent)', R.every((r) => r.after.active === 0 && r.after.nodes === 0 && r.after.players === 0 && r.after.rms < 1e-4), R.map((r) => r.after.active + '/' + r.after.nodes + '/' + r.after.players).join(' '));

  // ---- behaviour around it ----
  let r = await page.evaluate(async () => {
    const A = window.MB.Audio, wait = (ms) => new Promise((res) => setTimeout(res, ms)), out = {};
    // the key the jingles use follows the track
    A.playMusic('bridge', { fade: 0.05 }); await wait(300); out.keyBridge = A.debugInfo().key;
    A.playMusic('boss', { fade: 0.05 }); await wait(300); out.keyBoss = A.debugInfo().key;
    A.stopMusic(0.05); await wait(300); out.keyNone = A.debugInfo().key;
    // same track twice is a no-op
    A.playMusic('title', { fade: 0.1 }); await wait(500);
    const s1 = A.debugInfo().scheduled; A.playMusic('title'); A.playMusic('title', { fade: 0 }); await wait(300);
    out.noop = A.debugInfo().players === 1 && A.debugInfo().scheduled >= s1;
    // rapid switching
    A.playMusic('dock'); A.playMusic('bridge'); A.playMusic('reactor'); A.playMusic('zerog'); A.playMusic('boss');
    out.playersDuringSwitch = A.debugInfo().players;
    await wait(1500);
    out.playersAfterSwitch = A.debugInfo().players; out.playingAfterSwitch = A.debugInfo().playing;
    // cross-fade: both tracks present for a moment, then one
    A.playMusic('victory', { fade: 1.0 }); await wait(300);
    out.playersMidFade = A.debugInfo().players; await wait(1300);
    out.playersAfterFade = A.debugInfo().players;
    // playMusic(null) stops
    A.playMusic(null); await wait(1000);
    out.afterNull = { players: A.debugInfo().players, track: A.debugInfo().track };
    // duck and volume ramp smoothly (read the real AudioParams)
    A.playMusic('title', { fade: 0 }); await wait(600);
    const tapLevel = async () => { let m = 0; for (let i = 0; i < 12; i++) { const a = A._test.tap(), b = new Float32Array(a.fftSize); a.getFloatTimeDomainData(b); let s = 0; for (let j = 0; j < b.length; j++) s += b[j] * b[j]; m += Math.sqrt(s / b.length); await wait(50); } return m / 12; };
    out.levelNormal = await tapLevel();
    A.duck(0.8, 0.2); await wait(500); out.levelDucked = await tapLevel();
    A.duck(0, 0.2); await wait(500); out.levelBack = await tapLevel();
    A.setVolume('music', 0); await wait(300); out.levelMuted = await tapLevel();
    A.setVolume('music', 0.6); await wait(300);
    out.getVolume = [A.getVolume('master'), A.getVolume('music'), A.getVolume('sfx'), A.getVolume('voice')];
    return out;
  });
  check('realtime: jingles are keyed to the playing track (bridge -3, boss -5, none 0)', r.keyBridge === -3 && r.keyBoss === -5 && r.keyNone === 0, [r.keyBridge, r.keyBoss, r.keyNone].join(' '));
  check('playMusic with the current track is a no-op', r.noop, '');
  check('rapid switching (5 tracks in one frame): never more than 2 players, settles on the last track', r.playersDuringSwitch <= 2 && r.playersAfterSwitch === 1 && r.playingAfterSwitch === 'boss', r.playersDuringSwitch + ' -> ' + r.playersAfterSwitch + ' (' + r.playingAfterSwitch + ')');
  check('cross-fade: two players during the fade, one after', r.playersMidFade === 2 && r.playersAfterFade === 1, r.playersMidFade + ' -> ' + r.playersAfterFade);
  check('playMusic(null) stops the music', r.afterNull.players === 0 && r.afterNull.track === null, JSON.stringify(r.afterNull));
  check('duck(0.8) lowers the music by roughly 14 dB and duck(0) restores it', r.levelDucked < r.levelNormal * 0.4 && r.levelDucked > r.levelNormal * 0.08 && r.levelBack > r.levelNormal * 0.6,
    f3(r.levelNormal) + ' -> ' + f3(r.levelDucked) + ' -> ' + f3(r.levelBack));
  check('setVolume("music", 0) silences the music; getVolume returns what was set', r.levelMuted < 0.001 && JSON.stringify(r.getVolume) === '[0.8,0.6,0.8,1]', f3(r.levelMuted) + ' ' + JSON.stringify(r.getVolume));

  // pause / resume, tab hidden, a blocked main thread, effect spam
  r = await page.evaluate(async () => {
    const A = window.MB.Audio, wait = (ms) => new Promise((res) => setTimeout(res, ms)), out = {};
    A._test.record(true);
    A.sfx('pause'); A.pauseAll(); await wait(700);
    let d = A.debugInfo(); out.pausedState = d.state; const t1 = d.time; await wait(400); out.frozen = A.debugInfo().time - t1;
    A.sfx('uiMove'); A.sfx('uiMove');
    out.sfxWhilePaused = A.debugInfo().sfxLive;
    await wait(300);
    A.sfx('unpause'); A.resumeAll(); await wait(150);
    out.sfxAfterResume = A.debugInfo().sfxLive; await wait(350);
    d = A.debugInfo(); out.resumedState = d.state; out.missedAfterPause = d.missed; const s2 = d.scheduled; await wait(400);
    out.schedulingAfterResume = A.debugInfo().scheduled > s2;
    // tab hidden
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    document.dispatchEvent(new Event('visibilitychange')); await wait(400);
    out.hiddenState = A.debugInfo().state;
    A.unlock(); A.resumeAll(); await wait(200);                    // must not wake a hidden tab
    out.hiddenAfterResumeAll = A.debugInfo().state;
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
    document.dispatchEvent(new Event('visibilitychange')); await wait(400);
    out.visibleState = A.debugInfo().state;
    // pauseAll while visible, then hide and show: must stay paused
    A.pauseAll(); await wait(500);
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')); await wait(100);
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange')); await wait(300);
    out.stillPaused = A.debugInfo().state;
    delete document.hidden;
    A.resumeAll(); await wait(400);
    // main thread blocked for 600 ms (five times the look-ahead)
    const before = A.debugInfo(); const tb = performance.now(); while (performance.now() - tb < 600) { /* busy */ }
    await wait(500);
    const aft = A.debugInfo();
    out.block = { missed: aft.missed - before.missed, late: aft.late - before.late, scheduled: aft.scheduled - before.scheduled, state: aft.state };
    const rec = A._test.record(false) || [];
    let past = 0, maxLead = 0; for (const e of rec) { if (e.time < e.at - 1e-6) past++; maxLead = Math.max(maxLead, e.time - e.at); }
    out.block.inPast = past; out.block.maxLead = maxLead; out.block.events = rec.length;
    await wait(300);
    // effect spam: 6 s of far more calls than a game would make
    let peakLive = 0, peakNodes = 0, calls = 0;
    const names = ['step', 'chip', 'textBlip', 'jump', 'bossShoot', 'zap', 'cellPlace', 'land', 'bossDefeat', 'reactorOnline'];
    const tEnd = performance.now() + 6000;
    while (performance.now() < tEnd) {
      for (let i = 0; i < 6; i++) { A.sfx(names[(calls + i) % names.length], { pitch: calls % 12, pan: (calls % 5 - 2) / 2 }); }
      calls += 6;
      const di = A.debugInfo(); peakLive = Math.max(peakLive, di.sfxLive); peakNodes = Math.max(peakNodes, di.nodes);
      await wait(16);
    }
    A.stopMusic(0.1);
    await wait(3800);
    d = A.debugInfo();
    out.spam = { calls, peakLive, peakNodes, leftLive: d.sfxLive, leftVoices: d.activeVoices, leftNodes: d.nodes, players: d.players, errors: d.errors };
    return out;
  });
  results.realtime.behaviour = r;
  results.notes.push('Chromium delivered "ended" more than once for ' + (await page.evaluate(() => window.MB.Audio.debugInfo().dupEnded)) + ' voices during the realtime section (handled: each voice is counted out once)');
  check('pauseAll(): context suspended and its clock frozen', r.pausedState === 'suspended' && r.frozen === 0, r.pausedState + ', clock moved ' + r.frozen);
  check('effects requested while paused do not pile up; sfx("unpause") + resumeAll() is heard', r.sfxWhilePaused === 0 && r.sfxAfterResume === 1, 'live while paused ' + r.sfxWhilePaused + ', after resume ' + r.sfxAfterResume);
  check('resumeAll(): running again, music carries on without dropped events', r.resumedState === 'running' && r.schedulingAfterResume && r.missedAfterPause === 0, r.resumedState + ', missed ' + r.missedAfterPause);
  check('visibilitychange hidden suspends; resumeAll()/unlock() while hidden do not wake it; visible resumes', r.hiddenState === 'suspended' && r.hiddenAfterResumeAll === 'suspended' && r.visibleState === 'running',
    r.hiddenState + ' / ' + r.hiddenAfterResumeAll + ' / ' + r.visibleState);
  check('a game pause survives the tab being hidden and shown again', r.stillPaused === 'suspended', r.stillPaused);
  check('main thread blocked 600 ms: music carries on, nothing is scheduled in the past, late notes are dropped or joined (not bunched)',
    r.block.state === 'running' && r.block.inPast === 0 && r.block.scheduled > 0 && (r.block.missed + r.block.late) > 0,
    'dropped ' + r.block.missed + ', joined late ' + r.block.late + ', then scheduled ' + r.block.scheduled + ', max look-ahead used ' + (r.block.maxLead * 1000).toFixed(0) + ' ms');
  check('effect spam (' + r.spam.calls + ' calls in 6 s): live effects and nodes capped, everything freed afterwards', r.spam.peakLive <= 24 && r.spam.peakNodes < 1000 && r.spam.leftLive === 0 && r.spam.leftVoices === 0 && r.spam.leftNodes === 0 && r.spam.errors.length === 0,
    'peak ' + r.spam.peakLive + ' effects / ' + r.spam.peakNodes + ' nodes; left ' + r.spam.leftLive + '/' + r.spam.leftVoices + '/' + r.spam.leftNodes);
}

async function testVoice(browser) {
  console.log('\n[5] playVoice');
  const mp3 = path.join(HERE, 'voice_test.mp3');
  if (!fs.existsSync(mp3)) {
    cp.execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.45',
      '-af', 'afade=t=in:d=0.02,afade=t=out:st=0.4:d=0.05,volume=0.5', '-ac', '1', '-ar', '22050', '-b:a', '32k', mp3]);
  }
  const uri = 'data:audio/mpeg;base64,' + fs.readFileSync(mp3).toString('base64');
  const page = await open(browser);
  const r = await page.evaluate(async (uri) => {
    const A = window.MB.Audio, wait = (ms) => new Promise((res) => setTimeout(res, ms)), out = {};
    const tapLevel = () => { const a = A._test.tap(), b = new Float32Array(a.fftSize); a.getFloatTimeDomainData(b); let s = 0; for (let j = 0; j < b.length; j++) s += b[j] * b[j]; return Math.sqrt(s / b.length); };
    let calls;
    const cb = (tag) => (done) => { calls.push([tag, done, Math.round(performance.now())]); };
    // locked, with assets present
    window.MB_ASSETS = { audio: { 'voice/test1': uri, 'voice/test2': uri, 'voice/bad': 'data:audio/mpeg;base64,' + btoa('this is not an mp3 file at all, sorry........') } };
    calls = []; out.locked = A.playVoice('test1', cb('locked')); out.lockedDur = A.voiceDuration('test1');
    A.unlock(); await wait(300);
    // MB_ASSETS undefined
    const keep = window.MB_ASSETS; window.MB_ASSETS = undefined;
    out.noAssets = A.playVoice('test1', cb('noAssets')); out.noAssetsDur = A.voiceDuration('test1');
    window.MB_ASSETS = {}; out.noAudioMap = A.playVoice('test1', cb('noAudioMap'));
    window.MB_ASSETS = keep;
    out.unknown = A.playVoice('nope', cb('unknown')); out.unknownDur = A.voiceDuration('nope');
    await wait(400); out.callsForFalse = calls.length;
    // normal play
    calls = []; out.durBefore = A.voiceDuration('test1');
    const t0 = performance.now(); out.play = A.playVoice('test1', cb('a')); out.voiceId = A.debugInfo().voice;
    let lv = 0; for (let i = 0; i < 16; i++) { await wait(40); lv = Math.max(lv, tapLevel()); }
    await wait(600);
    out.playCalls = calls.slice(0); out.playElapsed = calls.length ? calls[0][2] - t0 : -1; out.level = lv; out.durAfter = A.voiceDuration('test1'); out.voiceIdAfter = A.debugInfo().voice;
    // stop in the middle (clip is cached now)
    calls = []; out.play2 = A.playVoice('test1', cb('b')); await wait(120); A.stopVoice(); const n1 = calls.length; A.stopVoice(); await wait(700);
    out.stopCalls = calls.slice(0); out.stopSync = n1;
    // a second voice replaces the first
    calls = []; out.play3 = A.playVoice('test1', cb('c1')); await wait(60); out.play4 = A.playVoice('test2', cb('c2')); await wait(1100);
    out.replaceCalls = calls.slice(0);
    // undecodable data
    calls = []; out.bad = A.playVoice('bad', cb('bad')); await wait(500); out.badCalls = calls.slice(0); out.badAgain = A.playVoice('bad', cb('bad2')); await wait(200); out.badCalls2 = calls.length;
    // paused in the middle: finishes after resume
    calls = []; out.play5 = A.playVoice('test1', cb('p')); await wait(100); A.pauseAll(); await wait(900); out.pausedCalls = calls.length; A.resumeAll(); await wait(900);
    out.pauseCalls = calls.slice(0);
    // no callback at all
    out.noCb = A.playVoice('test1'); await wait(800);
    // voice volume
    A.setVolume('voice', 0); await wait(200); calls = []; A.playVoice('test1', cb('m')); let lm = 0; for (let i = 0; i < 12; i++) { await wait(40); lm = Math.max(lm, tapLevel()); } out.mutedLevel = lm; A.setVolume('voice', 1);
    await wait(500);
    const d = A.debugInfo(); out.errors = d.errors; out.leftVoice = d.voice;
    return out;
  }, uri);
  results.voice = r;
  check('playVoice before unlock returns false and never calls onEnd', r.locked === false && r.lockedDur === 0, '');
  check('playVoice returns false when MB_ASSETS is undefined, has no audio map, or the id is unknown; onEnd never called',
    r.noAssets === false && r.noAudioMap === false && r.unknown === false && r.callsForFalse === 0 && r.unknownDur === 0 && r.noAssetsDur === 0, JSON.stringify([r.noAssets, r.noAudioMap, r.unknown, r.callsForFalse]));
  check('playVoice with a test MP3 data URI returns true and calls onEnd(true) exactly once', r.play === true && r.playCalls.length === 1 && r.playCalls[0][1] === true,
    JSON.stringify(r.playCalls.map((c) => c.slice(0, 2))) + ' after ' + r.playElapsed + ' ms');
  check('the clip is audible on the voice bus and took about its own length', r.level > 0.02 && r.playElapsed > 350 && r.playElapsed < 1200, 'tap rms ' + f3(r.level) + ', ' + r.playElapsed + ' ms');
  check('voiceDuration: 0 before decoding, the clip length after', r.durBefore === 0 && r.durAfter > 0.4 && r.durAfter < 0.7, r.durBefore + ' -> ' + f3(r.durAfter) + ' s');
  check('debugInfo().voice names the playing clip, then null', r.voiceId === 'test1' && r.voiceIdAfter === null, r.voiceId + ' -> ' + r.voiceIdAfter);
  check('stopVoice() calls onEnd(false) exactly once (synchronously); a second stopVoice() does nothing', r.play2 === true && r.stopSync === 1 && r.stopCalls.length === 1 && r.stopCalls[0][1] === false, JSON.stringify(r.stopCalls.map((c) => c.slice(0, 2))));
  check('only one voice at a time: a new clip ends the old one with onEnd(false), then finishes with onEnd(true)',
    r.replaceCalls.length === 2 && r.replaceCalls[0][0] === 'c1' && r.replaceCalls[0][1] === false && r.replaceCalls[1][0] === 'c2' && r.replaceCalls[1][1] === true, JSON.stringify(r.replaceCalls.map((c) => c.slice(0, 2))));
  check('undecodable data: queued (true), then onEnd(false) once; false from then on', r.bad === true && r.badCalls.length === 1 && r.badCalls[0][1] === false && r.badAgain === false && r.badCalls2 === 1, JSON.stringify([r.bad, r.badCalls.map((c) => c.slice(0, 2)), r.badAgain]));
  check('a clip paused by pauseAll() finishes after resumeAll() with onEnd(true)', r.pausedCalls === 0 && r.pauseCalls.length === 1 && r.pauseCalls[0][1] === true, JSON.stringify(r.pauseCalls.map((c) => c.slice(0, 2))));
  check('playVoice without a callback works; setVolume("voice", 0) silences the clip', r.noCb === true && r.mutedLevel < 0.001, 'muted tap rms ' + f3(r.mutedLevel));
  check('voice: nothing left over, no errors caught', r.leftVoice === null && r.errors.length === 0, r.errors.slice(0, 2).join(' | '));
  const errs = await pageErrors(page);
  check('zero console errors (voice page)', errs.length === 0, errs.slice(0, 3).join(' | '));
  await page.close();
}

async function calibrate(page) {
  console.log('Calibration (paste into js/audio.js)\n');
  const cal = await page.evaluate(async (names) => {
    const A = window.MB.Audio._test, T = window.MBT, out = { sfx: {}, music: {} };
    out.makeup = await T.compGain(0.02);
    const unity = { master: 1, music: 1, sfx: 1, voice: 1 };
    for (const n of names) {
      const info = A.sfxInfo(n);
      const r = await A.render({ seconds: info.len + 0.25, raw: true, vols: unity, sfx: [{ name: n, at: 0 }] });
      const st = T.stats(r.buffer);
      out.sfx[n] = { peak: st.peak, rms: st.activeRms, secs: st.activeSeconds, len: info.len };
    }
    for (const t of A.tracks()) { const st = await T.trackFull(t, {}); out.music[t] = { peak: st.peak, rms: st.rms, rmsDb: st.rmsDb, aRms: st.aRms, aRmsDb: st.aRmsDb, lf150: st.lf150, hf8: st.hf8 }; }
    return out;
  }, SPEC_SFX);
  console.log('  var COMP_TRIM = ' + (1 / cal.makeup).toFixed(3) + ';      // 1 / make-up gain (x' + cal.makeup.toFixed(3) + ')\n');
  let s = '  var SFX_CAL = {\n', line = '   ';
  SPEC_SFX.forEach((n, i) => {
    const item = ' ' + n + ': ' + cal.sfx[n].peak.toFixed(3) + (i < SPEC_SFX.length - 1 ? ',' : '');
    if ((line + item).length > 118) { s += line + '\n'; line = '   '; }
    line += item;
  });
  s += line + '\n  };';
  console.log(s + '\n');
  if (ARGV.includes('--write')) {
    const file = path.join(HERE, '..', '..', 'js', 'audio.js');
    let src = fs.readFileSync(file, 'utf8');
    const a = src.indexOf('  var SFX_CAL = {'), b = src.indexOf('};', a);
    const trimRe = /var COMP_TRIM = [\d.]+;/;
    if (a < 0 || b < 0 || !trimRe.test(src)) throw new Error('SFX_CAL / COMP_TRIM not found in js/audio.js');
    src = src.slice(0, a) + s + src.slice(b + 2);
    src = src.replace(trimRe, 'var COMP_TRIM = ' + (1 / cal.makeup).toFixed(3) + ';');
    fs.writeFileSync(file, src);
    console.log('  written to js/audio.js\n');
  }
  console.log('  music at default volumes, whole loop (current gains):');
  for (const t of Object.keys(cal.music)) {
    const m = cal.music[t];
    console.log('   ' + t.padEnd(8) + ' peak ' + f3(m.peak) + '  rms ' + f3(m.rms) + ' (' + f1(m.rmsDb) + ' dB)  A-weighted ' + f1(m.aRmsDb) + ' dB  <150Hz ' + pct(m.lf150) + '  >8k ' + pct(m.hf8) +
      '   x' + (0.0891 / m.rms).toFixed(2) + ' -> rms -21 dB;  x' + (0.0562 / m.aRms).toFixed(2) + ' -> A-weighted -25 dB');
  }
}

(async () => {
  const browser = await launch(AUTOPLAY);
  console.log('Chromium ' + browser.version() + ', page ' + PAGE);
  if (CALIBRATE) {
    const page = await open(browser);
    await calibrate(page);
    await browser.close();
    return;
  }
  await testApi(browser);
  await testAutoplayPolicy(browser);
  const page = await open(browser);
  await testOffline(page);
  await testSeams(page);
  if (!QUICK) await testRealtime(page); else console.log('\n[4] realtime scheduler: SKIPPED (--quick)');
  const errs = await pageErrors(page);
  check('zero console errors (offline / seam / realtime page)', errs.length === 0, errs.slice(0, 3).join(' | '));
  await page.close();
  await testVoice(browser);
  await browser.close();

  results.finished = new Date().toISOString();
  results.failed = failed; results.total = results.checks.length;
  fs.writeFileSync(path.join(HERE, 'results.json'), JSON.stringify(results, null, 1));
  console.log('\n' + (results.total - failed) + ' of ' + results.total + ' checks passed' + (QUICK ? ' (realtime section skipped)' : '') + '. Details: tools/audio_test/results.json');
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('test run crashed:', e); process.exit(2); });
