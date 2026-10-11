/* Math Blast Arcade - shared constants and fraction maths. */
window.MB = window.MB || {};
(function () {
  'use strict';
  var q = new URLSearchParams(window.location.search);
  MB.DEBUG = q.has('debug');
  MB.QUERY = q;

  MB.CFG = {
    W: 960, H: 540,            // canvas size (screen pixels)
    ZOOM: 2,                   // 1 art pixel = 2 screen pixels
    VW: 480, VH: 270,          // visible world size in art pixels
    T: 16,                     // tile size
    // --- Jake's movement (art pixels per second) ---
    RUN: 118, ACC_G: 1050, ACC_A: 780, FRIC: 1400,
    JUMP: 340, GRAV_UP: 1000, GRAV_DOWN: 1550, MAXFALL: 340,
    COYOTE: 110, BUFFER: 140, CUT: 0.45,
    LOWG: { scale: 0.34, jump: 228, maxfall: 150 },
    HEARTS: 4, INVULN: 1400
  };

  MB.COL = {
    ink: 0x080a14, navy: 0x141a3a, navy2: 0x1e2a5a, cyan: 0x2de0d0, cyanL: 0x8ff7ea, teal: 0x12a3a6,
    gold: 0xffcf33, orange: 0xff9340, pink: 0xff8cc0, red: 0xe8384f, redL: 0xff7a7a,
    green: 0x7bea8a, greenD: 0x3fc468, white: 0xffffff, text: 0xe6f1ff, dim: 0x8c9db3, purple: 0xa26bf0
  };
  // One colour per denominator, used everywhere a fraction piece is drawn.
  MB.denColor = function (d) {
    return ({ 1: 0x7bea8a, 2: 0xffcf33, 4: 0x2de0d0, 8: 0xa26bf0, 3: 0xff9340, 6: 0xff8cc0 })[d] || 0xe6f1ff;
  };
  // Bitmap font metrics (from assets/fonts/*.fnt): line height, baseline, capital height.
  MB.FONT = {
    ui20: { lh: 25, base: 20, cap: 14, bar: 2, gap: 2 },
    ui28: { lh: 35, base: 28, cap: 20, bar: 3, gap: 3 },
    ui44: { lh: 54, base: 43, cap: 31, bar: 4, gap: 4 },
    pix8: { lh: 8, base: 8, cap: 7, bar: 1, gap: 1 }
  };

  // ------------------------------------------------------------------ fractions
  var F = MB.F = {
    gcd: function (a, b) { a = Math.abs(a); b = Math.abs(b); while (b) { var t = a % b; a = b; b = t; } return a || 1; },
    make: function (n, d) { return { n: n, d: d }; },
    add: function (a, b) {
      var d = a.d * b.d / F.gcd(a.d, b.d);
      return { n: a.n * (d / a.d) + b.n * (d / b.d), d: d };
    },
    sub: function (a, b) { return F.add(a, { n: -b.n, d: b.d }); },
    cmp: function (a, b) { var v = a.n * b.d - b.n * a.d; return v < 0 ? -1 : v > 0 ? 1 : 0; },
    eq: function (a, b) { return a.n * b.d === b.n * a.d; },
    val: function (a) { return a.n / a.d; },
    simp: function (a) { var g = F.gcd(a.n, a.d); return { n: a.n / g, d: a.d / g }; },
    // express a with denominator den (returns null if it does not fit exactly)
    toDen: function (a, den) { var n = a.n * den / a.d; return Math.abs(n - Math.round(n)) < 1e-9 ? { n: Math.round(n), d: den } : null; },
    str: function (a) { return a.d === 1 ? String(a.n) : a.n + '/' + a.d; },
    words: function (a) {
      var num = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
      var den = { 2: ['half', 'halves'], 3: ['third', 'thirds'], 4: ['quarter', 'quarters'], 6: ['sixth', 'sixths'], 8: ['eighth', 'eighths'] };
      if (a.n === a.d) return 'one whole';
      if (a.n === 0) return 'zero';
      if (a.d === 1) return (num[a.n] || a.n) + (a.n === 1 ? ' whole' : ' wholes');
      var w = den[a.d];
      return (num[a.n] || a.n) + ' ' + (w ? w[a.n === 1 ? 0 : 1] : 'over ' + a.d);
    }
  };

  // ------------------------------------------------------------------ helpers
  MB.clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
  MB.approach = function (v, target, step) { return v < target ? Math.min(v + step, target) : Math.max(v - step, target); };
  MB.lerp = function (a, b, t) { return a + (b - a) * t; };
  // frame index of a named frame in a sheet (see assets/manifest/*.json)
  MB.fr = function (sheet, name) {
    var s = window.MB_ASSETS && MB_ASSETS.manifest.sheets[sheet];
    if (s && s.names && s.names[name] != null) return s.names[name];
    return 0;
  };
  // seeded random so decoration is identical on every load
  MB.rng = function (seed) {
    var s = seed >>> 0 || 1;
    return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  };
  // safe audio wrappers (audio is optional; the game never depends on it)
  MB.sfx = function (name, opts) { try { if (MB.Audio) MB.Audio.sfx(name, opts); } catch (e) { /* ignore */ } };
  MB.music = function (name, opts) { try { if (MB.Audio) MB.Audio.playMusic(name, opts); } catch (e) { /* ignore */ } };
  MB.isTouch = false;   // set true on the first touch event
})();
