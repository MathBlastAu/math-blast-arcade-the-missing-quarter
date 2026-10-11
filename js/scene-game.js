/* Math Blast Arcade - Game scene: builds one area, runs the player, camera,
 * parallax, collisions, checkpoints, story triggers and area transitions. */
(function () {
  'use strict';
  var C = MB.CFG, COL = MB.COL, T = 16;
  var NOINPUT = {};

  MB.Scenes.Game = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Game() { Phaser.Scene.call(this, { key: 'Game' }); },

    create: function () {
      var self = this;
      var run = this.run = MB.Save.data.run || MB.Save.newRun();
      if (run.area < 0 || run.area >= MB.AREAS.length) run.area = 0;
      this.areaIndex = run.area;
      var def = this.def = MB.AREAS[this.areaIndex];

      // per-area state
      this.updaters = []; this.interactables = []; this.checkpoints = []; this.npcs = {}; this.holos = {};
      this.tanks = {}; this.podGroups = []; this.starIds = []; this.hinters = [];
      this.totalChips = 0; this.qkeys = 0; this.qkeyTotal = 0;
      this.frozen = false; this.inConsole = false; this.started = false; this.over = false; this.falling = false;
      this.safe = null; this.chipStreak = 0; this.chipAt = 0; this.stoodOnPod = false; this.boss = null;
      this.inp = NOINPUT;
      this.fx = new MB.FX(this);
      this.sensors = this.add.group();
      this.solids = this.add.group();

      // tiles
      var A = this.A = def.build();
      var built = A.build(this);
      this.layer = built.layer; this.pxW = built.pxW; this.pxH = built.pxH;
      this.physics.world.setBounds(0, -600, this.pxW, this.pxH + 1200);
      this.physics.world.setBoundsCollision(true, true, false, false);

      // camera
      var cam = this.cameras.main;
      cam.setZoom(C.ZOOM);
      cam.setBounds(0, 0, this.pxW, this.pxH);
      cam.setRoundPixels(true);
      cam.setBackgroundColor(def.bg.noSpace ? '#120a12' : '#05060c');
      this.makeBackground(def.bg);
      this.makeAmbient(def.ambient);

      // player
      var sp = A.spawnPt || { x: 40, y: 100 };
      var cp = run.checkpoint;
      if (cp && cp.area === this.areaIndex) sp = { x: cp.x, y: cp.y };
      this.spawnAt = sp;
      this.player = new MB.Player(this, sp.x, sp.y);
      this.player.lowG = !!def.lowG;
      this.player.setCollideWorldBounds(true);
      // sprite platforms first, then tiles: stops Jake catching on the seam between a bridge plank and the deck
      this.physics.add.collider(this.player, this.solids, this.onSolid, this.solidProcess, this);
      this.physics.add.collider(this.player, this.layer, null, this.tileProcess, this);

      // entities
      A.ents.forEach(function (e) {
        var fn = MB.Ent[e.type];
        if (!fn) { if (MB.DEBUG) console.warn('unknown entity', e.type); return; }
        fn(self, e);
      });
      this.physics.add.overlap(this.player, this.sensors, function (pl, obj) { if (obj.onTouch) obj.onTouch(pl); });

      this.ctl = new MB.Controls(this);
      this.prompt = this.add.image(0, 0, 'hud', MB.fr('hud', 'key_e')).setDepth(88).setVisible(false);
      this.promptT = 0;

      cam.startFollow(this.player, false, 0.14, 0.14, 0, 26);
      cam.centerOn(sp.x, sp.y - 26);
      this.lookX = 0;

      this.events.once('shutdown', function () {
        self.events.off('power'); self.events.off('qkey');
        self.started = false;
      });

      // HUD (separate scene on top, kept alive between areas)
      var hud = this.hud = this.scene.get('Hud');
      var begin = function () { self.begin(); };
      if (hud.ready) begin();
      else {
        hud.events.once('hud-ready', begin);
        if (!this.scene.isActive('Hud')) this.scene.launch('Hud');
      }
    },

    begin: function () {
      var self = this, def = this.def, hud = this.hud;
      hud.attach(this);
      hud.refresh();
      hud.irisIn(this.player.x, this.player.y - 14);
      if (!this.run.checkpoint || this.run.checkpoint.area !== this.areaIndex) hud.banner(def.name, def.sub);
      if (def.music) MB.music(def.music); else if (!def.boss) MB.music(null);
      this.started = true;
      this.ctl.flush();
      MB.Save.store();
      if (MB.DEBUG) window.MBG = this;
    },

    // ---------------------------------------------------------------- background
    makeBackground: function (bg) {
      var self = this, VW = C.VW;
      this.bgLayers = [];
      var add = function (key, f, depth, yOff, drift) {
        if (!key || !self.textures.exists(key)) return;
        var w = self.textures.get(key).getSourceImage().width, imgs = [];
        var n = Math.ceil(VW / w) + 1;
        for (var i = 0; i < n; i++) imgs.push(self.add.image(0, 135 + (yOff || 0), key).setOrigin(0, 0).setScrollFactor(0).setDepth(depth));
        self.bgLayers.push({ imgs: imgs, w: w, f: f, drift: drift || 0 });
      };
      if (!bg.noSpace) {
        add('bg_stars', 0.02, -100, -9, 1.2);
        if (bg.nebula) add('bg_nebula', 0.04, -99, -9, 2.2);
        if (bg.planet) {
          this.planet = this.add.image(0, 135 + bg.planet.y, 'bg_planet').setOrigin(0, 0).setScrollFactor(0).setDepth(-98);
          this.planetX = bg.planet.x;
        }
      }
      add(bg.far, 0.14, -90, 0);
      add(bg.mid, 0.32, -80, 0);
      this.updateBackground(0);
    },
    updateBackground: function (time) {
      var cam = this.cameras.main, camX = cam.scrollX + 240, i, k;
      for (i = 0; i < this.bgLayers.length; i++) {
        var L = this.bgLayers[i];
        var off = (camX * L.f + (time || 0) / 1000 * L.drift) % L.w;
        for (k = 0; k < L.imgs.length; k++) L.imgs[k].x = Math.round((240 - off + k * L.w) * 2) / 2;
      }
      if (this.planet) this.planet.x = Math.round((240 + this.planetX - camX * 0.03) * 2) / 2;
    },

    // drifting motes / embers in front of the scene: cheap atmosphere
    makeAmbient: function (kind) {
      this.motes = [];
      var K = {
        dust: { n: 14, tints: [0xa9c5f0, 0x8ff7ea], vx: [-6, -1], vy: [-4, 2], a: [0.15, 0.45] },
        stars: { n: 10, tints: [0xe6f1ff, 0x8ff7ea], vx: [-10, -3], vy: [1, 4], a: [0.2, 0.55] },
        embers: { n: 20, tints: [0xff9340, 0xffc46b, 0xf26a22], vx: [-4, 6], vy: [-22, -8], a: [0.3, 0.8] },
        motes: { n: 20, tints: [0xcfa8ff, 0x8ff7ea, 0xa26bf0], vx: [-5, 5], vy: [-5, 5], a: [0.2, 0.6] },
        data: { n: 12, tints: [0xff8cc0, 0x2de0d0], vx: [-3, 3], vy: [-14, -4], a: [0.2, 0.6] }
      }[kind];
      if (!K) return;
      var r = MB.rng(77);
      for (var i = 0; i < K.n; i++) {
        var im = this.add.image(r() * 480, r() * 270, 'pixel').setDepth(72).setBlendMode(Phaser.BlendModes.ADD);
        im.setScale(r() < 0.3 ? 1 : 0.5).setTint(K.tints[Math.floor(r() * K.tints.length)]);
        im.baseA = K.a[0] + r() * (K.a[1] - K.a[0]);
        this.motes.push({ im: im, vx: K.vx[0] + r() * (K.vx[1] - K.vx[0]), vy: K.vy[0] + r() * (K.vy[1] - K.vy[0]), ph: r() * 6.28 });
      }
    },
    updateAmbient: function (time, dt) {
      if (!this.motes || !this.motes.length) return;
      var cam = this.cameras.main, vx = cam.scrollX + 240, vy = cam.scrollY + 135, k = dt / 1000;
      for (var i = 0; i < this.motes.length; i++) {
        var m = this.motes[i], im = m.im;
        im.x += (m.vx + Math.sin(time / 900 + m.ph) * 3) * k; im.y += m.vy * k;
        if (im.x < vx - 8) im.x += 496; else if (im.x > vx + 488) im.x -= 496;
        if (im.y < vy - 8) im.y += 286; else if (im.y > vy + 278) im.y -= 286;
        im.alpha = m.im.baseA * (0.65 + 0.35 * Math.sin(time / 400 + m.ph * 3));
      }
    },

    // ---------------------------------------------------------------- collisions
    tileProcess: function (player, tile) {
      if (!tile.oneWay) return true;
      if (player.gdir < 0) return false;
      var b = player.body;
      return b.velocity.y >= 0 && (b.bottom - b.deltaY()) <= tile.pixelY + 4;
    },
    solidProcess: function (player, obj) {
      if (!obj.topOnly) return true;
      if (player.gdir < 0) return false;
      var b = player.body, ob = obj.body;
      return b.velocity.y >= -1 && (b.bottom - b.deltaY()) <= (ob.top - ob.deltaY()) + 5;
    },
    onSolid: function (player, obj) {
      if (obj.onCollide) obj.onCollide(player);
      if (obj.onBump && player.gdir > 0 && player.body.touching.up && obj.body.touching.down) obj.onBump(player);
      if (obj.onStand && player.body.touching.down) { obj.onStand(player); this.podAt = this.time.now; }
    },

    // ---------------------------------------------------------------- frame update
    update: function (time, delta) {
      this.updateBackground(time);
      this.updateAmbient(time, Math.min(delta, 34));
      if (!this.started) return;
      var dt = Math.min(delta, 34), p = this.player, i;
      var inp = this.inp = this.ctl.poll();
      var hud = this.hud;
      var busy = hud.dialogue.active || this.inConsole || this.over || hud.paused;

      if (inp.pausePressed && !busy && !p.locked) { hud.openPause(); return; }

      p.tick(dt, busy ? NOINPUT : inp);
      for (i = 0; i < this.updaters.length; i++) { var u = this.updaters[i]; if (u.active !== false && u.tick) u.tick(dt); }
      if (this.boss) this.boss.tick(dt);

      // interaction prompt
      var best = null, bd = 1e9;
      if (!busy && !p.locked && p.onFloor) {
        for (i = 0; i < this.interactables.length; i++) {
          var it = this.interactables[i];
          var dx = Math.abs(p.x - it.x), dy = Math.abs((p.y - 12) - it.y);
          if (dx < it.r && dy < 30 && dx < bd && it.can()) { best = it; bd = dx; }
        }
      }
      if (best) {
        this.promptT += dt;
        this.prompt.setVisible(true).setFrame(MB.fr('hud', MB.isTouch ? 'tap' : 'key_e'));
        this.prompt.x = best.x; this.prompt.y = best.y - 34 + Math.sin(this.promptT / 180) * 2;
        hud.setInteractHint(true);
        if (inp.interactPressed) { this.prompt.setVisible(false); best.act(); }
      } else { this.prompt.setVisible(false); hud.setInteractHint(false); }

      // optional hints: a light-bulb appears near any unsolved maths machine (H key or tap)
      var hp = null, hd = 1e9;
      if (!busy) {
        for (i = 0; i < this.hinters.length; i++) {
          var hn = this.hinters[i];
          if (!hn.active()) continue;
          var ddx = Math.abs(p.x - hn.x), ddy = Math.abs(p.y - hn.y);
          if (ddx < hn.rx && ddy < hn.ry && ddx < hd) { hp = hn; hd = ddx; }
        }
      }
      hud.setHintAvailable(!!hp);
      if (hp && inp.hintPressed) this.giveHint(hp);
      MB.touch.hint = false;

      // pods: stepping back onto ordinary ground lets the same pod be stepped on again
      if (p.onFloor && time - (this.podAt || 0) > 160) for (i = 0; i < this.podGroups.length; i++) this.podGroups[i].leave();

      // remember the last safe piece of ground (for falls)
      if (p.onFloor && p.gdir > 0 && p.body.blocked.down && p.hurtT <= 0) {
        var ty = Math.floor((p.body.bottom + 2) / T);
        if (this.A.get(Math.floor((p.body.left - 4) / T), ty) === 1 && this.A.get(Math.floor((p.body.right + 4) / T), ty) === 1) {
          this.safe = { x: p.x, y: p.y };
        }
      }
      if (!this.falling && (p.y > this.pxH + 60 || p.y < -90)) this.fell();

      // camera look-ahead
      var cam = this.cameras.main;
      if (!this.camFocus) {
        if (Math.abs(p.body.velocity.x) > 40) this.lookX = MB.approach(this.lookX, -p.facing * 26, 0.9);
        cam.followOffset.x = this.lookX;
      }
      if (!this.frozen && !busy) this.run.time += dt;
    },

    giveHint: function (hn) {
      var list = typeof hn.hints === 'function' ? hn.hints() : hn.hints;
      if (!list || !list.length) return;
      hn.i = hn.i || 0;
      MB.sfx('hintOpen');
      this.toast('Hint: ' + list[Math.min(hn.i, list.length - 1)], 'priya_smile', 7000);
      hn.i++;
      this.run.hints = (this.run.hints || 0) + 1;
      if (hn.onHint) hn.onHint();
    },

    // ---------------------------------------------------------------- helpers used by entities
    isPowered: function (id) { return !!this.run.solved[id]; },
    setPowered: function (id) {
      if (this.run.solved[id]) return;
      this.run.solved[id] = 1;
      MB.Save.store();
      this.events.emit('power', id);
    },
    nearCamera: function (x, y) { var m = this.cameras.main.midPoint; return Math.abs(x - m.x) < 280 && Math.abs(y - m.y) < 190; },
    shake: function (intensity, ms) { if (MB.Save.get('shake')) this.cameras.main.shake(ms || 120, intensity || 0.004); },
    // in the boss arena the top of the screen is busy, so radio messages go along the bottom
    toast: function (text, face, ms) { this.hud.toast.show(text, face, ms, this.def.boss ? { bottom: true, maxw: 600 } : null); },
    say: function (ids, cb) {
      var self = this;
      if (!ids || !ids.length) { if (cb) cb(); return; }
      this.frozen = true;
      this.player.locked = true; this.player.body.velocity.x = 0;
      this.hud.toast.clear();
      var top = !this.def.boss;
      this.hud.dialogue.anchor(top);
      if (top) this.hud.showStatus(false);
      this.hud.dialogue.play(ids, function () {
        self.hud.showStatus(true);
        self.frozen = false;
        if (!self.inConsole && !self.over && !self.cutscene) self.player.unfreeze();
        self.ctl.flush();
        MB.Save.store();
        if (cb) cb();
      });
    },
    focusCamera: function (x, y) {
      var cam = this.cameras.main;
      this.camFocus = true;
      cam.stopFollow();
      cam.pan(x, y == null ? cam.midPoint.y : y, 500, 'Sine.easeInOut');
    },
    releaseCamera: function () {
      var cam = this.cameras.main;
      this.camFocus = false;
      cam.startFollow(this.player, false, 0.08, 0.14, this.lookX, 26);
      this.time.delayedCall(900, function () { cam.setLerp(0.14, 0.14); });
    },

    collectQuarter: function (x, y) {
      var run = this.run, now = this.time.now;
      this.chipStreak = (now - this.chipAt < 900) ? Math.min(this.chipStreak + 1, 12) : 0;
      this.chipAt = now;
      run.quarters++;
      this.fx.collect(x, y);
      if (run.quarters % 4 === 0) {
        MB.sfx('whole');
        this.fx.text(x, y - 6, '4 quarters = 1 whole!', COL.gold, 'ui28');
        this.fx.ring(x, y, COL.gold, 0.7);
      } else {
        MB.sfx('chip', { pitch: this.chipStreak });
      }
      this.hud.refresh(true);
    },

    setCheckpoint: function (id, x, y) {
      var run = this.run;
      run.checkpoint = { area: this.areaIndex, id: id, x: x, y: y };
      if (run.hearts < C.HEARTS) { run.hearts = C.HEARTS; this.fx.text(x, y - 44, 'Hearts refilled!', COL.pink, 'ui20'); }
      this.hud.refresh();
      MB.Save.store();
    },

    onPlayerHurt: function () {
      var run = this.run;
      this.shake(0.008, 140);
      this.hud.flash(0xe8384f, 0.22);
      if (MB.Save.get('relaxed')) return;
      run.hearts = Math.max(0, run.hearts - 1);
      this.hud.refresh();
      if (run.hearts <= 0) this.die();
    },

    fell: function () {
      var self = this, run = this.run, p = this.player;
      this.falling = true;
      MB.sfx('hurt', { pitch: -4 });
      if (!this.def.kindPits && !MB.Save.get('relaxed')) { run.hearts = Math.max(0, run.hearts - 1); this.hud.refresh(); }
      if (run.hearts <= 0) { this.die(); return; }
      var to = this.safe || this.spawnAt;
      this.hud.fade(true, 220, function () {
        p.setGravityDir(1);
        p.setPosition(to.x, to.y); p.body.reset(to.x, to.y); p.inv = 1200; p.hurtT = 0;
        self.cameras.main.centerOn(to.x, to.y - 26);
        self.falling = false;
        self.hud.fade(false, 260);
      });
    },

    die: function () {
      var self = this, run = this.run, p = this.player;
      if (this.dying) return;
      this.dying = true; this.falling = true;
      p.dead = true;
      run.falls = (run.falls || 0) + 1;
      MB.sfx('wrong');
      this.time.delayedCall(450, function () {
        self.hud.irisOut(p.x, p.y - 14, function () {
          run.hearts = C.HEARTS;
          MB.Save.store();
          self.scene.restart();
          self.dying = false;
        });
      });
    },

    // leave through a door
    exitArea: function (to, x, y) {
      var self = this, run = this.run;
      if (this.over) return;
      this.over = true;
      MB.sfx('transition');
      this.hud.irisOut(x, y, function () {
        run.area = to; run.checkpoint = null;
        MB.Save.store();
        self.scene.restart();
      });
    },

    finishGame: function () {
      var self = this;
      this.over = true;
      MB.Save.store();
      this.hud.irisOut(this.player.x, this.player.y - 14, function () {
        self.hud.detach();
        self.scene.stop('Hud');
        self.scene.start('Victory');
      });
    }
  });
})();
