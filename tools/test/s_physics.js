// Measure Jake's real jump height and distance.
module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  await h.waitGame();
  await h.ev(() => { MBG.run.seen['t0_intro'] = 1; MBG.player.setPosition(19 * 16, 224); MBG.player.body.reset(19 * 16, 224); });
  await h.wait(300);
  const s0 = await h.state();
  // full jump straight up
  let minY = 999; await h.down('Space');
  for (let i = 0; i < 50; i++) { await h.frames(1); const s = await h.state(); minY = Math.min(minY, s.y); }
  await h.up('Space'); await h.wait(500);
  h.log('full jump height px:', s0.y - minY, 'tiles:', ((s0.y - minY) / 16).toFixed(2));
  // tap jump
  minY = 999; await h.down('Space'); await h.frames(3); await h.up('Space');
  for (let i = 0; i < 50; i++) { await h.frames(1); const s = await h.state(); minY = Math.min(minY, s.y); }
  h.log('tap jump height px:', s0.y - minY);
  // running jump distance on flat
  await h.ev(() => { MBG.player.setPosition(13 * 16, 224); MBG.player.body.reset(13 * 16, 224); });
  await h.down('ArrowRight'); await h.frames(40);
  const a = await h.state(); await h.down('Space'); let air = 0, b;
  for (let i = 0; i < 80; i++) { await h.frames(1); b = await h.state(); if (i > 3 && b.floor) { air = i; break; } }
  await h.up('Space'); await h.up('ArrowRight');
  h.log('running jump distance px:', b.x - a.x, 'tiles:', ((b.x - a.x) / 16).toFixed(2), 'air frames:', air);
}};
