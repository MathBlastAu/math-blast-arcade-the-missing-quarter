// Bot playthrough of Area 1 (Docking Bay) with real inputs.
module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  const T = h.tile, F = 13;
  await h.waitGame();
  const step = async (name, x, y, o, max) => { const ok = await h.go(x, y, o, max); const s = await h.state(); h.log((ok ? 'ok   ' : 'FAIL ') + name, JSON.stringify({ x: s.x, y: s.y, tx: s.tx, hearts: s.hearts, q: s.q })); if (!ok) { await h.shot('fail_' + name); throw new Error('stuck at ' + name); } };
  await step('to priya', ...T(12, F));           // triggers the intro dialogue (auto-advanced)
  await step('step block', ...T(29, 11));
  await step('past dip', ...T(38, F));
  await step('gate hint', ...T(52, F));
  await step('plat qkey1', ...T(55, 11));
  await step('floor', ...T(60, F));
  await step('after pit', ...T(72, F));
  await step('raised', ...T(80, 9));
  await step('qkey2', ...T(83, 9), { jumpNow: true });
  await h.go(...T(83, 9), { jumpNow: true }); 
  await step('down', ...T(89, F));
  await step('checkpoint', ...T(91, F));
  await step('plat a', ...T(97, 11));
  await step('plat b', ...T(101, 11));
  await h.go(...T(101, 11), { jumpNow: true });  // hop for qkey 3
  await step('floor c', ...T(106, F));
  await step('spring', ...T(109, F), { walkOff: true });
  h.log(await h.state());
}};
