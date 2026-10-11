/* Math Blast Arcade - Jake: responsive, forgiving platforming.
 * Features: acceleration/friction, variable jump height, coyote time, jump
 * buffering, asymmetric gravity, low-gravity and flipped-gravity modes,
 * squash-and-stretch, dust, invulnerability frames. */
(function () {
  'use strict';
  var C = MB.CFG;

  MB.Player = new Phaser.Class({
    Extends: Phaser.Physics.Arcade.Sprite,
    initialize: function Player(scene, x, y) {
      Phaser.Physics.Arcade.Sprite.call(this, scene, x, y, 'jake', 0);
      scene.add.existing(this);
      scene.physics.add.existing(this);
      this.setOrigin(0.5, 1);
      this.body.setSize(10, 22);
      this.body.setOffset(11, 9);
      this.body.setAllowGravity(true);
      this.setDepth(60);
      this.gdir = 1;            // +1 normal gravity, -1 flipped
      this.lowG = false;
      this.facing = 1;
      this.coyote = 0; this.buffer = 0; this.jumpHeld = false;
      this.inv = 0; this.hurtT = 0; this.landT = 0; this.stepT = 0;
      this.locked = false;      // cut-scenes / consoles
      this.pose = null;         // forced animation: 'interact' | 'celebrate'
      this.onFloor = false; this.wasOnFloor = true; this.airVy = 0;
      this.dead = false;
      this.play('jake_idle');
    },

    setGravityDir: function (dir) {
      if (dir === this.gdir) return;
      this.gdir = dir;
      // keep the body where it is while the art flips inside the frame
      if (dir < 0) { this.body.setOffset(11, 1); this.y += 8; } else { this.body.setOffset(11, 9); this.y -= 8; }
      this.setFlipY(dir < 0);
      this.coyote = 0;
    },

    tick: function (dt, inp) {
      var b = this.body, g = this.gdir, scene = this.scene;
      var onFloor = g > 0 ? (b.blocked.down || b.touching.down) : (b.blocked.up || b.touching.up);
      this.onFloor = onFloor;
      var canAct = !this.locked && this.hurtT <= 0 && !this.dead;

      if (onFloor) this.coyote = C.COYOTE; else this.coyote -= dt;
      if (inp.jumpPressed && canAct) this.buffer = C.BUFFER; else this.buffer -= dt;

      // ---- horizontal ----
      var dir = canAct ? ((inp.right ? 1 : 0) - (inp.left ? 1 : 0)) : 0;
      var k = dt / 1000;
      if (this.hurtT > 0) {
        b.velocity.x = MB.approach(b.velocity.x, 0, 260 * k);
      } else if (dir) {
        var turning = (b.velocity.x * dir < 0);
        b.velocity.x = MB.approach(b.velocity.x, dir * C.RUN, (onFloor ? C.ACC_G : C.ACC_A) * (turning ? 2.2 : 1) * k);
        this.facing = dir;
      } else {
        b.velocity.x = MB.approach(b.velocity.x, 0, (onFloor ? C.FRIC : C.FRIC * 0.45) * k);
      }

      // ---- jump ----
      if (this.buffer > 0 && this.coyote > 0 && canAct) {
        b.velocity.y = -(this.lowG ? C.LOWG.jump : C.JUMP) * g;
        this.buffer = 0; this.coyote = 0; this.jumpHeld = true;
        MB.sfx('jump');
        scene.fx.dust(this.x, this.feetY(), 3);
        this.stretch(0.86, 1.14, 140);
        onFloor = false;
      }
      var rising = b.velocity.y * g < 0;
      if (this.jumpHeld && !inp.jump && rising) { b.velocity.y *= C.CUT; this.jumpHeld = false; }
      if (!rising) this.jumpHeld = false;

      // ---- gravity ----
      var grav = rising ? C.GRAV_UP : C.GRAV_DOWN;
      var maxFall = C.MAXFALL;
      if (this.lowG) { grav *= C.LOWG.scale; maxFall = C.LOWG.maxfall; }
      b.setGravityY(grav * g);
      if (b.velocity.y * g > maxFall) b.velocity.y = maxFall * g;

      // ---- landing ----
      if (onFloor && !this.wasOnFloor) {
        if (this.airVy > 120) {
          MB.sfx('land', { vol: Math.min(1, this.airVy / 300) });
          scene.fx.dust(this.x, this.feetY(), this.airVy > 240 ? 5 : 3);
          this.stretch(1.16, 0.84, 150);
          this.landT = 110;
        }
      }
      if (!onFloor) this.airVy = b.velocity.y * g;
      this.wasOnFloor = onFloor;

      // ---- timers / feedback ----
      if (this.inv > 0) {
        this.inv -= dt;
        this.setAlpha(this.inv > 0 && (Math.floor(this.inv / 70) % 2 === 0) ? 0.35 : 1);
      }
      if (this.hurtT > 0) this.hurtT -= dt;
      if (this.landT > 0) this.landT -= dt;
      if (onFloor && Math.abs(b.velocity.x) > 60) {
        this.stepT -= dt;
        if (this.stepT <= 0) { this.stepT = 230; MB.sfx('step', { vol: 0.35 }); if (Math.random() < 0.5) scene.fx.dust(this.x - this.facing * 4, this.feetY(), 1); }
      }

      // ---- animation ----
      var a;
      if (this.hurtT > 0) a = 'jake_hurt';
      else if (this.pose) a = 'jake_' + this.pose;
      else if (!onFloor) a = rising ? 'jake_jump' : 'jake_fall';
      else if (this.landT > 0 && Math.abs(b.velocity.x) < 40) a = 'jake_land';
      else if (Math.abs(b.velocity.x) > 14) a = 'jake_run';
      else a = 'jake_idle';
      if (this.anims.getName() !== a) this.play(a, true);
      this.setFlipX(this.facing < 0);
    },

    feetY: function () { return this.gdir > 0 ? this.body.bottom : this.body.top; },
    centerY: function () { return this.body.center.y; },

    stretch: function (sx, sy, ms) {
      this.scene.tweens.killTweensOf(this);
      this.setScale(sx, sy);
      this.scene.tweens.add({ targets: this, scaleX: 1, scaleY: 1, duration: ms, ease: 'Quad.out' });
    },

    bounce: function (v, held) {
      this.body.velocity.y = -(v || 250) * this.gdir;
      this.jumpHeld = !!held; this.coyote = 0;
      this.stretch(0.86, 1.14, 160);
    },

    // returns true if damage was taken
    hurt: function (fromX, opts) {
      if (this.inv > 0 || this.dead || this.locked) return false;
      opts = opts || {};
      var dirx = (this.x < fromX) ? -1 : 1;
      this.body.velocity.x = dirx * 150;
      this.body.velocity.y = -210 * this.gdir;
      this.hurtT = 320; this.inv = C.INVULN; this.jumpHeld = false;
      MB.sfx('hurt');
      this.scene.onPlayerHurt(opts);
      return true;
    },

    freeze: function (pose) {
      this.locked = true; this.pose = pose || null;
      this.body.velocity.x = 0;
    },
    unfreeze: function () { this.locked = false; this.pose = null; }
  });
})();
