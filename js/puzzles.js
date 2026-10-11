/* Math Blast Arcade - maths machines.  The fractions ARE the mechanics:
 *   qkey/qgate  - four quarter cells make one whole power cell (Area 1)
 *   bridge      - extend a hard-light bridge by adding fraction cells (Area 2)
 *   reactor     - bump +/- fraction blocks to fill a reactor to an exact level (Area 3, boss)
 *   cmpgate     - only the gate with the LARGER fraction opens (Area 4)
 *   pods        - hop the number-line pods from smallest to largest (Area 4)
 * Nothing here is timed; every wrong attempt has a visible, harmless consequence. */
(function () {
  'use strict';
  var COL = MB.COL, T = 16, F = MB.F, Ent = MB.Ent, U = MB.EntUtil, UI = MB.UI;

  // A small holo plate with a stacked fraction, in world space.
  MB.fracPlate = function (scene, x, y, n, d, o) {
    o = o || {};
    var c = scene.add.container(x, y).setDepth(o.depth == null ? 48 : o.depth);
    var fr = UI.Frac(scene, 0, 0, n, d, { font: o.font || 'ui28', prefix: o.prefix || '', tint: o.tint == null ? COL.white : o.tint });
    fr.setScale(0.5);
    var bg = scene.add.rectangle(0, 0, 10, 10, 0x0d1126, o.bgAlpha == null ? 0.92 : o.bgAlpha).setStrokeStyle(1, o.border == null ? MB.denColor(d) : o.border);
    c.add([bg, fr]); c.fr = fr; c.bg = bg;
    c.set = function (n2, d2, prefix, border) {
      fr.set(n2, d2, prefix);
      var w = Math.max(14, Math.ceil(fr.fw / 2) + 7), h = Math.ceil(fr.fh / 2) + 7;
      bg.setSize(w, h); bg.setOrigin(0.5, 0.5);
      bg.setStrokeStyle(1, border != null ? border : (o.border == null ? MB.denColor(d2) : o.border));
      fr.x = fr.prefix ? Math.round((fr.tp.width + 4) / 4) : 0;
      c.pw = w; c.ph = h;
      return c;
    };
    c.set(n, d, o.prefix);
    return c;
  };
  // small bar model in world space (art-pixel resolution)
  MB.miniBar = function (scene, x, y, w, h, n, d, depth) {
    var g = scene.add.graphics().setDepth(depth == null ? 48 : depth);
    g.redraw = function (n2, d2, col) {
      g.clear();
      g.fillStyle(0x0d1126, 1); g.fillRect(x - 1, y - 1, w + 2, h + 2);
      g.fillStyle(col == null ? MB.denColor(d2) : col, 1); g.fillRect(x, y, Math.round(w * n2 / d2), h);
      g.fillStyle(0xffffff, 0.35); g.fillRect(x, y, Math.round(w * n2 / d2), 1);
      g.fillStyle(0x080a14, 1);
      for (var i = 1; i < d2; i++) g.fillRect(x + Math.round(w * i / d2), y, 1, h);
      g.lineStyle(1, 0x8c9db3, 1); g.strokeRect(x - 0.5, y - 0.5, w + 1, h + 1);
    };
    g.redraw(n, d);
    return g;
  };

  function solvedFirst(scene, st) {
    scene.run.tests = (scene.run.tests || 0) + 1;
    if (st.attempts === 1 && !st.hinted) scene.run.firstTry = (scene.run.firstTry || 0) + 1;
    scene.run.puzzles = (scene.run.puzzles || 0) + 1;
  }
  function praise(scene) {
    var k = ['k01', 'k02', 'k03'][Math.floor(Math.random() * 3)];
    scene.toast(MB.STORY.lines[k].text, 'priya_smile', 2200);
  }

  // =================================================================== Area 1
  Ent.qkey = function (scene, e) {
    scene.qkeyTotal = (scene.qkeyTotal || 0) + 1;
    if (U.isGot(scene, e)) { scene.qkeys = (scene.qkeys || 0) + 1; return null; }
    var sp = scene.add.sprite(e.cx, e.cy, 'qkey').setDepth(43).play('qkey_glow');
    U.sensor(scene, sp, 16, 16);
    var gl = scene.fx.glow(e.cx, e.cy, COL.cyan, 0.9, 0.4);
    scene.tweens.add({ targets: [sp, gl], y: e.cy - 3, duration: 800, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    sp.onTouch = function () {
      if (sp.gone) return; sp.gone = true;
      U.markGot(scene, e);
      scene.qkeys = (scene.qkeys || 0) + 1;
      MB.sfx('qkey', { pitch: (scene.qkeys - 1) * 2 });
      scene.fx.ring(sp.x, sp.y, COL.cyan); scene.fx.sparks(sp.x, sp.y, 6, COL.cyanL, 22);
      var k = scene.qkeys;
      scene.fx.text(sp.x, sp.y - 10, k === 4 ? '4 quarters = 1 whole!' : k + (k === 1 ? ' quarter' : ' quarters'), COL.cyanL, 'ui28');
      scene.events.emit('qkey', k);
      gl.destroy(); sp.destroy();
    };
    return sp;
  };

  // Blast door that needs four quarter cells (one whole).
  Ent.qgate = function (scene, e) {
    e.bx += 8;                                   // centre the door on two tiles
    var sp = scene.add.sprite(e.bx, e.by, 'door', 0).setOrigin(0.5, 1).setDepth(30);
    U.solid(scene, sp);
    sp.body.setSize(20, 48); sp.body.setOffset(6, 0);
    var open = scene.isPowered('qgate');
    var sign = scene.add.image(e.bx, e.by - 66, 'sign_display', 0).setDepth(31);
    var pie = scene.add.image(e.bx, e.by - 66, 'hud', MB.fr('hud', 'pie0')).setDepth(32);
    var plate = MB.fracPlate(scene, e.bx + 30, e.by - 66, 0, 4, { depth: 32 });
    var gl = scene.fx.glow(e.bx, e.by - 44, COL.red, 0.5, 0.45);
    function show(k) {
      k = Math.min(4, k || 0);
      pie.setFrame(MB.fr('hud', 'pie' + k));
      plate.set(k, 4);
      sign.setFrame(k >= 4 ? 1 : 0);
    }
    show(scene.qkeys || 0);
    scene.events.on('qkey', function (k) { show(k); scene.tweens.add({ targets: pie, scale: 1.6, duration: 120, yoyo: true }); });
    function doOpen(instant) {
      sp.opened = true; sp.body.enable = false; gl.setTint(COL.green);
      if (instant) { sp.setFrame(7); return; }
      MB.sfx('doorOpen'); sp.play('door_open');
      scene.fx.sparks(e.bx, e.by - 44, 8, COL.green, 24);
    }
    if (open) { show(4); doOpen(true); }
    var told = 0;
    sp.onCollide = function (player) {
      if (sp.opened || sp.busy) return;
      if ((scene.qkeys || 0) >= 4) {
        sp.busy = true;
        scene.setPowered('qgate');
        MB.sfx('whole');
        scene.say(['j04'], function () { doOpen(false); });
      } else if (scene.time.now - told > 3000) {
        told = scene.time.now; MB.sfx('doorLocked');
        var k = scene.qkeys || 0;
        scene.toast('This gate needs 1 whole power cell. That is 4 quarter cells. You have ' + k + (k === 1 ? ' quarter' : ' quarters') + ' so far.');
      }
    };
    return sp;
  };

  // =================================================================== Area 2: energy bridge
  Ent.bridge = function (scene, e) {
    var gapX = e.gapX, gapW = e.gapW, row = e.row, den = e.den;
    var y = row * T, st = { attempts: 0, hinted: false };
    var solved = scene.isPowered(e.pid);
    var startN = Math.round(F.val(e.start) * gapW);

    var con = scene.add.sprite(e.bx, e.by, 'console').setOrigin(0.5, 1).setDepth(32).play(solved ? 'console_done' : 'console_idle');
    scene.fx.glow(e.bx, e.by - 22, COL.cyan, 0.7, 0.3);
    var em = scene.add.sprite(gapX * T - 12, y, 'bridge_emitter').setOrigin(0.5, 1).setDepth(33).play('bridge_emitter_idle');
    scene.fx.glow(gapX * T - 4, y - 6, COL.cyan, 0.8, 0.35);

    // planks: enough for the gap plus an overshoot zone
    var planks = [], over = Math.round(gapW / 2);
    for (var i = 0; i < gapW + over; i++) {
      var p = scene.add.sprite((gapX + i) * T + 8, y, 'bridge_seg').setOrigin(0.5, 0).setDepth(i < gapW ? 34 : 62);
      p.play({ key: 'bridge_seg_flow', startFrame: i % 4 });
      U.solid(scene, p, true);
      p.body.setSize(16, 6); p.body.setOffset(0, 0);
      p.setVisible(false); p.body.enable = false;
      planks.push(p);
    }
    function setPlank(i, mode, tint) {   // mode: 0 hidden, 1 solid, 2 ghost
      var p = planks[i]; if (!p) return;
      p.setVisible(mode > 0); p.setAlpha(mode === 2 ? 0.42 : 1);
      p.body.enable = (mode === 1 && i < gapW);
      if (tint != null && mode > 0) p.setTint(tint); else p.clearTint();
    }
    function showBase(n) { for (var k = 0; k < planks.length; k++) setPlank(k, k < n ? 1 : 0); }
    showBase(solved ? gapW : startN);

    // ruler under the gap
    var g = scene.add.graphics().setDepth(24);
    g.fillStyle(0x8c9db3, 0.9); g.fillRect(gapX * T, y + 15, gapW * T, 1);
    for (var t2 = 0; t2 <= den; t2++) {
      var rx = gapX * T + Math.round(gapW * T * t2 / den);
      g.fillStyle(t2 === den ? COL.gold : 0xe6f1ff, 0.95); g.fillRect(rx - (t2 === den ? 1 : 0), y + 12, t2 === den ? 2 : 1, 7);
      var lab = (t2 === 0) ? UI.text(scene, rx, y + 21, '0', 'ui20', COL.dim, 0.5, 0).setScale(0.5)
        : UI.Frac(scene, rx, y + 30, t2, den, { font: 'ui20', tint: t2 === den ? COL.gold : COL.dim }).setScale(0.5);
      lab.setDepth(24);
    }
    var endGlow = scene.fx.glow((gapX + gapW) * T, y - 2, COL.gold, 0.5, 0.35);
    scene.tweens.add({ targets: endGlow, alpha: 0.15, duration: 700, yoyo: true, repeat: -1 });

    function total(cells) { var s = e.start; cells.forEach(function (c) { s = F.add(s, c); }); return s; }
    function preview(cells) {
      var n = startN, k;
      showBase(startN);
      cells.forEach(function (c) {
        var len = Math.round(F.val(c) * gapW);
        for (k = 0; k < len; k++) setPlank(n + k, 2, (n + k) >= gapW ? COL.red : MB.denColor(c.d));
        n += len;
      });
    }

    var api = {
      onChange: function (cells, added) { preview(cells); if (added) MB.sfx('cellPlace'); else MB.sfx('cellRemove'); },
      onTest: function (cells, done) {
        st.attempts++;
        var sum = total(cells), n = Math.round(F.val(sum) * gapW), k = startN, cmp = F.cmp(sum, { n: 1, d: 1 });
        MB.sfx('bridgeExtend');
        em.anims.timeScale = 3;
        var ev = scene.time.addEvent({ delay: 45, repeat: Math.max(0, n - startN - 1), callback: function () {
          setPlank(k, 1, k >= gapW ? COL.red : null);
          scene.fx.sparks((gapX + k) * T + 8, y + 2, 1, COL.cyanL, 8);
          k++;
        } });
        scene.time.delayedCall(45 * Math.max(1, n - startN) + 260, function () {
          em.anims.timeScale = 1;
          var sumD = F.toDen(sum, den) || sum;
          if (cmp === 0) {
            MB.sfx('bridgeSolid'); MB.sfx('correct');
            scene.shake(0.004, 140);
            scene.fx.ring((gapX + gapW) * T, y, COL.gold, 1.2);
            for (var q = 0; q < gapW; q += 2) scene.fx.sparks((gapX + q) * T + 8, y, 2, COL.cyanL, 14);
            showBase(gapW);
            solvedFirst(scene, st);
            scene.setPowered(e.pid);
            con.play('console_done');
            done({ ok: true, msg: 'Exactly 1 whole. The bridge is complete!' });
          } else if (cmp < 0) {
            var gap = F.sub({ n: 1, d: 1 }, sum); gap = F.toDen(gap, den) || gap;
            MB.sfx('bridgeFail');
            scene.fx.sparks((gapX + n) * T, y + 2, 8, COL.orange, 20);
            scene.time.delayedCall(700, function () { preview(cells); });
            done({ ok: false, kind: 'short', msg: 'The bridge reaches ' + F.str(sumD) + '. It is still ' + F.str(gap) + ' short of 1 whole.' });
          } else {
            var ex = F.sub(sum, { n: 1, d: 1 }); ex = F.toDen(ex, den) || ex;
            MB.sfx('bridgeFail'); MB.sfx('zap', { vol: 0.5 });
            scene.shake(0.006, 200);
            for (var z = startN; z < n; z++) { setPlank(z, 1, COL.red); }
            scene.fx.sparks((gapX + gapW) * T, y, 10, COL.red, 26);
            scene.time.delayedCall(700, function () { preview(cells); });
            done({ ok: false, kind: 'long', msg: 'Overload! ' + F.str(sumD) + ' is ' + F.str(ex) + ' more than 1 whole.' });
          }
        });
      },
      onHint: function () { st.hinted = true; scene.run.hints = (scene.run.hints || 0) + 1; },
      onClose: function (ok) {
        scene.player.unfreeze(); scene.inConsole = false; scene.ctl.flush();
        scene.releaseCamera();
        con.play(ok || scene.isPowered(e.pid) ? 'console_done' : 'console_idle');
        if (!scene.isPowered(e.pid)) showBase(startN);
        if (ok) {
          scene.player.pose = 'celebrate';
          scene.time.delayedCall(900, function () { scene.player.pose = null; if (e.sayDone) scene.say(e.sayDone); });
        }
      }
    };
    scene.interactables.push({
      x: e.bx, y: e.by - 12, r: 22,
      can: function () { return !scene.isPowered(e.pid); },
      act: function () {
        scene.inConsole = true;
        scene.player.freeze('interact'); scene.player.facing = 1;
        con.play('console_active');
        MB.sfx('uiSelect');
        scene.focusCamera((gapX + gapW / 2) * T, null);
        scene.hud.console.open({
          title: e.title || 'ENERGY BRIDGE', goal: e.goal || 'Add energy cells so the bridge is exactly 1 whole long.',
          den: den, start: e.start, target: { n: 1, d: 1 }, cells: e.cells, hints: e.hints || [], span: 1.5
        }, api);
      }
    });
    return con;
  };

  // =================================================================== Area 3: reactor + bump blocks
  // Shared "tank" logic used by the reactors and by the boss cannon.
  MB.FracTank = function (scene, cfg) {
    this.s = scene; this.cfg = cfg;
    this.value = cfg.start; this.start = cfg.start; this.target = cfg.target; this.den = cfg.den;
    this.busy = false; this.locked = false;
  };

  Ent.reactor = function (scene, e) {
    var st = { attempts: 0, hinted: false };
    var solved = scene.isPowered(e.pid);
    var bx = e.bx + 8, by = e.by;                 // e.tx is the left-centre tile of a 4-tile-wide vessel
    var left = bx - 32 + 20, top = by - 112 + 16, TW = 24, TH = 80;
    scene.add.image(bx, by, 'reactor_back').setOrigin(0.5, 1).setDepth(26);
    var liq = scene.add.graphics().setDepth(27);
    var surf = scene.add.sprite(left, top, 'liquid_top').setOrigin(0, 0).setDepth(27).play('liquid_top_wave');
    scene.add.image(bx, by, 'reactor_front').setOrigin(0.5, 1).setDepth(28);
    var glow = scene.fx.glow(bx, by - 56, COL.cyan, 1.6, solved ? 0.5 : 0.18, 'glow_soft');
    var value = solved ? e.target : e.start, shown = F.val(value), col = COL.cyan;

    // tick marks on both sides of the tube
    var g = scene.add.graphics().setDepth(29);
    for (var i = 0; i <= e.den; i++) {
      var ty = top + TH - Math.round(TH * i / e.den);
      var major = (i === 0 || i === e.den || (e.den === 8 && i % 2 === 0));
      g.fillStyle(0xe6f1ff, major ? 0.95 : 0.6); g.fillRect(left - (major ? 5 : 3), ty, major ? 5 : 3, 1);
    }
    // target marker (right side) and live level pointer (left side)
    var tyT = top + TH - Math.round(TH * F.val(e.target));
    g.fillStyle(COL.gold, 1); g.fillRect(left + TW, tyT, 7, 1); g.fillTriangle(left + TW + 1, tyT, left + TW + 6, tyT - 3, left + TW + 6, tyT + 4);
    g.fillStyle(COL.gold, 0.35); g.fillRect(left, tyT, TW, 1);
    var tPlate = MB.fracPlate(scene, bx + 36, tyT, e.target.n, e.target.d, { border: COL.gold, tint: COL.gold, depth: 49 });
    tPlate.x = bx + 40;
    UI.text(scene, bx + 40, tyT - Math.round(tPlate.ph / 2) - 11, 'TARGET', 'pix8', COL.gold, 0.5, 0).setScale(1).setDepth(49);
    var vPlate = MB.fracPlate(scene, bx - 45, top + TH, 0, e.den, { depth: 49 });
    var ptr = scene.add.graphics().setDepth(49);

    function draw() {
      var lvl = Math.round(TH * shown);
      liq.clear();
      if (lvl > 0) {
        liq.fillStyle(col, 1); liq.fillRect(left, top + TH - lvl, TW, lvl);
        liq.fillStyle(0xffffff, 0.22); liq.fillRect(left + 2, top + TH - lvl, 3, lvl);
        liq.fillStyle(0x080a14, 0.22); liq.fillRect(left + TW - 4, top + TH - lvl, 4, lvl);
      }
      surf.setVisible(lvl > 2); surf.y = top + TH - lvl - 4; surf.setTint(col);
      var py = top + TH - lvl;
      ptr.clear(); ptr.fillStyle(0xffffff, 1); ptr.fillRect(left - 14, py, 10, 1); ptr.fillTriangle(left - 4, py, left - 9, py - 3, left - 9, py + 4);
      vPlate.y = MB.clamp(py, top + 8, top + TH - 2);
    }
    function label() { var v = F.toDen(value, e.den) || value; vPlate.set(v.n, v.d); }
    function animTo(v, ms, cb) {
      var o = { t: shown };
      scene.tweens.add({ targets: o, t: F.val(v), duration: ms || 380, ease: 'Quad.out', onUpdate: function () { shown = o.t; draw(); }, onComplete: function () { shown = F.val(v); draw(); if (cb) cb(); } });
    }
    label(); draw();
    if (solved) { col = COL.green; draw(); }

    var tank = { busy: false };
    function vent(msg) {
      tank.busy = true;
      MB.sfx('reactorVent'); scene.shake(0.005, 220);
      for (var k = 0; k < 6; k++) scene.fx.dust(bx - 20 + Math.random() * 40, top - 2 - Math.random() * 6, 2);
      scene.fx.one('fx_poof', bx - 14, top - 6, 76); scene.fx.one('fx_poof', bx + 14, top - 6, 76);
      col = COL.red; draw();
      scene.toast(msg, 'priya_neutral');
      scene.time.delayedCall(450, function () {
        value = e.start; label(); col = COL.cyan;
        animTo(value, 600, function () { tank.busy = false; });
      });
    }
    // called by bump blocks
    tank.apply = function (delta, sign, block) {
      if (tank.busy || scene.isPowered(e.pid)) { MB.sfx('blockBump', { vol: 0.3, pitch: -8 }); return; }
      var nv = sign > 0 ? F.add(value, delta) : F.sub(value, delta);
      var txt = (sign > 0 ? '+' : '–') + F.str(delta);
      scene.fx.text(block.x, block.y - 34, txt, sign > 0 ? COL.green : COL.pink, 'ui28');
      if (nv.n < 0) {
        MB.sfx('wrong');
        scene.toast('You cannot take away ' + F.str(delta) + '. There is only ' + F.str(F.toDen(value, e.den) || value) + ' in the reactor.');
        return;
      }
      if (F.cmp(nv, { n: 1, d: 1 }) > 0) {
        MB.sfx(sign > 0 ? 'blockBump' : 'blockBumpMinus');
        tank.busy = true;
        animTo({ n: 1, d: 1 }, 220, function () { vent('Overflow! That would be ' + F.str(F.toDen(nv, e.den) || nv) + ', which is more than 1 whole. The reactor has reset.'); });
        return;
      }
      value = nv; label();
      MB.sfx(sign > 0 ? 'blockBump' : 'blockBumpMinus'); MB.sfx('reactorFill', { vol: 0.7 });
      animTo(value, 380);
      scene.tweens.add({ targets: vPlate, scale: 1.25, duration: 100, yoyo: true });
    };
    tank.test = function (lever) {
      if (tank.busy || scene.isPowered(e.pid)) return;
      st.attempts++;
      var c = F.cmp(value, e.target), v = F.toDen(value, e.den) || value;
      tank.busy = true;
      MB.sfx('lever');
      lever.setFrame(1);
      scene.time.delayedCall(110, function () {
        lever.setFrame(2);
        if (c === 0) {
          MB.sfx('reactorOnline'); MB.sfx('correct');
          col = COL.green; draw();
          scene.shake(0.005, 260);
          scene.tweens.add({ targets: glow, alpha: 0.55, duration: 500 });
          scene.fx.ring(bx, by - 56, COL.green, 1.6); scene.fx.sparks(bx, by - 100, 10, COL.green, 30);
          solvedFirst(scene, st);
          scene.setPowered(e.pid);
          scene.player.pose = 'celebrate';
          scene.time.delayedCall(1000, function () {
            scene.player.pose = null; tank.busy = false;
            if (e.sayDone) scene.say(e.sayDone, function () { if (e.after && scene.def.on[e.after]) scene.def.on[e.after](scene, e); });
            else if (e.after && scene.def.on[e.after]) scene.def.on[e.after](scene, e);
          });
        } else if (c < 0) {
          MB.sfx('wrong');
          scene.tweens.add({ targets: glow, alpha: 0.05, duration: 120, yoyo: true, repeat: 2 });
          var need = F.sub(e.target, value);
          scene.toast('The reactor stalls. ' + F.str(v) + ' is less than ' + F.str(e.target) + '. ' +
            (st.attempts > 1 ? 'It needs ' + F.str(F.toDen(need, e.den) || need) + ' more.' : 'It needs more energy.'), 'priya_neutral');
          scene.time.delayedCall(600, function () { lever.setFrame(0); tank.busy = false; });
        } else {
          tank.busy = false;
          vent('Too much! ' + F.str(v) + ' is more than ' + F.str(e.target) + '. The reactor vented and reset.');
          scene.time.delayedCall(600, function () { lever.setFrame(0); });
        }
      });
    };
    scene.tanks[e.pid] = tank;
    scene.hinters.push({ x: bx - 60, y: by - 40, rx: 250, ry: 130, hints: e.hints || [],
      active: function () { return !scene.isPowered(e.pid); }, onHint: function () { st.hinted = true; } });
    return tank;
  };

  // Bump block: e.tx,e.ty = top-left tile of the 2x2 block. props: tank (pid), n, d, sign
  Ent.fblock = function (scene, e) {
    var x = e.tx * T + 16, y = e.ty * T + 16, plus = (e.sign || 1) > 0;
    var sp = scene.add.sprite(x, y, 'fblock', MB.fr('fblock', plus ? 'plus' : 'minus')).setDepth(40);
    U.solid(scene, sp);
    var sym = UI.text(scene, x, y, plus ? '+' : '–', 'ui44', plus ? COL.green : COL.pink, 0.5, 0).setScale(0.5).setDepth(41);
    sym.y = y - 15;
    var plate = MB.fracPlate(scene, x, y - 34, e.n, e.d, { prefix: plus ? '+' : '–', depth: 48, border: plus ? COL.greenD : COL.pink });
    var cd = 0, y0 = y;
    function off() { sp.setFrame(MB.fr('fblock', 'off')); sym.setTint(COL.dim); plate.setAlpha(0.5); }
    if (scene.isPowered(e.tank)) off();
    scene.events.on('power', function (id) { if (id === e.tank) off(); });
    sp.tick = function (dt) { if (cd > 0) cd -= dt; };
    sp.onBump = function () {
      if (cd > 0) return; cd = 260;
      scene.tweens.add({ targets: [sp], y: y0 - 5, duration: 70, yoyo: true, ease: 'Quad.out' });
      scene.tweens.add({ targets: sym, y: y0 - 20, duration: 70, yoyo: true, ease: 'Quad.out' });
      scene.tweens.add({ targets: plate, y: y0 - 39, duration: 70, yoyo: true, ease: 'Quad.out' });
      scene.fx.sparks(x, y + 14, 3, plus ? COL.green : COL.pink, 12);
      var tank = scene.tanks[e.tank];
      if (tank) tank.apply({ n: e.n, d: e.d }, plus ? 1 : -1, sp);
    };
    scene.updaters.push(sp);
    return sp;
  };

  Ent.lever = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'lever', scene.isPowered(e.tank) ? 2 : 0).setOrigin(0.5, 1).setDepth(33);
    scene.interactables.push({
      x: e.bx, y: e.by - 10, r: 20,
      can: function () { var t = scene.tanks[e.tank]; return t && !t.busy && !scene.isPowered(e.tank) && (!t.canTest || t.canTest()); },
      act: function () { scene.tanks[e.tank].test(sp); }
    });
    return sp;
  };

  // Power-controlled energy wall. e.tx, e.ty = top tile; h tiles tall.
  Ent.barrier = function (scene, e) {
    var h = e.h || 3, parts = [];
    var z = scene.add.zone(e.cx, e.ty * T + h * T / 2, 10, h * T);
    U.solid(scene, z);
    for (var i = 0; i < h; i++) {
      var b = scene.add.sprite(e.cx, e.ty * T + i * T + 8, 'barrier').setDepth(45).setTint(e.color == null ? COL.orange : e.color);
      b.play({ key: 'barrier_on', startFrame: i % 4 }); parts.push(b);
    }
    function open(instant) {
      z.body.enable = false;
      parts.forEach(function (b, k) {
        if (instant) b.destroy(); else scene.tweens.add({ targets: b, alpha: 0, scaleX: 0.2, delay: k * 50, duration: 220, onComplete: function () { b.destroy(); } });
      });
      if (!instant) { if (scene.nearCamera(e.cx, e.ty * T)) MB.sfx('gateOpen'); scene.fx.sparks(e.cx, e.ty * T + h * 8, 8, COL.green, 26); }
    }
    if (scene.isPowered(e.power)) open(true);
    else scene.events.on('power', function (id) { if (id === e.power) open(false); });
    return z;
  };

  // =================================================================== Area 4: compare gates
  // e.tx = barrier column. props: a:{n,d,y0,h}, b:{n,d,y0,h}  (two openings; the LARGER fraction opens)
  Ent.cmpgate = function (scene, e) {
    var solved = scene.isPowered(e.pid), sides = [e.a, e.b], objs = [], st = { attempts: 0, hinted: false };
    var bigger = F.cmp(e.a, e.b) > 0 ? 0 : 1;
    scene.hinters.push({ x: e.cx - 70, y: 14 * T, rx: 150, ry: 400, hints: e.hints || [],
      active: function () { return !scene.isPowered(e.pid); }, onHint: function () { st.hinted = true; } });
    sides.forEach(function (sd, idx) {
      var h = sd.h || 4, x = e.cx, top = sd.y0 * T;
      var z = scene.add.zone(x, top + h * T / 2, 10, h * T);
      U.solid(scene, z);
      var parts = [];
      for (var i = 0; i < h; i++) {
        var b = scene.add.sprite(x, top + i * T + 8, 'barrier').setDepth(45).setTint(COL.cyan);
        b.play({ key: 'barrier_on', startFrame: i % 4 }); parts.push(b);
      }
      var sx = x - 40, sy = top + h * T / 2 - 6;
      var board = scene.add.rectangle(sx, sy, 50, 52, 0x0a1322, 0.94).setStrokeStyle(1, COL.cyan).setDepth(31);
      var sign = { setFrame: function (f) { board.setStrokeStyle(f ? 2 : 1, f === 1 ? COL.green : f === 2 ? COL.red : COL.cyan); } };
      var plate = MB.fracPlate(scene, sx, sy - 8, sd.n, sd.d, { depth: 33, bgAlpha: 0 });
      plate.bg.setStrokeStyle(0);
      var bar = MB.miniBar(scene, sx - 20, sy + 15, 40, 7, sd.n, sd.d, 33);
      scene.fx.glow(sx, sy, COL.cyan, 0.9, 0.2);
      var o = { z: z, parts: parts, sign: sign, sd: sd };
      function open(instant) {
        z.body.enable = false; sign.setFrame(1);
        parts.forEach(function (b, k) {
          if (instant) b.destroy(); else scene.tweens.add({ targets: b, alpha: 0, scaleX: 0.2, delay: k * 50, duration: 220, onComplete: function () { b.destroy(); } });
        });
      }
      o.open = open;
      if (solved && idx === bigger) open(true);
      var told = 0;
      z.onCollide = function (player) {
        if (scene.isPowered(e.pid) || scene.time.now - told < 900) return;
        told = scene.time.now;
        st.attempts++;
        var other = sides[1 - idx];
        if (idx === bigger) {
          MB.sfx('gateOpen'); MB.sfx('correct', { vol: 0.7 });
          open(false);
          scene.fx.ring(x, top + h * 8, COL.green); scene.fx.sparks(x, top + h * 8, 8, COL.green, 26);
          scene.fx.text(sx, sy - 30, F.str(sd) + ' is greater than ' + F.str(other), COL.green, 'ui28');
          solvedFirst(scene, st);
          scene.setPowered(e.pid);
          if (e.sayDone) scene.time.delayedCall(500, function () { scene.say(e.sayDone); }); else praise(scene);
        } else {
          MB.sfx('gateWrong');
          sign.setFrame(2);
          scene.time.delayedCall(900, function () { if (!scene.isPowered(e.pid) || idx !== bigger) sign.setFrame(0); });
          player.body.velocity.x = -130; player.body.velocity.y = -60 * player.gdir;
          scene.fx.sparks(x - 6, player.centerY(), 5, COL.redL, 16);
          var sameDen = sd.d === other.d;
          scene.toast(F.str(sd) + ' is smaller than ' + F.str(other) + '. ' +
            (sameDen ? 'The pieces are the same size, so count how many there are.' : 'Look at the bars under each fraction. Which bar is filled further?'), 'priya_neutral');
        }
      };
      objs.push(o);
    });
    return objs;
  };

  // =================================================================== Area 4: number-line pods
  // props: pid, list: [{tx, ty, n, d}]
  Ent.pods = function (scene, e) {
    var solved = scene.isPowered(e.pid), st = { attempts: 0, hinted: false };
    var order = e.list.slice().sort(function (a, b) { return F.cmp(a, b); });
    var next = solved ? order.length : 0, pods = [], last = null;
    var FR = { idle: MB.fr('pod', 'idle'), ok: MB.fr('pod', 'correct'), bad: MB.fr('pod', 'wrong'), done: MB.fr('pod', 'done') };
    e.list.forEach(function (pd) {
      var x = pd.tx * T + 8, y = pd.ty * T;
      var sp = scene.add.sprite(x, y, 'pod', solved ? FR.done : FR.idle).setOrigin(0.5, 0).setDepth(41);
      U.solid(scene, sp, true);
      sp.body.setSize(44, 8); sp.body.setOffset(2, 0);
      sp.pd = pd; sp.rank = order.indexOf(pd); sp.state = solved ? 'done' : 'idle';
      MB.miniBar(scene, x - 11, y + 8, 22, 6, pd.n, pd.d, 42);
      MB.fracPlate(scene, x, y + 33, pd.n, pd.d, { depth: 42 });
      scene.fx.glow(x, y + 22, COL.cyan, 0.7, 0.25);
      sp.onStand = function () {
        if (last === sp || scene.isPowered(e.pid)) { last = sp; return; }
        last = sp;
        if (sp.state === 'ok') return;
        if (sp.rank === next) {
          sp.state = 'ok'; sp.setFrame(FR.ok); next++;
          MB.sfx('podStep', { pitch: next * 2 });
          scene.fx.sparks(x, y, 5, COL.green, 16);
          if (next === order.length) {
            pods.forEach(function (p) { p.state = 'done'; p.setFrame(FR.done); scene.fx.sparks(p.x, p.y, 5, COL.gold, 18); });
            MB.sfx('correct');
            solvedFirst(scene, st);
            scene.setPowered(e.pid);
            scene.fx.text(x, y - 34, 'Smallest to largest!', COL.gold, 'ui28');
            if (e.sayDone) scene.time.delayedCall(700, function () { scene.say(e.sayDone); });
          }
        } else {
          st.attempts++;
          MB.sfx('podWrong');
          var want = order[next];
          pods.forEach(function (p) { if (p.state !== 'done') { p.state = 'idle'; p.setFrame(FR.idle); } });
          sp.setFrame(FR.bad);
          scene.time.delayedCall(650, function () { if (sp.state === 'idle') sp.setFrame(FR.idle); });
          var first = (next === 0);
          next = 0;
          scene.toast(first ? 'Start on the smallest fraction. Compare the bars on the pods.'
            : F.str(pd) + ' is not the next one. After that pod comes ' + (st.attempts > 2 ? F.str(want) + '.' : 'the next smallest fraction.') + ' Start again from the smallest.', 'priya_neutral');
        }
      };
      pods.push(sp);
    });
    var mx = 0; e.list.forEach(function (pd) { mx += pd.tx * T; }); mx /= e.list.length;
    scene.hinters.push({ x: mx, y: e.list[0].ty * T + 40, rx: 250, ry: 160, hints: e.hints || [],
      active: function () { return !scene.isPowered(e.pid); }, onHint: function () { st.hinted = true; } });
    scene.podGroups.push({ leave: function () { last = null; }, debug: function () { return { next: next, states: pods.map(function (p) { return p.pd.n + '/' + p.pd.d + ':' + p.state; }) }; } });
    return pods;
  };
})();
