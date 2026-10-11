// Mouse / pointer operation of menus and the fraction console.
module.exports = { query: 'debug', run: async h => {
  const expect = (c, m) => { h.log((c ? 'PASS ' : 'CHECK FAILED ') + m); if (!c) throw new Error(m); };
  const active = () => h.ev(() => MB.game.scene.getScenes(true).map(s => s.scene.key));
  const click = async (x, y) => { await h.page.mouse.move(x, y); await h.frames(2); await h.page.mouse.down(); await h.frames(2); await h.page.mouse.up(); await h.frames(10); };
  await h.frames(60);
  await click(480, 434);   // Options
  await h.frames(20); await h.shot('mouse_options');
  await click(480, 232); await h.frames(5);     // relaxed toggle row
  expect(await h.ev(() => MB.Save.get('relaxed') === true), 'clicking an option row toggles it');
  await click(480, 232); 
  await click(480, 386 + 0); await h.frames(10);   // Back
  await click(480, 330); await h.frames(60);       // Play
  expect((await active()).includes('Intro'), 'clicking Play starts the cinematic');
  await click(880, 22); await h.frames(60);        // Skip
  for (let i = 0; i < 30 && !(await active()).includes('Game'); i++) await h.frames(10);
  expect((await active()).includes('Game'), 'Skip button jumps to the game');
  await h.waitGame();
  // go straight to the bridge console in area 2
  await h.ev(() => { MB.Save.data.run.area = 1; MBG.scene.restart(); }); await h.frames(20); await h.waitGame();
  await h.ev(() => { MBG.run.seen['t1_b_intro'] = 1; MBG.player.setPosition(168, 208); MBG.player.body.reset(168, 208); }); await h.frames(20);
  await h.key('KeyE', 60); await h.until(() => MBG.hud.console.active, 100); await h.frames(40);
  await click(125, 230);   // first cell (1/4)
  expect(await h.ev(() => MBG.hud.console.placed.length === 1), 'clicking a cell adds it to the bridge');
  await h.shot('mouse_console');
  await click(634, 230);   // Hint
  expect(await h.ev(() => MBG.hud.console.hintI === 1), 'Hint button shows a hint');
  await h.shot('mouse_hint');
  await click(772, 230);   // POWER ON
  await h.until(() => !MBG.hud.console.active, 600); await h.frames(60);
  expect(await h.ev(() => !!MBG.run.solved.b1), 'POWER ON by mouse solves the bridge');
}};
