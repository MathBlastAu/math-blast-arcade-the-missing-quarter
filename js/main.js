/* Math Blast Arcade - start the game. */
(function () {
  'use strict';
  if (!window.Phaser) {
    var el = document.getElementById('fatal');
    if (el) { el.textContent = 'The game engine (lib/phaser.min.js) did not load.'; el.style.display = 'block'; el.hidden = false; }
    return;
  }
  var S = MB.Scenes;
  MB.game = new Phaser.Game({
    type: MB.QUERY.has('canvas') ? Phaser.CANVAS : Phaser.AUTO,
    parent: 'game',
    width: MB.CFG.W, height: MB.CFG.H,
    backgroundColor: '#05060c',
    pixelArt: true, antialias: false, roundPixels: true,
    banner: false,
    disableContextMenu: true,
    audio: { noAudio: true },                    // we use our own Web Audio synth (js/audio.js)
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    input: { activePointers: 4 },
    physics: { default: 'arcade', arcade: { gravity: { x: 0, y: 0 }, tileBias: 16, debug: MB.QUERY.has('physdebug') } },
    scene: [S.Boot, S.Title, S.Intro, S.Game, S.Hud, S.Victory]
  });
  // save whenever the page is hidden or closed
  var saveNow = function () { try { if (MB.Save && MB.Save.data.run) MB.Save.store(); } catch (e) { /* ignore */ } };
  document.addEventListener('visibilitychange', function () { if (document.hidden) saveNow(); });
  window.addEventListener('pagehide', saveNow);
  // keep keyboard focus on the game (important inside iframes / embedded previews)
  window.addEventListener('pointerdown', function () { try { window.focus(); } catch (e) { /* ignore */ } });
})();
