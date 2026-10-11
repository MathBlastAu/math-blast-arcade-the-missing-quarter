/* Math Blast Arcade - HUD scene (drawn above the game at full canvas resolution):
 * hearts, fuel-quarter pie, secrets, area banner, dialogue, radio toasts, the
 * fraction console, touch controls, pause/options menus, fades and iris wipes. */
(function () {
  'use strict';
  var C = MB.CFG, COL = MB.COL, UI = MB.UI, F = MB.F;
  var W = C.W, H = C.H;
  MB.TOTAL_STARS = 4;

  // =================================================================== options panel (shared with the title screen)
  MB.OptionsPanel = function (scene, onClose, depth) {
    var c = scene.add.container(0, 0).setDepth(depth || 960);
    var dim = scene.add.rectangle(0, 0, W, H, 0x05060c, 0.72).setOrigin(0, 0).setInteractive();
    var pw = 520, ph = 424, px = (W - pw) / 2, py = (H - ph) / 2;
    c.add([dim, UI.panel(scene, px, py, pw, ph, 'panel'), UI.text(scene, W / 2, py + 22, 'OPTIONS', 'pix8', COL.cyan, 0.5, 0)]);
    var S = MB.Save, items = [], y = py + 74;
    function row(label, get, change, fmt) {
      var b = UI.button(scene, W / 2, y, 440, 44, '', function () { change(1); upd(); MB.sfx('uiSelect'); });
      var tl = UI.text(scene, -200, -13, label, 'ui20', COL.text, 0, 0);
      var tv = UI.text(scene, 200, -13, '', 'ui20', COL.gold, 1, 0);
      b.add([tl, tv]);
      function upd() { tv.setText(fmt(get())); }
      b.onLeft = function () { change(-1); upd(); MB.sfx('uiMove'); };
      b.onRight = function () { change(1); upd(); MB.sfx('uiMove'); };
      upd(); c.add(b); items.push(b); y += 50;
    }
    function vol(key) {
      row({ music: 'Music volume', sfx: 'Sound effects', voice: 'Voice volume' }[key], function () { return S.get(key); }, function (d) {
        var v = Math.round(S.get(key) * 10) + d; if (v > 10) v = 0; if (v < 0) v = 10;
        S.set(key, v / 10); S.applyAudio();
      }, function (v) { var n = Math.round(v * 10); return n === 0 ? 'Off' : '← ' + n + ' →'; });
    }
    function toggle(key, label, on, off) {
      row(label, function () { return S.get(key); }, function () { S.set(key, !S.get(key)); }, function (v) { return v ? (on || 'On') : (off || 'Off'); });
    }
    vol('music'); vol('sfx');
    toggle('relaxed', 'Relaxed mode (no heart loss)');
    toggle('shake', 'Screen shake');
    if (window.speechSynthesis) toggle('readAloud', 'Read story aloud (device voice)');
    if (window.MB_ASSETS && Object.keys(MB_ASSETS.audio || {}).length) vol('voice');
    var back = UI.button(scene, W / 2, y + 6, 200, 44, 'Back', function () { close(); });
    c.add(back); items.push(back);
    var menu = new UI.Menu(scene, items, { onBack: function () { close(); } });
    function close() { MB.sfx('uiBack'); menu.destroy(); c.destroy(); if (onClose) onClose(); }
    this.close = close;
  };

  // =================================================================== fraction console (bridge puzzles)
  function ConsoleUI(hud) {
    this.s = hud; this.active = false;
    this.c = hud.add.container(0, 0).setDepth(700).setVisible(false);
  }
  ConsoleUI.prototype.open = function (cfg, api) {
    var s = this.s, self = this, c = this.c;
    c.removeAll(true);
    this.cfg = cfg; this.api = api; this.active = true; this.busy = false; this.placed = []; this.hintI = 0;
    var PX = 40, PY = 6, PW = 880, PH = 252;
    c.add(UI.panel(s, PX, PY, PW, PH, 'panel_holo'));
    c.add(UI.text(s, PX + 24, PY + 16, cfg.title, 'pix8', COL.cyan));
    this.msg = s.add.bitmapText(PX + 24, PY + 38, 'ui20', cfg.goal).setTint(COL.text).setMaxWidth(PW - 48);
    c.add(this.msg);
    this.eq = s.add.container(370, PY + 100); c.add(this.eq);
    this.g = s.add.graphics(); c.add(this.g);
    this.x0 = 150; this.by = PY + 134; this.W1 = 440; this.bh = 26;
    var den = cfg.den, span = cfg.span || 1.5, i;
    for (i = 0; i <= den * span; i++) {
      var tx = this.x0 + Math.round(this.W1 * i / den), lab;
      if (i === 0) lab = UI.text(s, tx, PY + 172, '0', 'ui20', COL.dim, 0.5, 0);
      else if (i === den) lab = UI.Frac(s, tx, PY + 184, 1, 1, { font: 'ui28', tint: COL.gold });
      else lab = UI.Frac(s, tx, PY + 184, i, den, { font: 'ui20', tint: i > den ? COL.redL : COL.dim });
      c.add(lab);
    }
    c.add(UI.text(s, this.x0 + this.W1 + 8, this.by - 14, '1 WHOLE', 'pix8', COL.gold, 0, 0).setScale(1));
    // tray + actions
    var items = [], by = PY + 224;
    this.cellBtns = [];
    cfg.cells.forEach(function (cell, k) {
      var b = UI.button(s, PX + 85 + k * 128, by, 122, 44, '', function () { self.addCell(k); });
      var col = MB.denColor(cell.d);
      var bar = s.add.graphics();
      var bw = Math.max(8, Math.round(64 * cell.n / cell.d));
      bar.fillStyle(col, 1); bar.fillRect(-54, -8, bw, 16);
      bar.fillStyle(0xffffff, 0.35); bar.fillRect(-54, -8, bw, 4);
      bar.lineStyle(2, COL.ink, 1); bar.strokeRect(-54, -8, bw, 16);
      var fr = UI.Frac(s, 30, 0, cell.n, cell.d, { font: 'ui20', tint: col });
      var cnt = UI.text(s, 56, 6, '', 'pix8', COL.dim, 1, 0).setScale(1);
      b.add([bar, fr, cnt]); b.cell = cell; b.left = cell.c || 1; b.cnt = cnt;
      c.add(b); items.push(b); self.cellBtns.push(b);
    });
    var undo = UI.button(s, 520, by, 104, 44, 'Undo', function () { self.undo(); });
    var hint = UI.button(s, 634, by, 104, 44, 'Hint', function () { self.hint(); }, { tint: COL.gold });
    var go = UI.button(s, 772, by, 150, 44, 'POWER ON', function () { self.test(); }, { tint: COL.green });
    var ex = UI.button(s, 884, by, 52, 44, '', function () { self.close(false); }, { icon: 'exit' });
    ex.icon.x = 0;
    c.add([undo, hint, go, ex]); items.push(undo, hint, go, ex);
    this.menu = new UI.Menu(s, items, { horizontal: true, onBack: function () { if (!self.busy) self.close(false); } });
    this.redraw();
    c.setVisible(true); c.alpha = 0; c.y = -30;
    s.tweens.add({ targets: c, alpha: 1, y: 0, duration: 200, ease: 'Quad.out' });
    try { if (MB.Audio) MB.Audio.duck(0.35, 0.3); } catch (e) { /* ignore */ }
    s.toast.clear();
    s.showStatus(false);
    s.tweens.killTweensOf(s.bannerC); s.bannerC.y = -80;
  };
  ConsoleUI.prototype.total = function () { var t = this.cfg.start; this.placed.forEach(function (p) { t = F.add(t, p); }); return t; };
  ConsoleUI.prototype.say = function (text, col) { this.msg.setText(text); this.msg.setTint(col == null ? COL.text : col); };
  ConsoleUI.prototype.redraw = function () {
    var s = this.s, cfg = this.cfg, g = this.g, self = this;
    // bar model
    g.clear();
    var span = cfg.span || 1.5, x0 = this.x0, y = this.by, W1 = this.W1, h = this.bh;
    var parts = [];
    if (cfg.start.n > 0) parts.push({ n: cfg.start.n, d: cfg.start.d, color: 0xb9c7d6 });
    this.placed.forEach(function (p) { parts.push({ n: p.n, d: p.d, color: MB.denColor(p.d) }); });
    // overflow zone
    g.fillStyle(0x3a0a18, 1); g.fillRect(x0 + W1, y, W1 * (span - 1), h);
    UI.drawBar(g, x0, y, W1, h, cfg.den, [], { span: 1 });
    var px = x0;
    parts.forEach(function (p, i) {
      var w = W1 * p.n / p.d, a = Math.round(px), b = Math.min(Math.round(px + w), x0 + Math.round(W1 * span));
      var over = (px + w) > x0 + W1 + 0.5;
      g.fillStyle(p.color, 1); g.fillRect(a, y, b - a, h);
      g.fillStyle(0xffffff, 0.35); g.fillRect(a, y, b - a, 5);
      g.fillStyle(0x080a14, 0.25); g.fillRect(a, y + h - 5, b - a, 5);
      if (over) { g.fillStyle(0xe8384f, 0.55); g.fillRect(Math.max(a, x0 + W1), y, b - Math.max(a, x0 + W1), h); }
      if (i > 0) { g.fillStyle(0x080a14, 1); g.fillRect(a - 1, y, 2, h); }
      px += w;
    });
    for (var i = 1; i < cfg.den * span; i++) {
      var tx = x0 + Math.round(W1 * i / cfg.den);
      g.fillStyle(0xe6f1ff, i % cfg.den === 0 ? 0 : 0.5); g.fillRect(tx - 1, y, 2, h);
    }
    g.lineStyle(2, 0x8ff7ea, 1); g.strokeRect(x0 - 1, y - 1, W1 * span + 2, h + 2);
    g.fillStyle(COL.gold, 1); g.fillRect(x0 + W1 - 2, y - 6, 4, h + 12);
    // equation
    var eq = this.eq; eq.removeAll(true);
    var els = [], x = 0;
    function addFrac(fr, col) { var o = UI.Frac(s, 0, 0, fr.n, fr.d, { font: 'ui28', tint: col }); els.push({ o: o, w: Math.max(18, o.fw) }); }
    function addOp(t, col) { var o = UI.text(s, 0, -22, t, 'ui28', col == null ? COL.text : col, 0.5, 0); els.push({ o: o, w: o.width + 4 }); }
    if (cfg.start.n > 0) addFrac(cfg.start, 0xb9c7d6);
    this.placed.forEach(function (p, i) { if (i > 0 || cfg.start.n > 0) addOp('+'); addFrac(p, MB.denColor(p.d)); });
    if (!this.placed.length) { addOp('+'); addOp('?', COL.gold); }
    else { addOp('='); var t = this.total(); addFrac(F.toDen(t, cfg.den) || t, COL.white); }
    var total = 0; els.forEach(function (e) { total += e.w + 14; }); total -= 14;
    x = -total / 2;
    els.forEach(function (e) { e.o.x = Math.round(x + e.w / 2); eq.add(e.o); x += e.w + 14; });
    // tray counts
    this.cellBtns.forEach(function (b) {
      b.cnt.setText(b.cell.c > 1 ? 'x' + b.left : '');
      b.enabled = b.left > 0; b.setAlpha(b.left > 0 ? 1 : 0.35);
    });
  };
  ConsoleUI.prototype.addCell = function (k) {
    var b = this.cellBtns[k];
    if (this.busy || !b || b.left <= 0) return;
    var t = F.add(this.total(), b.cell);
    if (F.val(t) > (this.cfg.span || 1.5) + 1e-9) { MB.sfx('wrong'); this.say('That is far too long to fit. Try a smaller cell.', COL.redL); return; }
    b.left--; this.placed.push({ n: b.cell.n, d: b.cell.d, k: k });
    this.say(this.cfg.goal);
    this.redraw();
    this.api.onChange(this.placed, true);
  };
  ConsoleUI.prototype.undo = function () {
    if (this.busy || !this.placed.length) { MB.sfx('uiBack'); return; }
    var p = this.placed.pop(); this.cellBtns[p.k].left++;
    this.say(this.cfg.goal);
    this.redraw();
    this.api.onChange(this.placed, false);
  };
  ConsoleUI.prototype.hint = function () {
    if (this.busy) return;
    var hs = this.cfg.hints; if (!hs.length) return;
    MB.sfx('hintOpen');
    this.say('Hint: ' + hs[Math.min(this.hintI, hs.length - 1)], COL.gold);
    this.hintI++;
    if (this.api.onHint) this.api.onHint();
  };
  ConsoleUI.prototype.test = function () {
    var self = this;
    if (this.busy) return;
    if (!this.placed.length) { MB.sfx('wrong'); this.say('Add an energy cell first, then switch the power on.', COL.gold); return; }
    this.busy = true; this.menu.active = false;
    this.say('Powering up...', COL.cyanL);
    this.api.onTest(this.placed.slice(), function (res) {
      self.say(res.msg, res.ok ? COL.green : (res.kind === 'long' ? COL.redL : COL.gold));
      if (res.ok) {
        self.s.time.delayedCall(1500, function () { self.close(true); });
      } else {
        self.s.time.delayedCall(500, function () { self.busy = false; if (self.menu) self.menu.active = true; });
      }
    });
  };
  ConsoleUI.prototype.close = function (ok) {
    if (!this.active) return;
    var self = this, api = this.api;
    this.active = false; this.busy = false;
    if (this.menu) { this.menu.destroy(); this.menu = null; }
    try { if (MB.Audio) MB.Audio.duck(0, 0.4); } catch (e) { /* ignore */ }
    if (!ok) MB.sfx('uiBack');
    this.s.showStatus(true);
    this.s.tweens.add({ targets: this.c, alpha: 0, y: -30, duration: 160, onComplete: function () { self.c.setVisible(false); self.c.removeAll(true); } });
    if (api) api.onClose(ok);
  };

  // =================================================================== HUD scene
  MB.Scenes.Hud = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Hud() { Phaser.Scene.call(this, { key: 'Hud' }); },

    create: function () {
      var self = this, i;
      this.game2 = null; this.paused = false;
      this.input.addPointer(3);
      this.add.image(0, 0, 'vignette').setOrigin(0, 0).setScale(2).setDepth(1).setAlpha(0.85);

      // hearts
      this.hearts = [];
      for (i = 0; i < C.HEARTS; i++) this.hearts.push(this.add.image(30 + i * 36, 30, 'hud', MB.fr('hud', 'heart_full')).setScale(2).setDepth(10));
      // quarters: whole orbs + pie of the current whole
      this.orb = this.add.image(30, 72, 'hud', MB.fr('hud', 'whole')).setScale(2).setDepth(10);
      this.orbT = UI.shadow(UI.text(this, 52, 62, 'x0', 'pix8', COL.gold).setDepth(10));
      this.pie = this.add.image(126, 72, 'hud', MB.fr('hud', 'pie0')).setScale(2).setDepth(10);
      this.pieF = UI.Frac(this, 162, 72, 0, 4, { font: 'ui20', tint: COL.gold }).setDepth(10);
      // secrets
      this.star = this.add.image(W - 132, 30, 'hud', MB.fr('hud', 'starcell_empty')).setScale(2).setDepth(10);
      this.starT = UI.shadow(UI.text(this, W - 112, 20, '0/' + MB.TOTAL_STARS, 'pix8', COL.cyanL).setDepth(10));
      // pause button (mouse + touch)
      this.pauseBtn = this.add.image(W - 34, 32, 'touch', MB.fr('touch', 'pause')).setDepth(12).setAlpha(0.8).setInteractive({ useHandCursor: true });
      this.pauseBtn.on('pointerup', function () { if (self.canPause()) self.openPause(); });

      // optional hint button (only shown near an unsolved maths machine)
      this.hintBtn = this.add.image(W - 34, 86, 'hud', MB.fr('hud', 'hint')).setScale(2).setDepth(12).setVisible(false).setInteractive({ useHandCursor: true });
      this.hintKey = UI.shadow(UI.text(this, W - 34, 106, 'H', 'pix8', COL.gold, 0.5, 0).setScale(1).setDepth(12).setVisible(false));
      this.hintBtn.on('pointerdown', function () { MB.touch.hint = true; });
      this.tweens.add({ targets: this.hintBtn, scale: 2.3, duration: 600, yoyo: true, repeat: -1, ease: 'Sine.inOut' });

      // boss bar
      this.bossC = this.add.container(W / 2, 26).setDepth(10).setVisible(false);
      this.bossC.add(UI.shadow(UI.text(this, 0, -14, 'FRACTION PHANTOM', 'pix8', COL.pink, 0.5, 0).setScale(1)));
      this.bossPips = [];
      for (i = 0; i < 3; i++) { var r = this.add.rectangle(-44 + i * 44, 14, 36, 12, COL.pink).setStrokeStyle(2, COL.ink); this.bossPips.push(r); this.bossC.add(r); }

      // banner
      this.bannerC = this.add.container(W / 2, -80).setDepth(600);
      this.bannerC.add(UI.panel(this, -220, -36, 440, 76, 'panel_holo'));
      this.bannerSub = UI.text(this, 0, -24, '', 'pix8', COL.cyan, 0.5, 0).setScale(1);
      this.bannerName = UI.text(this, 0, -12, '', 'ui28', COL.white, 0.5, 0);
      this.bannerC.add([this.bannerSub, this.bannerName]);

      this.dialogue = new UI.Dialogue(this);
      this.toast = new UI.Toast(this);
      this.console = new ConsoleUI(this);

      // touch controls
      this.touchBtns = [];
      var mk = function (name, x, y, sc) {
        var b = self.add.image(x, y, 'touch', MB.fr('touch', name)).setScale(sc).setDepth(500).setAlpha(0.78).setVisible(false);
        b.setInteractive(); b.tname = name; b.pid = -1;
        var down = function (pointer) { b.pid = pointer.id; MB.touch[name] = true; b.setFrame(MB.fr('touch', name + '_on')); };
        var up = function () { b.pid = -1; MB.touch[name] = false; b.setFrame(MB.fr('touch', name)); };
        b.on('pointerdown', down);
        b.on('pointerover', function (pointer) { if (pointer.isDown) down(pointer); });
        b.on('pointerout', up); b.on('pointerup', up);
        b.release = up;
        self.touchBtns.push(b);
        return b;
      };
      mk('left', 76, 462, 2.5); mk('right', 196, 462, 2.5);
      this.btnJump = mk('jump', 882, 452, 2.7); this.btnAct = mk('interact', 770, 484, 2.1);
      this.input.on('pointerup', function (pointer) { self.touchBtns.forEach(function (b) { if (b.pid === pointer.id) b.release(); }); });
      this.forceTouch = MB.QUERY.has('touch');

      // overlays
      this.flashR = this.add.rectangle(0, 0, W, H, 0xffffff, 0).setOrigin(0, 0).setDepth(980);
      this.fadeR = this.add.rectangle(0, 0, W, H, 0x05060c, 0).setOrigin(0, 0).setDepth(985);
      this.iris = this.add.graphics().setDepth(990);
      this.irisR = 0; this.irisOn = false;

      // input: advance dialogue
      this.input.keyboard.on('keydown', function (ev) {
        if (!self.dialogue.active) return;
        if (ev.code === 'KeyE' || ev.code === 'Space' || ev.code === 'Enter' || ev.code === 'KeyX' || ev.code === 'NumpadEnter') self.dialogue.advance();
        else if (ev.code === 'Escape') self.dialogue.skipAll();
      });
      this.input.on('pointerdown', function () { if (self.dialogue.active) self.dialogue.advance(); });

      this.events.once('shutdown', function () { self.ready = false; MB.clearTouch(); });
      this.ready = true;
      this.events.emit('hud-ready');
    },

    showStatus: function (v) {
      var list = this.hearts.concat([this.orb, this.orbT, this.pie, this.pieF, this.star, this.starT]);
      for (var i = 0; i < list.length; i++) list[i].setVisible(v);
    },

    attach: function (game) {
      this.game2 = game;
      this.showStatus(true);
      this.paused = false;
      if (this.console.active) { this.console.active = false; this.console.c.setVisible(false); if (this.console.menu) { this.console.menu.destroy(); this.console.menu = null; } }
      this.bossC.setVisible(false);
      this.fadeR.setAlpha(0);
    },
    detach: function () { this.game2 = null; },

    refresh: function (pulse) {
      var g = this.game2; if (!g) return;
      var run = g.run, i;
      for (i = 0; i < this.hearts.length; i++) this.hearts[i].setFrame(MB.fr('hud', i < run.hearts ? 'heart_full' : 'heart_empty'));
      var wholes = Math.floor(run.quarters / 4), q = run.quarters % 4;
      this.orbT.setText('x' + wholes);
      this.pie.setFrame(MB.fr('hud', 'pie' + q));
      this.pieF.set(q, 4);
      var stars = Object.keys(run.stars).length;
      this.star.setFrame(MB.fr('hud', stars > 0 ? 'starcell' : 'starcell_empty'));
      this.starT.setText(stars + '/' + MB.TOTAL_STARS);
      if (pulse) {
        this.tweens.killTweensOf(this.pie); this.pie.setScale(2);
        this.tweens.add({ targets: this.pie, scale: 2.7, duration: 90, yoyo: true });
        if (q === 0) { this.tweens.killTweensOf(this.orb); this.orb.setScale(2); this.tweens.add({ targets: this.orb, scale: 3.2, duration: 160, yoyo: true, ease: 'Back.out' }); }
      }
    },

    banner: function (name, sub) {
      var c = this.bannerC, self = this;
      this.bannerName.setText(name); this.bannerSub.setText(sub || '');
      this.tweens.killTweensOf(c); c.y = -80;
      this.tweens.add({ targets: c, y: 150, duration: 450, ease: 'Back.out', onComplete: function () {
        self.tweens.add({ targets: c, y: -80, delay: 2000, duration: 350, ease: 'Quad.in' });
      } });
    },

    bossBar: function (show, hp) {
      this.bossC.setVisible(!!show);
      for (var i = 0; i < this.bossPips.length; i++) this.bossPips[i].setFillStyle(i < hp ? COL.pink : 0x2a1657);
    },

    setHintAvailable: function (on) {
      on = on && !this.console.active && !this.paused;
      if (this.hintBtn.visible !== on) { this.hintBtn.setVisible(on); this.hintKey.setVisible(on && !MB.isTouch); }
    },

    setInteractHint: function (on) {
      if (this.btnAct) this.btnAct.setAlpha(on ? 1 : 0.5);
    },

    flash: function (col, a) {
      this.flashR.setFillStyle(col, 1); this.flashR.setAlpha(a == null ? 0.4 : a);
      this.tweens.killTweensOf(this.flashR);
      this.tweens.add({ targets: this.flashR, alpha: 0, duration: 260 });
    },
    fade: function (out, ms, cb) {
      this.tweens.killTweensOf(this.fadeR);
      this.tweens.add({ targets: this.fadeR, alpha: out ? 1 : 0, duration: ms || 250, onComplete: function () { if (cb) cb(); } });
    },

    // iris wipe centred on a WORLD position of the game camera
    screenPos: function (x, y) {
      var g = this.game2; if (!g) return { x: W / 2, y: H / 2 };
      var cam = g.cameras.main;
      var lx = MB.clamp(cam.scrollX + 240, 0, Math.max(0, g.pxW - C.VW)), ly = MB.clamp(cam.scrollY + 135, 0, Math.max(0, g.pxH - C.VH));
      return { x: MB.clamp((x - lx) * 2, 0, W), y: MB.clamp((y - ly) * 2, 0, H) };
    },
    drawIris: function () {
      var g = this.iris; g.clear();
      if (!this.irisOn) return;
      var r = Math.max(0, this.irisR), th = 1400;
      g.lineStyle(th, 0x05060c, 1);
      g.strokeCircle(this.irisX, this.irisY, r + th / 2);
      if (r <= 1) { g.fillStyle(0x05060c, 1); g.fillRect(0, 0, W, H); }
    },
    irisOut: function (x, y, cb) {
      var self = this, p = this.screenPos(x, y);
      this.irisX = p.x; this.irisY = p.y; this.irisOn = true; this.irisR = 1150;
      MB.sfx('irisOut');
      this.tweens.add({ targets: this, irisR: 0, duration: 520, ease: 'Quad.in', onUpdate: function () { self.drawIris(); }, onComplete: function () { self.irisR = 0; self.drawIris(); if (cb) cb(); } });
    },
    irisIn: function (x, y) {
      var self = this, p = this.screenPos(x, y);
      this.irisX = p.x; this.irisY = p.y; this.irisOn = true; this.irisR = 0; this.drawIris();
      MB.sfx('irisIn');
      this.tweens.add({ targets: this, irisR: 1150, delay: 120, duration: 560, ease: 'Quad.out', onUpdate: function () { self.drawIris(); }, onComplete: function () { self.irisOn = false; self.drawIris(); } });
    },

    // ---------------------------------------------------------------- pause menu
    canPause: function () {
      var g = this.game2;
      return g && g.started && !g.over && !this.paused && !this.dialogue.active && !this.console.active && !g.player.locked && !this.irisOn;
    },
    openPause: function () {
      if (!this.canPause()) return;
      var self = this, g = this.game2;
      this.paused = true;
      MB.clearTouch();
      this.scene.pause('Game');
      MB.sfx('pause');
      try { if (MB.Audio) MB.Audio.duck(0.6, 0.2); } catch (e) { /* ignore */ }
      var c = this.pauseC = this.add.container(0, 0).setDepth(940);
      var dim = this.add.rectangle(0, 0, W, H, 0x05060c, 0.66).setOrigin(0, 0).setInteractive();
      var pw = 420, ph = 392, px = (W - pw) / 2, py = (H - ph) / 2;
      c.add([dim, UI.panel(this, px, py, pw, ph, 'panel'), UI.text(this, W / 2, py + 22, 'PAUSED', 'pix8', COL.cyan, 0.5, 0)]);
      var items = [], y = py + 78;
      var add = function (label, fn) { var b = UI.button(self, W / 2, y, 320, 46, label, fn); c.add(b); items.push(b); y += 54; };
      add('Resume', function () { self.closePause(); });
      add('How to play', function () { self.showHelp(); });
      add('Options', function () { self.pauseMenu.active = false; c.setVisible(false); new MB.OptionsPanel(self, function () { c.setVisible(true); self.pauseMenu.active = true; }); });
      add('Back to checkpoint', function () { self.closePause(true); g.run.hearts = C.HEARTS; g.scene.restart(); });
      add('Quit to title', function () {
        self.closePause(true); MB.Save.store();
        self.detach(); self.scene.stop('Game'); self.scene.start('Title');
      });
      this.pauseMenu = new UI.Menu(this, items, { onBack: function () { self.closePause(); } });
    },
    closePause: function (silent) {
      if (!this.paused) return;
      this.paused = false;
      if (this.pauseMenu) { this.pauseMenu.destroy(); this.pauseMenu = null; }
      if (this.pauseC) { this.pauseC.destroy(); this.pauseC = null; }
      if (!silent) MB.sfx('unpause');
      try { if (MB.Audio) MB.Audio.duck(0, 0.3); } catch (e) { /* ignore */ }
      this.scene.resume('Game');
      if (this.game2 && this.game2.ctl) this.game2.ctl.flush();
    },
    showHelp: function () {
      var self = this, c = this.add.container(0, 0).setDepth(960);
      var dim = this.add.rectangle(0, 0, W, H, 0x05060c, 0.8).setOrigin(0, 0).setInteractive();
      c.add([dim]);
      MB.buildHelp(this, c);
      this.pauseMenu.active = false;
      var b = UI.button(this, W / 2, 478, 200, 44, 'Back', function () { m.destroy(); c.destroy(); self.pauseMenu.active = true; MB.sfx('uiBack'); });
      c.add(b);
      var m = new UI.Menu(this, [b], { onBack: function () { b.press(); } });
    },

    update: function (time, delta) {
      this.dialogue.update(delta);
      var g = this.game2;
      var showTouch = (MB.isTouch || this.forceTouch) && g && g.started && !this.dialogue.active && !this.console.active && !this.paused && !g.over;
      for (var i = 0; i < this.touchBtns.length; i++) {
        var b = this.touchBtns[i];
        if (b.visible !== showTouch) { b.setVisible(showTouch); if (!showTouch) b.release(); }
      }
      this.pauseBtn.setVisible(!!(g && g.started && !this.console.active && !g.over));
    }
  });

  // "How to play" card, used by the pause menu and the title screen.
  MB.buildHelp = function (scene, c) {
    var px = 130, py = 56, pw = 700, ph = 384;
    c.add(UI.panel(scene, px, py, pw, ph, 'panel'));
    c.add(UI.text(scene, W / 2, py + 22, 'HOW TO PLAY', 'pix8', COL.cyan, 0.5, 0));
    var rows = [
      [['key_left', 'key_right'], 'Move   (or A and D)'],
      [['key_space'], 'Jump   (hold for a higher jump)'],
      [['key_e'], 'Use consoles and levers, continue the story'],
      [['key_esc'], 'Pause'],
      [['pie3'], 'Collect fuel quarters. Four quarters make one whole.'],
      [['hint'], 'Maths machines are never timed. Press H (or tap the bulb) for a hint.'],
      [['heart_full'], 'Checkpoints refill your hearts. Relaxed mode is in Options.']
    ];
    var y = py + 70;
    rows.forEach(function (r) {
      var x = px + 40;
      r[0].forEach(function (ic) { c.add(scene.add.image(x + 16, y + 10, 'hud', MB.fr('hud', ic)).setScale(2)); x += 38; });
      c.add(UI.text(scene, px + 130, y - 2, r[1], 'ui20', COL.text));
      y += 43;
    });
    if (MB.isTouch) c.add(UI.text(scene, W / 2, py + ph - 34, 'On a touch screen use the buttons at the bottom of the screen.', 'ui20', COL.gold, 0.5, 0));
  };
})();
