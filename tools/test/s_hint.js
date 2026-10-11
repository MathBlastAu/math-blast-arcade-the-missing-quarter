module.exports = { query: 'debug&scene=game&new&area=2', run: async h => {
  const expect = (c, m) => { h.log((c ? 'PASS ' : 'CHECK FAILED ') + m); if (!c) throw new Error(m); };
  await h.waitGame(); await h.go(7 * 16, 496, {}, 300); await h.frames(20);
  expect(await h.ev(() => MBG.hud.hintBtn.visible), 'hint bulb appears next to an unsolved reactor');
  await h.key('KeyH', 60); await h.frames(40);
  expect(await h.ev(() => MBG.run.hints === 1 && MBG.hud.toast.busy), 'pressing H shows a hint');
  await h.shot('hint_reactor');
}};
