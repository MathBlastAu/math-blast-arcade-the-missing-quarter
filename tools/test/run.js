// Scenario runner: node tools/test/run.js <scenario.js> [outDir]
// scenario exports: { query, run: async (h) => {} }  with helpers h.
let chromium; try { chromium = require('playwright').chromium; } catch (e) { chromium = require('/opt/npm-tools/node_modules/playwright').chromium; }
const path = require('path');
const fs = require('fs');
(async () => {
  const scen = require(path.resolve(process.argv[2]));
  const outDir = process.argv[3] || path.resolve(__dirname, 'out');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ viewport: scen.viewport || { width: 960, height: 540 }, hasTouch: !!scen.touch });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { const t = m.text(); if ((m.type() === 'error' || m.type() === 'warning') && !/GL Driver|GPU stall/.test(t)) errs.push(m.type() + ': ' + t); });
  page.on('pageerror', e => errs.push('PAGEERROR: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 5).join('\n')));
  await page.goto('file://' + path.resolve(__dirname, '../../index.html') + '?' + (scen.query || 'debug'));
  await page.waitForFunction(() => window.MB && MB.ready, null, { timeout: 20000 });
  // Deterministic stepping: stop the real-time loop and advance the game frame by frame.
  // (Headless software rendering is far below 60 fps, and the game clamps long frames.)
  // Tweens use Date.now() internally, so the simulated clock replaces it too.
  await page.evaluate(() => { MB.game.loop.stop(); MB.T = Date.now(); Date.now = () => Math.floor(MB.T); });
  await page.addScriptTag({ path: path.resolve(__dirname, 'bot.js') });
  const frames = (n, render) => page.evaluate(([n, render]) => {
    for (let i = 0; i < n; i++) { MB.T += 1000 / 60; if (window.BOT) window.BOT.frame(); if (render && i === n - 1) MB.game.step(MB.T, 1000 / 60); else MB.game.headlessStep(MB.T, 1000 / 60); }
  }, [n, !!render]);
  const h = {
    page, errs, frames,
    wait: ms => frames(Math.max(1, Math.round(ms / (1000 / 60)))),
    ev: (fn, arg) => page.evaluate(fn, arg),
    // cameras only follow during rendered frames, so snap the camera for the one rendered frame
    shot: async name => { await page.evaluate(() => { const g = window.MBG; if (g && g.cameras && g.cameras.main && !g.camFocus) { g.__l = [g.cameras.main.lerp.x, g.cameras.main.lerp.y]; g.cameras.main.setLerp(1, 1); } }); await frames(1, true); await page.evaluate(() => { const g = window.MBG; if (g && g.__l) { g.cameras.main.setLerp(g.__l[0], g.__l[1]); g.__l = null; } }); await page.screenshot({ path: path.join(outDir, name + '.png') }); },
    key: async (k, ms) => { await page.keyboard.down(k); await frames(Math.max(2, Math.round((ms || 60) / 16.7))); await page.keyboard.up(k); await frames(1); },
    down: k => page.keyboard.down(k), up: k => page.keyboard.up(k),
    tap: async k => { await page.keyboard.down(k); await frames(3); await page.keyboard.up(k); await frames(4); },
    waitGame: async () => { for (let i = 0; i < 600; i++) { await frames(5); if (await page.evaluate(() => !!(window.MBG && MBG.started && !MBG.hud.irisOn && MBG.scene.isActive()))) return; } throw new Error('game did not start'); },
    until: async (fn, maxFrames, arg) => { for (let i = 0; i < (maxFrames || 600); i += 3) { await frames(3); if (await page.evaluate(fn, arg)) return true; } return false; },
    // press E until dialogue is finished
    talk: async (max) => {
      for (let i = 0; i < (max || 60); i++) {
        const a = await page.evaluate(() => { const s = MB.game.scene.getScenes(true).find(x => x.dialogue && x.dialogue.active); return !!s; });
        if (!a) return i;
        await page.keyboard.down('KeyE'); await frames(3); await page.keyboard.up('KeyE'); await frames(14);
      }
      return -1;
    },
    state: () => page.evaluate(() => { const g = window.MBG; if (!g || !g.player) return null; const p = g.player; return { x: Math.round(p.x), y: Math.round(p.y), tx: Math.floor(p.x / 16), ty: Math.floor((p.y - 1) / 16), floor: p.onFloor, hearts: g.run.hearts, q: g.run.quarters, area: g.areaIndex, locked: p.locked, dlg: g.hud.dialogue.active, solved: Object.keys(g.run.solved), gdir: p.gdir, qkeys: g.qkeys, stars: Object.keys(g.run.stars).length, first: g.run.firstTry || 0, con: g.hud.console.active }; }),
    // walk/jump to a world position (pixels). Returns true if reached.
    go: async (x, y, opts, maxFrames) => {
      await page.evaluate(([x, y, o]) => window.BOT.go(x, y, o), [x, y == null ? null : y, opts || {}]);
      for (let i = 0; i < (maxFrames || 900); i += 4) {
        await frames(4);
        const st = await page.evaluate(() => ({ done: window.BOT.done, dlg: MBG.hud.dialogue.active, dead: MBG.dying || MBG.falling }));
        if (st.dlg) { await page.evaluate(() => window.BOT.stop()); await h.talk(); await page.evaluate(([x, y, o]) => window.BOT.go(x, y, o), [x, y == null ? null : y, opts || {}]); }
        if (st.done) return true;
      }
      await page.evaluate(() => window.BOT.stop());
      return false;
    },
    tile: (tx, ty) => [tx * 16 + 8, (ty + 1) * 16],
    log: (...a) => console.log(...a)
  };
  let ok = true;
  try { await scen.run(h); } catch (e) { ok = false; console.log('SCENARIO ERROR:', e.message); try { await h.shot('error'); } catch (e2) {} }
  console.log(errs.length ? 'CONSOLE ISSUES:\n' + [...new Set(errs)].slice(0, 12).join('\n') : 'no console errors');
  await browser.close();
  process.exit(ok && !errs.some(e => /PAGEERROR|error:/.test(e)) ? 0 : 1);
})();
