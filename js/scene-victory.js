/* Math Blast Arcade - victory sequence and results card. */
(function () {
  'use strict';
  var C = MB.CFG, COL = MB.COL, UI = MB.UI, W = C.W, H = C.H;

  // Count every fuel quarter in the level (plus the Missing Quarter itself).
  MB.countQuarters = function () {
    if (MB._totalQ) return MB._totalQ;
    var n = 0;
    MB.AREAS.forEach(function (a) { a.build().ents.forEach(function (e) { if (e.type === 'chip') n++; }); });
    MB._totalQ = n + 1;
    return MB._totalQ;
  };
  MB.TOTAL_PUZZLES = 13;   // 3 bridges, 3 reactors, 3 gates, the pods, 3 boss shields

  MB.Scenes.Victory = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Victory() { Phaser.Scene.call(this, { key: 'Victory' }); },

    create: function () {
      var self = this;
      this.cameras.main.setBackgroundColor('#05060c');
      this.bg = MB.spaceBackdrop(this, { planetX: 560, planetY: 90 });
      this.station = this.add.image(40, 150, 'intro_station').setOrigin(0, 0).setScale(2).setDepth(-90);
      this.add.image(0, 0, 'vignette').setOrigin(0, 0).setScale(2).setDepth(-50);
      this.ships = [];
      this.dialogue = new UI.Dialogue(this);
      MB.music('victory');
      MB.clearTouch();
      var run = MB.Save.data.run || MB.Save.newRun();
      this.result = this.score(run);
      // the three cargo ships can finally launch
      [0, 1, 2].forEach(function (i) {
        var s = self.add.sprite(300 + i * 30, 300 + i * 26, 'shuttle').setScale(2).setDepth(-80).play({ key: 'shuttle_fly', startFrame: i });
        s.setTint([0xffffff, 0xa9c5f0, 0xffc46b][i]);
        self.tweens.add({ targets: s, x: W + 200, y: 120 + i * 60, delay: 600 + i * 900, duration: 5200, ease: 'Quad.in' });
      });
      this.input.keyboard.on('keydown', function (ev) {
        if (ev.code === 'KeyE' || ev.code === 'Space' || ev.code === 'Enter' || ev.code === 'KeyX') self.dialogue.advance();
        else if (ev.code === 'Escape') self.dialogue.skipAll();
      });
      this.input.on('pointerdown', function () { self.dialogue.advance(); });
      this.cameras.main.fadeIn(500, 5, 6, 12);
      this.time.delayedCall(900, function () { self.dialogue.play(['n04', 'n05'], function () { self.showCard(); }); });
    },

    score: function (run) {
      var totalQ = MB.countQuarters(), q = Math.min(run.quarters, totalQ);
      var stars = Object.keys(run.stars || {}).length;
      var first = Math.min(run.firstTry || 0, MB.TOTAL_PUZZLES);
      var rating = 1;
      if (q >= Math.ceil(totalQ * 0.75)) rating++;
      if (first >= 9) rating++;
      var res = { quarters: q, totalQ: totalQ, secrets: stars, firstTry: first, hints: run.hints || 0, time: Math.round((run.time || 0) / 1000), stars: rating };
      var best = MB.Save.data.best;
      if (!best || res.stars > best.stars || (res.stars === best.stars && res.quarters > best.quarters)) MB.Save.data.best = res;
      MB.Save.data.completed = true;
      MB.Save.data.run = null;
      MB.Save.store();
      return res;
    },

    showCard: function () {
      var self = this, r = this.result, c = this.add.container(0, 0).setDepth(100);
      MB.sfx('victory');
      var pw = 640, ph = 452, px = (W - pw) / 2, py = 44;
      c.add(UI.panel(this, px, py, pw, ph, 'panel'));
      c.add(UI.text(this, W / 2, py + 22, 'MISSION COMPLETE', 'pix8', COL.gold, 0.5, 0));
      var tr = this.add.sprite(px + 64, py + 100, 'missingq').setScale(2).play('missingq_glow');
      c.add(tr);
      this.tweens.add({ targets: tr, y: py + 94, duration: 900, yoyo: true, repeat: -1, ease: 'Sine.inOut' });
      c.add(UI.text(this, W / 2, py + 50, 'The Missing Quarter is back where it belongs!', 'ui20', COL.text, 0.5, 0));
      // star rating
      for (var i = 0; i < 3; i++) (function (k) {
        var st = self.add.image(W / 2 - 60 + k * 60, py + 112, 'hud', MB.fr('hud', 'star_empty')).setScale(3);
        c.add(st);
        if (k < r.stars) self.time.delayedCall(500 + k * 380, function () {
          st.setFrame(MB.fr('hud', 'star_full')); st.setScale(5);
          self.tweens.add({ targets: st, scale: 3, duration: 260, ease: 'Back.out' });
          MB.sfx('chip', { pitch: 4 + k * 3 });
        });
      })(i);
      // rows
      var y = py + 150, x0 = px + 44;
      var jake = this.add.sprite(px + pw - 84, py + 250, 'jake').setScale(4).play('jake_celebrate');
      c.add(jake);
      var wholes = Math.floor(r.quarters / 4), rem = r.quarters % 4;
      function row(icon, label, value, col) {
        c.add(self.add.image(x0 + 14, y + 12, 'hud', MB.fr('hud', icon)).setScale(2));
        c.add(UI.text(self, x0 + 44, y, label, 'ui20', COL.text));
        c.add(UI.text(self, x0 + 44, y + 22, value, 'ui20', col || COL.gold).setScale(0.9));
        y += 54;
      }
      row('pie' + (rem || 4), 'Fuel quarters collected: ' + r.quarters + ' of ' + r.totalQ,
        r.quarters + ' quarters = ' + wholes + (wholes === 1 ? ' whole' : ' wholes') + (rem ? ' and ' + rem + (rem === 1 ? ' quarter' : ' quarters') : ' exactly'));
      row('go', 'Maths machines solved on the first test: ' + r.firstTry + ' of ' + MB.TOTAL_PUZZLES,
        r.hints ? 'Hints used: ' + r.hints + '. Asking for a hint is smart thinking.' : 'No hints needed. Sharp fractions, Inspector!', COL.cyanL);
      row('starcell', 'Secret star cells found: ' + r.secrets + ' of ' + MB.TOTAL_STARS,
        r.secrets >= MB.TOTAL_STARS ? 'You found every one!' : 'Some are still hidden on Kepler Station.', COL.cyanL);
      var m = Math.floor(r.time / 60), s = r.time % 60;
      c.add(UI.text(this, x0 + 44, y, 'Time on station: ' + m + ' min ' + (s < 10 ? '0' : '') + s + ' s', 'ui20', COL.dim).setScale(0.9));
      c.add(UI.text(this, W / 2, py + ph - 88, 'NEXT:  INTO THE FOG NEBULA   (coming soon)', 'pix8', COL.pink, 0.5, 0).setScale(1));
      var b1 = UI.button(this, W / 2 - 130, py + ph - 44, 230, 46, 'Play again', function () { self.leave('Intro', true); }, { tint: COL.gold });
      var b2 = UI.button(this, W / 2 + 130, py + ph - 44, 230, 46, 'Title screen', function () { self.leave('Title', false); });
      c.add([b1, b2]);
      this.menu = new UI.Menu(this, [b1, b2], { horizontal: true });
      c.alpha = 0; c.y = 20;
      this.tweens.add({ targets: c, alpha: 1, y: 0, duration: 350, ease: 'Quad.out' });
    },

    leave: function (key, fresh) {
      var self = this;
      if (this.leaving) return; this.leaving = true;
      MB.sfx('uiSelect');
      if (this.menu) this.menu.active = false;
      this.cameras.main.fadeOut(350, 5, 6, 12);
      this.cameras.main.once('camerafadeoutcomplete', function () {
        self.leaving = false;
        if (fresh) MB.Save.newRun();
        self.scene.start(key);
      });
    },

    update: function (time, delta) { this.bg.update(time); this.dialogue.update(delta); }
  });
})();
