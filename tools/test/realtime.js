// Real-time smoke test (no frame stepping): title -> play -> skip intro -> move/jump, audio engine state, fps.
let chromium; try { chromium = require('playwright').chromium; } catch (e) { chromium = require('/opt/npm-tools/node_modules/playwright').chromium; }
const path = require('path');
(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errs = [];
  page.on('console', m => { const t = m.text(); if ((m.type() === 'error' || m.type() === 'warning') && !/GL Driver|GPU stall/.test(t)) errs.push(m.type() + ': ' + t); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await page.goto('file://' + path.resolve(__dirname, '../../index.html'));
  await page.waitForFunction(() => window.MB && MB.ready, null, { timeout: 20000 });
  await page.waitForTimeout(1500);
  await page.keyboard.press('Enter');                       // Play
  await page.waitForFunction(() => MB.game.scene.isActive('Intro'), null, { timeout: 10000 });
  await page.waitForTimeout(1500);
  await page.keyboard.press('Escape');                      // skip cinematic
  await page.waitForFunction(() => MB.game.scene.isActive('Game') && MB.game.scene.getScene('Game').started, null, { timeout: 15000 });
  await page.waitForTimeout(2500);
  const audio = await page.evaluate(() => MB.Audio.debugInfo());
  const x0 = await page.evaluate(() => MB.game.scene.getScene('Game').player.x);
  await page.keyboard.down('ArrowRight'); await page.waitForTimeout(2500);
  await page.keyboard.down('Space'); await page.waitForTimeout(300); await page.keyboard.up('Space');
  await page.waitForTimeout(1500); await page.keyboard.up('ArrowRight');
  const out = await page.evaluate(() => { const g = MB.game.scene.getScene('Game'); return { x: Math.round(g.player.x), fps: Math.round(MB.game.loop.actualFps), dialogue: g.hud.dialogue.active, canvas: [MB.game.canvas.width, MB.game.canvas.height], css: [MB.game.canvas.clientWidth, MB.game.canvas.clientHeight] }; });
  await page.screenshot({ path: path.resolve(__dirname, 'out/realtime.png') });
  console.log('audio:', JSON.stringify({ state: audio.state, track: audio.track }));
  console.log('moved from', Math.round(x0), 'to', out.x, '| headless software-rendered fps:', out.fps, '| dialogue open:', out.dialogue, '| canvas', out.canvas.join('x'), 'shown at', out.css.join('x'));
  console.log(errs.length ? 'CONSOLE ISSUES:\n' + errs.join('\n') : 'no console errors');
  await browser.close();
})();
