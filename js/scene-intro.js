/* Math Blast Arcade - opening cinematic (skippable). */
(function () {
  'use strict';
  var C = MB.CFG, COL = MB.COL, UI = MB.UI, W = C.W, H = C.H;

  MB.Scenes.Intro = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Intro() { Phaser.Scene.call(this, { key: 'Intro' }); },

    create: function () {
      var self = this;
      this.cameras.main.setBackgroundColor('#05060c');
      this.bg = MB.spaceBackdrop(this, { planetX: 520, planetY: 40 });
      this.layer = this.add.container(0, 0).setDepth(0);
      this.add.image(0, 0, 'vignette').setOrigin(0, 0).setScale(2).setDepth(50);
      // cinematic bars
      this.add.rectangle(0, 0, W, 44, 0x05060c).setOrigin(0, 0).setDepth(60);
      this.add.rectangle(0, H - 44, W, 44, 0x05060c).setOrigin(0, 0).setDepth(60);
      this.dialogue = new UI.Dialogue(this);
      this.done = false; this.step = -1;
      MB.music('title');

      var skip = UI.button(this, W - 80, 22, 120, 36, 'Skip', function () { self.finish(); });
      skip.setDepth(950);
      this.input.keyboard.on('keydown', function (ev) {
        if (ev.code === 'Escape') { self.finish(); return; }
        if (ev.code === 'KeyE' || ev.code === 'Space' || ev.code === 'Enter' || ev.code === 'KeyX') self.dialogue.advance();
      });
      this.input.on('pointerdown', function (p, over) { if (!over || !over.length) self.dialogue.advance(); });
      this.cameras.main.fadeIn(400, 5, 6, 12);
      this.next();
    },

    clearShot: function () { this.layer.removeAll(true); this.tweens.killTweensOf(this.layer); this.layer.setPosition(0, 0).setScale(1).setAlpha(1); },

    next: function () {
      var self = this;
      this.step++;
      var shots = [this.shotStation, this.shotTanks, this.shotArrive];
      if (this.step >= shots.length) { this.finish(); return; }
      var run = function () {
        self.clearShot();
        var lines = shots[self.step].call(self);
        self.cameras.main.fadeIn(350, 5, 6, 12);
        self.time.delayedCall(450, function () { if (!self.done) self.dialogue.play(lines, function () { if (!self.done) self.next(); }); });
      };
      if (this.step === 0) run();
      else { this.cameras.main.fadeOut(300, 5, 6, 12); this.cameras.main.once('camerafadeoutcomplete', run); }
    },

    // shot 1: Kepler Station
    shotStation: function () {
      var st = this.add.image(170, 70, 'intro_station').setOrigin(0, 0).setScale(2);
      this.layer.add(st);
      this.tweens.add({ targets: st, x: 130, y: 60, duration: 9000, ease: 'Sine.inOut' });
      for (var i = 0; i < 3; i++) {
        var gl = this.add.image(250 + i * 90, 190 + i * 22, 'glow').setBlendMode(Phaser.BlendModes.ADD).setTint(COL.cyan).setAlpha(0.25).setScale(1.5);
        this.layer.add(gl);
        this.tweens.add({ targets: gl, alpha: 0.05, duration: 700 + i * 200, yoyo: true, repeat: -1 });
      }
      return ['n01'];
    },

    // shot 2: the tanks lose a quarter
    shotTanks: function () {
      var self = this, i;
      var back = this.add.rectangle(W / 2, 250, 700, 330, 0x0d1126, 0.88).setStrokeStyle(4, 0x1e2a5a);
      this.layer.add(back);
      var tanks = [];
      for (i = 0; i < 3; i++) {
        var t = this.add.image(260 + i * 220, 376, 'tank4', 4).setOrigin(0.5, 1).setScale(3);
        var gl = this.add.image(260 + i * 220, 250, 'glow_soft').setBlendMode(Phaser.BlendModes.ADD).setTint(COL.cyan).setAlpha(0.3).setScale(2);
        var fr = UI.Frac(this, 260 + i * 220, 116, 4, 4, { font: 'ui44', tint: COL.cyanL });
        this.layer.add([gl, t, fr]); tanks.push({ t: t, fr: fr });
      }
      tanks.forEach(function (o, k) {
        self.time.delayedCall(1500 + k * 550, function () {
          if (!o.t.active) return;
          o.t.setFrame(3); o.fr.set(3, 4); o.fr.setCol(COL.redL);
          MB.sfx('wrong', { vol: 0.6 });
          self.tweens.add({ targets: o.t, x: o.t.x + 4, duration: 50, yoyo: true, repeat: 3 });
          var sp = self.add.sprite(o.t.x, 190, 'fx_ring').setScale(2).setTint(COL.pink).play('fx_ring_play');
          sp.once('animationcomplete', function () { sp.destroy(); });
          self.layer.add(sp);
        });
      });
      var ph = this.add.sprite(W / 2, 250, 'phantom').setScale(4).setAlpha(0).play('phantom_float');
      this.layer.add(ph);
      this.time.delayedCall(3300, function () { if (ph.active) { self.tweens.add({ targets: ph, alpha: 0.22, duration: 300, yoyo: true, hold: 500 }); MB.sfx('bossLaugh', { vol: 0.5 }); } });
      return ['n02'];
    },

    // shot 3: Jake's shuttle arrives
    shotArrive: function () {
      var st = this.add.image(430, 40, 'intro_station').setOrigin(0, 0).setScale(2);
      var sh = this.add.sprite(-120, 400, 'shuttle').setScale(4).play('shuttle_fly');
      var gl = this.add.image(-200, 404, 'glow').setBlendMode(Phaser.BlendModes.ADD).setTint(COL.orange).setAlpha(0.6).setScale(2);
      this.layer.add([st, gl, sh]);
      this.tweens.add({ targets: sh, x: 330, y: 330, duration: 5200, ease: 'Sine.out' });
      this.tweens.add({ targets: gl, x: 220, y: 334, duration: 5200, ease: 'Sine.out' });
      this.tweens.add({ targets: sh, scale: 3, delay: 5200, duration: 5000 });
      MB.sfx('transition', { vol: 0.5 });
      return ['n03', 'j01'];
    },

    finish: function () {
      var self = this;
      if (this.done) return;
      this.done = true;
      this.dialogue.skipAll();
      this.cameras.main.fadeOut(400, 5, 6, 12);
      this.cameras.main.once('camerafadeoutcomplete', function () { self.scene.start('Game'); });
    },

    update: function (time, delta) { this.bg.update(time); this.dialogue.update(delta); }
  });
})();
