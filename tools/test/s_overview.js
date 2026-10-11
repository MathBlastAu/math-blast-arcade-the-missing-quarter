// Zoomed-out maps of every area for layout review.
module.exports = { query: 'debug&scene=game&new&area=0', run: async h => {
  for (let a = 0; a < 5; a++) {
    await h.ev(a => { MB.Save.data.run.area = a; MB.Save.data.run.checkpoint = null; MBG.scene.restart(); }, a);
    await h.wait(300); await h.waitGame(); await h.wait(600);
    const dim = await h.ev(() => ({ w: MBG.pxW, h: MBG.pxH }));
    const n = Math.ceil(dim.w / 960);
    for (let i = 0; i < n; i++) {
      await h.ev(([i, dim]) => { const c = MBG.cameras.main; c.stopFollow(); c.removeBounds(); c.setZoom(1); c.setScroll(i * 960, Math.max(0, dim.h - 540) / 2 - (dim.h < 540 ? (540 - dim.h) / 2 : 0)); MBG.hud.cameras.main.setVisible(false); MBG.bgLayers.forEach(L => L.imgs.forEach(im => im.setVisible(false))); if (MBG.planet) MBG.planet.setVisible(false); }, [i, dim]);
      await h.shot('map_a' + a + '_' + i);
    }
  }
}};
