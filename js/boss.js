/* Math Blast Arcade - the Fraction Phantom showdown.
 * Beats alternate so that maths is never timed:
 *   ATTACK  - dodge the Phantom's fraction bolts (action, no maths)
 *   THINK   - the Phantom waits behind its shield for as long as you like.
 *             Bump the +/- blocks to charge the restorer cannon so it EXACTLY
 *             matches the shield, then pull the lever.
 *   STRIKE  - a matching beam shatters the shield; stomp the stunned Phantom.
 * Phase 1: add quarters (1/4 + 2/4 = 3/4)
 * Phase 2: equivalent fractions (how many eighths make 1/2?)
 * Phase 3: take away + equivalence (7/8 - ?/8 = 3/4) */
(function () {
  'use strict';
  var COL = MB.COL, T = 16, F = MB.F, UI = MB.UI, U = MB.EntUtil;

  var PHASES = [
    { den: 4, start: { n: 0, d: 4 }, shield: { n: 3, d: 4 },
      blocks: [{ n: 1, d: 4, s: 1 }, { n: 2, d: 4, s: 1 }, null],
      tip: 'The shield is 3/4. Bump the blocks to add quarters until the cannon matches, then pull the lever.',
      hints: ['Count the quarters in the shield bar. The cannon bar must be filled exactly as far.', '1/4 + 2/4 = 3/4. Bump each green block once, then pull the lever.'] },
    { den: 8, start: { n: 0, d: 8 }, shield: { n: 1, d: 2 },
      blocks: [{ n: 1, d: 8, s: 1 }, { n: 3, d: 8, s: 1 }, { n: 1, d: 8, s: -1 }],
      tip: 'The shield is 1/2, but the cannon counts in eighths. Compare the two bars on the wall.',
      hints: ['Look at the wall bars. How many eighths reach as far as 1/2?', '1/2 is the same as 4/8. Try 3/8 + 1/8.'] },
    { den: 8, start: { n: 7, d: 8 }, shield: { n: 3, d: 4 },
      blocks: [{ n: 1, d: 8, s: -1 }, { n: 3, d: 8, s: -1 }, { n: 2, d: 8, s: 1 }],
      tip: 'The cannon has 7/8, which is too much. The shield is 3/4. Take some away until the bars match.',
      hints: ['Change 3/4 into eighths. How many eighths is that?', '3/4 is the same as 6/8. 7/8 take away 1/8 leaves 6/8.'] }
  ];
  var BLOCK_TILES = [[4, 9], [8, 9], [24, 9]];
  var STUN_X = 312;                 // clear floor between the cannon and the right-hand block

  MB.Ent.boss = function (scene, e) { scene.boss = new Boss(scene, e); return scene.boss; };

  function Boss(scene, e) {
    var self = this;
    this.s = scene;
    this.floorY = e.by;
    this.cx = 240;
    var run = scene.run;
    this.hp = (run.bossHp != null) ? run.bossHp : 3;
    if (this.hp <= 0) this.hp = 3;
    this.phase = 3 - this.hp;
    this.state = 'wait'; this.t = 0; this.attempts = 0;
    this.value = { n: 0, d: 4 };

    // cannon + lever
    this.cannon = scene.add.sprite(this.cx, this.floorY, 'cannon').setOrigin(0.5, 1).setDepth(33).play('cannon_idle');
    this.lever = scene.add.sprite(196, this.floorY, 'lever', 0).setOrigin(0.5, 1).setDepth(34);
    scene.interactables.push({
      x: 196, y: this.floorY - 10, r: 20,
      can: function () { return self.state === 'think' && !self.busy; },
      act: function () { self.fire(); }
    });

    // bump blocks
    this.blocks = BLOCK_TILES.map(function (bt, i) {
      var x = bt[0] * T + 16, y = bt[1] * T + 16;
      var sp = scene.add.sprite(x, y, 'fblock', MB.fr('fblock', 'off')).setDepth(40);
      U.solid(scene, sp);
      var sym = UI.text(scene, x, y - 15, '', 'ui44', COL.dim, 0.5, 0).setScale(0.5).setDepth(41);
      var plate = MB.fracPlate(scene, x, y - 34, 1, 4, { depth: 48 });
      var b = { sp: sp, sym: sym, plate: plate, op: null, cd: 0, y0: y };
      sp.onBump = function () { self.bump(b); };
      return b;
    });

    // wall board: SHIELD bar above CANNON bar, same scale, so they can be compared
    var bx = 292, by = 22;
    scene.add.rectangle(bx - 8, by, 156, 60, 0x0a1322, 0.92).setOrigin(0, 0).setStrokeStyle(1, COL.cyan).setDepth(24);
    UI.text(scene, bx, by + 4, 'SHIELD', 'pix8', COL.pink).setScale(1).setDepth(25);
    UI.text(scene, bx, by + 32, 'CANNON', 'pix8', COL.cyanL).setScale(1).setDepth(25);
    this.barS = MB.miniBar(scene, bx, by + 15, 96, 8, 0, 4, 25);
    this.barC = MB.miniBar(scene, bx, by + 43, 96, 8, 0, 4, 25);
    this.plS = MB.fracPlate(scene, bx + 124, by + 15, 3, 4, { font: 'ui20', depth: 25, border: COL.pink });
    this.plC = MB.fracPlate(scene, bx + 124, by + 44, 0, 4, { font: 'ui20', depth: 25, border: COL.cyan });

    // the Phantom
    this.sp = scene.add.sprite(this.cx, 74, 'phantom').setDepth(50).setVisible(false);
    this.ring = scene.add.graphics().setDepth(51);
    this.glow = scene.fx.glow(this.cx, 74, COL.cyan, 2.2, 0, 'glow_soft');
    this.hit = scene.add.zone(this.cx, 74, 38, 28);
    U.sensor(scene, this.hit);
    this.hit.body.enable = false;
    this.hit.onTouch = function (player) { self.touch(player); };
    this.shieldOn = false; this.shieldA = 0; this.ringT = 0;

    this.hinter = { x: 240, y: 180, rx: 400, ry: 300, i: 0, hints: function () { return PHASES[self.phase].hints; },
      active: function () { return self.state === 'think' && !self.busy; }, onHint: function () { self.attempts += 1; } };
    scene.hinters.push(this.hinter);
    this.applyPhase(true);
    scene.time.delayedCall(700, function () { self.intro(); });
  }

  Boss.prototype.applyPhase = function (silent) {
    var ph = PHASES[this.phase], self = this;
    this.value = ph.start;
    this.blocks.forEach(function (b, i) {
      var op = ph.blocks[i];
      b.op = op;
      b.plate.setVisible(!!op); b.sym.setVisible(!!op);
      if (op) { b.plate.set(op.n, op.d, op.s > 0 ? '+' : '–', op.s > 0 ? COL.greenD : COL.pink); b.sym.setText(op.s > 0 ? '+' : '–'); }
    });
    this.setBlocksLive(false);
    this.barS.redraw(ph.shield.n, ph.shield.d, COL.pink);
    this.plS.set(ph.shield.n, ph.shield.d, '', COL.pink);
    this.showValue();
  };
  Boss.prototype.setBlocksLive = function (live) {
    this.blocks.forEach(function (b) {
      var on = live && b.op;
      b.sp.setFrame(MB.fr('fblock', on ? (b.op.s > 0 ? 'plus' : 'minus') : 'off'));
      b.sym.setTint(on ? (b.op.s > 0 ? COL.green : COL.pink) : COL.dim);
      b.plate.setAlpha(on ? 1 : 0.45);
    });
  };
  Boss.prototype.showValue = function () {
    var ph = PHASES[this.phase], v = F.toDen(this.value, ph.den) || this.value;
    this.barC.redraw(v.n, v.d, COL.cyan);
    this.plC.set(v.n, v.d, '', COL.cyan);
  };

  // ------------------------------------------------------------------ flow
  Boss.prototype.intro = function () {
    var self = this, s = this.s, sp = this.sp;
    s.cutscene = true;
    s.player.freeze();
    MB.music(null);
    MB.sfx('bossAppear');
    sp.setVisible(true).play('phantom_appear');
    s.tweens.add({ targets: this.glow, alpha: 0.35, duration: 600 });
    s.shake(0.004, 300);
    sp.once('animationcomplete', function () {
      sp.play('phantom_float');
      s.hud.bossBar(true, self.hp);
      var lines = s.run.seen.bossIntro ? ['f07'] : ['f06', 'j12', 'f07', 'p14'];
      s.run.seen.bossIntro = 1;
      s.say(lines, function () {
        s.cutscene = false; s.player.unfreeze();
        MB.music('boss'); self.setIntensity();
        self.raiseShield();
        self.startAttack();
      });
    });
  };
  Boss.prototype.setIntensity = function () { try { if (MB.Audio) MB.Audio.setIntensity(this.phase); } catch (e) { /* ignore */ } };
  Boss.prototype.raiseShield = function () { this.shieldOn = true; MB.sfx('bossTelegraph', { vol: 0.5 }); };

  Boss.prototype.after = function (ms, fn) {
    var self = this, token = this.token;
    return this.s.time.delayedCall(ms, function () { if (self.token === token && self.state !== 'defeat') fn(); });
  };

  Boss.prototype.startAttack = function () {
    var self = this, p = this.phase, t = 600;
    this.state = 'attack'; this.token = (this.token || 0) + 1; this.busy = false;
    this.setBlocksLive(false);
    this.lever.setFrame(0);
    var add = function (dur, fn) { self.after(t, fn); t += dur; };
    if (p === 0) {
      add(1500, function () { self.volley(1); }); add(1500, function () { self.volley(1); }); add(1700, function () { self.volley(1); });
      add(2600, function () { self.sweep(-1); });
    } else if (p === 1) {
      add(2600, function () { self.rain(4); });
      add(1400, function () { self.volley(2); }); add(1800, function () { self.volley(2); });
      add(1500, function () { self.sweep(1); }); add(2600, function () { self.sweep(-1); });
    } else {
      add(1500, function () { self.volley(2); }); add(2400, function () { self.rain(5); });
      add(1300, function () { self.sweep(-1); }); add(2000, function () { self.sweep(1); });
      add(2600, function () { self.rain(5); self.volley(1); });
    }
    this.after(t + 300, function () { self.startThink(true); });
  };

  Boss.prototype.startThink = function (announce) {
    var ph = PHASES[this.phase];
    this.state = 'think'; this.busy = false;
    if (announce) this.hinter.i = 0;
    this.value = ph.start; this.showValue();
    this.setBlocksLive(true);
    this.lever.setFrame(0);
    this.cannon.play('cannon_idle');
    MB.sfx('hintOpen', { vol: 0.6 });
    if (announce) {
      var k = this.phase === 1 ? 'p15' : this.phase === 2 ? 'p16' : null;
      this.s.toast((k ? MB.STORY.lines[k].text + ' ' : '') + ph.tip, 'priya_neutral', 7000);
    }
    this.blocks.forEach(function (b) { if (b.op) b.sp.scene.fx.sparks(b.sp.x, b.sp.y, 4, COL.cyanL, 18); });
  };

  Boss.prototype.bump = function (b) {
    var s = this.s, ph = PHASES[this.phase];
    if (b.cd > 0) return; b.cd = 260;
    s.tweens.add({ targets: b.sp, y: b.y0 - 5, duration: 70, yoyo: true, ease: 'Quad.out' });
    if (this.state !== 'think' || this.busy || !b.op) { MB.sfx('blockBump', { vol: 0.3, pitch: -8 }); return; }
    var nv = b.op.s > 0 ? F.add(this.value, b.op) : F.sub(this.value, b.op);
    s.fx.text(b.sp.x, b.sp.y - 34, (b.op.s > 0 ? '+' : '–') + b.op.n + '/' + b.op.d, b.op.s > 0 ? COL.green : COL.pink, 'ui28');
    if (nv.n < 0) { MB.sfx('wrong'); s.toast('The cannon only has ' + F.str(F.toDen(this.value, ph.den) || this.value) + '. You cannot take away more than that.'); return; }
    if (F.cmp(nv, { n: 1, d: 1 }) > 0) {
      MB.sfx('cannonFizzle'); s.fx.sparks(this.cx, this.floorY - 44, 8, COL.red, 24);
      this.value = ph.start; this.showValue();
      s.toast('Overload! That would be more than 1 whole. The cannon has reset to ' + F.str(ph.start) + '.');
      return;
    }
    this.value = nv; this.showValue();
    MB.sfx(b.op.s > 0 ? 'blockBump' : 'blockBumpMinus');
    s.fx.sparks(this.cx, this.floorY - 44, 3, COL.cyanL, 14);
    s.tweens.add({ targets: this.plC, scale: 1.3, duration: 90, yoyo: true });
  };

  Boss.prototype.fire = function () {
    var self = this, s = this.s, ph = PHASES[this.phase];
    if (this.state !== 'think' || this.busy) return;
    this.busy = true; this.attempts++;
    s.run.tests = (s.run.tests || 0) + 1;
    this.lever.setFrame(1);
    MB.sfx('lever'); MB.sfx('cannonCharge');
    this.cannon.play('cannon_charge');
    s.time.delayedCall(120, function () { self.lever.setFrame(2); });
    s.time.delayedCall(750, function () {
      var c = F.cmp(self.value, ph.shield), v = F.toDen(self.value, ph.den) || self.value;
      if (c === 0) {
        if (self.attempts === 1) s.run.firstTry = (s.run.firstTry || 0) + 1;
        s.run.puzzles = (s.run.puzzles || 0) + 1;
        self.attempts = 0;
        self.beam(true);
      } else {
        MB.sfx('cannonFizzle');
        self.cannon.play('cannon_idle');
        s.fx.poof(self.cx - 8, self.floorY - 50); s.fx.poof(self.cx + 8, self.floorY - 52);
        s.toast('The shield holds. The cannon has ' + F.str(v) + ' and the shield is ' + F.str(ph.shield) + '. ' +
          F.str(v) + (c < 0 ? ' is less than ' : ' is more than ') + F.str(ph.shield) + '. Make them exactly equal.', 'priya_neutral', 6500);
        MB.sfx('bossLaugh', { vol: 0.7 });
        self.sp.play('phantom_attack'); self.sp.chain('phantom_float');
        // harmless-ish consequence: one easy volley, then think again (still no timer)
        self.state = 'punish'; self.setBlocksLive(false);
        self.token++;
        self.after(600, function () { self.volley(1); });
        self.after(2600, function () { self.startThink(false); });
      }
    });
  };

  Boss.prototype.beam = function () {
    var self = this, s = this.s, top = this.sp.y + 10, y, parts = [];
    this.cannon.play('cannon_fire');
    MB.sfx('cannonFire');
    for (y = this.floorY - 56; y > top; y -= 16) {
      var b = s.add.sprite(this.cx, y, 'beam').setDepth(49).play({ key: 'beam_flow', startFrame: parts.length % 4 });
      parts.push(b);
    }
    s.shake(0.008, 320); s.hud.flash(0xdcfffa, 0.35);
    s.time.delayedCall(380, function () {
      parts.forEach(function (b2) { s.tweens.add({ targets: b2, alpha: 0, scaleX: 0.2, duration: 200, onComplete: function () { b2.destroy(); } }); });
      MB.sfx('shieldBreak');
      self.shieldOn = false;
      s.fx.ring(self.sp.x, self.sp.y, COL.pink, 2.2); s.fx.ring(self.sp.x, self.sp.y, COL.white, 1.4);
      s.fx.sparks(self.sp.x, self.sp.y, 14, COL.pink, 60); s.fx.debris(self.sp.x, self.sp.y, 10);
      self.stun();
    });
  };

  Boss.prototype.stun = function () {
    var self = this, s = this.s;
    this.state = 'stunned'; this.token++;
    this.setBlocksLive(false);
    MB.sfx('bossStun');
    this.sp.play('phantom_stunned');
    var tx = STUN_X;
    s.tweens.add({ targets: this.sp, x: tx, y: this.floorY - 31, duration: 700, ease: 'Bounce.out', onComplete: function () {
      if (self.state !== 'stunned') return;
      self.hit.body.enable = true;
      s.toast('The shield is down! Jump on the Phantom\'s glowing core!', 'priya_smile', 3500);
      self.arrow = s.add.image(self.sp.x, self.sp.y - 34, 'hud', MB.fr('hud', 'arrow_d')).setDepth(88).setTint(COL.gold);
      s.tweens.add({ targets: self.arrow, y: self.sp.y - 28, duration: 300, yoyo: true, repeat: -1 });
    } });
    // generous window; if it passes the Phantom recovers and the SAME phase repeats
    this.after(11000, function () {
      if (self.state !== 'stunned') return;
      self.hit.body.enable = false;
      if (self.arrow) { self.arrow.destroy(); self.arrow = null; }
      self.sp.play('phantom_float');
      s.tweens.add({ targets: self.sp, x: self.cx, y: 74, duration: 800, ease: 'Sine.inOut', onComplete: function () { self.raiseShield(); self.startAttack(); } });
    });
  };

  Boss.prototype.touch = function (player) {
    var self = this, s = this.s;
    if (this.state !== 'stunned') return;
    // generous: any landing on the upper part of the core counts
    if (!(player.body.velocity.y > 20 && player.body.bottom < this.hit.body.bottom - 5)) return;
    this.state = 'hit'; this.token++;
    this.hit.body.enable = false;
    if (this.arrow) { this.arrow.destroy(); this.arrow = null; }
    this.hp--; s.run.bossHp = this.hp;
    s.hud.bossBar(true, this.hp);
    MB.sfx('bossHit'); MB.sfx('stomp');
    player.bounce(330, false);
    s.shake(0.012, 260); s.hud.flash(0xffffff, 0.4);
    s.fx.boom(this.sp.x, this.sp.y + 4); s.fx.sparks(this.sp.x, this.sp.y, 12, COL.gold, 44);
    this.sp.play('phantom_hurt');
    if (this.hp <= 0) { s.time.delayedCall(500, function () { self.defeat(); }); return; }
    s.time.delayedCall(600, function () {
      self.sp.play('phantom_float');
      s.tweens.add({ targets: self.sp, x: self.cx, y: 74, duration: 800, ease: 'Sine.inOut', onComplete: function () {
        self.phase = 3 - self.hp;
        MB.Save.store();
        s.say(self.phase === 1 ? ['f08', 'f09'] : ['f10'], function () {
          self.applyPhase();
          self.setIntensity();
          self.raiseShield();
          self.startAttack();
        });
      } });
    });
  };

  Boss.prototype.defeat = function () {
    var self = this, s = this.s, sp = this.sp;
    this.state = 'defeat'; this.token++;
    s.cutscene = true;
    s.player.freeze();
    MB.music(null);
    MB.sfx('bossDefeat');
    s.hud.bossBar(false, 0);
    s.hud.toast.clear();
    sp.play('phantom_defeat');
    for (var i = 0; i < 7; i++) (function (k) {
      s.time.delayedCall(k * 180, function () {
        s.fx.boom(sp.x + (Math.random() * 60 - 30), sp.y + (Math.random() * 50 - 25), 0.8 + Math.random() * 0.5);
        s.shake(0.008, 160);
      });
    })(i);
    s.tweens.add({ targets: this.glow, alpha: 0, duration: 900 });
    s.time.delayedCall(1500, function () {
      sp.setVisible(false);
      s.hud.flash(0xffffff, 0.7);
      s.fx.ring(sp.x, sp.y, COL.gold, 2.5);
      // the Missing Quarter drops out
      var q = s.add.sprite(sp.x, sp.y, 'missingq').setDepth(55).play('missingq_glow');
      var gl = s.fx.glow(sp.x, sp.y, COL.gold, 1.6, 0.6);
      U.sensor(s, q, 20, 20);
      q.body.enable = false;
      var ty = self.floorY - 22;
      s.tweens.add({ targets: [q, gl], y: ty, duration: 1100, ease: 'Bounce.out', onComplete: function () {
        q.body.enable = true;
        s.cutscene = false; s.player.unfreeze();
        s.tweens.add({ targets: [q, gl], y: ty - 5, duration: 700, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
        s.toast('The missing quarter! Grab it, Jake!', 'priya_smile', 3000);
      } });
      q.onTouch = function () {
        if (q.gone) return; q.gone = true;
        MB.sfx('quarterGet');
        s.run.quarters += 1; s.run.gotMissing = 1; s.hud.refresh(true);
        s.fx.ring(q.x, q.y, COL.gold, 2); s.fx.sparks(q.x, q.y, 16, COL.gold, 50);
        s.hud.flash(0xfff0b8, 0.5);
        gl.destroy(); q.destroy();
        s.cutscene = true;
        s.player.freeze('celebrate');
        s.time.delayedCall(1300, function () {
          // the Phantom's fading hologram has the last word
          var h = s.add.sprite(self.cx, 86, 'phantom_holo').setDepth(50).play('phantom_holo_flicker').setAlpha(0);
          s.tweens.add({ targets: h, alpha: 0.9, duration: 400 });
          s.player.pose = null;
          s.say(['f11', 'f12'], function () {
            s.player.locked = true;
            s.tweens.add({ targets: h, alpha: 0, duration: 500, onComplete: function () { h.destroy(); } });
            MB.sfx('bossLaugh', { vol: 0.5 });
            MB.music('victory');
            s.say(['j13', 'p17'], function () {
              s.player.locked = true; s.player.pose = 'celebrate';
              s.run.bossHp = null;
              s.time.delayedCall(900, function () { s.finishGame(); });
            });
          });
        });
      };
    });
  };

  // ------------------------------------------------------------------ attacks
  Boss.prototype.volley = function (n) {
    var self = this, s = this.s, sp = this.sp;
    if (this.state === 'defeat') return;
    MB.sfx('bossTelegraph');
    sp.play('phantom_attack'); sp.chain('phantom_float');
    for (var i = 0; i < n; i++) (function (k) {
      self.s.time.delayedCall(330 + k * 320, function () {
        if (self.state !== 'attack' && self.state !== 'punish') return;
        var p = s.player, dir = p.x < sp.x ? -1 : 1;
        var x = sp.x + dir * 34, y = sp.y - 2;
        var ang = Math.atan2((p.centerY() + (k ? 10 : 0)) - y, p.x - x);
        self.spawnShot('bolt', x, y, Math.cos(ang) * 96, Math.sin(ang) * 96, ang);
        MB.sfx('bossShoot');
      });
    })(i);
  };
  Boss.prototype.sweep = function (dir) {
    var self = this, s = this.s, y = this.floorY - 7;
    if (this.state === 'defeat') return;
    var wx = dir > 0 ? 14 : 466;
    var warn = s.add.image(wx, y - 12, 'hud', MB.fr('hud', dir > 0 ? 'arrow_r' : 'arrow_l')).setDepth(88).setTint(COL.red);
    s.tweens.add({ targets: warn, alpha: 0.2, duration: 120, yoyo: true, repeat: 3, onComplete: function () { warn.destroy(); } });
    MB.sfx('bossTelegraph', { pitch: -5 });
    s.time.delayedCall(850, function () {
      if (self.state !== 'attack') return;
      self.spawnShot('bolt', dir > 0 ? -12 : 492, y, dir * 118, 0, dir > 0 ? 0 : Math.PI);
      MB.sfx('bossBeam', { vol: 0.6 });
    });
  };
  Boss.prototype.rain = function (n) {
    var self = this, s = this.s, p = s.player, xs = [], i;
    if (this.state === 'defeat') return;
    // columns near the player plus a spread; always leaves gaps to stand in
    var base = MB.clamp(p.x, 60, 420);
    for (i = 0; i < n; i++) xs.push(MB.clamp(base + (i - (n - 1) / 2) * 62 + (Math.random() * 16 - 8), 26, 454));
    MB.sfx('bossTelegraph', { pitch: 4 });
    this.warnXs = xs;
    s.time.delayedCall(1800, function () { if (self.warnXs === xs) self.warnXs = null; });
    this.sp.play('phantom_attack'); this.sp.chain('phantom_float');
    xs.forEach(function (x, k) {
      var w = s.add.rectangle(x, 20, 3, self.floorY - 20, COL.red, 0.35).setOrigin(0.5, 0).setDepth(43);
      s.tweens.add({ targets: w, alpha: 0.08, duration: 150, yoyo: true, repeat: 2 + k % 2, onComplete: function () {
        w.destroy();
        if (self.state !== 'attack') return;
        self.spawnShot('orb', x, 14, 0, 185, 0);
        if (k === 0) MB.sfx('bossShoot', { pitch: 5 });
      } });
    });
  };
  Boss.prototype.spawnShot = function (key, x, y, vx, vy, ang) {
    var s = this.s, self = this;
    var sp = s.add.sprite(x, y, key).setDepth(52).play(key + (key === 'bolt' ? '_fly' : '_pulse'));
    if (key === 'bolt') sp.setRotation(ang || 0);
    U.sensor(s, sp, 8, 6);
    sp.vx = vx; sp.vy = vy;
    var gl = s.fx.glow(x, y, COL.pink, 0.5, 0.45);
    sp.tick = function (dt) {
      if (s.frozen) return;
      sp.x += vx * dt / 1000; sp.y += vy * dt / 1000; gl.x = sp.x; gl.y = sp.y;
      // shots never linger into the thinking beat: maths is never done under fire
      var calm = self.state === 'defeat' || self.state === 'stunned' || self.state === 'think' || self.state === 'hit';
      var gone = sp.x < -30 || sp.x > 510 || sp.y < -30 || (vy > 0 && sp.y > self.floorY - 3) || calm;
      if (gone) { if (sp.y > self.floorY - 12 || calm) s.fx.sparks(sp.x, sp.y, 3, COL.pink, 12); gl.destroy(); sp.destroy(); }
    };
    sp.onTouch = function (player) {
      if (player.hurt(sp.x)) { s.fx.sparks(sp.x, sp.y, 5, COL.pink, 16); gl.destroy(); sp.destroy(); }
    };
    s.updaters.push(sp);
    return sp;
  };

  // ------------------------------------------------------------------ per frame
  Boss.prototype.tick = function (dt) {
    var s = this.s, sp = this.sp, ph = PHASES[this.phase], i;
    this.t += dt / 1000;
    for (i = 0; i < this.blocks.length; i++) if (this.blocks[i].cd > 0) this.blocks[i].cd -= dt;
    if (!sp.visible) { this.ring.clear(); return; }
    if (!s.frozen) {
      if (this.state === 'attack' || this.state === 'punish') {
        var k = Math.min(1, dt / 400);
        sp.x = MB.lerp(sp.x, this.cx + Math.sin(this.t * 0.9) * 120, k);
        sp.y = MB.lerp(sp.y, 74 + Math.sin(this.t * 1.9) * 8, k);
      } else if (this.state === 'think') {
        sp.x = MB.lerp(sp.x, this.cx, Math.min(1, dt / 300));
        sp.y = MB.lerp(sp.y, 72 + Math.sin(this.t * 1.5) * 5, Math.min(1, dt / 300));
      }
    }
    if (this.state !== 'stunned' && this.state !== 'hit' && this.state !== 'defeat') sp.setFlipX(s.player.x < sp.x);
    this.hit.x = sp.x; this.hit.y = sp.y + 6;
    this.glow.x = sp.x; this.glow.y = sp.y;
    // shield ring: one arc per part of the shield fraction
    this.shieldA = MB.approach(this.shieldA, this.shieldOn ? 1 : 0, dt / 250);
    var g = this.ring; g.clear();
    if (this.shieldA > 0.02) {
      this.ringT += dt / 1000;
      var d = ph.shield.d, n = ph.shield.n, r = 46, a0 = -Math.PI / 2 + this.ringT * 0.35, seg = Math.PI * 2 / d, gap = 0.09;
      for (i = 0; i < d; i++) {
        var lit = i < n;
        g.lineStyle(lit ? 3 : 1, lit ? COL.pink : 0x6f3fc0, (lit ? 0.95 : 0.6) * this.shieldA);
        g.beginPath(); g.arc(sp.x, sp.y, r, a0 + i * seg + gap, a0 + (i + 1) * seg - gap, false); g.strokePath();
      }
      if (this.state === 'think') {
        g.lineStyle(1, COL.white, 0.25 * this.shieldA); g.strokeCircle(sp.x, sp.y, r + 4 + Math.sin(this.t * 4) * 1.5);
      }
    }
  };
})();
