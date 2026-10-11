/* Math Blast Arcade - local save (localStorage, with an in-memory fallback). */
(function () {
  'use strict';
  var KEY = 'mathblast-arcade-missing-quarter-v1';

  function fresh() {
    return {
      v: 1,
      settings: { music: 0.6, sfx: 0.8, voice: 1, subs: true, relaxed: false, shake: true, readAloud: false },
      run: null,          // current playthrough (see newRun)
      best: null,         // best finished result
      completed: false
    };
  }
  function newRun() {
    return {
      area: 0, checkpoint: null, hearts: MB.CFG.HEARTS,
      quarters: 0,              // total fuel quarters collected
      got: {},                  // { areaIndex: { entityId: 1 } } collected items
      stars: {},                // secret star cells found, by id
      solved: {},               // puzzles solved, by id
      seen: {},                 // one-off story beats already shown
      firstTry: 0, tests: 0, hints: 0, falls: 0, time: 0
    };
  }

  var mem = null;
  var Save = MB.Save = {
    data: fresh(),
    load: function () {
      var raw = null;
      try { raw = window.localStorage.getItem(KEY); } catch (e) { raw = mem; }
      if (raw) {
        try {
          var d = JSON.parse(raw), base = fresh(), k;
          if (d && d.v === 1) {
            for (k in base.settings) if (d.settings && d.settings[k] !== undefined) base.settings[k] = d.settings[k];
            base.run = d.run || null; base.best = d.best || null; base.completed = !!d.completed;
            Save.data = base;
          }
        } catch (e) { Save.data = fresh(); }
      }
      return Save.data;
    },
    store: function () {
      var raw = JSON.stringify(Save.data);
      try { window.localStorage.setItem(KEY, raw); } catch (e) { mem = raw; }
    },
    newRun: function () { Save.data.run = newRun(); Save.store(); return Save.data.run; },
    hasRun: function () { return !!Save.data.run; },
    clearRun: function () { Save.data.run = null; Save.store(); },
    set: function (k, v) { Save.data.settings[k] = v; Save.store(); },
    get: function (k) { return Save.data.settings[k]; },
    applyAudio: function () {
      if (!MB.Audio) return;
      var s = Save.data.settings;
      try { MB.Audio.setVolume('music', s.music); MB.Audio.setVolume('sfx', s.sfx); MB.Audio.setVolume('voice', s.voice); } catch (e) { /* ignore */ }
    }
  };
})();
