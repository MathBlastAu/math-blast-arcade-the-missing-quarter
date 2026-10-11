// Gallery screenshots for visual review / the delivery report.
module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  await h.waitGame();
  await h.go(300, 224, {}, 300); await h.frames(10);
  await h.go(12 * 16, 224, {}, 60);
  await h.ev(() => { delete MBG.run.seen['t0_intro']; MBG.player.setPosition(170, 224); MBG.player.body.reset(170, 224); });
  await h.down('ArrowRight'); await h.frames(30); await h.up('ArrowRight'); await h.frames(60);
  await h.shot('g_dialogue_top');
  await h.talk();
  await h.go(22 * 16, 224); await h.frames(30); await h.shot('g_dock_move_tip');
  await h.ev(() => { ['t0_tanks', 't0_gatehint'].forEach(k => MBG.run.seen[k] = 1); MBG.player.setPosition(40 * 16, 224); MBG.player.body.reset(40 * 16, 224); });
  await h.frames(40); await h.shot('g_dock_tanks');
  await h.ev(() => { MBG.player.setPosition(137 * 16, 224); MBG.player.body.reset(137 * 16, 224); MBG.run.solved.qgate = 1; });
  await h.down('ArrowRight'); await h.frames(20); await h.up('ArrowRight'); await h.frames(90); await h.shot('g_phantom_holo');
  await h.talk();
  // reactor area
  await h.ev(() => { MB.Save.data.run.area = 2; MB.Save.data.run.checkpoint = null; MBG.scene.restart(); }); await h.frames(20); await h.waitGame();
  await h.frames(150); await h.shot('g_reactor_start');
  await h.ev(() => { MBG.run.seen['t2_r_intro'] = 1; MBG.run.seen['t2_r2_intro'] = 1; MBG.player.setPosition(45 * 16, 256); MBG.player.body.reset(45 * 16, 256); });
  await h.frames(60); await h.shot('g_reactor_upper');
  await h.ev(() => { MB.Save.data.run.area = 3; MB.Save.data.run.checkpoint = null; MBG.scene.restart(); }); await h.frames(20); await h.waitGame();
  await h.ev(() => { ['t3_z_intro', 't3_g_intro', 't3_p_intro'].forEach(k => MBG.run.seen[k] = 1); MBG.player.setPosition(22 * 16, 250); MBG.player.body.reset(22 * 16, 250); });
  await h.frames(40); await h.shot('g_zerog_spikes');
}};
