/* Objective measurements for tools/audio_test (runs in the browser).
 * Nothing here can tell whether the audio is pleasant - it only measures. */
(function () {
  'use strict';
  var T = window.MBT = {};

  function db(x) { return x > 0 ? 20 * Math.log(x) / Math.LN10 : -200; }
  T.db = db;

  // in-place radix-2 FFT
  function fft(re, im) {
    var n = re.length, i, j, k, len, half, ang, wr, wi, cr, ci, tr, ti, t;
    for (i = 1, j = 0; i < n; i++) {
      var bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (len = 2; len <= n; len <<= 1) {
      half = len >> 1; ang = -2 * Math.PI / len; wr = Math.cos(ang); wi = Math.sin(ang);
      for (i = 0; i < n; i += len) {
        cr = 1; ci = 0;
        for (k = 0; k < half; k++) {
          tr = re[i + k + half] * cr - im[i + k + half] * ci;
          ti = re[i + k + half] * ci + im[i + k + half] * cr;
          re[i + k + half] = re[i + k] - tr; im[i + k + half] = im[i + k] - ti;
          re[i + k] += tr; im[i + k] += ti;
          t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
        }
      }
    }
  }

  // long-term power spectrum (Hann, 4096, 50% overlap) -> band energy fractions
  function spectrum(x, sr) {
    var N = 4096, hop = 2048, pow = new Float64Array(N / 2), win = new Float64Array(N), i, f, frames = 0;
    var re = new Float64Array(N), im = new Float64Array(N);
    for (i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N);
    for (f = 0; f + N <= x.length; f += hop) {
      for (i = 0; i < N; i++) { re[i] = x[f + i] * win[i]; im[i] = 0; }
      fft(re, im);
      for (i = 0; i < N / 2; i++) pow[i] += re[i] * re[i] + im[i] * im[i];
      frames++;
    }
    var tot = 0, hf8 = 0, hf5 = 0, lf150 = 0, cen = 0, aw = 0, hz, f2, a;
    for (i = 1; i < N / 2; i++) {
      hz = i * sr / N; tot += pow[i]; cen += pow[i] * hz;
      if (hz >= 8000) hf8 += pow[i];
      if (hz >= 5000) hf5 += pow[i];
      if (hz < 150) lf150 += pow[i];
      // A-weighting (IEC 61672), as a rough stand-in for how loud the ear takes each band to be
      f2 = hz * hz;
      a = 1.2589 * 148693636 * f2 * f2 / ((f2 + 424.36) * Math.sqrt((f2 + 11599.29) * (f2 + 544496.41)) * (f2 + 148693636));
      aw += pow[i] * a * a;
    }
    if (!(tot > 0)) return { hf8: 0, hf5: 0, lf150: 0, centroid: 0, aFrac: 0, frames: frames };
    return { hf8: hf8 / tot, hf5: hf5 / tot, lf150: lf150 / tot, centroid: cen / tot, aFrac: aw / tot, frames: frames };
  }

  // RMS in consecutive windows of `ms`
  function envelope(x, sr, ms) {
    var w = Math.max(1, Math.round(sr * ms / 1000)), out = [], i, j, s;
    for (i = 0; i + w <= x.length; i += w) {
      s = 0;
      for (j = 0; j < w; j++) s += x[i + j] * x[i + j];
      out.push(Math.sqrt(s / w));
    }
    return out;
  }
  T.envelope = envelope;

  // peak / RMS / spectrum of an AudioBuffer between t0 and t1 seconds
  T.stats = function (buf, t0, t1) {
    var sr = buf.sampleRate, a = Math.floor((t0 || 0) * sr), b = Math.min(buf.length, Math.floor((t1 || buf.duration) * sr));
    var L = buf.getChannelData(0), R = buf.numberOfChannels > 1 ? buf.getChannelData(1) : L;
    var n = Math.max(0, b - a), mono = new Float32Array(n), i, peak = 0, sum = 0, dc = 0, last = 0, v, bad = 0;
    for (i = 0; i < n; i++) {
      var l = L[a + i], r = R[a + i];
      if (l !== l || r !== r) bad++;
      v = Math.max(Math.abs(l), Math.abs(r));
      if (v > peak) peak = v;
      sum += (l * l + r * r) / 2;
      mono[i] = (l + r) / 2; dc += mono[i];
    }
    var thr = Math.max(peak * 0.0316, 1e-4);       // "sounding" = within 30 dB of the peak
    for (i = n - 1; i >= 0; i--) if (Math.abs(mono[i]) > thr) { last = i; break; }
    var env = envelope(mono, sr, 100), silent = 0, sorted;
    for (i = 0; i < env.length; i++) if (env[i] < 0.001) silent++;
    sorted = env.slice(0).sort(function (p, q) { return p - q; });
    var rms = n ? Math.sqrt(sum / n) : 0, sp = spectrum(mono, sr);
    // RMS over the part that is actually sounding (for one-shot effects)
    var sumA = 0;
    for (i = 0; i <= last; i++) sumA += mono[i] * mono[i];
    return {
      seconds: n / sr, peak: peak, peakDb: db(peak), rms: rms, rmsDb: db(rms),
      crestDb: db(peak) - db(rms), dc: n ? dc / n : 0, nan: bad,
      activeSeconds: (last + 1) / sr, activeRms: Math.sqrt(sumA / (last + 1)), activeRmsDb: db(Math.sqrt(sumA / (last + 1))),
      silentWindows: silent, windows: env.length,
      envMin: sorted.length ? sorted[0] : 0, envP05: sorted.length ? sorted[Math.floor(sorted.length * 0.05)] : 0,
      envMedian: sorted.length ? sorted[Math.floor(sorted.length * 0.5)] : 0, envMax: sorted.length ? sorted[sorted.length - 1] : 0,
      hf8: sp.hf8, hf5: sp.hf5, lf150: sp.lf150, centroid: sp.centroid,
      aRms: rms * Math.sqrt(sp.aFrac), aRmsDb: db(rms * Math.sqrt(sp.aFrac)),
      activeARmsDb: db(Math.sqrt(sumA / (last + 1)) * Math.sqrt(sp.aFrac * n / (last + 1)))
    };
  };

  T.mono = function (buf) {
    var L = buf.getChannelData(0), R = buf.numberOfChannels > 1 ? buf.getChannelData(1) : L, m = new Float32Array(buf.length), i;
    for (i = 0; i < m.length; i++) m[i] = (L[i] + R[i]) / 2;
    return m;
  };

  // 16-bit stereo WAV as base64 (for --wav: lets a person listen to the renders)
  T.wav = function (buf) {
    var n = buf.length, sr = buf.sampleRate, L = buf.getChannelData(0), R = buf.numberOfChannels > 1 ? buf.getChannelData(1) : L;
    var bytes = new Uint8Array(44 + n * 4), dv = new DataView(bytes.buffer), i, s = '', v;
    function str(o, t) { for (var k = 0; k < t.length; k++) bytes[o + k] = t.charCodeAt(k); }
    str(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); str(8, 'WAVEfmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 2, true); dv.setUint32(24, sr, true); dv.setUint32(28, sr * 4, true);
    dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, n * 4, true);
    for (i = 0; i < n; i++) {
      v = Math.max(-1, Math.min(1, L[i])); dv.setInt16(44 + i * 4, v * 32767, true);
      v = Math.max(-1, Math.min(1, R[i])); dv.setInt16(46 + i * 4, v * 32767, true);
    }
    for (i = 0; i < bytes.length; i += 8192) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
    return btoa(s);
  };

  // ---- renders through the engine's own offline path ---------------------------
  var A = function () { return window.MB.Audio._test; };

  T.track = function (name, seconds, opts) {
    var o = { track: name, seconds: seconds, rec: true }, k;
    for (k in (opts || {})) o[k] = opts[k];
    return A().render(o).then(function (r) {
      var st = T.stats(r.buffer, 0.02);
      st.scheduled = r.scheduled; st.missed = r.missed; st.leftActive = r.active;
      if (opts && opts.wav) st.wav = T.wav(r.buffer);
      return st;
    });
  };
  // one effect, rendered for exactly as long as its voices live (+ 0.25 s)
  T.sfx = function (name, opts, o2) {
    var info = A().sfxInfo(name), o = { seconds: info.len + 0.25, sfx: [{ name: name, at: 0, opts: opts || null }] }, k;
    for (k in (o2 || {})) o[k] = o2[k];
    return A().render(o).then(function (r) {
      var st = T.stats(r.buffer, 0);
      st.level = info.level; st.len = info.len;
      st.tailPeak = T.stats(r.buffer, r.buffer.duration - 0.05).peak;
      if (o2 && o2.wav) st.wav = T.wav(r.buffer);
      // "ended" events of the last voices are delivered just after the render completes
      return new Promise(function (res) { setTimeout(function () { var c = r.counts(); st.leftActive = c.active; st.leftNodes = c.nodes; st.leftLive = c.sfxLive; res(st); }, 30); });
    });
  };

  // One continuous render of the whole piece: intro + one full pass of the loop
  // + 4 bars of the second pass. Returns the level statistics of all of it and
  // a look at the audio around the loop point: 50 ms RMS windows within 1 s of
  // the seam against the whole render (a gap would show as a hole, an overlap
  // as a bump), and the first 4 bars of pass 2 against the first 4 of pass 1.
  T.trackFull = function (name, opts) {
    opts = opts || {};
    var info = A().trackInfo(name), spb = 60 / info.bpm, lead = 0.02;
    var seamT = lead + (info.introBeats + info.loopBeats) * spb, secs = seamT + 16 * spb;
    return A().render({ track: name, seconds: secs, intensity: opts.intensity || 0, rec: true }).then(function (r) {
      var st = T.stats(r.buffer, lead), sr = r.buffer.sampleRate, m = T.mono(r.buffer), i;
      var env = envelope(m, sr, 50), w = Math.round(seamT / 0.05);
      var sorted = env.slice(4).sort(function (p, q) { return p - q; });
      var near = env.slice(w - 20, w + 20), nmin = Infinity, nmax = 0;
      for (i = 0; i < near.length; i++) { nmin = Math.min(nmin, near[i]); nmax = Math.max(nmax, near[i]); }
      var p1 = lead + info.introBeats * spb;
      var e1 = envelope(m.subarray(Math.round(p1 * sr), Math.round((p1 + 16 * spb) * sr)), sr, spb * 1000);
      var e2 = envelope(m.subarray(Math.round(seamT * sr), Math.round((seamT + 16 * spb) * sr)), sr, spb * 1000);
      var maxDiff = 0, n = Math.min(e1.length, e2.length, 16);
      for (i = 1; i < n; i++) maxDiff = Math.max(maxDiff, Math.abs(db(e2[i]) - db(e1[i])));
      var lastBar = envelope(m.subarray(Math.round((seamT - 4 * spb) * sr), Math.round(seamT * sr)), sr, spb * 1000);
      st.scheduled = r.scheduled; st.missed = r.missed;
      st.seam = {
        time: seamT, nearMin: nmin, nearMax: nmax, p05: sorted[Math.floor(sorted.length * 0.05)],
        median: sorted[Math.floor(sorted.length * 0.5)], max: sorted[sorted.length - 1],
        firstBeatDiffDb: db(e2[0]) - db(e1[0]), maxBeatDiffDb: maxDiff,
        lastBarBeats: lastBar.slice(0, 4), firstBarBeats: e2.slice(0, 4)
      };
      if (opts.wav) st.wav = T.wav(r.buffer);
      return st;
    });
  };

  // make-up gain of this browser's DynamicsCompressor at the engine's settings
  T.compGain = function (amp) {
    var c = A().defaults.comp, sr = 44100, o = new OfflineAudioContext(1, sr * 2, sr);
    var osc = o.createOscillator(), g = o.createGain(), comp = o.createDynamicsCompressor();
    osc.frequency.value = 440; g.gain.value = amp;
    comp.threshold.value = c.threshold; comp.knee.value = c.knee; comp.ratio.value = c.ratio;
    comp.attack.value = c.attack; comp.release.value = c.release;
    osc.connect(g); g.connect(comp); comp.connect(o.destination); osc.start(0);
    return o.startRendering().then(function (b) {
      var d = b.getChannelData(0), i, pk = 0;
      for (i = sr; i < d.length; i++) pk = Math.max(pk, Math.abs(d[i]));
      return pk / amp;
    });
  };
})();
