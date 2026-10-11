/* Math Blast Arcade - Boot scene: decode embedded assets, register textures,
 * animations and bitmap fonts, then go to the title screen. */
(function () {
  'use strict';
  MB.Scenes = MB.Scenes || {};

  MB.Scenes.Boot = new Phaser.Class({
    Extends: Phaser.Scene,
    initialize: function Boot() { Phaser.Scene.call(this, { key: 'Boot' }); },

    create: function () {
      var self = this, A = window.MB_ASSETS;
      var W = MB.CFG.W, H = MB.CFG.H;
      this.cameras.main.setBackgroundColor('#05060c');
      var g = this.add.graphics();
      var draw = function (p) {
        g.clear();
        g.fillStyle(0x141a3a, 1); g.fillRect(W / 2 - 182, H / 2 - 12, 364, 24);
        g.fillStyle(0x2de0d0, 1); g.fillRect(W / 2 - 178, H / 2 - 8, Math.round(356 * p), 16);
        // quarter ticks: the loading bar is a fraction bar too
        g.fillStyle(0x05060c, 1);
        for (var i = 1; i < 4; i++) g.fillRect(W / 2 - 178 + 89 * i - 1, H / 2 - 8, 2, 16);
      };
      draw(0);
      if (!A || !A.manifest) { this.fail('Asset bundle missing (js/assets-embedded.js). Run: python3 tools/build.py'); return; }
      MB.Save.load();

      var man = A.manifest, jobs = [], k;
      for (k in man.sheets) (function (key, v) {
        jobs.push({ file: v.file, cb: function (img) { self.textures.addSpriteSheet(key, img, { frameWidth: v.fw, frameHeight: v.fh }); } });
      })(k, man.sheets[k]);
      for (k in man.images) (function (key, v) {
        jobs.push({ file: v.file, cb: function (img) { self.textures.addImage(key, img); } });
      })(k, man.images[k]);
      for (k in man.fonts) (function (key, v) {
        jobs.push({ file: v.png, cb: function (img) {
          var tex = self.textures.addImage(key, img);
          var xml = new DOMParser().parseFromString(A.text[v.fnt], 'application/xml');
          var data = Phaser.GameObjects.BitmapText.ParseXMLBitmapFont(xml, self.textures.getFrame(key), 0, 0, tex);
          self.cache.bitmapFont.add(key, { data: data, texture: key, frame: null });
        } });
      })(k, man.fonts[k]);

      var done = 0, failed = false;
      jobs.forEach(function (j) {
        var img = new Image();
        img.onload = function () {
          if (failed) return;
          try { j.cb(img); } catch (e) { failed = true; self.fail('Could not prepare ' + j.file + ': ' + e.message); return; }
          done++; draw(done / jobs.length);
          if (done === jobs.length) self.finish();
        };
        img.onerror = function () { failed = true; self.fail('Could not decode ' + j.file); };
        img.src = A.files[j.file];
      });
    },

    finish: function () {
      var man = MB_ASSETS.manifest, k, a, self = this;
      for (k in man.sheets) {
        var sh = man.sheets[k];
        for (a in (sh.anims || {})) {
          var d = sh.anims[a];
          this.anims.create({
            key: k + '_' + a,
            frames: this.anims.generateFrameNumbers(k, { frames: d.frames }),
            frameRate: d.fps, repeat: d.loop ? -1 : 0
          });
        }
      }
      // smooth filtering for the soft lighting textures (everything else stays crisp)
      ['glow', 'glow_soft', 'lightcone', 'vignette'].forEach(function (key) {
        if (self.textures.exists(key)) self.textures.get(key).setFilter(Phaser.Textures.FilterMode.LINEAR);
      });
      if (MB.Audio) { try { MB.Audio.init(); MB.Save.applyAudio(); } catch (e) { /* audio is optional */ } }
      // first user gesture unlocks audio; also detect touch devices
      var unlock = function (ev) {
        if (ev && ev.type === 'touchstart') MB.isTouch = true;
        try { if (MB.Audio) MB.Audio.unlock(); } catch (e) { /* ignore */ }
      };
      window.addEventListener('pointerdown', unlock, true);
      window.addEventListener('touchstart', unlock, { capture: true, passive: true });
      window.addEventListener('keydown', unlock, true);
      MB.ready = true;
      var start = MB.QUERY.get('scene');
      if (MB.DEBUG && start === 'game') {
        if (!MB.Save.hasRun() || MB.QUERY.has('new')) MB.Save.newRun();
        if (MB.QUERY.has('area')) { MB.Save.data.run.area = parseInt(MB.QUERY.get('area'), 10) || 0; MB.Save.data.run.checkpoint = null; }
        this.scene.start('Game');
      } else if (MB.DEBUG && start) {
        this.scene.start(start);
      } else {
        this.scene.start('Title');
      }
    },

    fail: function (msg) {
      var el = document.getElementById('fatal');
      if (el) { el.textContent = msg; el.style.display = 'block'; el.hidden = false; }
      if (window.console) console.error(msg);
    }
  });
})();
