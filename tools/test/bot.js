// Test bot (injected into the page by the scenario runner). Drives Jake through
// MB.touch, exactly as the on-screen buttons do, one decision per frame.
window.BOT = {
  target: null, done: true, jumpHold: 0, log: [], stuck: 0, lastX: 0,
  go(x, y, opts) { this.target = { x, y: y == null ? null : y, o: opts || {} }; this.done = false; this.stuck = 0; },
  stop() { this.target = null; this.done = true; MB.touch.left = MB.touch.right = MB.touch.jump = false; },
  solidAt(px, py) { const g = MBG; const v = g.A.get(Math.floor(px / 16), Math.floor(py / 16)); return v; },
  mode: null,
  bossFrame() {
    const g = MBG, p = g.player, b = g.boss, T = MB.touch;
    const shots = g.sensors.getChildren().filter(s => s.active && s.texture && (s.texture.key === 'bolt' || s.texture.key === 'orb'));
    let best = p.x, bs = -1e9;
    for (let x = 40; x <= 440; x += 20) {
      let sc = -Math.abs(x - p.x) * 0.05 - Math.max(0, 40 - Math.abs(x - 240)) * 0.2;
      for (const s of shots) {
        const vy = s.vy || 0, vx = s.vx || 0; if (Math.abs(vy) < 5) continue;
        const dy = (p.y - 12) - s.y; const px = vy > 5 ? s.x + vx * (dy / vy) : s.x;
        sc -= Math.max(0, 56 - Math.abs(x - px));
      }
      for (const wx of (b.warnXs || [])) sc -= Math.max(0, 44 - Math.abs(x - wx));
      if (sc > bs) { bs = sc; best = x; }
    }
    const dx = best - p.x;
    T.left = dx < -4; T.right = dx > 4;
    let jump = false;
    for (const s of shots) if (Math.abs(s.vy || 0) < 5 && Math.abs(s.x - p.x) < 50 && (p.x - s.x) * (s.vx || 0) > 0) jump = true;
    if (jump && p.onFloor) this.jumpHold = 16;
    T.jump = this.jumpHold-- > 0;
  },
  frame() {
    if (this.mode === 'boss' && window.MBG && MBG.boss) return this.bossFrame();
    const g = window.MBG; if (!g || !g.started || !this.target) return;
    const p = g.player, t = this.target, b = p.body, T = MB.touch;
    const feet = p.gdir > 0 ? b.bottom : b.top, x = p.x;
    const dx = t.x - x, dir = Math.abs(dx) < 3 ? 0 : (dx > 0 ? 1 : -1);
    const low = p.lowG;
    T.left = dir < 0; T.right = dir > 0;
    let jump = false;
    const gd = p.gdir;
    if (p.onFloor) {
      const ahead = x + dir * 9;
      const wall = dir && this.solidAt(ahead, feet - 4 * gd) === 1 || (dir && this.solidAt(ahead, feet - 14 * gd) === 1);
      // is there ground within a few tiles below the next step?
      let ground = false;
      for (let k = 0; k <= (t.o.drop || 2); k++) if (this.solidAt(x + dir * 12, feet + (2 + k * 16) * gd)) ground = true;
      // solid sprites (bridge planks, platforms, pods) also count as ground
      if (!ground) g.solids.getChildren().forEach(s => { if (s.body && s.body.enable && Math.abs((s.body.center.x) - (x + dir * 12)) < s.body.halfWidth + 2 && s.body.top >= feet - 3 && s.body.top < feet + 40) ground = true; });
      const need = t.y != null && (feet - t.y) * gd > 10 && Math.abs(dx) < (t.o.reach || (low ? 110 : 62));
      let enemy = false;
      g.sensors.getChildren().forEach(s => { if ((s.isEnemy || s.texture && (s.texture.key === 'spikes')) && s.body && s.body.enable && dir && (s.x - x) * dir > 0 && (s.x - x) * dir < (t.o.enemyDist || 34) && Math.abs(s.y - (feet - 8)) < 26) enemy = true; });
      if (wall || (!ground && dir && !t.o.walkOff) || need || enemy || t.o.jumpNow) jump = true;
      if (t.o.jumpNow) t.o.jumpNow = false;
      if (jump) this.jumpHold = t.o.hold || (low ? 40 : 24);
    } else {
      if (this.jumpHold > 0) { this.jumpHold--; jump = true; }
      // release early for small hops when the target is level and close
      if (t.o.short && this.jumpHold < 14) jump = false;
    }
    T.jump = jump;
    if (dir === 0 && p.onFloor && (t.y == null || Math.abs(feet - t.y) < 8)) { this.stop(); }
    if (Math.abs(x - this.lastX) < 0.2) this.stuck++; else this.stuck = 0;
    this.lastX = x;
  }
};
