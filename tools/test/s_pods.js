const full = require('./full.js');
module.exports = { query: 'debug&scene=game&new&area=3', run: async h => {
  await h.waitGame();
  await h.ev(() => { const r = MBG.run; r.solved.g1 = 1; r.solved.g2 = 1; ['t3_z_intro','t3_g_intro','t3_p_intro'].forEach(k => r.seen[k] = 1); r.checkpoint = { area: 3, id: 999, x: 85 * 16 + 8, y: 23 * 16 }; MBG.scene.restart(); });
  await h.wait(300); await h.waitGame();
  const step = async (name, x, y, o, max) => { const ok = await h.go(x, y, o, max); const s = await h.state(); h.log((ok ? 'ok   ' : 'FAIL ') + name, s.x, s.y); };
  const pod = async (tx, ty, name) => { await step('pod ' + name, tx * 16 + 8, ty * 16, { reach: 26, hold: 44 }, 700); await h.frames(20); h.log('   pods:', JSON.stringify(await h.ev(() => MBG.podGroups[0].debug()))); };
  const down = async (tx) => { await step('catwalk ' + tx, tx * 16 + 8, 320, { walkOff: true, drop: 6 }); h.log('   pods:', JSON.stringify(await h.ev(() => MBG.podGroups[0].debug()))); };
  await step('catwalk', 89 * 16 + 8, 320);
  await pod(91, 17, '1/2 wrong'); await down(94); await pod(96, 16, '1/8'); await down(104); await pod(106, 16, '1/4');
  await down(93); await pod(91, 17, '1/2'); await down(99); await pod(101, 17, '3/4'); await down(109); await pod(111, 17, '7/8');
  await h.shot('pods_dbg');
}};
