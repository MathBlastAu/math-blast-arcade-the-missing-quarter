module.exports = { query: 'debug&scene=game&new&area=4', run: async h => {
  await h.waitGame();
  for (let i = 0; i < 300; i++) { await h.frames(6); await h.talk(); if (await h.ev(() => MBG.boss.state === 'attack')) break; }
  await h.ev(() => { const b = MBG.boss; b.token++; b.startThink(true); b.value = { n: 3, d: 4 }; b.showValue(); });
  await h.go(196, 224); 
  await h.down('KeyE'); await h.frames(3); await h.up('KeyE');
  const ok = await h.until(() => MBG.boss.hit.body.enable, 600);
  h.log('stompable', ok, JSON.stringify(await h.ev(() => ({ st: MBG.boss.state, sx: MBG.boss.sp.x, sy: MBG.boss.sp.y, hit: [MBG.boss.hit.body.x, MBG.boss.hit.body.y, MBG.boss.hit.body.width, MBG.boss.hit.body.height], px: MBG.player.x, hearts: MBG.run.hearts }))));
  await h.shot('bossdbg_stunned');
  const hx = await h.ev(() => MBG.boss.sp.x);
  await h.go(hx + (hx < 240 ? 44 : -44), 224, { walkOff: true });
  await h.down(hx < 240 ? 'ArrowLeft' : 'ArrowRight'); await h.down('Space');
  for (let i = 0; i < 50; i++) { await h.frames(1); if (i === 22) await h.up('Space'); const s = await h.ev(() => ({ x: Math.round(MBG.player.x), bot: Math.round(MBG.player.body.bottom), vy: Math.round(MBG.player.body.velocity.y), st: MBG.boss.state, hp: MBG.boss.hp, hb: MBG.boss.hit.body.enable, hy: Math.round(MBG.boss.hit.body.y) })); if (i % 3 === 0) h.log(i, JSON.stringify(s)); }
  await h.up('ArrowLeft'); await h.up('ArrowRight');
  await h.shot('bossdbg_after');
}};
