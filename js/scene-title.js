/* Math Blast Arcade - title screen. */
(function () {
  'use strict';
  var C = MB.CFG, COL = MB.COL, UI = MB.UI, W = C.W, H = C.H;

  // Shared drifting space backdrop (title, intro, victory). Returns { update(time) }.
  MB.spaceBackdrop = function (scene, o) {
    o = o || {};
    var stars = [0, 1].map(function (i) { return scene.add.image(i * 1024, -18, 'bg_stars').setOrigin(0, 0).setScale(2).setDepth(-100); });
    var neb = [0, 1].map(function (i) { return scene.add.image(i * 1024, -18, 'bg_nebula').setOrigin(0, 0).setScale(2).setDepth(-99); });
    var planet = scene.add.image(o.planetX == null ? 560 : o.planetX, o.planetY == null ? 120 : o.planetY, 'bg_planet').setOrigin(0, 0).setScale(2).setDepth(-98);
    var tw = [];
    for (var i = 0; i < 14; i++) {
      var st = scene.add.sprite(40 + ((i * 197) % 880), 20 + ((i * 131) % 380), 'fx_star').setScale(2).setDepth(-97).setAlpha(0.8);
      st.play({ key: 'fx_star_play', startFrame: i % 4, frameRate: 3 + (i % 4) });
      tw.push(st);
    }
    return {
      planet: planet,
      update: function (time) {
        var a = (time / 1000 * 6) % 1024, b = (time / 1000 * 11) % 1024;
        stars[0].x = Math.round(-a); stars[1].x = Math.round(1024 - a);
        neb[0].x = Math.round(-b); neb[1].x = Math.round(1024 - b);
      }
    };
  };

  MB.Scenes.Title = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Title() { Phaser.Scene.call(this, { key: 'Title' }); },

    create: function () {
      var self = this;
      window.MB_STARTED_OK = true;
      this.cameras.main.setBackgroundColor('#05060c');
      this.bg = MB.spaceBackdrop(this, { planetX: 590, planetY: 150 });
      this.station = this.add.image(-40, 190, 'intro_station').setOrigin(0, 0).setScale(2).setDepth(-90).setAlpha(0.95);
      this.tweens.add({ targets: this.station, y: 198, duration: 4200, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
      this.shuttle = this.add.sprite(-80, 400, 'shuttle').setScale(2).setDepth(-80).play('shuttle_fly');
      this.add.image(0, 0, 'vignette').setOrigin(0, 0).setScale(2).setDepth(-50);
      // the Phantom lurks
      var ph = this.add.sprite(828, 300, 'phantom').setScale(2).setDepth(-60).setAlpha(0.0).play('phantom_float').setFlipX(true);
      this.tweens.add({ targets: ph, alpha: 0.5, delay: 1200, duration: 1800 });
      this.tweens.add({ targets: ph, y: 310, duration: 2600, yoyo: true, repeat: -1, ease: 'Sine.inOut' });

      var logo = this.add.image(W / 2, 128, 'logo').setScale(2).setDepth(10);
      logo.y = -140;
      this.tweens.add({ targets: logo, y: 128, duration: 700, ease: 'Back.out' });
      this.tweens.add({ targets: logo, scale: 2.04, delay: 800, duration: 1600, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
      UI.shadow(UI.text(this, W / 2, 252, 'SPACE ARC   LEVEL 1', 'pix8', COL.cyan, 0.5, 0).setScale(1).setDepth(10));
      UI.shadow(UI.text(this, W / 2, 268, 'The Missing Quarter', 'ui28', COL.white, 0.5, 0).setDepth(10));

      this.buildMenu();
      UI.text(this, W / 2, H - 22, 'A fractions adventure for Year 4.   Move: arrow keys or A / D.   Jump: Space.   Use: E.', 'ui20', COL.dim, 0.5, 0.5).setDepth(10).setAlpha(0.9);
      MB.music('title');
      this.cameras.main.fadeIn(400, 5, 6, 12);
      MB.clearTouch();
    },

    buildMenu: function () {
      var self = this, items = [], y = 330;
      if (this.menu) { this.menu.destroy(); this.menuC.destroy(); }
      var c = this.menuC = this.add.container(0, 0).setDepth(20);
      var add = function (label, fn, opts) { var b = UI.button(self, W / 2, y, 300, 46, label, fn, opts); c.add(b); items.push(b); y += 52; return b; };
      var has = MB.Save.hasRun();
      if (has) {
        var a = MB.AREAS[MB.Save.data.run.area] || MB.AREAS[0];
        add('Continue', function () { self.go(false); }, { tint: COL.gold });
        c.add(UI.text(this, W / 2 + 162, 330 - 12, a.sub + ': ' + a.name, 'ui20', COL.dim, 0, 0).setScale(0.8));
        add('New game', function () { self.go(true); });
      } else {
        add('Play', function () { self.go(true); }, { tint: COL.gold });
      }
      add('How to play', function () { self.help(); });
      add('Options', function () { self.menu.active = false; c.setVisible(false); new MB.OptionsPanel(self, function () { c.setVisible(true); self.menu.active = true; }); });
      if (MB.Save.data.completed) c.add(UI.text(this, W / 2, y - 18, 'Level complete!  Best: ' + (MB.Save.data.best ? MB.Save.data.best.stars : 1) + ' of 3 stars', 'ui20', COL.gold, 0.5, 0).setScale(0.8));
      this.menu = new UI.Menu(this, items, {});
    },

    help: function () {
      var self = this, c = this.add.container(0, 0).setDepth(960);
      c.add(this.add.rectangle(0, 0, W, H, 0x05060c, 0.8).setOrigin(0, 0).setInteractive());
      MB.buildHelp(this, c);
      this.menu.active = false;
      var m;
      var b = UI.button(this, W / 2, 478, 200, 44, 'Back', function () { m.destroy(); c.destroy(); self.menu.active = true; MB.sfx('uiBack'); });
      c.add(b);
      m = new UI.Menu(this, [b], { onBack: function () { b.press(); } });
    },

    go: function (fresh) {
      var self = this;
      if (this.leaving) return;
      this.leaving = true;
      MB.sfx('uiSelect');
      try { if (MB.Audio) MB.Audio.unlock(); } catch (e) { /* ignore */ }
      this.menu.active = false;
      this.cameras.main.fadeOut(350, 5, 6, 12);
      this.cameras.main.once('camerafadeoutcomplete', function () {
        self.leaving = false;
        if (fresh) { MB.Save.newRun(); self.scene.start('Intro'); }
        else self.scene.start('Game');
      });
    },

    update: function (time) {
      this.bg.update(time);
      var s = this.shuttle;
      s.x += 0.9; s.y = 404 + Math.sin(time / 700) * 6;
      if (s.x > W + 120) s.x = -400;
    }
  });
})();
