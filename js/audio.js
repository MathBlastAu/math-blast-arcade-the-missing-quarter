/* Math Blast Arcade - audio engine (window.MB.Audio)
 *
 * Everything you hear is synthesised at run time with the Web Audio API:
 * seven original music loops, every sound effect, and the voice bus that
 * plays the (optional) base64 MP3 story lines from MB_ASSETS.
 * No samples, no libraries, no network: works from file://.
 * The brief is js/AUDIO_SPEC.md; the tests are in tools/audio_test.
 *
 * Layout of this file
 *   1. utilities + music theory helpers
 *   2. rig      : bus graph built on ANY BaseAudioContext (realtime or offline)
 *   3. voices   : synth instruments (lead, pluck, bass, pad, bell, flute, drums)
 *   4. tracks   : the compositions, as data
 *   5. compiler : track data -> flat, time-sorted event lists
 *   6. player   : one playing track; schedules by absolute beat (cannot drift)
 *   7. sfx      : layered, level-matched sound effects
 *   8. engine   : the realtime context, look-ahead timer, pause, voice clips
 *   9. public API + test hooks (MB.Audio._test)
 *
 * Notes for whoever calls this
 *   - Nothing here throws, with or without Web Audio. Before unlock() every
 *     call is safe; playMusic() is remembered and starts once sound is allowed,
 *     effects and voice clips asked for before that are simply not played.
 *   - unlock() must be called from a user gesture. If it was called too early,
 *     the engine finishes the job itself on the next key press / tap, and it
 *     also recovers there from interruptions (phone call, iOS tab switch).
 *   - pauseAll() suspends the whole context, so effects requested while paused
 *     are dropped (they would all sound at once on resume). An effect started
 *     just before pauseAll() is allowed to ring out (up to 0.35 s), and
 *     sfx('unpause') immediately followed by resumeAll() is heard. For a pause
 *     MENU with its own sounds, use duck() instead of pauseAll().
 *   - A hidden tab is suspended automatically and resumed when visible again
 *     (unless the game itself is paused).
 *   - Volumes are plain linear gains (0..1). Defaults: master 0.8, music 0.6,
 *     sfx 0.8, voice 1.0. At the defaults the music sits near -21 dBFS RMS and
 *     effects peak between -20 and -8 dBFS; a limiter guards the output.
 *   - The pitched jingles (chip, correct, whole, quarterGet, the UI blips...)
 *     are written in C and transposed to the key of the track that is
 *     playing, so they never clash with the music. opts.pitch adds to that.
 *   - playVoice() returns false (and never calls onEnd) when there is no clip
 *     for the id, when MB_ASSETS is missing, or when sound is not unlocked.
 *   - unlock() returns true once sound is actually running; the first call
 *     may return false and isUnlocked() turns true a moment later.
 */
