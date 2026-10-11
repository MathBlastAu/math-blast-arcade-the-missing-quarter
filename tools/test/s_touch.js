// Touch controls: real multi-touch events through the Chrome DevTools protocol, phone-sized viewport.
module.exports = { query: 'debug&scene=game&new&area=0', touch: true, viewport: { width: 844, height: 390 }, run: async h => {
  const expect = (c, m) => { h.log((c ? 'PASS ' : 'CHECK FAILED ') + m); if (!c) throw new Error(m); };
  const cdp = await h.page.context().newCDPSession(h.page);
  // canvas rect -> convert game coords (960x540) to page coords
  const rect = await h.ev(() => { const r = MB.game.canvas.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
  h.log('  canvas rect in 844x390 viewport:', JSON.stringify(rect));
  expect(Math.abs(rect.w / rect.h - 16 / 9) < 0.01 && rect.h <= 390.5 && rect.w <= 844.5, 'canvas keeps 16:9 and fits the phone viewport');
  const P = (gx, gy, id) => ({ x: rect.x + gx / 960 * rect.w, y: rect.y + gy / 540 * rect.h, id });
  const touch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts });
  await h.waitGame();
  await h.ev(() => { MBG.run.seen['t0_intro'] = 1; });
  // first touch anywhere marks the device as touch and shows the buttons
  await touch('touchStart', [P(480, 200, 9)]); await h.frames(3); await touch('touchEnd', []); await h.frames(10);
  expect(await h.ev(() => MB.isTouch && MBG.hud.touchBtns.every(b => b.visible)), 'touch buttons appear after the first touch');
  await h.shot('touch_buttons');
  const x0 = (await h.state()).x;
  await touch('touchStart', [P(196, 462, 1)]); await h.frames(40);              // hold RIGHT
  const s1 = await h.state();
  expect(s1.x > x0 + 40, 'holding the right button moves Jake (' + x0 + ' -> ' + s1.x + ')');
  await touch('touchStart', [P(196, 462, 1), P(882, 452, 2)]); await h.frames(12);   // add JUMP with a second finger
  const s2 = await h.state();
  expect(!s2.floor && s2.x > s1.x + 10, 'second finger on jump: Jake jumps while still running (simultaneous touches)');
  await h.shot('touch_jump');
  await touch('touchEnd', [P(196, 462, 1)]); await h.frames(40);                // release jump, keep right
  await touch('touchEnd', []); await h.frames(30);
  const s3 = await h.state(); await h.frames(30); const s4 = await h.state();
  expect(Math.abs(s4.x - s3.x) < 2, 'releasing all fingers stops Jake');
  // pause button by touch
  await touch('touchStart', [P(926, 32, 3)]); await h.frames(3); await touch('touchEnd', []); await h.frames(20);
  expect(await h.ev(() => MBG.hud.paused), 'pause button works by touch');
  await h.shot('touch_pause');
}};
