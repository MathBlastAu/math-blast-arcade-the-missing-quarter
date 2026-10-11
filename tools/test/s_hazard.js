// Damage, falls, hearts, checkpoint respawn, relaxed mode.
module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  const expect = (c, m) => { h.log((c ? 'PASS ' : 'CHECK FAILED ') + m); if (!c) throw new Error(m); };
  const tp = (x, y) => h.ev(([x, y]) => { MBG.player.setPosition(x, y); MBG.player.body.reset(x, y); }, [x, y]);
  await h.waitGame();
  await h.ev(() => { ['t0_intro', 't0_tanks', 't0_gatehint'].forEach(k => MBG.run.seen[k] = 1); });
  // 1. walk into a robot from the side
  await tp(60 * 16, 224); await h.frames(10);
  await h.down('ArrowRight'); const ok = await h.until(() => MBG.run.hearts < 4, 400); await h.up('ArrowRight');
  expect(ok, 'touching a robot from the side costs one heart');
  expect(await h.ev(() => MBG.player.inv > 0), 'Jake gets a moment of invulnerability after a hit');
  await h.frames(120);
  // 2. stomp a robot
  const ex = await h.ev(() => { const e = MBG.sensors.getChildren().find(s => s.isEnemy && s.active && s.texture.key === 'crawler' && s.x > 78 * 16); return { x: e.x, y: e.y }; });
  await tp(ex.x - 6, ex.y - 44); await h.frames(40);
  expect(await h.ev(() => (MBG.run.stomps || 0) > 0), 'jumping on a robot switches it off');
  // 3. fall into a pit: lose a heart, come back on safe ground
  await h.ev(() => { MBG.run.hearts = 4; MBG.hud.refresh(); });
  await tp(66 * 16, 224); await h.frames(20);
  await h.down('ArrowRight'); await h.frames(50); await h.up('ArrowRight');
  await h.until(() => !MBG.falling && MBG.player.onFloor, 600); await h.frames(30);
  let s = await h.state();
  expect(s.hearts === 3 && s.tx <= 68, 'falling in a pit costs one heart and returns Jake to the last safe ground (tile ' + s.tx + ')');
  // 4. checkpoint, then lose all hearts -> restart at the checkpoint with full hearts
  await tp(89 * 16, 224); await h.frames(5); await h.go(91 * 16 + 8, 224); await h.frames(30);
  s = await h.state(); expect(s.hearts === 4, 'checkpoint refills hearts');
  await h.ev(() => { MBG.run.hearts = 1; MBG.hud.refresh(); });
  await tp(96 * 16, 300); await h.frames(10);     // drop into the drone pit
  await h.until(() => window.MBG && MBG.started && !MBG.dying && !MBG.falling && MBG.player.onFloor && !MBG.hud.irisOn, 1500); await h.frames(40);
  s = await h.state();
  expect(s.hearts === 4 && s.tx === 91, 'losing the last heart restarts at the checkpoint with full hearts (tile ' + s.tx + ', hearts ' + s.hearts + ')');
  await h.shot('hazard_respawn');
  // 5. relaxed mode: no heart loss
  await h.ev(() => { MB.Save.set('relaxed', true); });
  await tp(96 * 16, 300); await h.frames(10);
  await h.until(() => !MBG.falling && MBG.player.onFloor, 900); await h.frames(20);
  s = await h.state(); expect(s.hearts === 4, 'relaxed mode: falling costs no hearts');
  await h.ev(() => { MB.Save.set('relaxed', false); });
}};
