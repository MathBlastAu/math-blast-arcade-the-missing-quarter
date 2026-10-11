/* Math Blast Arcade - unified keyboard + touch controls. */
(function () {
  'use strict';
  // Touch buttons (drawn by the HUD scene) write here.
  MB.touch = { left: false, right: false, jump: false, interact: false, pause: false, hint: false };

  MB.Controls = function (scene) {
    var K = Phaser.Input.Keyboard.KeyCodes;
    this.k = scene.input.keyboard.addKeys({
      left: K.LEFT, right: K.RIGHT, up: K.UP, down: K.DOWN, a: K.A, d: K.D, w: K.W, s: K.S,
      space: K.SPACE, e: K.E, enter: K.ENTER, esc: K.ESC, z: K.Z, x: K.X, p: K.P, h: K.H
    });
    scene.input.keyboard.addCapture([K.SPACE, K.UP, K.DOWN, K.LEFT, K.RIGHT]);
    this.prev = {};
    this.s = {};
  };
  MB.Controls.prototype.poll = function () {
    var k = this.k, t = MB.touch, n;
    var cur = {
      left: k.left.isDown || k.a.isDown || t.left,
      right: k.right.isDown || k.d.isDown || t.right,
      down: k.down.isDown || k.s.isDown,
      jump: k.space.isDown || k.up.isDown || k.w.isDown || k.z.isDown || t.jump,
      interact: k.e.isDown || k.enter.isDown || k.x.isDown || t.interact,
      pause: k.esc.isDown || k.p.isDown || t.pause,
      hint: k.h.isDown || t.hint
    };
    for (n in cur) {
      this.s[n] = !!cur[n];
      this.s[n + 'Pressed'] = !!cur[n] && !this.prev[n];
    }
    this.prev = cur;
    return this.s;
  };
  // Forget held state (after menus / dialogue) so a held key does not fire again.
  MB.Controls.prototype.flush = function () {
    var n; for (n in this.prev) this.prev[n] = true;
    for (n in this.s) if (/Pressed$/.test(n)) this.s[n] = false;
  };
  MB.clearTouch = function () { var n; for (n in MB.touch) MB.touch[n] = false; };
})();
