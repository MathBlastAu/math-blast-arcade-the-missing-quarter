// Menus, intro, pause, options, help, save/continue.
module.exports = { query: 'debug', run: async h => {
  const active = () => h.ev(() => MB.game.scene.getScenes(true).map(s => s.scene.key));
  const press = async k => { await h.down(k); await h.frames(3); await h.up(k); await h.frames(8); };
  const expect = (c, m) => { h.log((c ? 'PASS ' : 'CHECK FAILED ') + m); if (!c) throw new Error(m); };
  await h.frames(60); await h.shot('ui_title');
  expect((await active()).includes('Title'), 'title screen shows');
  await press('ArrowDown'); await press('Enter'); await h.frames(30); await h.shot('ui_help');
  await press('Escape'); await h.frames(10);
  await press('ArrowDown'); await press('Enter'); await h.frames(30); await h.shot('ui_options');
  await press('ArrowRight'); await press('ArrowDown'); await press('ArrowDown'); await press('Enter');   // music +1, toggle relaxed on
  const set = await h.ev(() => MB.Save.data.settings); h.log('  settings', JSON.stringify(set));
  expect(set.relaxed === true && Math.abs(set.music - 0.7) < 1e-6, 'options change and save settings');
  await press('Enter'); await press('Escape'); await h.frames(10);      // relaxed back off, close
  await press('ArrowUp'); await press('ArrowUp'); await press('Enter');  // Play
  await h.frames(60); expect((await active()).includes('Intro'), 'Play starts the opening cinematic');
  await h.frames(60); await h.shot('ui_intro1');
  for (let i = 0; i < 8; i++) { await press('KeyE'); await h.frames(30); if (i === 2) await h.shot('ui_intro2'); if (i === 5) await h.shot('ui_intro3'); if (!(await active()).includes('Intro')) break; }
  for (let i = 0; i < 40 && !(await active()).includes('Game'); i++) { await press('KeyE'); await h.frames(30); }
  expect((await active()).includes('Game'), 'cinematic leads into the game');
  await h.waitGame(); await h.frames(60); await h.shot('ui_game_start');
  // pause
  await press('Escape'); await h.frames(20); await h.shot('ui_pause');
  expect(await h.ev(() => MBG.hud.paused && MBG.scene.isPaused()), 'Esc pauses the game');
  await press('Escape'); await h.frames(10);
  expect(await h.ev(() => !MBG.hud.paused && !MBG.scene.isPaused()), 'Esc resumes');
  // walk to trigger intro, finish it, reach checkpoint-free save, then reload: Continue must appear
  await h.go(300, 224); await h.frames(20);
  const q = (await h.state()).q;
  await h.page.reload(); await h.page.waitForFunction(() => window.MB && MB.ready);
  await h.page.waitForTimeout(1500);
  const has = await h.page.evaluate(() => ({ run: !!MB.Save.data.run, q: MB.Save.data.run && MB.Save.data.run.quarters, seen: MB.Save.data.run && Object.keys(MB.Save.data.run.seen) }));
  h.log('  after reload', JSON.stringify(has));
  expect(has.run, 'progress survives a page reload (local save)');
  await h.page.screenshot({ path: require('path').join(__dirname, 'out', 'ui_title_continue.png') });
}};
