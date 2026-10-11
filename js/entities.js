/* Math Blast Arcade - world entities: effects, collectibles, enemies, hazards,
 * platforms, checkpoints, doors, decoration.  Each MB.Ent[type](scene, e)
 * builds one entity from an AreaBuilder record. */
(function () {
  'use strict';
  var COL = MB.COL, T = 16;

  // ====================================================================== FX
  var FX = MB.FX = function (scene) { this.s = scene; };
  FX.prototype.one = function (key, x, y, depth, scale) {
    var sp = this.s.add.sprite(x, y, key).setDepth(depth == null ? 75 : depth);
    if (scale) sp.setScale(scale);
    sp.play(key + '_play');
    sp.once('animationcomplete', function () { sp.destroy(); });
    return sp;
  };
  FX.prototype.dust = function (x, y, n) {
    for (var i = 0; i < (n || 2); i++) {
      var sp = this.one('fx_dust', x + (Math.random() * 14 - 7), y - 2 - Math.random() * 2, 55);
      this.s.tweens.add({ targets: sp, x: sp.x + (Math.random() * 16 - 8), y: sp.y - 4 - Math.random() * 4, duration: 260 });
    }
  };
  FX.prototype.poof = function (x, y) { return this.one('fx_poof', x, y, 76); };
  FX.prototype.collect = function (x, y) { return this.one('fx_collect', x, y, 76); };
  FX.prototype.boom = function (x, y, scale) { return this.one('fx_boom', x, y, 78, scale || 1); };
  FX.prototype.ring = function (x, y, tint, scale) {
    var sp = this.one('fx_ring', x, y, 77, scale || 1);
    if (tint != null) sp.setTint(tint);
    return sp;
  };
  FX.prototype.sparks = function (x, y, n, tint, spread) {
    for (var i = 0; i < (n || 5); i++) {
      var a = Math.random() * Math.PI * 2, d = (spread || 18) * (0.5 + Math.random() * 0.7);
      var sp = this.s.add.sprite(x, y, 'fx_spark').setDepth(77);
      if (tint != null) sp.setTint(tint);
      sp.play({ key: 'fx_spark_play', frameRate: 10 + Math.random() * 8 });
      sp.once('animationcomplete', function (an, fr, obj) { obj.destroy(); });
      this.s.tweens.add({ targets: sp, x: x + Math.cos(a) * d, y: y + Math.sin(a) * d, duration: 300, ease: 'Quad.out' });
    }
  };
  FX.prototype.debris = function (x, y, n) {
    var s = this.s;
    for (var i = 0; i < (n || 6); i++) (function () {
      var im = s.add.image(x, y, 'fx_debris', Math.floor(Math.random() * 4)).setDepth(76);
      var dx = (Math.random() * 2 - 1) * 46, up = 14 + Math.random() * 26;
      s.tweens.add({ targets: im, x: x + dx, angle: Math.random() * 720 - 360, duration: 700 });
      s.tweens.add({ targets: im, y: y - up, duration: 240, ease: 'Quad.out', onComplete: function () {
        s.tweens.add({ targets: im, y: y + 60, alpha: 0, duration: 460, ease: 'Quad.in', onComplete: function () { im.destroy(); } });
      } });
    })();
  };
  // floating text in the world (drawn at screen resolution)
  FX.prototype.text = function (x, y, str, color, font) {
    var t = this.s.add.bitmapText(x, y, font || 'ui28', str).setOrigin(0.5, 1).setScale(0.5).setDepth(90).setTint(color == null ? COL.white : color);
    if (t.setDropShadow) t.setDropShadow(1, 2, COL.ink, 0.9);
    this.s.tweens.add({ targets: t, y: y - 18, duration: 900, ease: 'Quad.out' });
    this.s.tweens.add({ targets: t, alpha: 0, delay: 650, duration: 300, onComplete: function () { t.destroy(); } });
    return t;
  };
  // additive light
  FX.prototype.glow = function (x, y, tint, scale, alpha, key) {
    var im = this.s.add.image(x, y, key || 'glow').setDepth(82).setBlendMode(Phaser.BlendModes.ADD);
    im.setTint(tint == null ? COL.cyan : tint).setScale(scale || 1).setAlpha(alpha == null ? 0.5 : alpha);
    return im;
  };

  // ============================================================ helpers
  function sensor(scene, obj, w, h, ox, oy) {
    scene.physics.add.existing(obj);
    obj.body.setAllowGravity(false);
    obj.body.setImmovable(true);
    if (w) { obj.body.setSize(w, h); if (ox != null) obj.body.setOffset(ox, oy); }
    scene.sensors.add(obj);
    return obj;
  }
  function solid(scene, obj, topOnly) {
    scene.physics.add.existing(obj);
    obj.body.setAllowGravity(false);
    obj.body.setImmovable(true);
    if (topOnly) { obj.body.checkCollision.down = false; obj.body.checkCollision.left = false; obj.body.checkCollision.right = false; obj.topOnly = true; }
    scene.solids.add(obj);
    return obj;
  }
  MB.EntUtil = { sensor: sensor, solid: solid };
  function areaKey(scene) { return String(scene.areaIndex); }
  function isGot(scene, e) { var g = scene.run.got[areaKey(scene)]; return !!(g && g[e.id]); }
  function markGot(scene, e) { var k = areaKey(scene); if (!scene.run.got[k]) scene.run.got[k] = {}; scene.run.got[k][e.id] = 1; }
  MB.EntUtil.isGot = isGot; MB.EntUtil.markGot = markGot;

  var Ent = MB.Ent = {};

  // ============================================================ collectibles
  Ent.chip = function (scene, e) {
    scene.totalChips = (scene.totalChips || 0) + 1;
    if (isGot(scene, e)) return null;
    var sp = scene.add.sprite(e.cx, e.cy, 'quarter').setDepth(42);
    sp.play({ key: 'quarter_spin', startFrame: (e.id * 3) % 8 });
    sensor(scene, sp, 12, 12);
    scene.tweens.add({ targets: sp, y: e.cy - 2, duration: 700 + (e.id % 5) * 40, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    sp.onTouch = function () {
      if (sp.gone) return; sp.gone = true;
      markGot(scene, e);
      scene.collectQuarter(sp.x, sp.y);
      sp.destroy();
    };
    return sp;
  };

  Ent.starcell = function (scene, e) {
    var key = scene.areaIndex + '_' + e.id;
    scene.starIds.push(key);
    if (scene.run.stars[key]) return null;
    var sp = scene.add.sprite(e.cx, e.cy, 'starcell').setDepth(42).play('starcell_spin');
    sensor(scene, sp, 14, 14);
    var gl = scene.fx.glow(e.cx, e.cy, COL.cyan, 0.7, 0.45);
    scene.tweens.add({ targets: [sp, gl], y: e.cy - 3, duration: 900, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    sp.onTouch = function () {
      if (sp.gone) return; sp.gone = true;
      scene.run.stars[key] = 1;
      MB.sfx('secret');
      scene.fx.ring(sp.x, sp.y, COL.cyan); scene.fx.sparks(sp.x, sp.y, 8, COL.cyanL, 26);
      scene.fx.text(sp.x, sp.y - 8, 'Secret star cell!', COL.cyanL, 'ui20');
      scene.hud.refresh();
      gl.destroy(); sp.destroy();
    };
    return sp;
  };

  Ent.heart = function (scene, e) {
    if (isGot(scene, e)) return null;
    var sp = scene.add.sprite(e.cx, e.cy, 'heart').setDepth(42).play('heart_beat');
    sensor(scene, sp, 12, 12);
    sp.onTouch = function () {
      if (sp.gone || scene.run.hearts >= MB.CFG.HEARTS) return;
      sp.gone = true; markGot(scene, e);
      scene.run.hearts++; scene.hud.refresh();
      MB.sfx('heart'); scene.fx.collect(sp.x, sp.y);
      sp.destroy();
    };
    return sp;
  };

  // ============================================================ enemies
  function autoRange(scene, e) {
    var A = scene.A, x0 = e.tx, x1 = e.tx, ty = e.ty;
    while (A.get(x0 - 1, ty) === 0 && A.get(x0 - 1, ty + 1) !== 0 && x0 - 1 > 0) x0--;
    while (A.get(x1 + 1, ty) === 0 && A.get(x1 + 1, ty + 1) !== 0 && x1 + 1 < A.w - 1) x1++;
    return [x0, x1];
  }
  function stompCheck(scene, enemy, player) {
    var falling = player.body.velocity.y * player.gdir > 30;
    var above = player.gdir > 0 ? (player.body.bottom <= enemy.body.top + 9) : (player.body.top >= enemy.body.bottom - 9);
    return falling && above;
  }
  MB.EntUtil.stompCheck = stompCheck;

  Ent.crawler = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'crawler').setOrigin(0.5, 1).setDepth(46).play('crawler_walk');
    sensor(scene, sp, 16, 13, 4, 11);
    var r = (e.x0 != null) ? [e.x0, e.x1] : autoRange(scene, e);
    var minX = r[0] * T + 9, maxX = r[1] * T + 7;
    sp.dir = e.dir || -1; sp.speed = e.speed || 24; sp.isEnemy = true;
    sp.tick = function (dt) {
      if (sp.dying || scene.frozen) return;
      sp.x += sp.dir * sp.speed * dt / 1000;
      if (sp.x >= maxX) { sp.x = maxX; sp.dir = -1; } else if (sp.x <= minX) { sp.x = minX; sp.dir = 1; }
      sp.setFlipX(sp.dir < 0);
    };
    sp.onTouch = function (player) {
      if (sp.dying) return;
      if (stompCheck(scene, sp, player)) {
        sp.dying = true; sp.body.enable = false;
        MB.sfx('stomp'); scene.shake(0.004, 90);
        player.bounce(scene.inp && scene.inp.jump ? 310 : 230, scene.inp && scene.inp.jump);
        scene.fx.sparks(sp.x, sp.y - 6, 5, COL.pink);
        sp.play('crawler_squash');
        sp.once('animationcomplete', function () {
          scene.time.delayedCall(160, function () { MB.sfx('enemyPop'); scene.fx.poof(sp.x, sp.y - 6); scene.fx.debris(sp.x, sp.y - 6, 4); sp.destroy(); });
        });
        scene.run.stomps = (scene.run.stomps || 0) + 1;
      } else {
        player.hurt(sp.x);
      }
    };
    scene.updaters.push(sp);
    return sp;
  };

  Ent.drone = function (scene, e) {
    var sp = scene.add.sprite(e.cx, e.cy, 'drone').setDepth(46).play('drone_hover');
    sensor(scene, sp, 16, 13, 4, 5);
    var minX = (e.x0 != null ? e.x0 : e.tx) * T + 8, maxX = (e.x1 != null ? e.x1 : e.tx) * T + 8;
    var minY = e.cy, maxY = (e.y1 != null ? e.y1 * T + 8 : e.cy);
    sp.dir = 1; sp.speed = e.speed || 30; sp.t = (e.id * 0.7) % 6; sp.baseY = e.cy; sp.isEnemy = true;
    sp.tick = function (dt) {
      if (sp.dying || scene.frozen) return;
      sp.t += dt / 1000;
      if (maxX > minX) {
        sp.x += sp.dir * sp.speed * dt / 1000;
        if (sp.x >= maxX) { sp.x = maxX; sp.dir = -1; } else if (sp.x <= minX) { sp.x = minX; sp.dir = 1; }
        sp.setFlipX(sp.dir < 0);
      }
      if (maxY > minY) {
        sp.baseY += sp.dir * sp.speed * dt / 1000;
        if (sp.baseY >= maxY) { sp.baseY = maxY; sp.dir = -1; } else if (sp.baseY <= minY) { sp.baseY = minY; sp.dir = 1; }
      }
      sp.y = sp.baseY + Math.sin(sp.t * 2.6) * 4;
    };
    sp.onTouch = function (player) {
      if (sp.dying) return;
      if (stompCheck(scene, sp, player)) {
        sp.dying = true; sp.body.enable = false;
        MB.sfx('stomp'); MB.sfx('enemyPop'); scene.shake(0.004, 90);
        player.bounce(scene.inp && scene.inp.jump ? 320 : 240, scene.inp && scene.inp.jump);
        sp.play('drone_pop');
        scene.fx.sparks(sp.x, sp.y, 6, COL.pink, 22);
        sp.once('animationcomplete', function () { scene.fx.poof(sp.x, sp.y); sp.destroy(); });
        scene.run.stomps = (scene.run.stomps || 0) + 1;
      } else {
        player.hurt(sp.x);
      }
    };
    scene.updaters.push(sp);
    return sp;
  };

  // ============================================================ hazards
  Ent.spikes = function (scene, e) {
    var n = e.n || 1, last = null;
    for (var i = 0; i < n; i++) {
      var sp = scene.add.sprite(e.bx + i * T, e.by, 'spikes').setOrigin(0.5, 1).setDepth(44);
      sp.play({ key: 'spikes_shimmer', startFrame: i % 4 });
      if (e.flip) { sp.setFlipY(true); sp.y = e.by - T; sp.setOrigin(0.5, 0); }
      sensor(scene, sp, 12, 8, 2, e.flip ? 0 : 8);
      sp.onTouch = function (player) { player.hurt(player.x + (player.facing || 1)); };
      last = sp;
    }
    return last;
  };

  Ent.mine = function (scene, e) {
    var sp = scene.add.sprite(e.cx, e.cy, 'mine').setDepth(46).play('mine_pulse');
    sensor(scene, sp, 10, 10, 3, 3);
    var gl = scene.fx.glow(e.cx, e.cy, COL.red, 0.45, 0.4);
    var dx = (e.dx || 0) * T, dy = (e.dy || 0) * T, per = e.period || 3.2, ph = e.phase || 0;
    sp.t = 0;
    sp.tick = function (dt) {
      if (scene.frozen) return;
      sp.t += dt / 1000;
      var k = (Math.sin((sp.t / per + ph) * Math.PI * 2) + 1) / 2;
      sp.x = e.cx + dx * k; sp.y = e.cy + dy * k + Math.sin(sp.t * 2) * 1.5;
      gl.x = sp.x; gl.y = sp.y;
    };
    sp.onTouch = function (player) { if (player.hurt(sp.x)) { MB.sfx('mineBeep'); scene.fx.sparks(sp.x, sp.y, 5, COL.redL); } };
    scene.updaters.push(sp);
    return sp;
  };

  // Electric arc between a ceiling emitter and a floor emitter; switches on and off.
  Ent.zap = function (scene, e) {
    var h = e.h || 3, x = e.cx, top = e.ty * T;
    var em1 = scene.add.image(x, top + 8, 'zap_emitter', 0).setDepth(44);
    var em2 = scene.add.image(x, top + (h + 1) * T + 8, 'zap_emitter', 0).setDepth(44).setFlipY(true);
    var arcs = [];
    for (var i = 0; i < h; i++) {
      var a = scene.add.sprite(x, top + T + i * T + 8, 'zap_arc').setDepth(45);
      a.play({ key: 'zap_arc_arc', startFrame: i % 4 }); a.setVisible(false); arcs.push(a);
    }
    var z = scene.add.zone(x, top + T + h * T / 2, 8, h * T);
    sensor(scene, z);
    var on = 1.3, off = 1.7, t = (e.phase || 0) * (on + off);
    z.active2 = false;
    z.tick = function (dt) {
      if (scene.frozen) return;
      if (e.power && scene.isPowered(e.power)) { if (z.active2) setOn(false); return; }
      t = (t + dt / 1000) % (on + off);
      var warn = t > off - 0.45 && t < off;
      var want = t >= off;
      if (want !== z.active2) setOn(want);
      em1.setFrame(want || (warn && Math.floor(t * 16) % 2) ? 1 : 0); em2.setFrame(em1.frame.name);
    };
    function setOn(v) {
      z.active2 = v;
      for (var k = 0; k < arcs.length; k++) arcs[k].setVisible(v);
      if (v && scene.nearCamera(x, top)) MB.sfx('zap', { vol: 0.5 });
    }
    z.onTouch = function (player) { if (z.active2) player.hurt(x); };
    scene.updaters.push(z);
    return z;
  };

  // Steam vent in the floor: periodic jet.
  Ent.steam = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'steam').setOrigin(0.5, 1).setDepth(44).setVisible(false);
    sensor(scene, sp, 10, 26, 3, 6);
    var noz = scene.add.rectangle(e.bx, e.by - 1, 10, 3, 0x161c2b).setDepth(43);
    var on = 1.2, off = 1.9, t = (e.phase || 0) * (on + off);
    sp.live = false;
    sp.tick = function (dt) {
      if (scene.frozen) return;
      if (e.power && scene.isPowered(e.power)) { if (sp.live) { sp.live = false; sp.setVisible(false); } return; }
      t = (t + dt / 1000) % (on + off);
      var want = t >= off;
      if (want !== sp.live) {
        sp.live = want; sp.setVisible(want);
        if (want) { sp.play('steam_puff'); if (scene.nearCamera(sp.x, sp.y)) MB.sfx('steam', { vol: 0.45 }); }
      }
      if (!want && t > off - 0.4 && Math.random() < 0.3) scene.fx.dust(e.bx, e.by - 2, 1);
    };
    sp.onTouch = function (player) { if (sp.live) player.hurt(sp.x); };
    scene.updaters.push(sp);
    return noz;
  };

  // ============================================================ platforms
  // Hover platform moving between two points (dx, dy in tiles). Can wait for power.
  Ent.mplat = function (scene, e) {
    var sp = scene.add.sprite(e.cx, e.cy, 'mplat').setDepth(41).play('mplat_hover');
    solid(scene, sp, true);
    sp.body.setSize(48, 8); sp.body.setOffset(0, 0);
    var x0 = e.cx, y0 = e.cy, x1 = e.cx + (e.dx || 0) * T, y1 = e.cy + (e.dy || 0) * T;
    var speed = e.speed || 34, dist = Math.max(1, Math.hypot(x1 - x0, y1 - y0));
    var k = 0, dir = 1, wait = 0;
    sp.powered = !e.power || scene.isPowered(e.power);
    if (!sp.powered) { sp.anims.pause(); sp.setTint(0x8c9db3); scene.events.on('power', function (id) { if (id === e.power) { sp.powered = true; sp.anims.resume(); sp.clearTint(); } }); }
    sp.tick = function (dt) {
      var b = sp.body;
      if (!sp.powered || scene.frozen) { b.setVelocity(0, 0); return; }
      if (wait > 0) { wait -= dt; b.setVelocity(0, 0); return; }
      k += dir * speed * dt / 1000 / dist;
      if (k >= 1) { k = 1; dir = -1; wait = e.wait == null ? 700 : e.wait; } else if (k <= 0) { k = 0; dir = 1; wait = e.wait == null ? 700 : e.wait; }
      var tx = x0 + (x1 - x0) * k, ty = y0 + (y1 - y0) * k;
      // drive with velocity so riders are carried by the physics engine
      b.setVelocity((tx - sp.x) / (dt / 1000), (ty - sp.y) / (dt / 1000));
    };
    scene.updaters.push(sp);
    return sp;
  };

  Ent.spring = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'spring', 0).setOrigin(0.5, 1).setDepth(44);
    sensor(scene, sp, 12, 6, 2, 10);
    var cd = 0;
    sp.tick = function (dt) { if (cd > 0) cd -= dt; };
    sp.onTouch = function (player) {
      if (cd > 0 || player.body.velocity.y * player.gdir < 0) return;
      cd = 220;
      player.bounce(e.power2 || 455, false);
      sp.play('spring_bounce'); MB.sfx('spring'); scene.fx.dust(sp.x, sp.y, 3);
    };
    scene.updaters.push(sp);
    return sp;
  };

  // Gravity-flip pad (zero-G sector). dir: 'up' sends Jake to the ceiling, 'down' back to the floor.
  Ent.gpad = function (scene, e) {
    var up = e.dir !== 'down';
    var sp = scene.add.sprite(e.bx, up ? e.by : e.by - T, 'gpad').setOrigin(0.5, up ? 1 : 0).setDepth(44);
    sp.play(up ? 'gpad_up' : 'gpad_down');
    if (!up) sp.setFlipY(true);
    sensor(scene, sp, 28, 14, 2, up ? -2 : 0);
    scene.fx.glow(sp.x, sp.y + (up ? -6 : 6), up ? COL.cyan : COL.pink, 0.8, 0.35);
    sp.onTouch = function (player) {
      var want = up ? -1 : 1;
      if (player.gdir === want) return;
      player.setGravityDir(want);
      player.body.velocity.y = -90 * want * -1;
      MB.sfx('gravityFlip');
      scene.fx.ring(player.x, player.centerY(), up ? COL.cyan : COL.pink);
    };
    return sp;
  };

  // ============================================================ checkpoints / doors
  Ent.checkpoint = function (scene, e) {
    var sp = scene.add.sprite(e.bx + 3, e.by, 'checkpoint', 0).setOrigin(0.5, 1).setDepth(40);
    sensor(scene, sp, 20, 40, 2, 0);
    var cp = scene.run.checkpoint;
    sp.lit = !!(cp && cp.area === scene.areaIndex && cp.id === e.id);
    if (sp.lit) { sp.play('checkpoint_on'); sp.gl = scene.fx.glow(sp.x, sp.y - 30, COL.cyan, 0.8, 0.4); }
    sp.onTouch = function (player) {
      if (sp.lit) return;
      scene.checkpoints.forEach(function (o) { if (o.lit) { o.lit = false; o.play('checkpoint_off'); if (o.gl) { o.gl.destroy(); o.gl = null; } } });
      sp.lit = true;
      sp.play('checkpoint_activate'); sp.chain('checkpoint_on');
      sp.gl = scene.fx.glow(sp.x, sp.y - 30, COL.cyan, 0.8, 0.4);
      MB.sfx('checkpoint'); scene.fx.sparks(sp.x, sp.y - 30, 6, COL.cyanL, 20);
      scene.setCheckpoint(e.id, e.bx, e.by);
    };
    scene.checkpoints.push(sp);
    return sp;
  };

  // Area exit. props: to (area index or 'victory'), lock (power id needed)
  Ent.door = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'door', 0).setOrigin(0.5, 1).setDepth(30);
    sensor(scene, sp, 12, 30, 10, 18);
    sp.locked = !!e.lock && !scene.isPowered(e.lock);
    sp.setFrame(sp.locked ? 0 : 1);
    sp.gl = scene.fx.glow(sp.x, sp.y - 44, sp.locked ? COL.red : COL.green, 0.5, 0.45);
    if (e.entry) { sp.setFrame(1); sp.body.enable = false; return sp; }
    scene.events.on('power', function (id) {
      if (id === e.lock && sp.locked) { sp.locked = false; sp.setFrame(1); sp.gl.setTint(COL.green); MB.sfx('doorOpen', { vol: 0.6 }); scene.fx.sparks(sp.x, sp.y - 44, 6, COL.green); }
    });
    var told = 0;
    sp.onTouch = function (player) {
      if (sp.used || !player.onFloor || player.locked) return;
      if (sp.locked) {
        if (scene.time.now - told > 2500) { told = scene.time.now; MB.sfx('doorLocked'); if (e.lockMsg) scene.toast(e.lockMsg); }
        return;
      }
      sp.used = true;
      player.freeze();
      MB.sfx('doorOpen');
      sp.play('door_open');
      sp.once('animationcomplete', function () { scene.exitArea(e.to, sp.x, sp.y - 16); });
    };
    return sp;
  };

  // ============================================================ decoration
  Ent.decor = function (scene, e) {
    var im = scene.add.image(e.bx + (e.ox || 0), e.by + (e.oy || 0), 'decor', MB.fr('decor', e.name)).setOrigin(0.5, 1).setDepth(e.front ? 70 : (e.depth || 28));
    if (e.flip) im.setFlipX(true);
    if (e.name === 'lamp_post') scene.fx.glow(im.x, im.y - 24, COL.cyan, 1.1, 0.35);
    if (e.name === 'monitor_wall' || e.name === 'terminal_small') scene.fx.glow(im.x, im.y - 18, COL.cyan, 0.7, 0.2);
    return im;
  };
  Ent.tank = function (scene, e) {
    var im = scene.add.image(e.bx, e.by, 'tank4', e.level == null ? 3 : e.level).setOrigin(0.5, 1).setDepth(26);
    scene.fx.glow(e.bx, e.by - 30, COL.cyan, 1.2, 0.18);
    return im;
  };
  Ent.shuttle = function (scene, e) {
    return scene.add.image(e.bx, e.by, 'shuttle', MB.fr('shuttle', 'parked')).setOrigin(0.5, 1).setDepth(29);
  };
  Ent.light = function (scene, e) {
    var g = scene.fx.glow(e.cx, e.cy, e.color == null ? COL.cyan : e.color, e.scale || 1, e.alpha == null ? 0.3 : e.alpha, e.soft ? 'glow_soft' : 'glow');
    if (e.pulse) scene.tweens.add({ targets: g, alpha: g.alpha * 0.55, duration: 900 + (e.id % 4) * 130, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    return g;
  };
  // ceiling lamp with a light cone
  Ent.lamp = function (scene, e) {
    var c = scene.add.image(e.cx, e.ty * T, 'lightcone').setOrigin(0.5, 0).setDepth(81).setBlendMode(Phaser.BlendModes.ADD);
    c.setTint(e.color == null ? 0x8ff7ea : e.color).setAlpha(e.alpha == null ? 0.16 : e.alpha).setScale(e.scale || 1.2);
    scene.add.rectangle(e.cx, e.ty * T + 2, 12, 4, 0xdcfffa).setDepth(31);
    return c;
  };
  // floating control tip ("Move", "Jump") shown near the player
  Ent.tip = function (scene, e) {
    var c = scene.add.container(e.cx, e.cy).setDepth(35);
    var icons = (MB.isTouch && e.touchIcons) ? e.touchIcons : (e.icons || []);
    var x = 0;
    icons.forEach(function (ic) { c.add(scene.add.image(x, 0, 'hud', MB.fr('hud', ic))); x += 18; });
    var t = scene.add.bitmapText(x - 4, -7, 'ui28', e.text).setScale(0.5).setTint(COL.text);
    if (t.setDropShadow) t.setDropShadow(1, 2, COL.ink, 0.9);
    c.add(t);
    c.x = e.cx - (x + t.width * 0.5) / 2;
    c.alpha = 0;
    c.tick = function () {
      var near = Math.abs(scene.player.x - e.cx) < 110;
      c.alpha = MB.approach(c.alpha, near ? 1 : 0, 0.06);
    };
    scene.tweens.add({ targets: c, y: e.cy - 3, duration: 800, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
    scene.updaters.push(c);
    return c;
  };

  Ent.npc = function (scene, e) {
    var sp = scene.add.sprite(e.bx, e.by, 'priya').setOrigin(0.5, 1).setDepth(44).play('priya_idle');
    scene.npcs[e.name || 'priya'] = sp;
    return sp;
  };

  // Floor projector + small Phantom hologram, shown by story triggers.
  Ent.holo = function (scene, e) {
    var pr = scene.add.sprite(e.bx, e.by, 'holo_proj').setOrigin(0.5, 1).setDepth(30).play('holo_proj_on');
    var ph = scene.add.sprite(e.bx, e.by - 34, 'phantom_holo').setDepth(47).play('phantom_holo_flicker').setVisible(false);
    var gl = scene.fx.glow(e.bx, e.by - 30, COL.cyan, 1.3, 0);
    scene.holos[e.name || 'holo'] = {
      show: function () { ph.setVisible(true); ph.alpha = 0; scene.tweens.add({ targets: ph, alpha: 1, duration: 300 }); scene.tweens.add({ targets: gl, alpha: 0.4, duration: 300 }); MB.sfx('bossAppear', { vol: 0.6 }); scene.fx.ring(ph.x, ph.y, COL.cyan); },
      hide: function () { scene.tweens.add({ targets: [ph, gl], alpha: 0, duration: 350, onComplete: function () { ph.setVisible(false); } }); MB.sfx('bossLaugh', { vol: 0.6 }); scene.fx.sparks(ph.x, ph.y, 8, COL.pink, 26); },
      x: e.bx, y: e.by - 34
    };
    return pr;
  };

  // Invisible story trigger. props: w,h (tiles), key, once (default true), fn (name in area.on)
  Ent.trigger = function (scene, e) {
    var w = (e.w || 1) * T, h = (e.h || 4) * T;
    var z = scene.add.zone(e.tx * T + w / 2, (e.ty + 1) * T - h / 2, w, h);
    sensor(scene, z);
    z.onTouch = function (player) {
      var key = 't' + scene.areaIndex + '_' + (e.key || e.id);
      if (z.done || (e.once !== false && scene.run.seen[key])) return;
      if (e.ground && !player.onFloor) return;
      if (player.locked) return;
      z.done = true; scene.run.seen[key] = 1;
      if (e.fn && scene.def.on && scene.def.on[e.fn]) scene.def.on[e.fn](scene, e);
      else if (e.say) scene.say(e.say);
      else if (e.toast) scene.toast(e.toast, e.face);
    };
    return z;
  };
})();
