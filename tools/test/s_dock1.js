module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  await h.waitGame();
  await h.down('ArrowRight'); await h.wait(700); await h.up('ArrowRight');
  await h.wait(400); h.log('after walk', await h.state());
  await h.shot('dock_dialogue');
  h.log('talk presses', await h.talk());
  h.log(await h.state());
  await h.down('ArrowRight'); await h.wait(1400); await h.shot('dock_tip'); 
  await h.down('Space'); await h.wait(350); await h.up('Space'); await h.wait(500);
  await h.down('Space'); await h.wait(350); await h.up('Space'); await h.wait(900);
  await h.up('ArrowRight');
  h.log(await h.state()); await h.shot('dock_jump');
}};
