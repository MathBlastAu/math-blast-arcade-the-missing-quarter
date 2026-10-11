// Usage: node tools/test/shot.js "<query>" out.png [waitMs] [js-to-eval-before-shot]
let chromium; try { chromium = require('playwright').chromium; } catch (e) { chromium = require('/opt/npm-tools/node_modules/playwright').chromium; }
const path = require('path');
(async () => {
  const [query = '', out = 'shot.png', wait = '2500', js = ''] = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  const errs = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n')));
  await page.goto('file://' + path.resolve(__dirname, '../../index.html') + (query ? '?' + query : ''));
  await page.waitForTimeout(parseInt(wait, 10));
  if (js) { const r = await page.evaluate(js); if (r !== undefined) console.log('eval:', JSON.stringify(r)); await page.waitForTimeout(600); }
  await page.screenshot({ path: out });
  const info = await page.evaluate(() => ({ ready: !!(window.MB && MB.ready), renderer: window.MB && MB.game ? MB.game.config.renderType : null, scenes: window.MB && MB.game ? MB.game.scene.getScenes(true).map(s => s.scene.key) : [] }));
  console.log(JSON.stringify(info));
  console.log(errs.length ? errs.join('\n') : 'no console errors');
  await browser.close();
})();
