/* Math Blast Arcade - UI kit: text, 9-slice panels, buttons, stacked fractions,
 * fraction bars, menus, dialogue box, radio toasts.  All sizes are screen pixels
 * (the UI art is authored at half size and drawn at 2x). */
(function () {
  'use strict';
  var UI = MB.UI = {};
  var COL = MB.COL;

  UI.text = function (scene, x, y, str, font, tint, ox, oy) {
    var t = scene.add.bitmapText(x, y, font || 'ui20', str == null ? '' : String(str));
    t.setOrigin(ox == null ? 0 : ox, oy == null ? 0 : oy);
    if (font === 'pix8') t.setScale(2);
    if (tint != null) t.setTint(tint);
    return t;
  };
  UI.shadow = function (t, a) { if (t.setDropShadow) t.setDropShadow(1, 2, COL.ink, a == null ? 0.85 : a); return t; };

  // Build (and cache) a stretched 9-slice texture. w,h in ART pixels.
  UI.panelTex = function (scene, src, w, h, slice, frame) {
    w = Math.max(slice * 2 + 1, Math.round(w)); h = Math.max(slice * 2 + 1, Math.round(h));
    var key = 'pn_' + src + '_' + (frame || 0) + '_' + w + 'x' + h;
    if (scene.textures.exists(key)) return key;
    var ct = scene.textures.createCanvas(key, w, h);
    var ctx = ct.getContext();
    ctx.imageSmoothingEnabled = false;
    var fr = scene.textures.getFrame(src, frame || 0);
    var img = fr.source.image, sx = fr.cutX, sy = fr.cutY, sw = fr.cutWidth, sh = fr.cutHeight, s = slice;
    var cs = [[0, s, 0, s], [s, sw - 2 * s, s, w - 2 * s], [sw - s, s, w - s, s]];
    var rs = [[0, s, 0, s], [s, sh - 2 * s, s, h - 2 * s], [sh - s, s, h - s, s]];
    for (var r = 0; r < 3; r++) for (var c = 0; c < 3; c++) {
      ctx.drawImage(img, sx + cs[c][0], sy + rs[r][0], cs[c][1], rs[r][1], cs[c][2], rs[r][2], cs[c][3], rs[r][3]);
    }
    ct.refresh();
    return key;
  };
  // Panel image at screen position/size.
  UI.panel = function (scene, x, y, w, h, src, frame, slice) {
    src = src || 'panel';
    var key = UI.panelTex(scene, src, w / 2, h / 2, slice || (src === 'tag' ? 4 : 8), frame);
    return scene.add.image(x, y, key).setOrigin(0, 0).setScale(2);
  };

  // ---------------------------------------------------------------- buttons
  // Centred at x,y. Returns a container with setFocus(bool), setLabel(str), w, h.
  UI.button = function (scene, x, y, w, h, label, onClick, opts) {
    opts = opts || {};
    var c = scene.add.container(x, y);
    var keys = [0, 1, 2].map(function (f) { return UI.panelTex(scene, 'button', w / 2, h / 2, 8, f); });
    var bg = scene.add.image(0, 0, keys[0]).setScale(2);
    var font = opts.font || 'ui20';
    var t = UI.text(scene, 0, 0, label, font, opts.tint != null ? opts.tint : COL.text, 0.5, 0);
    var m = MB.FONT[font];
    t.y = Math.round(-(m.base - m.cap / 2)) - 1;
    c.add([bg, t]);
    if (opts.icon != null) {
      var ic = scene.add.image(-w / 2 + 26, 0, 'hud', MB.fr('hud', opts.icon)).setScale(2);
      c.add(ic); t.x = 12; c.icon = ic;
    }
    c.w = w; c.h = h; c.bg = bg; c.label = t; c.focused = false; c.enabled = true;
    c.setSize(w, h);
    c.setInteractive({ useHandCursor: true });
    c.setFocus = function (f) { c.focused = f; bg.setTexture(keys[f ? 1 : 0]); t.setTint(f ? COL.white : (opts.tint != null ? opts.tint : COL.text)); };
    c.setLabel = function (s) { t.setText(s); };
    c.press = function () {
      if (!c.enabled) return;
      bg.setTexture(keys[2]);
      scene.time.delayedCall(90, function () { if (c.active) bg.setTexture(keys[c.focused ? 1 : 0]); });
      if (onClick) onClick(c);
    };
    c.on('pointerup', function () { if (c.menu) c.menu.focusItem(c); c.press(); });
    c.on('pointerover', function () { if (c.menu) c.menu.focusItem(c); else c.setFocus(true); });
    c.on('pointerout', function () { if (!c.menu) c.setFocus(false); });
    return c;
  };

  // Keyboard/touch focus manager for a list of buttons (or any object with setFocus/press).
  UI.Menu = function (scene, items, opts) {
    this.scene = scene; this.items = items; this.opts = opts || {}; this.i = 0; this.active = true;
    var self = this;
    items.forEach(function (it) { it.menu = self; });
    this.focus(this.opts.start || 0, true);
    this.handler = function (ev) {
      if (!self.active) return;
      var code = ev.code, hz = self.opts.horizontal;
      var it = self.items[self.i];
      if ((!hz && (code === 'ArrowUp' || code === 'KeyW')) || (hz && (code === 'ArrowLeft' || code === 'KeyA'))) self.move(-1);
      else if ((!hz && (code === 'ArrowDown' || code === 'KeyS')) || (hz && (code === 'ArrowRight' || code === 'KeyD'))) self.move(1);
      else if (!hz && (code === 'ArrowLeft' || code === 'KeyA') && it && it.onLeft) it.onLeft();
      else if (!hz && (code === 'ArrowRight' || code === 'KeyD') && it && it.onRight) it.onRight();
      else if (code === 'Enter' || code === 'Space' || code === 'KeyE' || code === 'NumpadEnter') { if (it && it.press) it.press(); }
      else if (code === 'Escape' && self.opts.onBack) self.opts.onBack();
    };
    scene.input.keyboard.on('keydown', this.handler);
  };
  UI.Menu.prototype.focus = function (i, silent) {
    var n = this.items.length; if (!n) return;
    this.i = (i + n) % n;
    for (var k = 0; k < n; k++) this.items[k].setFocus(k === this.i);
    if (!silent) MB.sfx('uiMove');
  };
  UI.Menu.prototype.focusItem = function (it) { var i = this.items.indexOf(it); if (i >= 0 && i !== this.i) this.focus(i); };
  UI.Menu.prototype.move = function (d) {
    var n = this.items.length, i = this.i;
    for (var k = 0; k < n; k++) { i = (i + d + n) % n; if (this.items[i].enabled !== false) break; }
    this.focus(i);
  };
  UI.Menu.prototype.destroy = function () { this.active = false; this.scene.input.keyboard.off('keydown', this.handler); };

  // ---------------------------------------------------------------- fractions
  // A properly stacked fraction (numerator over denominator with a bar).
  UI.Frac = function (scene, x, y, n, d, o) {
    o = o || {};
    var c = scene.add.container(x, y);
    c.font = o.font || 'ui28'; c.tintCol = o.tint != null ? o.tint : COL.white;
    var m = MB.FONT[c.font];
    c.tn = scene.add.bitmapText(0, 0, c.font, '').setOrigin(0.5, 0);
    c.td = scene.add.bitmapText(0, 0, c.font, '').setOrigin(0.5, 0);
    c.bar = scene.add.rectangle(0, 0, 10, m.bar, c.tintCol).setOrigin(0.5, 0.5);
    c.tp = scene.add.bitmapText(0, 0, c.font, '').setOrigin(1, 0);
    c.add([c.tn, c.td, c.bar, c.tp]);
    c.set = function (n2, d2, prefix) {
      c.n = n2; c.d = d2; c.prefix = prefix || '';
      c.tn.setText(String(n2)); c.td.setText(String(d2)); c.tp.setText(c.prefix);
      var whole = (d2 === 1);
      c.td.setVisible(!whole); c.bar.setVisible(!whole);
      var w = Math.max(c.tn.width, whole ? 0 : c.td.width);
      if (whole) {
        c.tn.y = Math.round(m.cap / 2 - m.base);
      } else {
        c.tn.y = Math.round(-(m.bar / 2 + m.gap) - m.base);
        c.td.y = Math.round(m.bar / 2 + m.gap - (m.base - m.cap));
        c.bar.width = w + Math.round(m.cap * 0.35);
      }
      c.tp.x = -Math.round(w / 2 + m.cap * 0.3); c.tp.y = Math.round(m.cap / 2 - m.base);
      c.fw = w + Math.round(m.cap * 0.35) + (c.prefix ? c.tp.width + 4 : 0);
      c.fh = whole ? m.cap : (m.cap * 2 + m.gap * 2 + m.bar);
      return c;
    };
    c.setCol = function (col) { c.tintCol = col; c.tn.setTint(col); c.td.setTint(col); c.tp.setTint(col); c.bar.setFillStyle(col); return c; };
    c.set(n, d, o.prefix);
    c.setCol(c.tintCol);
    return c;
  };

  // Draw a fraction bar ("bar model") into a Graphics object.
  // parts: [{n, d, color}] laid end to end; den: tick marks; whole: pixel width of one whole.
  UI.drawBar = function (g, x, y, whole, h, den, parts, o) {
    o = o || {};
    var total = o.span || 1;                       // how many wholes the track spans
    g.fillStyle(o.back != null ? o.back : 0x0d1126, 1); g.fillRect(x, y, whole * total, h);
    var px = x, i;
    for (i = 0; i < parts.length; i++) {
      var p = parts[i], w = whole * p.n / p.d;
      g.fillStyle(p.color, p.alpha == null ? 1 : p.alpha); g.fillRect(Math.round(px), y, Math.round(px + w) - Math.round(px), h);
      g.fillStyle(0xffffff, 0.35); g.fillRect(Math.round(px), y, Math.round(px + w) - Math.round(px), Math.max(2, Math.round(h * 0.18)));
      g.fillStyle(0x080a14, 0.25); g.fillRect(Math.round(px), y + h - Math.max(2, Math.round(h * 0.16)), Math.round(px + w) - Math.round(px), Math.max(2, Math.round(h * 0.16)));
      if (i > 0) { g.fillStyle(0x080a14, 0.9); g.fillRect(Math.round(px) - 1, y, 2, h); }
      px += w;
    }
    // ticks
    var ticks = den * total;
    for (i = 1; i < ticks; i++) {
      var tx = Math.round(x + whole * i / den);
      var major = (i % den === 0);
      g.fillStyle(major ? 0xffffff : 0xe6f1ff, major ? 0.95 : 0.55);
      g.fillRect(tx - 1, y - (major ? 4 : 0), 2, h + (major ? 8 : 0));
    }
    g.lineStyle(2, o.border != null ? o.border : 0x8ff7ea, 1); g.strokeRect(x - 1, y - 1, whole * total + 2, h + 2);
  };

  // ---------------------------------------------------------------- dialogue
  UI.Dialogue = function (scene) {
    this.s = scene;
    var x = 70, y = 380, w = 820, h = 146;
    this.x = x; this.y = y; this.w = w; this.h = h;
    this.c = scene.add.container(0, 0).setDepth(900).setVisible(false);
    this.panel = UI.panel(scene, x, y, w, h, 'panel');
    this.portBg = scene.add.rectangle(x + 20, y + 22, 102, 102, 0x0e4a5c).setOrigin(0, 0).setStrokeStyle(2, COL.cyan);
    this.port = scene.add.image(x + 23, y + 25, 'portraits', 0).setOrigin(0, 0).setScale(2);
    this.tag = null;
    this.name = UI.text(scene, 0, 0, '', 'pix8', COL.ink, 0, 0);
    this.txt = scene.add.bitmapText(x + 142, y + 24, 'ui20', '').setTint(COL.text);
    this.next = scene.add.image(x + w - 34, y + h - 30, 'hud', MB.fr('hud', 'key_e')).setScale(2);
    this.c.add([this.panel, this.portBg, this.port, this.name, this.txt, this.next]);
    scene.tweens.add({ targets: this.next, y: this.next.y - 4, duration: 420, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    this.queue = []; this.active = false; this.onDone = null; this.full = ''; this.pos = 0; this.acc = 0; this.openedAt = 0;
    this.baseY = 0;
  };
  // top = true puts the box at the top of the screen so the characters stay visible
  UI.Dialogue.prototype.anchor = function (top) { this.baseY = top ? -362 : 0; };
  UI.Dialogue.prototype.play = function (ids, onDone) {
    if (!ids || !ids.length) { if (onDone) onDone(); return; }
    this.queue = ids.slice(); this.onDone = onDone || null; this.active = true;
    this.s.tweens.killTweensOf(this.c);
    this.c.setVisible(true); this.c.alpha = 0; this.c.y = this.baseY + 16;
    this.s.tweens.add({ targets: this.c, alpha: 1, y: this.baseY, duration: 160, ease: 'Quad.out' });
    this.openedAt = this.s.time.now;
    if (MB.Audio) { try { MB.Audio.duck(0.45, 0.3); } catch (e) { /* ignore */ } }
    this.nextLine();
  };
  UI.Dialogue.prototype.nextLine = function () {
    var id = this.queue.shift();
    if (id == null) return this.close();
    var L = MB.STORY.lines[id] || { who: 'narrator', text: String(id) };
    var s = this.s, x = this.x, y = this.y, narr = !L.face;
    this.port.setVisible(!narr); this.portBg.setVisible(!narr);
    if (!narr) this.port.setFrame(MB.fr('portraits', L.face));
    // Priya's portraits face left; put her on the right-hand side so she faces into the box.
    var right = (L.who === 'priya');
    var px = right ? x + this.w - 122 : x + 20;
    this.portBg.x = px; this.port.x = px + 3;
    this.portBg.setStrokeStyle(2, L.who === 'phantom' ? COL.pink : L.who === 'priya' ? COL.cyan : COL.orange);
    if (this.tag) { this.tag.destroy(); this.tag = null; }
    var nm = MB.STORY.names[L.who] || '';
    this.name.setText(nm); this.name.setVisible(!!nm);
    if (nm) {
      var tw = this.name.width + 28;
      var tx = right ? x + this.w - 24 - tw : x + 136;
      this.tag = UI.panel(s, tx, y - 18, tw, 30, 'tag');
      this.c.addAt(this.tag, 1);
      this.name.x = tx + 14; this.name.y = y - 11;
      this.c.bringToTop(this.name);
    }
    var tx0 = narr ? x + 40 : (right ? x + 28 : x + 142);
    var maxw = narr ? this.w - 80 : this.w - 190;
    this.txt.x = tx0; this.txt.setTint(narr ? COL.cyanL : COL.text);
    this.txt.setMaxWidth(maxw); this.txt.setText(L.text);
    var b = this.txt.getTextBounds(false);
    this.full = (b && b.wrappedText) ? b.wrappedText : L.text;
    this.txt.setMaxWidth(0); this.txt.setText('');
    var lines = this.full.split('\n').length;
    this.txt.y = y + 30 + Math.max(0, (3 - lines)) * 10;
    this.next.x = right ? x + this.w - 150 : x + this.w - 34;
    this.next.setFrame(MB.fr('hud', MB.isTouch ? 'tap' : 'key_e'));
    this.next.setVisible(false);
    this.pos = 0; this.acc = 0; this.who = L.who; this.lineAt = s.time.now;
    this.voiced = false;
    if (MB.Audio) {
      try { MB.Audio.stopVoice(); this.voiced = !!MB.Audio.playVoice(id); } catch (e) { this.voiced = false; }
    }
    if (!this.voiced && MB.Save.get('readAloud') && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(L.text);
        u.rate = 0.98; u.pitch = L.who === 'jake' ? 1.35 : L.who === 'phantom' ? 0.7 : 1.0; u.volume = MB.Save.get('voice');
        window.speechSynthesis.speak(u);
      } catch (e) { /* ignore */ }
    }
  };
  UI.Dialogue.prototype.update = function (dt) {
    if (!this.active || this.pos >= this.full.length) return;
    this.acc += dt;
    var step = 24, changed = false;
    while (this.acc >= step && this.pos < this.full.length) {
      this.acc -= step; this.pos++; changed = true;
      var ch = this.full.charAt(this.pos - 1);
      if (ch === '.' || ch === '!' || ch === '?') this.acc -= 160; else if (ch === ',') this.acc -= 80;
      if (this.pos % 3 === 0 && ch !== ' ') MB.sfx('textBlip', { pitch: this.who === 'jake' ? 5 : this.who === 'phantom' ? -7 : this.who === 'priya' ? 2 : 0, vol: 0.5 });
    }
    if (changed) this.txt.setText(this.full.substring(0, this.pos));
    if (this.pos >= this.full.length) this.next.setVisible(true);
  };
  UI.Dialogue.prototype.advance = function () {
    if (!this.active) return false;
    if (this.s.time.now - this.lineAt < 180) return true;
    if (this.pos < this.full.length) { this.pos = this.full.length; this.txt.setText(this.full); this.next.setVisible(true); return true; }
    MB.sfx('uiSelect', { vol: 0.5 });
    this.nextLine();
    return true;
  };
  UI.Dialogue.prototype.skipAll = function () { if (this.active) { this.queue = []; this.close(); } };
  UI.Dialogue.prototype.close = function () {
    var self = this, cb = this.onDone;
    this.active = false; this.onDone = null;
    try { if (MB.Audio) { MB.Audio.stopVoice(); MB.Audio.duck(0, 0.4); } if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) { /* ignore */ }
    this.s.tweens.add({ targets: this.c, alpha: 0, y: this.baseY + 12, duration: 120, onComplete: function () { if (!self.active) self.c.setVisible(false); } });
    if (cb) cb();
  };

  // ---------------------------------------------------------------- radio toast
  // Small non-blocking message with a portrait (Priya on the radio, feedback, hints).
  UI.Toast = function (scene) {
    this.s = scene; this.q = []; this.busy = false;
    this.c = scene.add.container(0, 0).setDepth(880).setVisible(false);
  };
  UI.Toast.prototype.show = function (text, face, ms, opts) {
    this.q.push({ text: text, face: face || 'priya_neutral', ms: ms || Math.max(2600, 1400 + text.length * 55), opts: opts || {} });
    if (this.q.length > 2) this.q.splice(0, this.q.length - 2);
    if (!this.busy) this.pump();
  };
  UI.Toast.prototype.clear = function () { this.q = []; if (this.busy && this.timer) { this.timer.remove(); this.hide(); } };
  UI.Toast.prototype.pump = function () {
    var it = this.q.shift(), s = this.s, self = this;
    if (!it) { this.busy = false; return; }
    this.busy = true;
    this.c.removeAll(true);
    var t = s.add.bitmapText(0, 0, 'ui20', it.text).setTint(COL.text).setMaxWidth(it.opts.maxw || 560);
    var b = t.getTextBounds(false).local;
    var w = Math.max(260, Math.round(b.width) + 110), h = Math.max(72, Math.round(b.height) + 34);
    w += w % 2; h += h % 2;
    var x = Math.round((MB.CFG.W - w) / 2), y = it.opts.bottom ? MB.CFG.H - h - 6 : (it.opts.y != null ? it.opts.y : 96);
    var pn = UI.panel(s, x, y, w, h, 'panel_holo');
    var pb = s.add.rectangle(x + 14, y + 12, 52, 52, 0x0e4a5c).setOrigin(0, 0).setStrokeStyle(2, COL.cyan);
    var po = s.add.image(x + 16, y + 14, 'portraits', MB.fr('portraits', it.face)).setOrigin(0, 0);
    t.x = x + 82; t.y = y + Math.round((h - b.height) / 2) - 3;
    this.c.add([pn, pb, po, t]);
    this.c.setVisible(true); this.c.alpha = 0; this.c.y = -14;
    s.tweens.add({ targets: this.c, alpha: 1, y: 0, duration: 180, ease: 'Back.out' });
    this.timer = s.time.delayedCall(it.ms, function () { self.hide(); });
  };
  UI.Toast.prototype.hide = function () {
    var self = this;
    this.s.tweens.add({ targets: this.c, alpha: 0, y: -10, duration: 160, onComplete: function () { self.c.setVisible(false); self.pump(); } });
  };
})();