(function () {
  'use strict';

  var root = (typeof window !== 'undefined') ? window
    : (typeof globalThis !== 'undefined') ? globalThis
    : (typeof self !== 'undefined') ? self : {};
  var MB = root.MB = root.MB || {};
  if (MB.Audio && MB.Audio._test) return;            // script included twice: keep the first engine

  // --------------------------------------------------------------------------
  // 1. utilities
  // --------------------------------------------------------------------------
  var PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  var warnings = [];

  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function mtof(m) { return 440 * Math.pow(2, (m - 69) / 12); }
  function semis(s) { return Math.pow(2, s / 12); }
  function num(v, dflt) { return (typeof v === 'number' && isFinite(v)) ? v : dflt; }

  // "F#5" -> 78
  function noteNum(name) {
    var m = /^([A-G])([#b]?)(-?\d)$/.exec(name);
    if (!m) { warnings.push('bad note ' + name); return 60; }
    return 12 * (parseInt(m[3], 10) + 1) + PC[m[1]] + (m[2] === '#' ? 1 : (m[2] === 'b' ? -1 : 0));
  }

  var QUAL = {
    '': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'maj7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10],
    'sus4': [0, 5, 7], 'sus2': [0, 2, 7], 'add9': [0, 4, 7, 14], 'dim': [0, 3, 6], '5': [0, 7]
  };
  var chordCache = {};
  // "F#m7/E" -> { root: pitch class, iv: intervals, bass: pitch class }
  function parseChord(sym) {
    if (chordCache[sym]) return chordCache[sym];
    var m = /^([A-G])([#b]?)([a-z0-9]*)(?:\/([A-G])([#b]?))?$/.exec(sym);
    var c;
    if (!m || !QUAL[m[3]]) {
      warnings.push('bad chord ' + sym);
      c = { sym: sym, root: 0, iv: QUAL[''], bass: 0 };
    } else {
      var r = (PC[m[1]] + (m[2] === '#' ? 1 : (m[2] === 'b' ? 11 : 0))) % 12;
      var b = m[4] ? (PC[m[4]] + (m[5] === '#' ? 1 : (m[5] === 'b' ? 11 : 0))) % 12 : r;
      c = { sym: sym, root: r, iv: QUAL[m[3]], bass: b };
    }
    chordCache[sym] = c;
    return c;
  }
  // put a pitch class into the octave window [lo, lo + 12)
  function inWindow(pc, lo) { return lo + ((pc - lo) % 12 + 12) % 12; }
  // Close voicing inside one fixed octave window: every pitch class has exactly
  // one home, so successive chords move by the smallest possible steps.
  function voicing(ch, lo) {
    var out = [], seen = {}, i, n;
    for (i = 0; i < ch.iv.length; i++) {
      n = inWindow(ch.root + ch.iv[i], lo);
      if (!seen[n]) { seen[n] = 1; out.push(n); }
    }
    out.sort(function (a, b) { return a - b; });
    return out;
  }

  // deterministic noise so offline renders are repeatable
  function makeNoise(ctx, seconds) {
    var len = Math.floor(ctx.sampleRate * seconds);
    var buf = ctx.createBuffer(1, len, ctx.sampleRate);
    var d = buf.getChannelData(0), s = 22222, i;
    for (i = 0; i < len; i++) {
      s = (s * 16807) % 2147483647;
      d[i] = s / 1073741823.5 - 1;
    }
    return buf;
  }

  // band-limited pulse wave with a soft top end (duty 0.5 = square)
  function makePulse(ctx, duty, harmonics) {
    if (!ctx.createPeriodicWave) return null;
    var re = new Float32Array(harmonics + 1), im = new Float32Array(harmonics + 1), n;
    for (n = 1; n <= harmonics; n++) {
      re[n] = (2 / (n * Math.PI)) * Math.sin(n * Math.PI * duty) / (1 + Math.pow(n / 16, 2));
    }
    try { return ctx.createPeriodicWave(re, im); } catch (e) { return null; }
  }
  function makeSoftSaw(ctx, harmonics) {
    if (!ctx.createPeriodicWave) return null;
    var re = new Float32Array(harmonics + 1), im = new Float32Array(harmonics + 1), n;
    for (n = 1; n <= harmonics; n++) im[n] = (1 / n) / (1 + Math.pow(n / 12, 2));
    try { return ctx.createPeriodicWave(re, im); } catch (e) { return null; }
  }

  // --------------------------------------------------------------------------
  // 2. rig: the bus graph. Works on AudioContext and OfflineAudioContext alike.
  //    players -> music -> duck -> hold -+
  //    effects -> sfxIn -> low-pass -> sfx -+-> master -> compressor -> trim -> soft clip -> destination
  //    clips   -> voice --------------------+
  //    (music/sfx/voice/master carry the four user volumes, duck is duck(),
  //     hold mutes the music for pauseAll())
  // --------------------------------------------------------------------------
  var DEFAULT_VOL = { master: 0.8, music: 0.6, sfx: 0.8, voice: 1.0 };
  // The browser compressor adds automatic make-up gain; COMP_TRIM takes it back
  // out so quiet material passes at unity (measured in tools/audio_test).
  var COMP = { threshold: -6, knee: 4, ratio: 12, attack: 0.003, release: 0.15 };
  var COMP_TRIM = 0.745;
  var SFX_TOP = 7500;            // every effect passes one shared low-pass at this frequency

  var clipCurve = null;
  function softClipCurve() {
    var n = 4097, i, x, a, z, e;
    if (clipCurve) return clipCurve;
    clipCurve = new Float32Array(n);
    for (i = 0; i < n; i++) {
      x = i / (n - 1) * 2 - 1; a = Math.abs(x);
      if (a > 0.7) { z = (a - 0.7) / 0.25; e = Math.exp(2 * z); a = 0.7 + 0.25 * (e - 1) / (e + 1); }
      clipCurve[i] = x < 0 ? -a : a;
    }
    return clipCurve;
  }

  // A fader is an AudioParam plus a model of its last ramp, so that a new ramp
  // can start from the true current value on every browser. Only linear ramps
  // are used: they are computed from the clock, whereas Chrome advances
  // setTargetAtTime only while the node is being processed (an idle bus would
  // lag behind and be heard catching up when the next sound starts).
  function Fader(param, v) { this.p = param; this.from = v; this.to = v; this.t0 = 0; this.t1 = 0; param.value = v; }
  Fader.prototype.at = function (t) {
    if (t >= this.t1) return this.to;
    if (t <= this.t0) return this.from;
    return this.from + (this.to - this.from) * (t - this.t0) / (this.t1 - this.t0);
  };
  Fader.prototype.go = function (v, t, secs) {
    var cur = this.at(t);
    secs = Math.max(0.005, secs);
    try { this.p.cancelScheduledValues(t); } catch (e) { /* ok */ }
    this.p.setValueAtTime(cur, t);
    this.p.linearRampToValueAtTime(v, t + secs);
    this.from = cur; this.to = v; this.t0 = t; this.t1 = t + secs;
  };

  function createRig(ctx, vols, opts) {
    opts = opts || {};
    var rig = { ctx: ctx, active: 0, nodes: 0, sfxLive: 0, dup: 0, rec: null, dry: false, seed: 1, sink: null };
    rig.master = ctx.createGain();
    rig.master.gain.value = vols.master;
    var comp = null;
    if (opts.limiter !== false && ctx.createDynamicsCompressor) {
      try {
        comp = ctx.createDynamicsCompressor();
        comp.threshold.value = COMP.threshold; comp.knee.value = COMP.knee; comp.ratio.value = COMP.ratio;
        comp.attack.value = COMP.attack; comp.release.value = COMP.release;
      } catch (e) { comp = null; }
    }
    if (comp) {
      rig.comp = comp;
      rig.trim = ctx.createGain();
      rig.trim.gain.value = num(opts.trim, COMP_TRIM);
      rig.master.connect(comp); comp.connect(rig.trim);
      rig.out = rig.trim;
      // safety net after the limiter: exactly linear up to 0.7, then a soft
      // knee that can never exceed 0.91, so the output cannot hard-clip
      if (ctx.createWaveShaper) {
        try {
          rig.clip = ctx.createWaveShaper();
          rig.clip.curve = softClipCurve();
          rig.trim.connect(rig.clip);
          rig.out = rig.clip;
        } catch (e2) { rig.clip = null; rig.out = rig.trim; }
      }
      rig.out.connect(ctx.destination);
    } else {
      rig.out = rig.master;
      rig.master.connect(ctx.destination);
    }
    rig.music = ctx.createGain(); rig.music.gain.value = vols.music;
    rig.duck = ctx.createGain(); rig.duck.gain.value = 1;
    rig.hold = ctx.createGain(); rig.hold.gain.value = 1;
    rig.music.connect(rig.duck); rig.duck.connect(rig.hold); rig.hold.connect(rig.master);
    rig.sfx = ctx.createGain(); rig.sfx.gain.value = vols.sfx; rig.sfx.connect(rig.master);
    rig.sfxIn = ctx.createGain();
    rig.sfxLp = mkFilter(ctx, 'lowpass', SFX_TOP, 0.5);
    rig.sfxIn.connect(rig.sfxLp); rig.sfxLp.connect(rig.sfx);
    rig.voice = ctx.createGain(); rig.voice.gain.value = vols.voice; rig.voice.connect(rig.master);
    rig.fade = {
      master: new Fader(rig.master.gain, vols.master), music: new Fader(rig.music.gain, vols.music),
      sfx: new Fader(rig.sfx.gain, vols.sfx), voice: new Fader(rig.voice.gain, vols.voice),
      duck: new Fader(rig.duck.gain, 1), hold: new Fader(rig.hold.gain, 1)
    };
    rig.noise = makeNoise(ctx, 2);
    rig.waves = {
      pulse50: makePulse(ctx, 0.5, 24),
      pulse25: makePulse(ctx, 0.25, 24),
      pulse12: makePulse(ctx, 0.125, 24),
      softsaw: makeSoftSaw(ctx, 24)
    };
    return rig;
  }

  function mkOsc(rig, wave, freq) {
    var o = rig.ctx.createOscillator();
    if (wave === 'sine' || wave === 'triangle' || wave === 'square' || wave === 'sawtooth') {
      o.type = wave;
    } else if (rig.waves[wave]) {
      o.setPeriodicWave(rig.waves[wave]);
    } else {
      o.type = (wave === 'softsaw') ? 'sawtooth' : 'square';
    }
    o.frequency.value = freq;
    return o;
  }
  function mkNoise(rig, t, dur) {
    var s = rig.ctx.createBufferSource();
    s.buffer = rig.noise;
    s.loop = true;
    rig.seed = (rig.seed * 73 + 19) % 997;
    s.start(t, (rig.seed / 997) * 1.5);
    s.stop(t + dur);
    return s;
  }
  function mkFilter(ctx, type, freq, q) {
    var f = ctx.createBiquadFilter();
    f.type = type; f.frequency.value = freq; f.Q.value = num(q, 0.7);
    return f;
  }
  function mkPan(ctx, pan) {
    if (!pan || !ctx.createStereoPanner) return null;
    var p = ctx.createStereoPanner();
    p.pan.value = clamp(pan, -1, 1);
    return p;
  }
  // ADSR on a gain AudioParam. Returns the time at which the source may stop.
  function adsr(g, t, peak, a, d, s, dur, r) {
    g.setValueAtTime(0, t);
    g.linearRampToValueAtTime(peak, t + a);
    g.setTargetAtTime(peak * s, t + a, d / 3);
    var tr = Math.max(t + a + 0.004, t + dur);
    g.setTargetAtTime(0, tr, r / 4);
    return tr + r * 1.7;
  }
  // percussive envelope: fast attack then exponential fall
  function perc(g, t, peak, a, tau) {
    g.setValueAtTime(0, t);
    g.linearRampToValueAtTime(peak, t + a);
    g.setTargetAtTime(0, t + a, tau);
    return t + a + tau * 7;
  }
  // Bookkeeping for one voice: `srcs` is its source node, or a list of its
  // sources (entries may be null) with the one that ends the voice first.
  // When that source ends the voice is freed (its tail node is disconnected).
  // `sess` is the sound-effect session the voice belongs to, if any. While
  // rig.sink is set (a Player is scheduling), the voice is also listed there
  // so the Player can stop its voices early when it is disposed.
  function track(rig, srcs, tail, n, sess) {
    var src = srcs.length ? srcs[0] : srcs, v = null, over = false;
    rig.active++; rig.nodes += n;
    if (sess) sess.live++;
    if (rig.sink) { v = { srcs: srcs.length ? srcs : [src], over: false }; rig.sink.push(v); }
    src.onended = function () {
      // Chromium sometimes delivers "ended" more than once for a looping
      // buffer source (seen under load): count each voice out exactly once
      if (over) { rig.dup++; return; }
      over = true;
      if (v) v.over = true;
      src.onended = null;
      rig.active--; rig.nodes -= n;
      try { tail.disconnect(); } catch (e) { /* already gone */ }
      if (sess && --sess.live === 0 && sess.onDone) sess.onDone();
    };
  }
  // high notes are turned down a little so nothing gets piercing
  function tame(f) { return f > 700 ? Math.pow(700 / f, 0.45) : 1; }

  // --------------------------------------------------------------------------
  // 3. voices
  // --------------------------------------------------------------------------
  var VOICE = {};

  // pulse lead with a detuned twin, delayed vibrato and a low-pass
  VOICE.lead = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi), n = 3;
    var g = ctx.createGain();
    var lp = mkFilter(ctx, 'lowpass', Math.min(num(o.lp, 3200), f * 5 + 600), 0.6);
    var osc = mkOsc(rig, o.wave || 'pulse25', f), osc2 = null, lfo = null;
    osc.connect(lp);
    if (o.det) {
      osc2 = mkOsc(rig, o.wave2 || o.wave || 'pulse25', f * num(o.ratio2, 1));
      osc2.detune.value = o.det;
      var g2 = ctx.createGain(); g2.gain.value = num(o.mix2, 0.5);
      osc2.connect(g2); g2.connect(lp); n += 2;
    }
    if (o.vib && dur > 0.24) {
      lfo = ctx.createOscillator(); lfo.frequency.value = num(o.vibRate, 5.6);
      var lg = ctx.createGain();
      lg.gain.value = 0;
      lg.gain.setValueAtTime(0, t + 0.11);
      lg.gain.linearRampToValueAtTime(f * 0.0058 * o.vib, t + 0.32);
      lfo.connect(lg); lg.connect(osc.frequency);
      if (osc2) lg.connect(osc2.frequency);
      n += 2;
    }
    lp.connect(g); g.connect(out);
    var end = adsr(g.gain, t, vel * num(o.vol, 1) * tame(f), num(o.a, 0.008), num(o.d, 0.14), num(o.s, 0.7), dur, num(o.r, 0.09));
    osc.start(t); osc.stop(end);
    if (osc2) { osc2.start(t); osc2.stop(end); }
    if (lfo) { lfo.start(t); lfo.stop(end); }
    track(rig, [osc, osc2, lfo], g, n);
  };

  // plucked arp: filter snaps shut behind a quick decay
  VOICE.pluck = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi);
    var g = ctx.createGain();
    var top = Math.min(num(o.lp, 3800), f * 6 + 500);
    var lp = mkFilter(ctx, 'lowpass', top, 1.2);
    lp.frequency.setValueAtTime(top, t);
    lp.frequency.setTargetAtTime(Math.max(500, f * 1.5), t + 0.005, num(o.tau, 0.09) * 0.8);
    var osc = mkOsc(rig, o.wave || 'pulse12', f);
    osc.connect(lp); lp.connect(g); g.connect(out);
    var tau = num(o.tau, 0.09) * (dur > 0.3 ? 1.6 : 1);
    var end = perc(g.gain, t, vel * num(o.vol, 1) * tame(f), 0.004, tau);
    osc.start(t); osc.stop(end);
    track(rig, osc, g, 3);
  };

  // synth bass: soft saw through an enveloped low-pass plus a triangle an
  // octave up. The filter settles around the 5th harmonic and the octave layer
  // keeps the line readable on laptop and phone speakers, which cannot
  // reproduce the fundamental.
  VOICE.bass = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi);
    var g = ctx.createGain();
    var open = num(o.lp, 700) * (1 + 0.35 * num(o.drive, 0));
    var lp = mkFilter(ctx, 'lowpass', open, num(o.q, 1.5));
    lp.frequency.setValueAtTime(open, t);
    lp.frequency.setTargetAtTime(Math.max(330, f * 5), t + 0.01, 0.14);
    var osc = mkOsc(rig, o.wave || 'softsaw', f);
    var sub = mkOsc(rig, 'triangle', f * 2);
    var sg = ctx.createGain(); sg.gain.value = num(o.oct, 0.4);
    osc.connect(lp); lp.connect(g); sub.connect(sg); sg.connect(g); g.connect(out);
    var end = adsr(g.gain, t, vel * num(o.vol, 1), 0.006, 0.16, num(o.s, 0.6), dur, 0.06);
    osc.start(t); osc.stop(end); sub.start(t); sub.stop(end);
    track(rig, [osc, sub], g, 5);
  };

  // round bass for the gentle tracks: triangle, a quieter triangle an octave
  // up and a dark soft-saw layer (something for small speakers to play)
  VOICE.softbass = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi);
    var g = ctx.createGain();
    var osc = mkOsc(rig, 'triangle', f), sub = mkOsc(rig, 'triangle', f * 2), saw = mkOsc(rig, 'softsaw', f);
    var sg = ctx.createGain(); sg.gain.value = 0.3;
    var wg = ctx.createGain(); wg.gain.value = 0.4;
    var lp = mkFilter(ctx, 'lowpass', Math.max(400, f * 5), 0.6);
    osc.connect(g); sub.connect(sg); sg.connect(g); saw.connect(lp); lp.connect(wg); wg.connect(g); g.connect(out);
    var end = adsr(g.gain, t, vel * num(o.vol, 1), 0.012, 0.3, num(o.s, 0.75), dur, 0.12);
    osc.start(t); osc.stop(end); sub.start(t); sub.stop(end); saw.start(t); saw.stop(end);
    track(rig, [osc, sub, saw], g, 7);
  };

  // pad: two detuned saws per chord note, one shared low-pass that breathes
  VOICE.pad = function (rig, out, t, notes, dur, vel, o) {
    var ctx = rig.ctx, i, srcs = [];
    var g = ctx.createGain();
    var base = num(o.lp, 1100);
    var lp = mkFilter(ctx, 'lowpass', base * 0.6, 0.5);
    lp.frequency.setValueAtTime(base * 0.6, t);
    lp.frequency.linearRampToValueAtTime(base, t + Math.min(dur * 0.5, 1.2));
    lp.frequency.linearRampToValueAtTime(base * 0.7, t + dur);
    var det = num(o.det, 8);
    for (i = 0; i < notes.length; i++) {
      var a = mkOsc(rig, 'sawtooth', mtof(notes[i])), b = mkOsc(rig, 'sawtooth', mtof(notes[i]));
      a.detune.value = -det; b.detune.value = det;
      a.connect(lp); b.connect(lp); srcs.push(a, b);
    }
    lp.connect(g); g.connect(out);
    var peak = vel * num(o.vol, 1) / Math.sqrt(notes.length * 2);
    var att = Math.min(num(o.a, 0.25), dur * 0.4), rel = num(o.r, 0.5);
    var end = adsr(g.gain, t, peak, att, 0.4, 0.85, dur, rel);
    for (i = 0; i < srcs.length; i++) { srcs[i].start(t); srcs[i].stop(end); }
    track(rig, srcs, g, srcs.length + 2);
  };

  // bell: sine with two quieter, faster-fading partials
  VOICE.bell = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi);
    var g = ctx.createGain();
    var tau = num(o.tau, 0.55);
    var p1 = mkOsc(rig, 'sine', f), p2 = mkOsc(rig, 'sine', f * 2), p3 = mkOsc(rig, 'sine', f * 3.01);
    var g2 = ctx.createGain(), g3 = ctx.createGain();
    perc(g2.gain, t, 0.3, 0.003, tau * 0.45);
    perc(g3.gain, t, 0.12, 0.003, tau * 0.16);
    p1.connect(g); p2.connect(g2); g2.connect(g); p3.connect(g3); g3.connect(g); g.connect(out);
    var end = perc(g.gain, t, vel * num(o.vol, 1) * tame(f), 0.005, tau);
    end = Math.min(end, t + Math.max(dur, 0.2) + tau * 3.5);
    g.gain.setTargetAtTime(0, end - 0.12, 0.025);
    p1.start(t); p1.stop(end); p2.start(t); p2.stop(end); p3.start(t); p3.stop(end);
    track(rig, [p1, p2, p3], g, 6);
  };

  // airy lead for the Fraction Bridge: triangle + soft octave sine
  VOICE.flute = function (rig, out, t, midi, dur, vel, o) {
    var ctx = rig.ctx, f = mtof(midi), n = 4;
    var g = ctx.createGain();
    var osc = mkOsc(rig, 'triangle', f), oct = mkOsc(rig, 'sine', f * 2), lfo = null;
    var og = ctx.createGain(); og.gain.value = 0.18;
    osc.connect(g); oct.connect(og); og.connect(g); g.connect(out);
    if (dur > 0.3) {
      lfo = ctx.createOscillator(); lfo.frequency.value = 4.8;
      var lg = ctx.createGain();
      lg.gain.value = 0;
      lg.gain.setValueAtTime(0, t + 0.15);
      lg.gain.linearRampToValueAtTime(f * 0.005, t + 0.5);
      lfo.connect(lg); lg.connect(osc.frequency); n += 2;
    }
    var end = adsr(g.gain, t, vel * num(o.vol, 1) * tame(f), 0.03, 0.3, 0.8, dur, 0.18);
    osc.start(t); osc.stop(end); oct.start(t); oct.stop(end);
    if (lfo) { lfo.start(t); lfo.stop(end); }
    track(rig, [osc, oct, lfo], g, n);
  };

  // ---- drums ---------------------------------------------------------------
  var DRUM = {};
  // kick: a sine body that drops from ~165 Hz, plus a short mid "knock" so
  // the beat is still there on speakers with no bass
  DRUM.kick = function (rig, out, t, vel, o) {
    var ctx = rig.ctx, g = ctx.createGain(), kg = ctx.createGain();
    var osc = mkOsc(rig, 'sine', 150), knock = mkOsc(rig, 'triangle', 300);
    osc.frequency.setValueAtTime(num(o.f, 165), t);
    osc.frequency.exponentialRampToValueAtTime(50, t + 0.1);
    knock.frequency.setValueAtTime(340, t);
    knock.frequency.exponentialRampToValueAtTime(120, t + 0.04);
    perc(kg.gain, t, 0.6, 0.001, 0.014);
    osc.connect(g); knock.connect(kg); kg.connect(g); g.connect(out);
    var end = perc(g.gain, t, vel * 0.5, 0.002, num(o.tau, 0.065));
    osc.start(t); osc.stop(end); knock.start(t); knock.stop(end);
    track(rig, [osc, knock], g, 4);
  };
  DRUM.snare = function (rig, out, t, vel, o) {
    var ctx = rig.ctx, g = ctx.createGain();
    var nz = mkNoise(rig, t, 0.3);
    var bp = mkFilter(ctx, 'bandpass', num(o.f, 1900), 0.8);
    var ng = ctx.createGain();
    perc(ng.gain, t, 1.0, 0.001, num(o.tau, 0.06));
    var osc = mkOsc(rig, 'triangle', 190);
    osc.frequency.setValueAtTime(200, t);
    osc.frequency.exponentialRampToValueAtTime(140, t + 0.07);
    var og = ctx.createGain();
    perc(og.gain, t, 0.6, 0.001, 0.035);
    nz.connect(bp); bp.connect(ng); ng.connect(g); osc.connect(og); og.connect(g); g.connect(out);
    g.gain.value = vel;
    osc.start(t); osc.stop(t + 0.3);
    track(rig, [nz, osc], g, 6);
  };
  DRUM.hat = function (rig, out, t, vel, o) {
    var ctx = rig.ctx, g = ctx.createGain();
    var open = !!o.open, len = open ? 0.4 : 0.12;
    var nz = mkNoise(rig, t, len);
    var hp = mkFilter(ctx, 'highpass', 5200, 0.7);
    nz.connect(hp); hp.connect(g); g.connect(out);
    perc(g.gain, t, vel * 0.85, 0.001, open ? 0.07 : 0.022);
    track(rig, nz, g, 3);
  };
  DRUM.clap = function (rig, out, t, vel) {
    var ctx = rig.ctx, g = ctx.createGain();
    var nz = mkNoise(rig, t, 0.35);
    var bp = mkFilter(ctx, 'bandpass', 1300, 1.1);
    nz.connect(bp); bp.connect(g); g.connect(out);
    var p = g.gain, k;
    p.setValueAtTime(0, t);
    for (k = 0; k < 3; k++) {            // three quick bursts = many hands
      p.setValueAtTime(vel * 0.8, t + k * 0.011 + 0.0005);
      p.setTargetAtTime(vel * 0.15, t + k * 0.011 + 0.001, 0.004);
    }
    p.setTargetAtTime(0, t + 0.034, 0.045);
    track(rig, nz, g, 3);
  };
  DRUM.tom = function (rig, out, t, vel, o) {
    var ctx = rig.ctx, g = ctx.createGain();
    var f = num(o.f, 130);
    var osc = mkOsc(rig, 'sine', f);
    osc.frequency.setValueAtTime(f * 1.7, t);
    osc.frequency.exponentialRampToValueAtTime(f, t + 0.09);
    osc.connect(g); g.connect(out);
    var end = perc(g.gain, t, vel * 0.9, 0.002, 0.065);
    osc.start(t); osc.stop(end);
    track(rig, osc, g, 2);
  };
  // metallic clank: two inharmonic squares through a ringing band-pass
  DRUM.metal = function (rig, out, t, vel, o) {
    var ctx = rig.ctx, g = ctx.createGain();
    var f = num(o.f, 640);
    var a = mkOsc(rig, 'square', f), b = mkOsc(rig, 'square', f * 1.483);
    var bp = mkFilter(ctx, 'bandpass', f * 3.1, 4);
    a.connect(bp); b.connect(bp); bp.connect(g); g.connect(out);
    var end = perc(g.gain, t, vel * 0.5, 0.001, num(o.tau, 0.03));
    a.start(t); a.stop(end); b.start(t); b.stop(end);
    track(rig, [a, b], g, 4);
  };
  DRUM.rim = function (rig, out, t, vel) {
    var ctx = rig.ctx, g = ctx.createGain();
    var osc = mkOsc(rig, 'triangle', 820);
    var bp = mkFilter(ctx, 'bandpass', 1700, 2);
    osc.connect(bp); bp.connect(g); g.connect(out);
    var end = perc(g.gain, t, vel * 0.9, 0.001, 0.02);
    osc.start(t); osc.stop(end);
    track(rig, osc, g, 3);
  };
  DRUM.shaker = function (rig, out, t, vel) {
    var ctx = rig.ctx, g = ctx.createGain();
    var nz = mkNoise(rig, t, 0.25);
    var bp = mkFilter(ctx, 'bandpass', 4800, 1.2);
    nz.connect(bp); bp.connect(g); g.connect(out);
    perc(g.gain, t, vel * 0.8, 0.012, 0.03);
    track(rig, nz, g, 3);
  };

  // --------------------------------------------------------------------------
  // 4. tracks. All music is data.
  //
  // Notation
  //   chords : one symbol per bar, "F|G" = two chords sharing a bar
  //   lead   : one string per bar, tokens NOTE:LENGTH in 16th steps ("-" = rest);
  //            every bar adds up to 16
  //   arp    : 16 steps, digit = index into the chord's voicing ladder, "." rest
  //   bass   : 16 steps, r root, R root+8ve, f fifth, t third, s flat seventh,
  //            "-" holds the previous note, "." rest
  //   drums  : 16 steps per lane, X accent, x hit, o ghost, "." rest
  //            (hat lane: O = open hat; tom lane: h/m/l; metal lane: x/l)
  //   A lane may be { p: pattern, lo: n, hi: n } to exist only at some
  //   intensity levels (used by the boss fight).
  //   key    : semitones from C to the track's major scale (the relative major
  //            for minor keys); the pitched jingles among the sound effects are
  //            written in C and follow this, so they are always in key
  //
  // The game's leitmotif ("Jake's theme") is the rising cell
  //   so do re mi(long) so mi      e.g. G4 C5 D5 E5 . G5 E5 in C major.
  // It opens `title`, is hiccuped with rests in `dock`, floats past in `bridge`
  // and `zerog`, returns in `victory`, and is turned upside-down in E minor for
  // the Fraction Phantom in `boss`:  E6 B5 A5 G5 . E5 G5.
  // --------------------------------------------------------------------------
  var TRACKS = {};

  TRACKS.title = {
    bpm: 112, key: 0, gain: 0.86, delay: { beats: 0.75, fb: 0.3, wet: 0.5 },
    inst: {
      lead: ['lead', { wave: 'pulse25', det: 7, vib: 1, lp: 3000 }],
      arp: ['pluck', { wave: 'pulse12', lp: 3200 }],
      bass: ['bass', { lp: 750 }],
      pad: { lp: 1100 }
    },
    mix: { lead: 0.30, arp: 0.30, bass: 0.36, pad: 0.20, drums: 0.7 },
    send: { lead: 0.3, arp: 0.25 },
    sections: {
      A: {
        chords: 'C G Am F C Em F G',
        lead: [
          'G4:2 C5:2 D5:2 E5:6 G5:2 E5:2',
          'D5:6 B4:2 D5:4 G4:4',
          'A4:2 C5:2 D5:2 E5:6 A5:2 G5:2',
          'F5:6 E5:2 C5:8',
          'G4:2 C5:2 D5:2 E5:6 G5:2 C6:2',
          'B5:6 G5:2 E5:4 G5:4',
          'A5:4 G5:2 F5:6 A5:4',
          'G5:6 D5:2 B4:4 D5:4'
        ],
        arp: '0.1.2.3.2.1.2.1.',
        bass: 'r.r.r.r.r.r.r.R.',
        drums: { kick: 'X.......x.x.....', snare: '....x.......x...', hat: 'x.o.x.o.x.o.x.o.' },
        fill: { snare: '....x.......x.xx' }
      },
      A2: {
        chords: 'C G Am F C Em F|G C',
        lead: [
          'G4:2 C5:2 D5:2 E5:6 G5:2 E5:2',
          'D5:6 B4:2 D5:4 G4:4',
          'A4:2 C5:2 D5:2 E5:6 A5:2 G5:2',
          'F5:6 E5:2 C5:8',
          'G4:2 C5:2 D5:2 E5:6 G5:2 C6:2',
          'B5:6 G5:2 E5:4 G5:4',
          'A5:4 F5:4 G5:2 D5:2 B4:2 D5:2',
          'C5:2 E5:2 G5:2 C6:6 -:4'
        ],
        arp: '0213021302130213',
        bass: 'r.rRr.rRr.rRr.fR',
        drums: { kick: 'X.....x.x.x.....', snare: '....X.......X...', hat: 'x.xox.xox.xox.xo' },
        fill: { snare: '....X.....x.xxxx', tom: '..........h.m.l.' }
      },
      B: {
        chords: 'F G Em Am F G C G',
        lead: [
          'A5:6 G5:2 F5:4 C5:4',
          'B5:6 A5:2 G5:4 D5:4',
          'G5:2 E5:2 B4:2 E5:6 G5:4',
          'A5:8 E5:4 C5:4',
          'A5:6 G5:2 F5:4 A5:4',
          'B5:6 A5:2 G5:4 B5:4',
          'C6:6 G5:2 E5:4 G5:4',
          'G5:4 D5:4 G5:2 A5:2 B5:4'
        ],
        arp: '0.2.1.2.3.2.1.2.',
        bass: 'r-----r.f-----r.',
        drums: { kick: 'X.........x.....', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.O.', shaker: '..o...o...o...o.' },
        fill: { snare: '....x...x.x.xxxx' }
      }
    },
    form: ['A', 'A2', 'B', 'A2']
  };

  TRACKS.dock = {
    bpm: 120, key: 2, gain: 0.8, swing: 0.12, delay: { beats: 0.75, fb: 0.25, wet: 0.45 },
    inst: {
      lead: ['lead', { wave: 'pulse50', det: 5, vib: 0.8, lp: 2800, s: 0.6 }],
      arp: ['pluck', { wave: 'pulse25', lp: 3000, tau: 0.07 }],
      bass: ['bass', { lp: 800, s: 0.45 }],
      pad: { lp: 1000 }
    },
    mix: { lead: 0.24, arp: 0.30, bass: 0.36, pad: 0.17, drums: 0.7 },
    send: { lead: 0.25, arp: 0.3 },
    sections: {
      A: {
        chords: 'D D G G D Bm Em A',
        lead: [
          'A4:2 D5:2 E5:2 F#5:4 -:2 A5:2 F#5:2',
          'F#5:2 E5:2 D5:2 A4:4 -:2 D5:4',
          'B4:2 D5:2 E5:2 G5:4 -:2 B5:2 G5:2',
          'G5:2 A5:2 G5:2 D5:6 -:4',
          'A4:2 D5:2 E5:2 F#5:4 -:2 A5:2 D6:2',
          'B5:4 A5:2 F#5:4 -:2 D5:4',
          'G5:4 E5:2 G5:2 B5:4 G5:4',
          'A5:2 -:2 E5:2 -:2 C#5:2 E5:2 A5:4'
        ],
        arp: '..02..12..02..13',
        bass: 'r..r..f.r..r.Rf.',
        drums: { kick: 'X.....x.x.......', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', rim: '.......o......o.' },
        fill: { snare: '....x.......x.xx' }
      },
      A2: {
        chords: 'D D G G D Bm Em|A D',
        lead: [
          'A4:2 D5:2 E5:2 F#5:4 -:2 A5:2 F#5:2',
          'F#5:2 E5:2 D5:2 A4:4 -:2 D5:4',
          'B4:2 D5:2 E5:2 G5:4 -:2 B5:2 G5:2',
          'G5:2 A5:2 G5:2 D5:6 -:4',
          'A4:2 D5:2 E5:2 F#5:4 -:2 A5:2 D6:2',
          'B5:4 A5:2 F#5:4 -:2 D5:4',
          'G5:4 B5:4 A5:2 G5:2 E5:2 C#5:2',
          'D5:2 F#5:2 A5:2 D6:6 -:4'
        ],
        arp: '0.02.312.102.312',
        bass: 'r..r..f.r..r.Rf.',
        drums: { kick: 'X.....x.x..x....', snare: '....x.......x...', hat: 'x.xox.xox.xox.xo', clap: '............x...' },
        fill: { snare: '....x.....x.x.xx', tom: '.............h.l' }
      },
      B: {
        chords: 'G D Em Bm G D A A',
        lead: [
          'B5:4 D6:4 B5:2 A5:2 G5:4',
          'A5:6 F#5:2 D5:8',
          'G5:4 B5:4 G5:2 F#5:2 E5:4',
          'F#5:6 D5:2 B4:8',
          'B5:4 D6:4 B5:2 A5:2 G5:4',
          'A5:6 F#5:2 A5:4 D6:4',
          'C#6:4 B5:2 A5:2 E5:4 A5:4',
          'C#5:2 E5:2 F#5:2 G5:2 A5:2 C#6:2 -:4'
        ],
        arp: '0.1.2.1.3.1.2.1.',
        bass: 'r-----r.R---f.r.',
        drums: { kick: 'X.......x.x.....', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.O.' },
        fill: { snare: '....x...x...xxxx' }
      }
    },
    form: ['A', 'A2', 'B', 'A2']
  };

  TRACKS.bridge = {
    bpm: 104, key: -3, gain: 0.7, delay: { beats: 0.75, fb: 0.42, wet: 0.6 },
    inst: {
      lead: ['flute', {}],
      arp: ['pluck', { wave: 'triangle', lp: 4200, tau: 0.13 }],
      bass: ['softbass', {}],
      pad: { lp: 1300, a: 0.5, r: 0.8 }
    },
    mix: { lead: 0.34, arp: 0.28, bass: 0.34, pad: 0.28, drums: 0.8 },
    send: { lead: 0.4, arp: 0.45 },
    arpLo: 64,
    sections: {
      A: {
        chords: 'Dmaj7 A F#m7 E Dmaj7 A Bm7 E',
        lead: [
          'F#5:8 A5:4 C#6:4',
          'A5:2 B5:2 E5:12',
          'A5:8 C#6:4 E6:4',
          'B5:6 G#5:2 E5:8',
          'F#5:8 A5:4 C#6:4',
          'E6:6 C#6:2 A5:8',
          'D6:4 B5:4 F#5:4 A5:4',
          'G#5:6 B5:2 E5:8'
        ],
        arp: '0123432101234321',
        bass: 'r---------r-f---',
        drums: { kick: 'x.........o.....', rim: '....o.......o...', shaker: 'o.o.x.o.o.o.x.o.' }
      },
      B: {
        chords: 'F#m D A E F#m D E E',
        lead: [
          'C#6:8 A5:4 F#5:4',
          'F#5:4 A5:4 D6:8',
          'E5:2 A5:2 B5:2 C#6:6 E6:2 C#6:2',
          'B5:12 G#5:4',
          'C#6:8 A5:4 F#5:4',
          'F#5:4 A5:4 D6:6 E6:2',
          'E6:4 B5:4 G#5:4 B5:4',
          'G#5:8 E5:8'
        ],
        arp: '0.2.1.3.2.4.3.2.',
        bass: 'r-----r-R---f---',
        drums: { kick: 'x.......x.o.....', rim: '....x.......x...', shaker: 'o.o.x.o.o.o.x.o.', hat: '..............O.' }
      }
    },
    form: [{ s: 'A', mute: ['lead'] }, 'A', 'B', 'A']
  };

  TRACKS.reactor = {
    bpm: 126, key: 5, gain: 1.0, delay: { beats: 0.75, fb: 0.28, wet: 0.4 },
    inst: {
      lead: ['lead', { wave: 'pulse25', det: 9, vib: 0.7, lp: 2600, s: 0.6 }],
      arp: ['pluck', { wave: 'pulse25', lp: 2600, tau: 0.06 }],
      bass: ['bass', { lp: 900, q: 3, s: 0.5 }],
      pad: { lp: 900 }
    },
    mix: { lead: 0.30, arp: 0.28, bass: 0.38, pad: 0.2, drums: 0.64 },
    send: { lead: 0.25, arp: 0.2 },
    sections: {
      A: {
        chords: 'Dm Dm Bb C Dm Dm Gm A',
        lead: [
          'D5:2 -:1 D5:1 F5:2 D5:2 A5:3 G5:3 F5:2',
          'F5:2 E5:2 D5:4 -:2 A4:2 C5:2 D5:2',
          'D5:2 -:1 D5:1 F5:2 D5:2 Bb5:3 A5:3 F5:2',
          'G5:2 E5:2 C5:4 -:2 E5:2 G5:2 E5:2',
          'D5:2 -:1 D5:1 F5:2 A5:2 D6:3 C6:3 A5:2',
          'A5:2 G5:2 F5:4 -:2 D5:2 F5:2 A5:2',
          'Bb5:4 A5:2 G5:2 D5:4 G5:4',
          'A5:2 -:2 E5:2 -:2 C#5:2 E5:2 A5:2 C#6:2'
        ],
        arp: '0.0.2.0.1.0.2.0.',
        bass: 'r..r..r.r..r.rR.',
        drums: { kick: 'X...x...x...x...', snare: '....x.......x...', hat: '..x...x...x...x.', metal: 'x..x..l...x..l..' },
        fill: { snare: '....x.......x.xx', metal: 'x..x..l..xx.llxx' }
      },
      B: {
        chords: 'F C Gm Dm F C A A',
        lead: [
          'A5:6 F5:2 C5:4 F5:4',
          'G5:6 E5:2 C5:4 E5:4',
          'Bb5:6 G5:2 D5:4 G5:4',
          'A5:4 F5:4 D5:8',
          'A5:6 C6:2 A5:4 F5:4',
          'G5:6 C6:2 G5:4 E5:4',
          'E5:4 A5:4 C#6:4 E6:4',
          'E6:2 -:1 E6:1 C#6:2 A5:2 E5:4 -:4'
        ],
        arp: '0120312001203120',
        bass: 'r..r..r.R..r..f.',
        drums: { kick: 'X...x...x...x...', snare: '....x.......x...', hat: 'x.x.x.x.x.x.x.x.', metal: '..l...x...l..x..', clap: '....x.......x...' },
        fill: { snare: '....x...x.x.xxxx', metal: 'x.l.x.l.x.l.xlxl' }
      }
    },
    form: [{ s: 'A', mute: ['lead'] }, 'A', 'B', 'A']
  };

  TRACKS.zerog = {
    bpm: 92, key: 4, gain: 0.68, delay: { beats: 1.5, fb: 0.45, wet: 0.7 },
    inst: {
      lead: ['bell', { tau: 0.6 }],
      arp: ['pluck', { wave: 'sine', lp: 3000, tau: 0.22 }],
      bass: ['softbass', { s: 0.85 }],
      pad: { lp: 1250, a: 0.9, r: 1.2, det: 10 }
    },
    mix: { lead: 0.36, arp: 0.24, bass: 0.34, pad: 0.34, drums: 1.0 },
    send: { lead: 0.45, arp: 0.5 },
    arpLo: 64, padLo: 56,
    sections: {
      A: {
        chords: 'Emaj7 G#m7 Amaj7 Amaj7 Emaj7 C#m7 Amaj7 Bsus4',
        lead: [
          'B5:8 G#5:8',
          'D#6:12 B5:4',
          'C#6:8 E6:4 C#6:4',
          'G#5:12 -:4',
          'B5:8 E6:8',
          'G#5:4 B5:4 E6:8',
          'C#6:6 B5:2 A5:8',
          'F#5:8 B5:8'
        ],
        arp: '0...2...1...3...',
        bass: 'r-----------f---',
        drums: { kick: 'x...............', rim: '........o.......', shaker: '..o...o...o...o.' }
      },
      B: {
        chords: 'C#m7 Amaj7 Emaj7 Bsus4 C#m7 Amaj7 F#m7 B',
        lead: [
          'E6:8 B5:8',
          'C#6:6 E6:2 G#5:8',
          'B5:2 E6:2 F#6:2 G#6:6 -:4',
          'F#6:8 E6:8',
          'E6:8 G#5:8',
          'A5:4 C#6:4 E6:8',
          'A5:8 C#6:8',
          'D#6:8 B5:8'
        ],
        arp: '0.1.2.3.4.3.2.1.',
        bass: 'r-------R-----f-',
        drums: { kick: 'x.........o.....', rim: '........o.......', shaker: '..o...o...o...o.' }
      }
    },
    form: [{ s: 'A', mute: ['drums'] }, 'B', 'A', 'B']
  };

  TRACKS.boss = {
    bpm: 140, key: -5, gain: 0.84, delay: { beats: 0.75, fb: 0.25, wet: 0.35 },
    inst: {
      lead: ['lead', { wave: 'pulse25', det: 10, vib: 1, lp: 2900, s: 0.65 }],
      lead2: ['lead', { wave: 'pulse12', lp: 2200, s: 0.6 }],
      counter: ['lead', { wave: 'pulse50', lp: 1800, s: 0.7, a: 0.012 }],
      arp: ['pluck', { wave: 'pulse12', lp: 2800, tau: 0.05 }],
      bass: ['bass', { lp: 850, q: 2.5, s: 0.5 }],
      pad: { lp: 950 }
    },
    mix: { lead: 0.28, lead2: 0.15, counter: 0.14, arp: 0.34, bass: 0.38, pad: 0.19, drums: 0.64 },
    send: { lead: 0.22, arp: 0.2, counter: 0.15 },
    octave: { shift: -12, lo: 2 },
    sections: {
      A: {
        chords: 'Em Em C D Em Em C B',
        lead: [
          'E6:2 B5:2 A5:2 G5:6 E5:2 G5:2',
          'B5:2 C6:2 B5:2 G5:4 -:2 E5:2 G5:2',
          'E6:2 C6:2 B5:2 G5:6 E5:2 G5:2',
          'F#5:2 A5:2 D6:4 A5:2 C6:2 F#5:4',
          'E6:2 B5:2 A5:2 G5:6 E5:2 G5:2',
          'B5:2 C6:2 B5:2 G5:4 -:2 B5:2 E6:2',
          'G5:4 E5:2 G5:2 C6:4 E6:4',
          'D#6:2 -:2 B5:2 -:2 F#5:2 B5:2 D#6:4'
        ],
        counter: {
          lo: 1, lines: [
            'G4:6 B4:2 E5:8', 'E5:6 D5:2 B4:8', 'C5:6 E5:2 G4:8', 'A4:6 F#4:2 D5:8',
            'G4:6 B4:2 E5:8', 'G5:6 E5:2 B4:8', 'E5:6 C5:2 G4:8', 'F#4:6 B4:2 D#5:8'
          ]
        },
        arp: '0.2.1.2.0.2.1.2.',
        bass: 'r.rRr.rRr.rRr.rR',
        drums: {
          kick: 'X.....x.x.x.....', snare: '....X.......X...',
          hat: { p: 'x.x.x.x.x.x.x.x.', hi: 1 }, hat2: { p: 'xoxoxoxoxoxoxoxo', lo: 2 },
          clap: { p: '....x.......x...', lo: 1 }, tom: { p: '.......l......hm', lo: 1 }
        },
        fill: { snare: '....X.....x.xxxx' }
      },
      B: {
        chords: 'Am Em D B7 Am Em C B',
        lead: [
          'A5:2 C6:2 E6:4 C6:2 A5:2 E5:4',
          'G5:2 B5:2 E6:4 B5:2 G5:2 E5:4',
          'F#5:2 A5:2 D6:4 A5:2 F#5:2 D5:4',
          'D#5:2 F#5:2 B5:4 A5:2 F#5:2 D#5:4',
          'E6:6 C6:2 A5:4 C6:4',
          'B5:6 G5:2 E5:4 G5:4',
          'C6:2 B5:2 C6:2 E6:4 -:2 C6:2 E6:2',
          'F#6:2 D#6:2 B5:2 F#5:2 B5:2 D#6:2 F#6:4'
        ],
        counter: {
          lo: 1, lines: [
            'C5:8 E5:8', 'B4:8 E5:8', 'A4:8 D5:8', 'F#4:8 B4:8',
            'A4:6 C5:2 E5:8', 'G4:6 B4:2 E5:8', 'G4:6 C5:2 E5:8', 'B4:4 D#5:4 F#5:8'
          ]
        },
        arp: '0123012301230123',
        bass: 'r.rrR.rrr.rrR.rf',
        drums: {
          kick: 'X...x...X...x.x.', snare: '....X.......X...',
          hat: { p: '..x...x...x...x.', hi: 1 }, hat2: { p: 'xoxoxoxoxoxoxoxo', lo: 2 },
          clap: { p: '....x.......x..x', lo: 1 }, tom: { p: '......h......m.l', lo: 1 }
        },
        fill: { snare: '....X...x.x.xxxx' }
      }
    },
    form: ['A', 'A', 'B', 'A']
  };

  TRACKS.victory = {
    bpm: 120, key: 0, gain: 0.86, delay: { beats: 0.75, fb: 0.3, wet: 0.5 },
    inst: {
      lead: ['lead', { wave: 'pulse25', det: 6, vib: 1, lp: 3000 }],
      arp: ['pluck', { wave: 'pulse12', lp: 3200, tau: 0.1 }],
      bass: ['bass', { lp: 700 }],
      pad: { lp: 1200 }
    },
    mix: { lead: 0.29, arp: 0.30, bass: 0.36, pad: 0.22, drums: 0.66 },
    send: { lead: 0.3, arp: 0.3 },
    sections: {
      F: {
        chords: 'C F|G Ab|Bb C',
        lead: [
          'G4:1 G4:1 C5:2 D5:2 E5:4 G5:2 C6:4',
          'A5:4 F5:2 A5:2 B5:4 G5:2 B5:2',
          'C6:4 Ab5:2 C6:2 D6:4 Bb5:2 D6:2',
          'E6:3 E6:1 E6:12'
        ],
        arp: '0123012301230123',
        bass: 'r.r.r.rRr.r.r.rR',
        drums: { kick: 'X.....x.X.....x.', snare: '....X.......X.xx', hat: 'x.x.x.x.x.x.x.x.' },
        fill: { kick: 'X.......x.......', snare: 'X.xxX.xxX.......', hat: 'O...............', tom: '............h.ml' }
      },
      A: {
        chords: 'C Am F G C Am F|G C',
        lead: [
          'E5:4 G5:4 E5:2 D5:2 C5:4',
          'C5:4 E5:4 A5:8',
          'A5:4 G5:2 F5:2 C5:8',
          'D5:4 G5:4 B5:8',
          'G4:2 C5:2 D5:2 E5:6 G5:2 E5:2',
          'C5:4 E5:4 A5:4 G5:4',
          'F5:4 A5:4 G5:4 B5:4',
          'C6:8 G5:4 E5:4'
        ],
        arp: '0.1.2.1.3.1.2.1.',
        bass: 'r-----r.f---r...',
        drums: { kick: 'x.......x.o.....', snare: '....x.......x...', hat: 'x.o.x.o.x.o.x.o.' }
      },
      B: {
        chords: 'F C Dm G F C Dm|G C',
        lead: [
          'A5:6 G5:2 F5:8',
          'G5:6 E5:2 C5:8',
          'F5:6 E5:2 D5:4 F5:4',
          'G5:8 D5:8',
          'A5:6 C6:2 A5:8',
          'G5:6 C6:2 G5:8',
          'D5:4 F5:4 G5:4 B5:4',
          'C6:12 -:4'
        ],
        arp: '0.2.1.2.3.2.1.2.',
        bass: 'r-----r.R---f...',
        drums: { kick: 'x.......x.o.....', snare: '....x.......x...', hat: 'x.o.x.o.x.o.x.O.', shaker: '..o...o...o...o.' },
        fill: { snare: '....x.......x.xx' }
      }
    },
    intro: ['F'],
    form: ['A', 'B']
  };

  // --------------------------------------------------------------------------
  // 5. compiler: track data -> { intro: [events], loop: [events] }
  //    event = { t: beat, d: beats, p: part, n: midi | [midi], v: velocity,
  //              k: drum kind, o: drum options, lo/hi: intensity range }
  // --------------------------------------------------------------------------
  var EMPTY = {};
  var compiled = {};
  var DRUM_VEL = { X: 1, x: 0.8, o: 0.4 };
  var TOM_F = { h: 190, m: 140, l: 100 };

  function pick(spec, bar) { return (typeof spec === 'string') ? spec : spec[bar % spec.length]; }
  // two bars that each hold the same single chord (chord objects are cached, so === works)
  function sameBar(x, y) { return x.length === 1 && y.length === 1 && x[0] === y[0]; }

  function compileSection(def, key, bar0, mute, list) {
    var sec = def.sections[key];
    var bars = sec.chords.split(' ').map(function (b) { return b.split('|').map(parseChord); });
    var nb = bars.length, swing = def.swing || 0;
    var arpLo = def.arpLo || 60, padLo = def.padLo || 55, bassLo = def.bassLo || 36;
    var legato = def.inst.lead[0] !== 'lead';
    var b, i;

    function chordAt(bar, step) {
      var cs = bars[bar];
      return cs[Math.min(cs.length - 1, Math.floor(step * cs.length / 16))];
    }
    function beatOf(bar, step) {
      return (bar0 + bar) * 4 + (step + ((step % 2) ? swing : 0)) / 4;
    }
    function push(ev, lo, hi) {
      ev.lo = num(lo, 0); ev.hi = num(hi, 9);
      list.push(ev);
    }
    function addLine(lines, part, lo, hi, smooth) {
      if (lines.length !== nb) warnings.push(def.name + '/' + key + ' ' + part + ': ' + lines.length + ' bars, want ' + nb);
      for (var bar = 0; bar < Math.min(nb, lines.length); bar++) {
        var toks = lines[bar].split(' '), pos = 0;
        for (var k = 0; k < toks.length; k++) {
          var tk = toks[k].split(':'), len = parseInt(tk[1], 10);
          if (!(len > 0)) { warnings.push(def.name + '/' + key + ' bad token ' + toks[k]); len = 1; }
          if (tk[0] !== '-') {
            var midi = noteNum(tk[0]);
            var gate = smooth ? len * 0.97 : (len >= 4 ? len - 0.45 : len * 0.86);
            var vel = 0.8 + (pos === 0 ? 0.14 : (pos % 4 === 0 ? 0.07 : 0));
            push({ t: beatOf(bar, pos), d: gate / 4, p: part, n: midi, v: vel }, lo, hi);
            if (part === 'lead' && def.octave) {
              push({ t: beatOf(bar, pos), d: gate / 4, p: 'lead2', n: midi + def.octave.shift, v: vel }, def.octave.lo, 9);
            }
          }
          pos += len;
        }
        if (pos !== 16) warnings.push(def.name + '/' + key + ' ' + part + ' bar ' + (bar + 1) + ' has ' + pos + ' steps');
      }
    }

    // melody lines
    if (sec.lead && !mute.lead) addLine(sec.lead, 'lead', 0, 9, legato);
    if (sec.counter && !mute.lead) addLine(sec.counter.lines, 'counter', sec.counter.lo, sec.counter.hi, true);

    for (b = 0; b < nb; b++) {
      // arpeggio
      if (sec.arp && !mute.arp) {
        var ap = pick(sec.arp, b);
        for (i = 0; i < 16; i++) {
          var ac = ap.charAt(i);
          if (ac >= '0' && ac <= '9') {
            var lad = voicing(chordAt(b, i), arpLo), ix = parseInt(ac, 10);
            push({
              t: beatOf(b, i), d: 0.22, p: 'arp',
              n: lad[ix % lad.length] + 12 * Math.floor(ix / lad.length),
              v: (i % 4 === 0) ? 0.95 : ((i % 2 === 0) ? 0.76 : 0.6)
            });
          }
        }
      }
      // bass
      if (sec.bass && !mute.bass) {
        var bp = pick(sec.bass, b);
        for (i = 0; i < 16; i++) {
          var bc = bp.charAt(i);
          if (bc === '.' || bc === '-' || bc === '') continue;
          var hold = 1;
          while (i + hold < 16 && bp.charAt(i + hold) === '-') hold++;
          var ch = chordAt(b, i), base = inWindow(ch.bass, bassLo);
          var bn = bc === 'R' ? base + 12 : bc === 'f' ? base + 7 : bc === 't' ? base + ch.iv[1] : bc === 's' ? base + 10 : base;
          push({
            t: beatOf(b, i), d: (hold > 1 ? hold - 0.3 : 0.8) / 4, p: 'bass', n: bn,
            v: (i === 0) ? 0.95 : (bc === 'R' ? 0.7 : 0.82)
          });
        }
      }
      // pad: one sustained chord per harmony, tied over a repeated bar
      if (def.inst.pad && !mute.pad) {
        var cs = bars[b];
        if (!(b % 2 === 1 && sameBar(bars[b - 1], cs))) {           // odd bar with the same chord: tied over
          for (i = 0; i < cs.length; i++) {
            var beats = 4 / cs.length;
            if (b % 2 === 0 && b + 1 < nb && sameBar(cs, bars[b + 1])) beats = 8;
            push({ t: (bar0 + b) * 4 + i * (4 / cs.length), d: beats * 0.98, p: 'pad', n: voicing(cs[i], padLo), v: 1 });
          }
        }
      }
      // drums
      if (!mute.drums) {
        var lanes = {}, lk;
        for (lk in sec.drums) if (sec.drums.hasOwnProperty(lk)) lanes[lk] = 1;
        if (sec.fill && b === nb - 1) for (lk in sec.fill) if (sec.fill.hasOwnProperty(lk)) lanes[lk] = 1;
        for (lk in lanes) {
          var spec = sec.drums[lk], lo = 0, hi = 9, pat = null;
          if (spec && typeof spec === 'object' && !spec.length) { lo = num(spec.lo, 0); hi = num(spec.hi, 9); spec = spec.p; }
          if (spec) pat = pick(spec, b);
          if (sec.fill && b === nb - 1 && sec.fill[lk]) pat = sec.fill[lk];
          if (!pat) continue;
          var kind = lk.replace(/\d+$/, '');
          for (i = 0; i < 16; i++) {
            var dc = pat.charAt(i);
            if (dc === '.' || dc === '') continue;
            var ev = { t: beatOf(b, i), d: 0.25, p: 'drum', k: kind, v: DRUM_VEL[dc] || 0.8 };
            if (kind === 'hat' && dc === 'O') { ev.o = { open: true }; ev.v = 0.75; }
            if (kind === 'tom') { ev.o = { f: TOM_F[dc] || 140 }; ev.v = 0.85; }
            if (kind === 'metal') { ev.o = { f: dc === 'l' ? 430 : 640, tau: dc === 'l' ? 0.04 : 0.028 }; ev.v = dc === 'X' ? 1 : 0.8; }
            push(ev, lo, hi);
          }
        }
      }
    }
    return nb;
  }

  function compileForm(def, form, list) {
    var bar = 0, i;
    for (i = 0; i < form.length; i++) {
      var e = form[i], key = (typeof e === 'string') ? e : e.s, mute = {}, k;
      if (e.mute) for (k = 0; k < e.mute.length; k++) mute[e.mute[k]] = true;
      if (!def.sections[key]) { warnings.push(def.name + ': no section ' + key); continue; }
      bar += compileSection(def, key, bar, mute, list);
    }
    for (i = 0; i < list.length; i++) list[i].i = i;
    list.sort(function (a, b) { return (a.t - b.t) || (a.i - b.i); });
    return bar * 4;
  }

  function compile(name) {
    if (compiled[name]) return compiled[name];
    var def = TRACKS[name];
    if (!def) return null;
    def.name = name;
    var c = { name: name, def: def, bpm: def.bpm, spb: 60 / def.bpm, intro: [], loop: [] };
    c.introBeats = compileForm(def, def.intro || [], c.intro);
    c.loopBeats = compileForm(def, def.form, c.loop);
    compiled[name] = c;
    return c;
  }

  // --------------------------------------------------------------------------
  // 6. player + scheduler
  //    Every event time is computed from the track's start time and an absolute
  //    beat number (never by adding deltas), so timing cannot drift, and the
  //    same code schedules into a realtime or an offline context.
  // --------------------------------------------------------------------------
  var PAN = { arp: 0.3, pad: -0.2, counter: -0.35, lead2: 0.2 };

  function Player(rig, name, t0) {
    var c = compile(name), def = c.def, ctx = rig.ctx, part;
    this.rig = rig; this.c = c; this.name = name; this.t0 = t0;
    this.inIntro = c.intro.length > 0; this.idx = 0; this.loopN = 0;
    this.count = 0; this.missed = 0; this.late = 0;
    this.stopping = false; this.endAt = 0;
    this.live = [];              // voices that may still be sounding (see track())
    this.bus = ctx.createGain();
    this.fade = new Fader(this.bus.gain, 1);
    this.bus.connect(rig.music);
    // tempo-synced feedback delay (dotted eighth by default)
    var dl = def.delay || { beats: 0.75, fb: 0.3, wet: 0.4 };
    this.delayIn = ctx.createGain();
    this.delay = ctx.createDelay(2);
    this.delay.delayTime.value = Math.min(1.9, dl.beats * c.spb);
    this.delayLp = mkFilter(ctx, 'lowpass', 2200, 0.5);
    this.fb = ctx.createGain(); this.fb.gain.value = dl.fb;
    this.wet = ctx.createGain(); this.wet.gain.value = dl.wet;
    this.delayIn.connect(this.delay); this.delay.connect(this.delayLp);
    this.delayLp.connect(this.fb); this.fb.connect(this.delay);
    this.delayLp.connect(this.wet); this.wet.connect(this.bus);
    // one gain per part; drums get a low-pass so hats are never sharp; the
    // accompaniment sits a little off-centre (lead, bass and drums stay in the
    // middle), with sqrt(2) to make up for the panner's centre drop
    this.parts = {}; this.sends = []; this.pans = [];
    var place = def.pan || PAN;
    for (part in def.mix) {
      if (!def.mix.hasOwnProperty(part)) continue;
      var g = ctx.createGain(), pn = mkPan(ctx, num(place[part], 0));
      g.gain.value = def.mix[part] * num(def.gain, 1) * (pn ? Math.SQRT2 : 1);
      if (part === 'drums') {
        this.drumLp = mkFilter(ctx, 'lowpass', num(def.drumLp, 7000), 0.5);
        g.connect(this.drumLp); this.drumLp.connect(this.bus);
      } else if (pn) {
        g.connect(pn); pn.connect(this.bus); this.pans.push(pn);
      } else {
        g.connect(this.bus);
      }
      if (def.send && def.send[part]) {
        var sg = ctx.createGain(); sg.gain.value = def.send[part] / (pn ? Math.SQRT2 : 1);
        g.connect(sg); sg.connect(this.delayIn); this.sends.push(sg);
      }
      this.parts[part] = g;
    }
  }
  // Schedule every event whose start time is < until. An event that is already
  // in the past (the timer was held up for longer than the look-ahead) is not
  // bunched up: short notes are dropped, long ones join in late.
  Player.prototype.schedule = function (until, minTime, intensity) {
    var c = this.c, guard = 0;
    for (;;) {
      var list = this.inIntro ? c.intro : c.loop;
      if (this.idx >= list.length) {
        if (!c.loop.length || ++guard > 4) return;
        if (this.inIntro) this.inIntro = false; else this.loopN++;
        this.idx = 0;
        continue;
      }
      var ev = list[this.idx];
      var beat = this.inIntro ? ev.t : c.introBeats + this.loopN * c.loopBeats + ev.t;
      var time = this.t0 + beat * c.spb;
      if (time >= until) return;
      this.idx++; guard = 0;
      if (intensity < ev.lo || intensity > ev.hi) continue;
      var d = ev.d * c.spb;
      if (time < minTime) {
        var cut = minTime - time;
        if (ev.p === 'drum' || d - cut < 0.2) { this.missed++; continue; }
        this.late++;
        this.play(ev, minTime, beat, intensity, d - cut);
      } else {
        this.play(ev, time, beat, intensity, d);
      }
    }
  };
  Player.prototype.play = function (ev, time, beat, intensity, d) {
    var rig = this.rig, def = this.c.def;
    this.count++;
    if (rig.rec) {
      rig.rec.push({
        time: time, beat: beat, p: ev.p, k: ev.k || '', n: ev.n, d: d,
        loop: this.inIntro ? -1 : this.loopN, at: rig.ctx.currentTime, track: this.name
      });
    }
    if (rig.dry) return;
    if (this.live.length > 96) this.live = this.live.filter(function (v) { return !v.over; });
    rig.sink = this.live;
    try {
      if (ev.p === 'drum') {
        if (DRUM[ev.k] && this.parts.drums) DRUM[ev.k](rig, this.parts.drums, time, ev.v, ev.o || EMPTY);
      } else if (ev.p === 'pad') {
        if (this.parts.pad) VOICE.pad(rig, this.parts.pad, time, ev.n, d, ev.v, def.inst.pad || EMPTY);
      } else {
        var inst = def.inst[ev.p];
        if (inst && this.parts[ev.p]) {
          if (ev.p === 'bass') inst[1].drive = def.octave ? intensity : 0;   // boss: bass opens up as the fight escalates
          VOICE[inst[0]](rig, this.parts[ev.p], time, ev.n, d, ev.v, inst[1]);
        }
      }
    } finally {
      rig.sink = null;
    }
  };
  // Called once the bus has faded to silence (or before the track was ever
  // heard): unplug everything and stop the voices that are still running or
  // waiting to start, so long pads do not keep computing unheard.
  Player.prototype.dispose = function () {
    var list = [this.bus, this.fb, this.wet, this.delay, this.delayLp, this.delayIn, this.drumLp].concat(this.sends, this.pans), i, j, k, v;
    var now = this.rig.ctx.currentTime;
    for (k in this.parts) if (this.parts.hasOwnProperty(k)) list.push(this.parts[k]);
    for (i = 0; i < list.length; i++) { try { if (list[i]) list[i].disconnect(); } catch (e) { /* ok */ } }
    for (i = 0; i < this.live.length; i++) {
      v = this.live[i];
      if (v.over) continue;
      for (j = 0; j < v.srcs.length; j++) { try { if (v.srcs[j]) v.srcs[j].stop(now); } catch (e2) { /* ok */ } }
    }
    this.live = [];
  };

  // --------------------------------------------------------------------------
  // 7. sound effects
  //    Each effect is a few layers built from two primitives, tone() and
  //    noise(), on a per-play session. All of them leave through one shared
  //    low-pass, so nothing can be shrill, and every effect is level-matched:
  //    its output gain is level / SFX_CAL[name], where SFX_CAL is the raw peak
  //    measured by tools/audio_test (re-run `node run_tests.js --calibrate`
  //    after editing an effect).
  //
  //    tone  { w wave, f Hz | n midi, to Hz | ton midi (glide target),
  //            bend glide seconds, at start offset, v level, a attack,
  //            tau (percussive decay) | d + r (held, then release),
  //            lp / lpTo / q low-pass, det cents (adds a detuned twin),
  //            vib [rate Hz, depth semitones], trem [rate Hz, depth, rateTo] }
  //    noise { type, f, to, q, bend, at, v, a, tau | d + r, trem }
  // --------------------------------------------------------------------------
  var SFX = {};
  var SFX_LEVEL = { big: 0.60, mid: 0.48, soft: 0.36, tiny: 0.16 };
  var SFX_CAL = {
    jump: 0.642, land: 0.823, step: 0.619, spring: 0.989, hurt: 0.937, stomp: 0.883, enemyPop: 0.744,
    gravityFlip: 0.835, chip: 0.521, whole: 1.333, secret: 0.892, heart: 0.866, checkpoint: 1.279, qkey: 0.780,
    doorOpen: 0.679, doorLocked: 0.685, uiMove: 0.566, uiSelect: 0.528, uiBack: 0.568, pause: 0.812, unpause: 0.863,
    textBlip: 0.682, hintOpen: 0.628, irisOut: 0.670, irisIn: 0.739, cellPlace: 0.628, cellRemove: 0.634,
    bridgeExtend: 0.876, bridgeSolid: 1.817, bridgeFail: 0.748, blockBump: 0.881, blockBumpMinus: 0.855, lever: 1.091,
    reactorFill: 0.600, reactorOnline: 1.292, reactorVent: 0.433, correct: 0.869, wrong: 0.750, podStep: 0.764,
    podWrong: 0.876, gateOpen: 0.785, gateWrong: 0.752, zap: 0.662, steam: 0.419, mineBeep: 0.453, bossAppear: 0.989,
    bossLaugh: 0.704, bossTelegraph: 0.816, bossShoot: 0.550, bossBeam: 1.041, cannonCharge: 0.606, cannonFire: 1.295,
    cannonFizzle: 0.500, shieldBreak: 1.270, bossHit: 1.216, bossStun: 0.703, bossDefeat: 1.212, quarterGet: 1.428,
    victory: 1.570, transition: 0.561
  };
  var MAX_SFX = 24;              // effects sounding at once
  var MAX_NODES = 700;           // no new effect is started above this many live audio nodes

  function Sfx(rig, t, semi, out) {
    this.rig = rig; this.t = t; this.k = semis(semi); this.out = out; this.live = 0; this.onDone = null;
    this.end = t;                // when the last voice of the effect stops
  }
  Sfx.prototype._env = function (p, t, o, v) {
    var a = num(o.a, 0.004);
    return o.tau ? perc(p, t, v, a, o.tau) : adsr(p, t, v, a, 0.05, 1, o.d, num(o.r, 0.05));
  };
  Sfx.prototype._trem = function (g, tr, t, end, span) {
    var ctx = this.rig.ctx, tg = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    tg.gain.value = 1 - tr[1] / 2; lg.gain.value = tr[1] / 2;
    lfo.frequency.value = tr[0];
    if (tr[2]) {
      lfo.frequency.setValueAtTime(tr[0], t);
      lfo.frequency.exponentialRampToValueAtTime(tr[2], t + span);
    }
    lfo.connect(lg); lg.connect(tg.gain); g.connect(tg);
    lfo.start(t); lfo.stop(end);
    return tg;
  };
  Sfx.prototype.tone = function (o) {
    var rig = this.rig, ctx = rig.ctx, t = this.t + num(o.at, 0), k = this.k, n = 2, i;
    var f0 = (o.n !== undefined ? mtof(o.n) : o.f) * k;
    var f1 = (o.ton !== undefined) ? mtof(o.ton) * k : (o.to !== undefined ? o.to * k : 0);
    var g = ctx.createGain(), tail = g, dest = g;
    var end = this._env(g.gain, t, o, o.v * tame(f0));
    var span = num(o.bend, o.tau ? o.tau * 3 : o.d);
    var srcs = [mkOsc(rig, o.w || 'sine', f0)];
    if (o.det) {
      srcs.push(mkOsc(rig, o.w || 'sine', f0));
      srcs[1].detune.value = o.det; n++;
    }
    if (f1 > 0) {
      for (i = 0; i < srcs.length; i++) {
        srcs[i].frequency.setValueAtTime(f0, t);
        srcs[i].frequency.exponentialRampToValueAtTime(f1, t + span);
      }
    }
    if (o.vib) {
      var lfo = ctx.createOscillator(), lg = ctx.createGain();
      lfo.frequency.value = o.vib[0]; lg.gain.value = o.vib[1] * 100;
      lfo.connect(lg);
      for (i = 0; i < srcs.length; i++) lg.connect(srcs[i].detune);
      lfo.start(t); lfo.stop(end); n += 2;
    }
    if (o.lp) {
      var top = Math.min(8000, o.lp * k);
      var lp = mkFilter(ctx, 'lowpass', top, num(o.q, 0.7));
      if (o.lpTo) {
        lp.frequency.setValueAtTime(top, t);
        lp.frequency.exponentialRampToValueAtTime(Math.min(8000, o.lpTo * k), t + span);
      }
      lp.connect(g); dest = lp; n++;
    }
    if (o.trem) { tail = this._trem(g, o.trem, t, end, span); n += 3; }
    tail.connect(this.out);
    for (i = 0; i < srcs.length; i++) { srcs[i].connect(dest); srcs[i].start(t); srcs[i].stop(end); }
    if (end > this.end) this.end = end;
    track(rig, srcs, tail, n, this);
  };
  Sfx.prototype.noise = function (o) {
    var rig = this.rig, ctx = rig.ctx, t = this.t + num(o.at, 0), k = Math.sqrt(this.k), n = 3;
    var g = ctx.createGain(), tail = g;
    var end = this._env(g.gain, t, o, o.v);
    var span = num(o.bend, o.tau ? o.tau * 3 : o.d);
    var flt = mkFilter(ctx, o.type || 'bandpass', o.f * k, num(o.q, 1));
    if (o.to) {
      flt.frequency.setValueAtTime(o.f * k, t);
      flt.frequency.exponentialRampToValueAtTime(o.to * k, t + span);
    }
    var src = mkNoise(rig, t, end - t);
    src.connect(flt); flt.connect(g);
    if (o.trem) { tail = this._trem(g, o.trem, t, end, span); n += 3; }
    tail.connect(this.out);
    if (end > this.end) this.end = end;
    track(rig, src, tail, n, this);
  };
  // small bell: a sine with two quieter partials that fade faster
  Sfx.prototype.bell = function (n, at, v, tau) {
    this.tone({ n: n, at: at, v: v, tau: tau });
    this.tone({ n: n + 12, at: at, v: v * 0.28, tau: tau * 0.45 });
    this.tone({ f: mtof(n) * 3.01, at: at, v: v * 0.1, tau: tau * 0.16 });
  };
  // a pitched note on two layers: a filtered pulse and a triangle an octave below
  Sfx.prototype.note = function (n, at, d, v, o) {
    o = o || EMPTY;
    this.tone({ w: o.w || 'pulse25', n: n, at: at, d: d, v: v, r: num(o.r, 0.04), lp: num(o.lp, 3400), det: o.det, vib: o.vib });
    this.tone({ w: 'triangle', n: n - 12, at: at, d: d, v: v * 0.8, r: num(o.r, 0.04) });
  };

  function def(name, level, fn) { SFX[name] = { level: num(level, SFX_LEVEL[level]), len: 0, fn: fn, tonal: false }; }

  // ---- movement ------------------------------------------------------------
  def('jump', 'mid', function (s) {
    s.tone({ w: 'pulse25', f: 310, to: 680, bend: 0.12, v: 0.5, tau: 0.075, lp: 2600 });
    s.tone({ f: 155, to: 340, bend: 0.12, v: 0.45, tau: 0.06 });
    s.noise({ type: 'lowpass', f: 1500, v: 0.12, tau: 0.012 });
  });
  def('land', 'soft', function (s) {
    s.tone({ f: 150, to: 58, bend: 0.09, v: 0.8, tau: 0.045 });
    s.noise({ type: 'lowpass', f: 900, v: 0.35, tau: 0.03 });
  });
  def('step', 'tiny', function (s) {
    s.tone({ f: 190, to: 110, bend: 0.04, v: 0.6, tau: 0.014 });
    s.noise({ f: 800, q: 0.8, v: 0.4, tau: 0.012 });
  });
  def('spring', 'mid', function (s) {
    s.tone({ w: 'triangle', f: 196, to: 880, bend: 0.22, v: 0.6, tau: 0.11, vib: [26, 0.9] });
    s.tone({ w: 'pulse50', f: 392, to: 1175, bend: 0.2, v: 0.14, tau: 0.08, lp: 2400 });
    s.tone({ f: 120, to: 70, bend: 0.06, v: 0.5, tau: 0.03 });
  });
  def('hurt', 0.42, function (s) {
    s.tone({ w: 'pulse50', f: 494, to: 185, bend: 0.28, d: 0.24, v: 0.4, r: 0.08, lp: 1700, vib: [17, 0.7] });
    s.tone({ w: 'triangle', f: 247, to: 92, bend: 0.28, d: 0.24, v: 0.4, r: 0.08 });
    s.noise({ f: 700, q: 0.7, v: 0.3, tau: 0.03 });
  });
  def('stomp', 'mid', function (s) {
    s.tone({ f: 210, to: 70, bend: 0.08, v: 0.8, tau: 0.05 });
    s.noise({ f: 1200, q: 0.8, v: 0.3, tau: 0.03 });
    s.tone({ w: 'pulse25', f: 392, to: 784, bend: 0.07, at: 0.03, v: 0.3, tau: 0.045, lp: 2600 });
  });
  def('enemyPop', 'mid', function (s) {
    s.tone({ f: 880, to: 240, bend: 0.07, v: 0.7, tau: 0.035 });
    s.noise({ f: 2400, q: 0.9, v: 0.28, tau: 0.022 });
    s.bell(88, 0.05, 0.28, 0.09);
    s.bell(93, 0.11, 0.24, 0.12);
  });
  def('gravityFlip', 'mid', function (s) {
    s.tone({ w: 'triangle', f: 220, to: 880, bend: 0.3, d: 0.3, v: 0.4, a: 0.03, r: 0.12 });
    s.tone({ w: 'triangle', f: 880, to: 220, bend: 0.3, d: 0.3, v: 0.4, a: 0.03, r: 0.12 });
    s.noise({ f: 500, to: 2800, bend: 0.32, d: 0.3, q: 1.4, v: 0.3, a: 0.06, r: 0.12 });
  });

  // ---- collecting ----------------------------------------------------------
  def('chip', 'soft', function (s) {
    s.tone({ w: 'pulse25', n: 79, d: 0.05, v: 0.42, r: 0.03, lp: 4200 });
    s.tone({ w: 'pulse25', n: 84, at: 0.06, v: 0.42, tau: 0.075, lp: 4200 });
    s.tone({ w: 'triangle', n: 72, at: 0.06, v: 0.3, tau: 0.09 });
  });
  def('whole', 'big', function (s) {
    var q = [72, 76, 79, 84], i;                       // four quarters...
    for (i = 0; i < 4; i++) s.note(q[i], i * 0.075, 0.06, 0.34, { lp: 3600 });
    for (i = 0; i < 4; i++) {                          // ...make a whole
      s.tone({ w: 'pulse50', n: q[i], at: 0.32, d: 0.3, v: 0.14, r: 0.25, lp: 2600, det: 6 });
    }
    s.tone({ n: 48, at: 0.32, d: 0.25, v: 0.4, r: 0.2 });
    s.bell(84, 0.32, 0.3, 0.3);
    s.bell(88, 0.36, 0.22, 0.3);
  });
  def('secret', 'mid', function (s) {
    var n = [72, 76, 79, 83, 86, 91], i;               // C E G B D G: a rising shimmer
    for (i = 0; i < n.length; i++) {
      s.bell(n[i], i * 0.085, 0.3, 0.2 + i * 0.03);
      s.tone({ w: 'triangle', n: n[i] - 12, at: i * 0.085, v: 0.2, tau: 0.08 });
    }
    s.tone({ w: 'triangle', n: 60, d: 0.5, v: 0.14, a: 0.2, r: 0.4 });
  });
  def('heart', 'mid', function (s) {
    s.tone({ f: 82, to: 60, bend: 0.06, v: 0.6, tau: 0.04 });               // lub
    s.tone({ f: 82, to: 60, bend: 0.06, at: 0.13, v: 0.5, tau: 0.045 });    // dub
    s.tone({ w: 'triangle', n: 72, d: 0.1, v: 0.35, r: 0.05 });
    s.tone({ w: 'triangle', n: 79, at: 0.13, d: 0.1, v: 0.35, r: 0.05 });
    s.bell(84, 0.26, 0.4, 0.22);
    s.bell(88, 0.26, 0.2, 0.2);
  });
  def('checkpoint', 'mid', function (s) {
    var n = [67, 72, 79], i;
    for (i = 0; i < 3; i++) {
      s.tone({ w: 'pulse50', n: n[i], at: i * 0.09, d: i === 2 ? 0.22 : 0.07, v: 0.3, r: i === 2 ? 0.2 : 0.04, lp: 2800, det: 5 });
    }
    s.tone({ n: 48, d: 0.3, v: 0.4, r: 0.15 });
    s.bell(88, 0.18, 0.25, 0.3);
  });
  def('qkey', 'big', function (s) {
    var i;
    for (i = 0; i < 6; i++) {                          // a quick jingle of the key
      s.tone({ w: 'pulse25', n: (i % 2) ? 84 : 79, at: i * 0.045, d: 0.035, v: 0.3, r: 0.02, lp: 4200 });
    }
    s.bell(88, 0.28, 0.4, 0.35);
    s.bell(91, 0.3, 0.2, 0.3);
    s.tone({ w: 'triangle', n: 60, at: 0.28, d: 0.3, v: 0.3, r: 0.25 });
    s.tone({ w: 'triangle', n: 67, at: 0.28, d: 0.3, v: 0.22, r: 0.25 });
  });

  // ---- doors / UI ----------------------------------------------------------
  def('doorOpen', 'mid', function (s) {
    s.noise({ type: 'lowpass', f: 320, to: 1900, bend: 0.36, d: 0.34, q: 2, v: 0.3, a: 0.05, r: 0.08 });
    s.tone({ w: 'softsaw', f: 98, to: 196, bend: 0.36, d: 0.34, v: 0.3, a: 0.04, r: 0.06, lp: 900 });
    s.tone({ f: 170, to: 80, bend: 0.06, at: 0.38, v: 0.6, tau: 0.04 });
    s.noise({ f: 1500, q: 1, at: 0.38, v: 0.2, tau: 0.02 });
    s.bell(79, 0.42, 0.22, 0.14);
    s.bell(84, 0.5, 0.22, 0.18);
  });
  def('doorLocked', 'soft', function (s) {
    s.tone({ w: 'pulse50', f: 147, d: 0.06, v: 0.5, r: 0.03, lp: 700 });
    s.tone({ w: 'pulse50', f: 131, at: 0.11, d: 0.08, v: 0.5, r: 0.04, lp: 700 });
    s.noise({ f: 1800, q: 1.5, v: 0.2, tau: 0.01 });
    s.noise({ f: 1800, q: 1.5, at: 0.11, v: 0.2, tau: 0.01 });
  });
  def('uiMove', 'tiny', function (s) {
    s.tone({ w: 'triangle', n: 81, v: 0.6, tau: 0.02 });
    s.tone({ w: 'pulse25', n: 81, v: 0.15, tau: 0.012, lp: 3000 });
  });
  def('uiSelect', 'soft', function (s) {
    s.tone({ w: 'pulse25', n: 76, d: 0.05, v: 0.4, r: 0.03, lp: 3400 });
    s.tone({ w: 'pulse25', n: 83, at: 0.065, v: 0.4, tau: 0.07, lp: 3400 });
    s.bell(88, 0.065, 0.2, 0.12);
  });
  def('uiBack', 'soft', function (s) {
    s.tone({ w: 'pulse50', n: 79, d: 0.05, v: 0.4, r: 0.03, lp: 2400 });
    s.tone({ w: 'pulse50', n: 72, at: 0.065, v: 0.4, tau: 0.06, lp: 2400 });
  });
  def('pause', 'soft', function (s) {
    var n = [76, 72, 67], i;
    for (i = 0; i < 3; i++) s.note(n[i], i * 0.07, 0.05, 0.4, { w: 'pulse50', lp: 2400 });
  });
  def('unpause', 'soft', function (s) {
    var n = [67, 72, 76], i;
    for (i = 0; i < 3; i++) s.note(n[i], i * 0.07, 0.05, 0.4, { w: 'pulse50', lp: 2400 });
  });
  def('textBlip', 'tiny', function (s) {
    s.tone({ w: 'pulse50', n: 72, d: 0.022, v: 0.5, a: 0.003, r: 0.015, lp: 1900 });
  });
  def('hintOpen', 'soft', function (s) {
    s.bell(79, 0, 0.4, 0.2);
    s.bell(84, 0.12, 0.4, 0.3);
    s.bell(91, 0.24, 0.2, 0.25);
    s.tone({ w: 'triangle', n: 60, d: 0.4, v: 0.2, a: 0.1, r: 0.3 });
  });
  def('irisOut', 'mid', function (s) {
    s.tone({ w: 'triangle', f: 880, to: 150, bend: 0.5, d: 0.5, v: 0.4, a: 0.02, r: 0.1 });
    s.tone({ f: 440, to: 75, bend: 0.5, d: 0.5, v: 0.3, a: 0.02, r: 0.1 });
    s.noise({ f: 2600, to: 400, bend: 0.5, d: 0.5, q: 1.5, v: 0.25, a: 0.03, r: 0.1 });
  });
  def('irisIn', 'mid', function (s) {
    s.tone({ w: 'triangle', f: 150, to: 880, bend: 0.5, d: 0.5, v: 0.4, a: 0.02, r: 0.1 });
    s.tone({ f: 75, to: 440, bend: 0.5, d: 0.5, v: 0.3, a: 0.02, r: 0.1 });
    s.noise({ f: 400, to: 2600, bend: 0.5, d: 0.5, q: 1.5, v: 0.25, a: 0.03, r: 0.1 });
  });

  // ---- maths machines ------------------------------------------------------
  def('cellPlace', 'soft', function (s) {
    s.tone({ w: 'triangle', n: 72, v: 0.6, tau: 0.05 });
    s.tone({ n: 84, v: 0.2, tau: 0.03 });
    s.noise({ f: 2200, q: 1.2, v: 0.2, tau: 0.008 });
  });
  def('cellRemove', 'soft', function (s) {
    s.tone({ w: 'triangle', n: 67, ton: 64, bend: 0.06, v: 0.6, tau: 0.05 });
    s.noise({ f: 1400, q: 1.2, v: 0.18, tau: 0.01 });
  });
  def('bridgeExtend', 'mid', function (s) {
    s.tone({ w: 'softsaw', f: 110, to: 220, bend: 0.6, d: 0.6, v: 0.4, a: 0.35, r: 0.1, lp: 500, lpTo: 2200, det: 9 });
    s.tone({ w: 'triangle', f: 440, to: 880, bend: 0.6, d: 0.6, v: 0.22, a: 0.4, r: 0.1, trem: [18, 0.6] });
    s.noise({ f: 800, to: 3000, bend: 0.6, d: 0.6, q: 2, v: 0.12, a: 0.4, r: 0.08 });
  });
  def('bridgeSolid', 'big', function (s) {
    var n = [60, 67, 72], i;
    s.tone({ f: 130, to: 62, bend: 0.08, v: 0.8, tau: 0.07 });
    s.noise({ f: 1100, q: 0.8, v: 0.3, tau: 0.025 });
    for (i = 0; i < 3; i++) s.tone({ w: 'pulse50', n: n[i], d: 0.12, v: 0.16, r: 0.15, lp: 2400, det: 6 });
    s.bell(84, 0.02, 0.35, 0.3);
    s.bell(91, 0.09, 0.2, 0.3);
  });
  def('bridgeFail', 'soft', function (s) {
    s.noise({ f: 2400, to: 500, bend: 0.4, d: 0.3, q: 1.2, v: 0.3, a: 0.01, r: 0.2, trem: [22, 0.7] });
    s.tone({ w: 'triangle', n: 67, ton: 62, bend: 0.35, d: 0.3, v: 0.4, a: 0.02, r: 0.15, vib: [9, 0.3] });
    s.tone({ n: 55, ton: 50, bend: 0.35, d: 0.3, v: 0.25, a: 0.02, r: 0.15 });
  });
  def('blockBump', 'mid', function (s) {
    s.tone({ f: 190, to: 110, bend: 0.05, v: 0.6, tau: 0.035 });
    s.tone({ w: 'pulse25', n: 72, ton: 76, bend: 0.05, v: 0.4, tau: 0.06, lp: 3000 });
    s.tone({ w: 'triangle', n: 84, at: 0.05, v: 0.25, tau: 0.05 });
  });
  def('blockBumpMinus', 'mid', function (s) {
    s.tone({ f: 160, to: 90, bend: 0.05, v: 0.6, tau: 0.04 });
    s.tone({ w: 'pulse25', n: 64, ton: 60, bend: 0.06, v: 0.4, tau: 0.07, lp: 2400 });
    s.tone({ w: 'triangle', n: 67, at: 0.05, v: 0.25, tau: 0.05 });
  });
  def('lever', 'mid', function (s) {
    var i;
    for (i = 0; i < 3; i++) s.noise({ f: 2000 - i * 200, q: 2, at: i * 0.035, v: 0.4, tau: 0.008 });    // ratchet
    s.tone({ w: 'pulse50', f: 180, to: 120, bend: 0.05, at: 0.11, v: 0.45, tau: 0.04, lp: 1400 });
    s.tone({ f: 120, to: 60, bend: 0.06, at: 0.11, v: 0.7, tau: 0.045 });
    s.noise({ f: 1300, q: 1, at: 0.11, v: 0.3, tau: 0.02 });
  });
  def('reactorFill', 'mid', function (s) {
    var at = [0, 0.11, 0.2, 0.3], f = [170, 210, 190, 250], i;
    for (i = 0; i < 4; i++) {                          // glug glug: bubbles rise in pitch
      s.tone({ f: f[i], to: f[i] * 2.3, bend: 0.085, at: at[i], v: 0.6, a: 0.012, tau: 0.03 });
    }
    s.noise({ type: 'lowpass', f: 500, d: 0.36, v: 0.2, a: 0.05, r: 0.1 });
  });
  def('reactorOnline', 'big', function (s) {
    s.tone({ w: 'softsaw', f: 55, to: 220, bend: 0.8, d: 0.85, v: 0.4, a: 0.6, r: 0.2, lp: 300, lpTo: 2600, det: 10 });
    s.tone({ f: 110, to: 440, bend: 0.8, d: 0.85, v: 0.3, a: 0.5, r: 0.18, trem: [8, 0.4, 28] });
    s.noise({ f: 400, to: 2600, bend: 0.8, d: 0.8, q: 1.5, v: 0.14, a: 0.68, r: 0.12 });
    s.tone({ f: 150, to: 55, bend: 0.1, at: 0.8, v: 0.5, tau: 0.07 });
    s.bell(81, 0.8, 0.3, 0.13);                        // A major: the core is alive
    s.bell(85, 0.84, 0.22, 0.13);
    s.bell(88, 0.88, 0.22, 0.13);
  });
  def('reactorVent', 'mid', function (s) {
    s.noise({ f: 2400, to: 1100, bend: 0.6, d: 0.25, q: 1.0, v: 0.5, a: 0.015, r: 0.5 });
    s.noise({ type: 'lowpass', f: 700, d: 0.1, v: 0.25, a: 0.01, r: 0.25 });
    s.tone({ f: 300, to: 120, bend: 0.5, d: 0.2, v: 0.1, a: 0.02, r: 0.3 });
  });
  def('correct', 'big', function (s) {
    var n = [72, 76, 79, 84], i;
    for (i = 0; i < 4; i++) {
      s.note(n[i], i * 0.08, i === 3 ? 0.3 : 0.06, 0.32, { lp: 3600, r: i === 3 ? 0.25 : 0.04, det: i === 3 ? 6 : 0 });
    }
    s.bell(88, 0.24, 0.25, 0.16);
    s.bell(91, 0.32, 0.18, 0.16);
  });
  def('wrong', 'soft', function (s) {              // "bloop-down": two soft falling notes, no buzz
    s.tone({ w: 'triangle', n: 64, ton: 62.5, bend: 0.1, d: 0.1, v: 0.5, a: 0.01, r: 0.06 });
    s.tone({ n: 52, ton: 50.5, bend: 0.1, d: 0.1, v: 0.35, a: 0.01, r: 0.06 });
    s.tone({ w: 'triangle', n: 59, ton: 57, bend: 0.16, at: 0.14, d: 0.16, v: 0.5, a: 0.01, r: 0.12 });
    s.tone({ n: 47, ton: 45, bend: 0.16, at: 0.14, d: 0.16, v: 0.35, a: 0.01, r: 0.12 });
  });
  def('podStep', 'mid', function (s) {
    s.tone({ w: 'triangle', n: 72, v: 0.5, tau: 0.1 });
    s.tone({ f: 130, to: 80, bend: 0.04, v: 0.3, tau: 0.025 });
    s.bell(84, 0, 0.3, 0.14);
  });
  def('podWrong', 'soft', function (s) {
    s.tone({ w: 'triangle', n: 60, ton: 56, bend: 0.14, d: 0.12, v: 0.5, a: 0.008, r: 0.12, vib: [11, 0.35] });
    s.tone({ n: 48, ton: 44, bend: 0.14, d: 0.12, v: 0.4, a: 0.008, r: 0.12 });
  });
  def('gateOpen', 'big', function (s) {
    var n = [67, 72, 76, 79], i;
    s.noise({ f: 400, to: 2400, bend: 0.4, d: 0.4, q: 1.2, v: 0.2, a: 0.1, r: 0.15 });
    s.tone({ w: 'softsaw', f: 82, to: 165, bend: 0.4, d: 0.4, v: 0.3, a: 0.05, r: 0.1, lp: 800, lpTo: 1800 });
    for (i = 0; i < 4; i++) s.note(n[i], 0.3 + i * 0.07, i === 3 ? 0.2 : 0.055, 0.3, { r: i === 3 ? 0.2 : 0.04 });
    s.bell(84, 0.58, 0.3, 0.3);
  });
  def('gateWrong', 'soft', function (s) {
    s.tone({ w: 'triangle', n: 59, d: 0.07, v: 0.5, a: 0.008, r: 0.05 });
    s.tone({ n: 47, d: 0.07, v: 0.35, a: 0.008, r: 0.05 });
    s.tone({ w: 'triangle', n: 58, ton: 56, bend: 0.12, at: 0.12, d: 0.1, v: 0.5, a: 0.008, r: 0.12 });
    s.tone({ n: 46, ton: 44, bend: 0.12, at: 0.12, d: 0.1, v: 0.35, a: 0.008, r: 0.12 });
    s.noise({ type: 'lowpass', f: 600, v: 0.12, tau: 0.02 });
  });

  // ---- hazards -------------------------------------------------------------
  def('zap', 'mid', function (s) {
    s.tone({ w: 'softsaw', f: 950, to: 220, bend: 0.16, d: 0.14, v: 0.4, a: 0.002, r: 0.05, lp: 3200, trem: [62, 0.9] });
    s.tone({ w: 'pulse25', f: 480, to: 110, bend: 0.16, d: 0.12, v: 0.25, r: 0.05, lp: 2400 });
    s.noise({ f: 2800, q: 1.4, d: 0.1, v: 0.22, a: 0.002, r: 0.06, trem: [47, 1] });
  });
  def('steam', 'mid', function (s) {
    s.noise({ f: 1300, to: 2600, bend: 0.12, d: 0.14, q: 1.1, v: 0.5, a: 0.008, r: 0.22 });
    s.noise({ type: 'lowpass', f: 500, d: 0.08, v: 0.25, a: 0.005, r: 0.12 });
  });
  def('mineBeep', 0.22, function (s) {
    s.tone({ w: 'triangle', n: 83, d: 0.06, v: 0.5, a: 0.004, r: 0.04 });
    s.tone({ w: 'pulse25', n: 83, d: 0.06, v: 0.12, r: 0.03, lp: 3000 });
  });

  // ---- boss ----------------------------------------------------------------
  def('bossAppear', 'big', function (s) {
    // a low swell under the Phantom's motif (E6 B5 A5 G5 . E5), as in `boss`
    var n = [88, 83, 81, 79, 76], at = [0.25, 0.4, 0.55, 0.7, 0.95], i;
    s.tone({ w: 'softsaw', n: 40, d: 1.1, v: 0.3, a: 0.5, r: 0.4, lp: 300, lpTo: 1400, det: 12 });
    s.tone({ w: 'softsaw', n: 47, d: 1.1, v: 0.2, a: 0.6, r: 0.4, lp: 300, lpTo: 1400, det: 12 });
    s.noise({ type: 'lowpass', f: 250, to: 900, bend: 1.0, d: 1.0, v: 0.15, a: 0.6, r: 0.3 });
    for (i = 0; i < 5; i++) {
      s.note(n[i], at[i], i === 4 ? 0.4 : 0.11, 0.26, { lp: 2600, r: i === 4 ? 0.25 : 0.05, vib: i === 4 ? [6, 0.3] : null });
    }
  });
  def('bossLaugh', 'mid', function (s) {
    var f = [392, 370, 330, 349, 294, 262, 277], at = [0, 0.1, 0.2, 0.3, 0.38, 0.48, 0.62], i;
    for (i = 0; i < f.length; i++) {                   // ha-ha-ha, sliding down
      s.tone({ w: 'pulse25', f: f[i] * 1.3, to: f[i], bend: 0.05, at: at[i], d: 0.05, v: 0.4, a: 0.006, r: 0.035, lp: 1900, q: 2 });
      s.tone({ w: 'triangle', f: f[i] * 0.65, to: f[i] * 0.5, bend: 0.05, at: at[i], d: 0.05, v: 0.35, r: 0.035 });
    }
    // glitches: a stutter, an octave-jump blip and a burst of static
    for (i = 0; i < 3; i++) s.tone({ w: 'pulse12', f: 784, at: 0.3 + i * 0.022, d: 0.01, v: 0.16, a: 0.002, r: 0.008, lp: 3000 });
    s.tone({ w: 'pulse12', f: 1175, to: 587, bend: 0.03, at: 0.56, d: 0.025, v: 0.16, r: 0.01, lp: 3200 });
    s.noise({ f: 1500, q: 3, at: 0.62, d: 0.08, v: 0.12, a: 0.005, r: 0.06, trem: [38, 1] });
  });
  def('bossTelegraph', 'mid', function (s) {
    var i;
    for (i = 0; i < 2; i++) {
      s.tone({ w: 'pulse50', n: 76, ton: 82, bend: 0.12, at: i * 0.2, d: 0.12, v: 0.35, a: 0.01, r: 0.05, lp: 2200, trem: [24, 0.5] });
      s.tone({ w: 'triangle', n: 64, ton: 70, bend: 0.12, at: i * 0.2, d: 0.12, v: 0.35, a: 0.01, r: 0.05 });
    }
  });
  def('bossShoot', 'mid', function (s) {
    s.tone({ w: 'pulse25', f: 900, to: 220, bend: 0.14, v: 0.45, tau: 0.06, lp: 3000 });
    s.tone({ w: 'triangle', f: 450, to: 110, bend: 0.14, v: 0.4, tau: 0.06 });
    s.noise({ f: 2000, q: 1, v: 0.2, tau: 0.012 });
  });
  def('bossBeam', 'mid', function (s) {
    s.tone({ w: 'softsaw', n: 45, d: 0.7, v: 0.3, a: 0.05, r: 0.15, lp: 1500, det: 14, trem: [26, 0.5] });
    s.tone({ w: 'softsaw', n: 52, d: 0.7, v: 0.2, a: 0.05, r: 0.15, lp: 1500, det: 14 });
    s.tone({ w: 'triangle', f: 660, to: 990, bend: 0.7, d: 0.7, v: 0.16, a: 0.08, r: 0.15, vib: [13, 0.5] });
    s.noise({ f: 1700, q: 1.6, d: 0.7, v: 0.16, a: 0.05, r: 0.15, trem: [31, 0.8] });
  });
  def('cannonCharge', 'mid', function (s) {
    s.tone({ f: 110, to: 880, bend: 1.0, d: 1.0, v: 0.35, a: 0.5, r: 0.06 });
    s.tone({ w: 'pulse25', f: 220, to: 1320, bend: 1.0, d: 1.0, v: 0.2, a: 0.7, r: 0.06, lp: 2800, trem: [7, 0.9, 34] });
    s.noise({ f: 600, to: 3200, bend: 1.0, d: 1.0, q: 2.5, v: 0.14, a: 0.8, r: 0.05 });
  });
  def('cannonFire', 'big', function (s) {
    s.tone({ f: 170, to: 38, bend: 0.25, v: 0.9, tau: 0.14 });
    s.noise({ type: 'lowpass', f: 2600, to: 300, bend: 0.3, v: 0.5, tau: 0.11 });
    s.tone({ w: 'pulse25', f: 1250, to: 160, bend: 0.13, v: 0.3, tau: 0.06, lp: 3200 });
    s.tone({ w: 'softsaw', f: 330, to: 82, bend: 0.3, d: 0.2, v: 0.2, r: 0.2, lp: 1400, det: 15 });
  });
  def('cannonFizzle', 'soft', function (s) {
    s.tone({ w: 'triangle', f: 520, to: 130, bend: 0.5, d: 0.42, v: 0.4, a: 0.01, r: 0.15, vib: [12, 0.8] });
    s.noise({ f: 2500, to: 700, bend: 0.5, d: 0.4, q: 1.3, v: 0.2, a: 0.01, r: 0.15, trem: [19, 0.9] });
    s.tone({ f: 100, to: 60, bend: 0.1, at: 0.45, v: 0.3, tau: 0.04 });      // a little "pft"
  });
  def('shieldBreak', 'big', function (s) {
    var n = [83, 88, 91, 95, 86, 90], at = [0, 0.03, 0.07, 0.12, 0.18, 0.26], i;
    for (i = 0; i < 6; i++) s.bell(n[i], at[i], 0.22, 0.12 + i * 0.02);      // shards
    s.noise({ f: 3000, to: 1200, bend: 0.25, q: 0.9, v: 0.4, tau: 0.06 });
    s.tone({ f: 200, to: 60, bend: 0.1, v: 0.7, tau: 0.07 });
    s.tone({ w: 'softsaw', f: 660, to: 165, bend: 0.3, d: 0.25, v: 0.15, r: 0.1, lp: 2000, det: 20 });
  });
  def('bossHit', 'big', function (s) {
    s.noise({ f: 1000, q: 0.7, v: 0.5, tau: 0.035 });
    s.tone({ w: 'pulse50', f: 330, to: 110, bend: 0.12, v: 0.4, tau: 0.07, lp: 1800 });
    s.tone({ f: 165, to: 55, bend: 0.12, v: 0.7, tau: 0.07 });
    s.bell(83, 0.02, 0.3, 0.16);
    s.bell(90, 0.02, 0.15, 0.12);
  });
  def('bossStun', 'mid', function (s) {
    s.tone({ w: 'triangle', f: 620, to: 330, bend: 0.8, d: 0.75, v: 0.4, a: 0.02, r: 0.2, vib: [7, 3] });   // dizzy wobble
    s.tone({ f: 310, to: 165, bend: 0.8, d: 0.75, v: 0.25, a: 0.02, r: 0.2, vib: [7, 3] });
    s.bell(91, 0.1, 0.18, 0.1);
    s.bell(95, 0.35, 0.18, 0.1);
    s.bell(88, 0.6, 0.18, 0.12);
  });
  def('bossDefeat', 'big', function (s) {
    // glitchy pops tumble down over a rumble, then one last boom and a
    // major-key sparkle: the Phantom is gone
    var f = [1480, 1175, 1320, 988, 1109, 831, 740, 880, 587, 659, 440, 494, 330, 262];
    var n = [76, 80, 83, 88, 92], t = 0, i;
    for (i = 0; i < f.length; i++) {
      s.tone({ w: (i % 3 === 2) ? 'pulse12' : 'pulse25', f: f[i], to: f[i] * 0.5, bend: 0.09, at: t, v: 0.3, tau: 0.045, lp: 3000 });
      s.noise({ f: 900 + (f[i] % 700), q: 1.2, at: t, v: 0.3, tau: 0.03 });
      if (i % 4 === 1) s.tone({ f: 180, to: 50, bend: 0.1, at: t, v: 0.5, tau: 0.06 });
      t += 0.07 + 0.008 * i;                           // the cascade slows as it falls
    }
    s.tone({ w: 'softsaw', f: 120, to: 40, bend: 1.7, d: 1.7, v: 0.25, a: 0.3, r: 0.2, lp: 500, det: 18, trem: [14, 0.5] });
    s.tone({ f: 160, to: 36, bend: 0.3, at: 1.72, v: 0.9, tau: 0.17 });
    s.noise({ type: 'lowpass', f: 2400, to: 250, bend: 0.4, at: 1.72, v: 0.5, tau: 0.14 });
    for (i = 0; i < 5; i++) s.bell(n[i], 1.84 + i * 0.08, 0.22, 0.24);
  });
  def('quarterGet', 'big', function (s) {
    // Jake's theme: so do re mi - so - do'
    var n = [67, 72, 74, 76, 79, 84], at = [0, 0.09, 0.18, 0.27, 0.45, 0.6], d = [0.07, 0.07, 0.07, 0.15, 0.12, 0.6];
    var ch = [60, 64, 67], top = [84, 88, 91, 96], i;
    for (i = 0; i < 6; i++) {
      s.note(n[i], at[i], d[i], 0.3, { det: 6, r: i === 5 ? 0.3 : 0.04, vib: i === 5 ? [5.5, 0.25] : null });
    }
    for (i = 0; i < 3; i++) s.tone({ w: 'pulse50', n: ch[i], at: 0.6, d: 0.55, v: 0.1, r: 0.3, lp: 2400, det: 6 });
    s.tone({ n: 36, at: 0.6, d: 0.5, v: 0.4, r: 0.3 });
    for (i = 0; i < 4; i++) s.bell(top[i], 0.7 + i * 0.08, 0.18, 0.2);
  });

  // ---- misc ----------------------------------------------------------------
  def('victory', 'big', function (s) {
    // fanfare on Jake's theme, harmonised underneath, over a bass
    var n = [67, 67, 72, 74, 76, 79, 84], h = [64, 64, 67, 71, 72, 76, 79];
    var at = [0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0], d = [0.07, 0.07, 0.16, 0.16, 0.16, 0.16, 0.8];
    var ch = [60, 64, 67, 72], top = [84, 88, 91, 96], i;
    for (i = 0; i < 7; i++) {
      s.note(n[i], at[i], d[i], 0.3, { det: 6, r: i === 6 ? 0.3 : 0.05, vib: i === 6 ? [5.5, 0.25] : null });
      s.tone({ w: 'pulse50', n: h[i], at: at[i], d: d[i], v: 0.14, r: i === 6 ? 0.3 : 0.05, lp: 2400 });
    }
    s.tone({ n: 48, at: 0.2, d: 0.16, v: 0.4, r: 0.06 });
    s.tone({ n: 43, at: 0.4, d: 0.16, v: 0.4, r: 0.06 });
    s.tone({ n: 45, at: 0.6, d: 0.16, v: 0.4, r: 0.06 });
    s.tone({ n: 47, at: 0.8, d: 0.16, v: 0.4, r: 0.06 });
    s.tone({ n: 36, at: 1.0, d: 0.75, v: 0.45, r: 0.3 });
    for (i = 0; i < 4; i++) s.tone({ w: 'pulse50', n: ch[i], at: 1.0, d: 0.75, v: 0.08, r: 0.3, lp: 2400, det: 7 });
    for (i = 0; i < 4; i++) s.bell(top[i], 1.1 + i * 0.09, 0.16, 0.3);
    s.noise({ f: 1800, q: 1, v: 0.14, tau: 0.02 });
    s.noise({ f: 1800, q: 1, at: 0.1, v: 0.14, tau: 0.02 });
    s.noise({ f: 2800, q: 0.7, at: 1.0, v: 0.16, tau: 0.16 });
  });
  def('transition', 'mid', function (s) {
    s.noise({ f: 400, to: 2600, bend: 0.3, d: 0.3, q: 1.3, v: 0.4, a: 0.12, r: 0.25 });
    s.tone({ w: 'triangle', f: 220, to: 660, bend: 0.35, d: 0.3, v: 0.25, a: 0.1, r: 0.2 });
    s.tone({ f: 110, to: 330, bend: 0.35, d: 0.3, v: 0.2, a: 0.1, r: 0.2 });
  });

  // The jingles and pitched blips written in C major. They are transposed to
  // the key of the music that is playing (see `key` in the track data). The
  // boss effects are fixed in E minor, the boss track's key; glides, thuds
  // and noises have no key.
  (function (list) { for (var i = 0; i < list.length; i++) SFX[list[i]].tonal = true; })([
    'chip', 'whole', 'secret', 'heart', 'checkpoint', 'qkey', 'enemyPop', 'doorOpen', 'uiMove', 'uiSelect', 'uiBack',
    'pause', 'unpause', 'hintOpen', 'cellPlace', 'cellRemove', 'bridgeSolid', 'bridgeFail', 'blockBump', 'blockBumpMinus',
    'correct', 'wrong', 'podStep', 'podWrong', 'gateOpen', 'gateWrong', 'quarterGet', 'victory'
  ]);

  // Start one effect on `rig` at time t. Works on realtime and offline rigs.
  // `key` is the current music key in semitones from C (tonal effects only).
  // Returns how long its voices will live, in seconds (false if nothing started).
  function playSfx(rig, name, opts, t, raw, key) {
    var d = SFX.hasOwnProperty(name) ? SFX[name] : null;
    if (!d) return false;
    opts = opts || EMPTY;
    var ctx = rig.ctx, vol = clamp(num(opts.vol, 1), 0, 1), panv = clamp(num(opts.pan, 0), -1, 1);
    if (vol <= 0) return false;
    var out = ctx.createGain(), n = 1;
    var gain = vol * (raw ? 1 : d.level / (SFX_CAL[name] || 1));
    var pan = mkPan(ctx, panv);
    if (pan) {
      // equal-power panning drops a centred mono source by 3 dB: keep the louder side at the calibrated level
      var ang = (panv + 1) * Math.PI / 4;
      gain /= Math.max(Math.cos(ang), Math.sin(ang));
      out.connect(pan); pan.connect(rig.sfxIn); n++;
    } else {
      out.connect(rig.sfxIn);
    }
    out.gain.value = gain;
    var s = new Sfx(rig, t, clamp(num(opts.pitch, 0), -24, 24) + (d.tonal ? num(key, 0) : 0), out);
    rig.sfxLive++; rig.nodes += n;
    s.onDone = function () {
      rig.sfxLive--; rig.nodes -= n;
      try { out.disconnect(); if (pan) pan.disconnect(); } catch (e) { /* ok */ }
    };
    d.fn(s);
    if (!s.live) s.onDone();
    return s.end - t;
  }
  // lifetime of an effect's voices in seconds (measured once, on a throwaway offline context)
  function sfxLength(name) {
    var d = SFX.hasOwnProperty(name) ? SFX[name] : null, C = root.OfflineAudioContext || root.webkitOfflineAudioContext;
    if (!d) return 0;
    if (!d.len && C) d.len = playSfx(createRig(new C(1, 1, 44100), DEFAULT_VOL, { limiter: false }), name, null, 0) || 0;
    return d.len;
  }

  // --------------------------------------------------------------------------
  // 8. engine state (the one realtime context) and voice playback
  // --------------------------------------------------------------------------
  var LOOKAHEAD = 0.12;          // seconds scheduled ahead of ctx.currentTime
  var TICK_MS = 25;              // scheduler timer period
  var PAUSE_GRACE_MS = 350;      // pauseAll() lets an effect that has just started ring out
  var doc = (typeof document !== 'undefined') ? document : (root.document || null);
  var vols = { master: DEFAULT_VOL.master, music: DEFAULT_VOL.music, sfx: DEFAULT_VOL.sfx, voice: DEFAULT_VOL.voice };
  var E = {
    ctx: null, rig: null, failed: false, inited: false, wantUnlock: false, unlocked: false,
    userPaused: false, autoPaused: false, pauseTimer: null,
    wanted: null, wantedFade: 0.6, players: [], cur: null, intensity: 0, duck: 0,
    timer: null, lastTick: 0, sfxLast: {}, sfxLastMs: 0, held: null, errors: []
  };

  function noop() {}
  function later(fn, ms) { return (typeof setTimeout === 'function') ? setTimeout(fn, ms || 0) : 0; }
  function cancel(id) { if (id && typeof clearTimeout === 'function') clearTimeout(id); }
  function nowMs() { return Date.now ? Date.now() : new Date().getTime(); }
  function noteError(e) {
    if (E.errors.length < 20) E.errors.push(String((e && e.stack) || e));
  }
  function ctor() { return root.AudioContext || root.webkitAudioContext || null; }
  function running() { return !!E.ctx && (E.ctx.state === 'running' || E.ctx.state === undefined); }
  function ready() { return running() && !E.userPaused; }
  function hidden() { try { return !!(doc && doc.hidden); } catch (e) { return false; } }
  function stateName() {
    if (E.ctx) return E.ctx.state || 'running';
    return (ctor() && !E.failed) ? 'locked' : 'unavailable';
  }
  function ensureContext() {
    if (E.ctx) return E.ctx;
    var C = ctor(), ctx = null;
    if (!C || E.failed) return null;
    try { ctx = new C({ latencyHint: 'interactive' }); } catch (e) {
      try { ctx = new C(); } catch (e2) { ctx = null; }
    }
    if (!ctx) { E.failed = true; return null; }
    try {
      E.rig = createRig(ctx, vols, {});
      E.rig.fade.duck.go(1 - E.duck, 0, 0.005);
    } catch (e3) {
      noteError(e3);
      E.failed = true; E.rig = null;
      try { ctx.close(); } catch (e4) { /* ok */ }
      return null;
    }
    E.ctx = ctx;
    try {
      if (ctx.addEventListener) ctx.addEventListener('statechange', onState, false);
      else ctx.onstatechange = onState;
    } catch (e5) { /* ok */ }
    return ctx;
  }
  function resumeCtx() {
    var ctx = E.ctx, p;
    if (!ctx || !ctx.resume || ctx.state === 'running' || ctx.state === 'closed') return;
    try { p = ctx.resume(); if (p && p.then) p.then(onState, noop); } catch (e) { /* ok */ }
  }
  function suspendNow() {
    var ctx = E.ctx, p;
    E.pauseTimer = null;
    if (!ctx || !ctx.suspend || ctx.state !== 'running') return;
    try { p = ctx.suspend(); if (p && p.then) p.then(noop, noop); } catch (e) { /* ok */ }
  }
  // called whenever the context may have started running
  function onState() {
    if (!running()) return;
    E.unlocked = true;
    if (E.userPaused) return;
    try {
      startWanted();
      if (E.players.length) { ensureTimer(); tick(); }
      var h = E.held;
      E.held = null;
      if (h && nowMs() - h.ms < 250) sfx(h.name, h.opts);
    } catch (e) { noteError(e); }
  }
  function onGesture() {
    // Completes an unlock() that was made outside a user gesture and recovers
    // from interruptions (phone call, iOS tab switch). Does nothing until the
    // game has asked for sound by calling unlock().
    if (!E.wantUnlock || E.userPaused || running()) return;
    try { if (ensureContext() && !hidden()) { resumeCtx(); kick(); } } catch (e) { noteError(e); }
  }
  function onVisibility() {
    try {
      if (hidden()) {
        E.autoPaused = true;
        cancel(E.pauseTimer);
        suspendNow();
      } else if (E.autoPaused) {
        E.autoPaused = false;
        if (!E.userPaused && E.wantUnlock) resumeCtx();
      }
    } catch (e) { noteError(e); }
  }
  // iOS Safari only opens the output once a source has been started inside a gesture
  function kick() {
    var ctx = E.ctx, s;
    if (!ctx || E.unlocked) return;
    try {
      s = ctx.createBufferSource();
      s.buffer = ctx.createBuffer(1, 1, 22050);
      s.connect(ctx.destination);
      s.start(0);
    } catch (e) { /* ok */ }
  }

  function init() {
    if (E.inited) return;
    E.inited = true;
    var evs = ['pointerdown', 'touchend', 'mousedown', 'keydown', 'click'], i;
    if (doc && doc.addEventListener) {
      doc.addEventListener('visibilitychange', onVisibility, false);
      for (i = 0; i < evs.length; i++) doc.addEventListener(evs[i], onGesture, true);
    }
    if (root.addEventListener) {
      root.addEventListener('pagehide', onVisibility, false);
      root.addEventListener('pageshow', onVisibility, false);
    }
  }
  function unlock() {
    init();
    E.wantUnlock = true;
    if (!ensureContext()) return false;
    if (hidden()) E.autoPaused = true;
    if (!E.userPaused && !E.autoPaused) resumeCtx();
    else if (running()) suspendNow();          // created while paused or hidden: a new context starts by itself
    kick();
    onState();
    return E.unlocked;
  }

  // ---- volumes -------------------------------------------------------------
  function setVolume(kind, v) {
    if (!vols.hasOwnProperty(kind)) return;
    vols[kind] = clamp(num(v, vols[kind]), 0, 1);
    if (E.rig) E.rig.fade[kind].go(vols[kind], E.ctx.currentTime, 0.05);
  }
  function getVolume(kind) { return vols.hasOwnProperty(kind) ? vols[kind] : 0; }
  function duck(amount, seconds) {
    E.duck = clamp(num(amount, 0), 0, 1);
    if (E.rig) E.rig.fade.duck.go(1 - E.duck, E.ctx.currentTime, clamp(num(seconds, 0.3), 0.01, 10));
  }

  // ---- music ---------------------------------------------------------------
  function fadeOut(p, now, fade) {
    var end = now + fade + 0.05;
    if (p.stopping && p.endAt <= end) return;
    p.stopping = true;
    p.fade.go(0, now, fade);
    p.endAt = end;
  }
  function startWanted() {
    var name = E.wanted, i, had = false, now, fade, p;
    if (!name || !ready()) return;
    if (E.cur && !E.cur.stopping && E.cur.name === name) return;
    now = E.ctx.currentTime;
    fade = Math.max(0.02, E.wantedFade);
    for (i = E.players.length - 1; i >= 0; i--) {
      p = E.players[i];
      if (now < p.t0) {                 // superseded before its first note: drop it unheard
        p.dispose();
        E.players.splice(i, 1);
        continue;
      }
      if (!p.stopping) had = true;
      // only the newest outgoing track gets the full cross-fade; older ones leave at once
      fadeOut(p, now, i < E.players.length - 1 ? Math.min(fade, 0.05) : fade);
    }
    // the new track comes in at full level half-way through the cross-fade,
    // so its first downbeat is never swallowed by a fade-in
    p = new Player(E.rig, name, now + (had ? Math.min(0.4, fade * 0.5) : 0.06));
    E.players.push(p);
    E.cur = p;
    ensureTimer();
    tick();
  }
  function playMusic(name, opts) {
    var fade = num(opts && opts.fade, 0.6);
    if (name === null || name === undefined || name === '') { stopMusic(fade); return; }
    if (!TRACKS.hasOwnProperty(name)) return;
    if (E.wanted === name) return;
    E.wanted = name;
    E.wantedFade = clamp(fade, 0, 10);
    startWanted();
  }
  function stopMusic(fade) {
    var i, now;
    E.wanted = null;
    if (!E.ctx) return;
    now = E.ctx.currentTime;
    fade = clamp(num(fade, 0.6), 0.02, 10);
    for (i = 0; i < E.players.length; i++) fadeOut(E.players[i], now, fade);
    if (E.cur) E.cur = null;
  }
  function setIntensity(level) { E.intensity = clamp(Math.round(num(level, 0)), 0, 2); }

  function ensureTimer() {
    if (!E.timer && E.players.length && typeof setInterval === 'function') {
      E.lastTick = E.ctx.currentTime;
      E.timer = setInterval(tickSafe, TICK_MS);
    }
  }
  function tickSafe() { try { tick(); } catch (e) { noteError(e); } }
  // The look-ahead scheduler. Runs every TICK_MS and schedules LOOKAHEAD
  // seconds ahead on the audio clock; if the timer itself was held up (frame
  // drops, a throttled tab) it reaches further ahead next time.
  function tick() {
    var ctx = E.ctx, now, gap, ahead, i, p;
    if (!ctx || !running()) return;
    now = ctx.currentTime;
    gap = now - E.lastTick;
    E.lastTick = now;
    ahead = gap > 0.08 ? clamp(gap * 2 + 0.1, LOOKAHEAD, 2.5) : LOOKAHEAD;
    for (i = E.players.length - 1; i >= 0; i--) {
      p = E.players[i];
      if (p.stopping && now >= p.endAt) {
        p.dispose();
        E.players.splice(i, 1);
        if (E.cur === p) E.cur = null;
      } else {
        p.schedule(now + ahead, now, E.intensity);
      }
    }
    if (!E.players.length && E.timer) { clearInterval(E.timer); E.timer = null; }
  }

  // ---- sfx -----------------------------------------------------------------
  function sfx(name, opts) {
    var ctx = E.ctx, t;
    if (!SFX.hasOwnProperty(name) || !ctx || !E.rig) return;
    if (!running()) {
      // sfx('unpause') followed straight away by resumeAll() should still be heard
      if (E.userPaused) E.held = { name: name, opts: opts, ms: nowMs() };
      return;
    }
    t = ctx.currentTime;
    if (E.sfxLast[name] !== undefined && t - E.sfxLast[name] < 0.03 && t >= E.sfxLast[name]) return;   // same effect twice in a frame
    if (E.rig.sfxLive >= MAX_SFX || E.rig.nodes >= MAX_NODES) return;                               // far more than a game ever needs
    E.sfxLast[name] = t;
    E.sfxLastMs = nowMs();
    playSfx(E.rig, name, opts, t + 0.004, false, musicKey());
  }
  // key of the music that is playing now (0 = C, also when there is none)
  function musicKey() { return (E.cur && !E.cur.stopping) ? num(E.cur.c.def.key, 0) : 0; }

  // ---- pause / resume ------------------------------------------------------
  function pauseAll() {
    var wait;
    E.userPaused = true;
    cancel(E.pauseTimer); E.pauseTimer = null;
    if (!E.ctx) return;
    if (running()) E.rig.fade.hold.go(0, E.ctx.currentTime, 0.04);
    wait = Math.min(PAUSE_GRACE_MS, E.sfxLastMs + PAUSE_GRACE_MS - nowMs());
    if (wait > 5 && running() && !hidden()) E.pauseTimer = later(suspendNow, wait);
    else suspendNow();
  }
  function resumeAll() {
    E.userPaused = false;
    cancel(E.pauseTimer); E.pauseTimer = null;
    if (!E.ctx) return;
    E.rig.fade.hold.go(1, E.ctx.currentTime, 0.08);
    E.autoPaused = hidden();
    if (!E.autoPaused) resumeCtx();
    onState();
  }

  // ---- voice ---------------------------------------------------------------
  var VOICE_CACHE_MAX = 16;
  var V = { bufs: {}, order: [], dur: {}, bad: {}, src: {}, waiting: {}, cur: null };

  function voiceUri(id) {
    var a, u;
    try {
      a = root.MB_ASSETS && root.MB_ASSETS.audio;
      u = a ? a['voice/' + id] : null;
    } catch (e) { u = null; }
    return (typeof u === 'string' && u.length > 16) ? u : null;
  }
  // "data:audio/mpeg;base64,...." -> ArrayBuffer (no fetch: must work from file://)
  function uriToArrayBuffer(uri) {
    var a2b = root.atob || (typeof atob === 'function' ? atob : null);
    var body = uri, comma, bin, bytes, i;
    if (!a2b) return null;
    if (uri.slice(0, 5) === 'data:') {
      comma = uri.indexOf(',');
      if (comma < 0 || !/;base64$/i.test(uri.slice(0, comma))) return null;
      body = uri.slice(comma + 1);
    }
    bin = a2b(body.replace(/\s+/g, ''));
    bytes = new Uint8Array(bin.length);
    for (i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
  }
  function forgetVoice(id) {
    var i = V.order.indexOf(id);
    if (i >= 0) V.order.splice(i, 1);
    delete V.bufs[id]; delete V.dur[id]; delete V.bad[id];
  }
  // decode (or fetch from the cache) and call cb(buffer | null). Returns false
  // if the clip cannot even be queued.
  function decodeVoice(id, uri, cb) {
    var ab, p, done = false;
    if (V.src[id] !== uri) { forgetVoice(id); V.src[id] = uri; }   // the asset was replaced
    if (V.bufs[id]) {
      V.order.splice(V.order.indexOf(id), 1); V.order.push(id);
      cb(V.bufs[id]);
      return true;
    }
    if (V.bad[id]) return false;
    if (V.waiting[id]) { V.waiting[id].push(cb); return true; }
    try { ab = uriToArrayBuffer(uri); } catch (e) { ab = null; }
    if (!ab || !ab.byteLength) { V.bad[id] = true; return false; }
    V.waiting[id] = [cb];
    function finish(buf) {
      var list, i;
      if (done) return;
      done = true;
      list = V.waiting[id] || [];
      delete V.waiting[id];
      if (buf && buf.duration > 0) {
        V.bufs[id] = buf; V.dur[id] = buf.duration; V.order.push(id);
        while (V.order.length > VOICE_CACHE_MAX) delete V.bufs[V.order.shift()];
      } else {
        V.bad[id] = true; buf = null;
      }
      for (i = 0; i < list.length; i++) { try { list[i](buf); } catch (e) { noteError(e); } }
    }
    try {
      // callback form for old Safari; the promise (where there is one) is handled too
      p = E.ctx.decodeAudioData(ab, function (b) { finish(b); }, function () { finish(null); });
      if (p && p.then) p.then(function (b) { finish(b); }, function () { finish(null); });
    } catch (e2) {
      done = true;
      delete V.waiting[id];
      V.bad[id] = true;
      return false;
    }
    return true;
  }
  function endVoice(job, completed) {
    var src = job.src, g = job.g, ctx = E.ctx, t;
    if (job.done) return;
    job.done = true;
    if (V.cur === job) V.cur = null;
    if (src) {
      if (completed || !running()) {
        src.onended = null;
        try { src.stop(0); } catch (e) { /* ok */ }
        try { g.disconnect(); } catch (e2) { /* ok */ }
      } else {
        // stopped mid-line: a very short fade instead of a click
        t = ctx.currentTime;
        src.onended = function () { try { g.disconnect(); } catch (e) { /* ok */ } };
        try {
          g.gain.setValueAtTime(1, t);
          g.gain.linearRampToValueAtTime(0, t + 0.04);
          src.stop(t + 0.06);
        } catch (e3) { try { g.disconnect(); } catch (e4) { /* ok */ } }
      }
    }
    if (job.cb) {
      try { job.cb(!!completed); } catch (err) { later(function () { throw err; }); }
    }
  }
  function startVoice(job, buf) {
    var ctx = E.ctx, src = ctx.createBufferSource(), g = ctx.createGain();
    src.buffer = buf;
    src.connect(g); g.connect(E.rig.voice);
    job.src = src; job.g = g;
    src.onended = function () { endVoice(job, true); };
    src.start(ctx.currentTime + 0.01);
  }
  function playVoice(id, onEnd) {
    var uri = voiceUri(id), job, ok;
    if (!uri) return false;                               // no such clip: the caller shows text only
    if (!E.ctx || !E.rig || !E.unlocked) return false;    // no sound available (yet)
    stopVoice();
    job = { id: id, cb: (typeof onEnd === 'function') ? onEnd : null, src: null, g: null, done: false };
    V.cur = job;
    ok = decodeVoice(id, uri, function (buf) {
      if (job.done) return;
      if (buf) startVoice(job, buf); else endVoice(job, false);
    });
    if (!ok) {
      job.done = true;
      if (V.cur === job) V.cur = null;
      return false;
    }
    return true;
  }
  function stopVoice() { if (V.cur) endVoice(V.cur, false); }
  function voiceDuration(id) {
    var uri = voiceUri(id);
    if (!uri) return 0;
    if (V.src[id] === uri && V.dur[id]) return V.dur[id];
    // not decoded yet: start decoding in the background so a later call knows
    if (E.ctx && E.rig && !(V.src[id] === uri && (V.bad[id] || V.waiting[id]))) decodeVoice(id, uri, noop);
    return 0;
  }

  function debugInfo() {
    var rig = E.rig, p = E.cur;
    return {
      state: stateName(),
      track: E.wanted,
      activeVoices: rig ? rig.active : 0,
      playing: p ? p.name : null,
      nodes: rig ? rig.nodes : 0,
      sfxLive: rig ? rig.sfxLive : 0,
      dupEnded: rig ? rig.dup : 0,
      players: E.players.length,
      intensity: E.intensity,
      key: musicKey(),
      unlocked: E.unlocked,
      paused: E.userPaused,
      time: E.ctx ? E.ctx.currentTime : 0,
      scheduled: p ? p.count : 0,
      missed: p ? p.missed : 0,
      late: p ? p.late : 0,
      loop: p ? p.loopN : 0,
      voice: V.cur ? V.cur.id : null,
      errors: E.errors.slice(0),
      warnings: warnings.slice(0)
    };
  }

  // --------------------------------------------------------------------------
  // 9. public API + test hooks
  //    Audio must never take the game down: every entry point is guarded.
  //    Anything caught is kept in debugInfo().errors (the tests require it to
  //    stay empty).
  // --------------------------------------------------------------------------
  function guard(fn, dflt) {
    return function () {
      try { return fn.apply(null, arguments); } catch (e) { noteError(e); return dflt; }
    };
  }

  // ---- offline rendering (tests, tools) --------------------------------------
  // Renders a scene through the same rig / Player / sfx code as the realtime
  // engine. Music is scheduled in steps while the offline context is suspended,
  // i.e. by the same look-ahead method the game uses.
  //   o: { seconds, track, intensity (number | [[time, level], ...]), fromBeat,
  //        solo (part name), sfx: [{ name, at, opts }], key (for tonal effects;
  //        default: the track's), limiter (false = measure before the limiter),
  //        vols, raw, rec, dry, sampleRate, upfront }
  function renderScene(o) {
    o = o || {};
    var C = root.OfflineAudioContext || root.webkitOfflineAudioContext;
    if (!C) return Promise.reject(new Error('OfflineAudioContext is not available'));
    var sr = o.sampleRate || 44100, secs = num(o.seconds, 4), lead = 0.02, i;
    var octx = new C(2, Math.ceil(sr * secs), sr);
    var rig = createRig(octx, o.vols || DEFAULT_VOL, { limiter: !!o.limiter });
    var player = null, step = 0.5, margin = 0.25;
    if (o.rec) rig.rec = [];
    if (o.dry) rig.dry = true;
    function level(t) {
      var iv = o.intensity, lv = 0, j;
      if (typeof iv === 'number') return iv;
      if (iv && iv.length) for (j = 0; j < iv.length; j++) if (t >= iv[j][0]) lv = iv[j][1];
      return lv;
    }
    if (o.track) player = new Player(rig, o.track, lead - num(o.fromBeat, 0) * compile(o.track).spb);
    if (player && o.solo) {                               // hear one part on its own
      for (var part in player.parts) if (player.parts.hasOwnProperty(part) && part !== o.solo) player.parts[part].gain.value = 0;
    }
    var key = num(o.key, o.track ? num(TRACKS[o.track].key, 0) : 0);
    if (o.sfx) for (i = 0; i < o.sfx.length; i++) playSfx(rig, o.sfx[i].name, o.sfx[i].opts, lead + num(o.sfx[i].at, 0), o.raw, key);
    if (player) {
      if (octx.suspend && !o.upfront) {
        player.schedule(step + margin, 0, level(0));
        var hold = function (t) {
          octx.suspend(t).then(function () {
            player.schedule(t + step + margin, t, level(t + margin));
            octx.resume();
          });
        };
        for (i = 1; i * step < secs - 0.01; i++) hold(i * step);
      } else {
        player.schedule(secs, 0, level(0));
      }
    }
    return new Promise(function (resolve, reject) {
      var done = function (buf) {
        resolve({
          buffer: buf, events: rig.rec, active: rig.active, nodes: rig.nodes,
          counts: function () { return { active: rig.active, nodes: rig.nodes, sfxLive: rig.sfxLive, dup: rig.dup }; },
          scheduled: player ? player.count : 0, missed: player ? player.missed : 0
        });
      };
      var p;
      octx.oncomplete = function (e) { done(e.renderedBuffer); };
      p = octx.startRendering();
      if (p && p.then) p.then(done, reject);
    });
  }
  // every event the Player schedules for the intro plus `loops` passes of the
  // loop, without making a sound (loop-seam tests)
  function listEvents(name, loops, intensity) {
    var C = root.OfflineAudioContext || root.webkitOfflineAudioContext;
    var rig = createRig(new C(1, 1, 44100), DEFAULT_VOL, { limiter: false });
    var c = compile(name), p;
    rig.rec = []; rig.dry = true;
    p = new Player(rig, name, 0);
    p.schedule((c.introBeats + num(loops, 2) * c.loopBeats) * c.spb - 1e-9, 0, num(intensity, 0));
    return { bpm: c.bpm, spb: c.spb, introBeats: c.introBeats, loopBeats: c.loopBeats, events: rig.rec };
  }
  // melodic sanity check: which lead notes sound on the strong beats (1 and 3)
  // and are they notes of the chord underneath?
  function lint(name) {
    var d = TRACKS[name], out = { strong: 0, chordTone: 0, misses: [], lo: 127, hi: 0, bars: 0 }, seen = {}, keys, i;
    if (!d) return null;
    keys = (d.intro || []).concat(d.form).map(function (e) { return (typeof e === 'string') ? e : e.s; });
    for (i = 0; i < keys.length; i++) {
      var key = keys[i], sec = d.sections[key];
      if (seen[key] || !sec || !sec.lead) continue;
      seen[key] = 1;
      var bars = sec.chords.split(' ');
      for (var b = 0; b < bars.length; b++) {
        var cs = bars[b].split('|').map(parseChord), toks = sec.lead[b].split(' '), pos = 0, grid = [];
        out.bars++;
        for (var k = 0; k < toks.length; k++) {
          var tk = toks[k].split(':'), len = parseInt(tk[1], 10), m = tk[0] === '-' ? -1 : noteNum(tk[0]);
          if (m >= 0) { out.lo = Math.min(out.lo, m); out.hi = Math.max(out.hi, m); }
          while (len-- > 0) grid[pos++] = m;
        }
        for (var s = 0; s < 16; s += 8) {
          if (grid[s] === undefined || grid[s] < 0) continue;
          var ch = cs[Math.min(cs.length - 1, Math.floor(s * cs.length / 16))], ok = false;
          for (var q = 0; q < ch.iv.length; q++) if ((ch.root + ch.iv[q]) % 12 === grid[s] % 12) ok = true;
          out.strong++;
          if (ok) out.chordTone++; else out.misses.push(key + ' bar ' + (b + 1) + ' beat ' + (s / 4 + 1) + ' over ' + ch.sym);
        }
      }
    }
    return out;
  }

  var api = {
    init: guard(init),
    unlock: guard(unlock, false),
    isUnlocked: function () { return E.unlocked; },
    setVolume: guard(setVolume),
    getVolume: guard(getVolume, 0),
    playMusic: guard(playMusic),
    stopMusic: guard(stopMusic),
    setIntensity: guard(setIntensity),
    duck: guard(duck),
    sfx: guard(sfx),
    playVoice: guard(playVoice, false),
    stopVoice: guard(stopVoice),
    voiceDuration: guard(voiceDuration, 0),
    pauseAll: guard(pauseAll),
    resumeAll: guard(resumeAll),
    debugInfo: guard(debugInfo, { state: 'unavailable', track: null, activeVoices: 0 }),
    // not part of the game API: used by tools/audio_test
    _test: {
      tracks: function () { var k, out = []; for (k in TRACKS) if (TRACKS.hasOwnProperty(k)) out.push(k); return out; },
      sfxNames: function () { var k, out = []; for (k in SFX) if (SFX.hasOwnProperty(k)) out.push(k); return out; },
      sfxInfo: function (name) { return SFX[name] ? { level: SFX[name].level, len: sfxLength(name), cal: SFX_CAL[name] || 0, tonal: SFX[name].tonal } : null; },
      trackInfo: function (name) {
        var c = compile(name);
        return c ? { bpm: c.bpm, key: num(c.def.key, 0), introBeats: c.introBeats, loopBeats: c.loopBeats, loopSeconds: c.loopBeats * c.spb, events: c.loop.length + c.intro.length } : null;
      },
      render: renderScene,
      events: listEvents,
      lint: lint,
      warnings: function () { return warnings.slice(0); },
      record: function (on) { var r = E.rig ? E.rig.rec : null; if (E.rig) E.rig.rec = on ? [] : null; return r; },
      tap: function () {
        var rig = E.rig, a;
        if (!rig) return null;
        if (!rig.tap) {
          a = E.ctx.createAnalyser(); a.fftSize = 2048;
          rig.master.connect(a);
          rig.tap = a;
        }
        return rig.tap;
      },
      context: function () { return E.ctx; },
      rig: function () { return E.rig; },
      defaults: { vol: DEFAULT_VOL, comp: COMP, trim: COMP_TRIM, lookahead: LOOKAHEAD, tick: TICK_MS }
    }
  };
  MB.Audio = api;
})();
