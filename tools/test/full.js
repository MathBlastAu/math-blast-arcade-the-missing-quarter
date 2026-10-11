// FULL PLAYTHROUGH with real inputs (movement via the same flags the touch buttons set,
// consoles/levers/dialogue via real key presses). Run: node tools/test/run.js tools/test/full.js
// Optional env START=<area index> to begin at a later area.
const START = parseInt(process.env.START || '0', 10);
module.exports = { query: 'debug&scene=game&new&area=' + START, run: async h => {
  const T = h.tile;
  const st = async () => await h.state();
  const step = async (name, x, y, o, max) => {
    const ok = await h.go(x, y, o, max); const s = await st();
    h.log((ok ? 'ok   ' : 'FAIL ') + name, JSON.stringify({ x: s.x, y: s.y, tx: s.tx, ty: s.ty, hearts: s.hearts, q: s.q }));
    if (!ok) { await h.shot('fail_' + name.replace(/\W+/g, '_')); throw new Error('stuck at ' + name); }
  };
  const press = async k => { await h.down(k); await h.frames(3); await h.up(k); await h.frames(6); };
  const waitArea = async a => { const ok = await h.until(a => window.MBG && MBG.areaIndex === a && MBG.started && !MBG.hud.irisOn, 900, a); if (!ok) throw new Error('did not reach area ' + a); await h.frames(20); };
  const expect = (cond, msg) => { h.log((cond ? 'PASS ' : 'CHECK FAILED ') + msg); if (!cond) throw new Error(msg); };

  await h.waitGame();

  // ------------------------------------------------------------ AREA 1
  if (START <= 0) {
    const F = 13;
    await step('a1 priya (intro dialogue)', ...T(12, F));
    await step('a1 step block', ...T(29, 11));
    await step('a1 past dip', ...T(38, F));
    await step('a1 gate hint', ...T(52, F));
    await step('a1 platform + quarter cell 1', ...T(55, 11));
    await step('a1 floor', ...T(60, F));
    await step('a1 over pit', ...T(72, F));
    await step('a1 raised deck', ...T(80, 9));
    await step('a1 quarter cell 2', ...T(83, 9), { jumpNow: true });
    await h.go(...T(83, 9), { jumpNow: true });
    await step('a1 checkpoint', ...T(91, F));
    await step('a1 drone pit a', ...T(97, 11));
    await step('a1 drone pit b', ...T(101, 11));
    await h.go(...T(101, 11), { jumpNow: true });
    await step('a1 floor c', ...T(106, F));
    await step('a1 spring up to ledge', ...T(113, 8), { walkOff: true });
    await step('a1 quarter cell 4', ...T(114, 8), { jumpNow: true });
    await step('a1 secret platform', ...T(118, 6));
    await h.go(...T(119, 6), { jumpNow: true });
    await step('a1 down', ...T(128, F), { drop: 8 });
    let s = await st(); h.log('  quarter cells:', s.qkeys, 'secrets:', s.stars);
    expect(s.qkeys === 4, 'all four quarter cells collected');
    await h.shot('a1_gate_before');
    await step('a1 through the quarter gate', ...T(136, F), {}, 1500);
    await step('a1 phantom hologram', ...T(145, F), {}, 1500);
    await h.go(...T(147, F), {}, 200);
    await waitArea(1);
    h.log('PASS area 1 complete');
  }

  // console helper: keys = string of R (right), L (left), E (enter)
  const con = async keys => { for (const k of keys) { await press(k === 'R' ? 'ArrowRight' : k === 'L' ? 'ArrowLeft' : 'Enter'); } };
  const openConsole = async () => { await press('KeyE'); const ok = await h.until(() => MBG.hud.console.active, 120); if (!ok) throw new Error('console did not open'); await h.frames(40); };
  const waitConsoleClosed = async () => { const ok = await h.until(() => !MBG.hud.console.active && !MBG.inConsole, 600); if (!ok) throw new Error('console did not close'); await h.frames(80); await h.talk(); await h.frames(20); };
  const testResult = async () => { await h.until(() => !MBG.hud.console.busy || !MBG.hud.console.active, 400); await h.frames(50); };

  // ------------------------------------------------------------ AREA 2
  if (START <= 1) {
    const F = 12;
    await step('a2 intro dialogue', ...T(8, F));
    await step('a2 console 1', ...T(10, F));
    await openConsole();
    await h.shot('a2_console_open');
    // deliberate wrong answer first: 2/4 cell (cell index 1) -> overload
    await con('RE'); await h.shot('a2_console_wrong_preview');
    await con('RRRRE'); await testResult();
    await h.shot('a2_console_overload');
    let s = await st(); expect(!s.solved.includes('b1'), 'bridge 1: 3/4 + 2/4 is rejected (too long)');
    // undo, then the right cell: 1/4
    await con('LLE');           // Power -> Hint -> Undo, press
    await con('LLLE');          // -> cell 0, add
    await con('RRRRRE'); await testResult();
    await h.shot('a2_console_solved');
    await waitConsoleClosed();
    s = await st(); expect(s.solved.includes('b1'), 'bridge 1 solved with 3/4 + 1/4');
    await step('a2 cross bridge 1', ...T(33, F), {}, 1500);
    await h.shot('a2_after_bridge1');
    await step('a2 steps', ...T(40, 10));
    await step('a2 platform', ...T(45, 8));
    await step('a2 secret', ...T(40, 6), { reach: 80 });
    await step('a2 down to console 2', ...T(49, F), { drop: 8 });
    await openConsole();
    await con('E'); await con('RRRRRE'); await testResult();   // wrong: 1/2 cell -> 6/8 + 4/8 too long
    s = await st(); expect(!s.solved.includes('b2'), 'bridge 2: 6/8 + 1/2 is rejected');
    await con('LLE'); await con('LLE'); await con('RRRRE'); await testResult();   // undo, pick 1/4 (cell 1)
    await h.shot('a2_console2_solved');
    await waitConsoleClosed();
    s = await st(); expect(s.solved.includes('b2'), 'bridge 2 solved with the equivalent 1/4 cell');
    await step('a2 cross bridge 2', ...T(71, F), {}, 1500);
    await step('a2 to moving platform edge', ...T(76, F));
    // ride the hover platform across the pit
    const plat = () => h.ev(() => { const m = MBG.solids.getChildren().find(s => s.texture && s.texture.key === 'mplat'); return m ? { x: m.x, y: m.y, vx: m.body.velocity.x } : null; });
    await h.until(() => { const m = MBG.solids.getChildren().find(s => s.texture && s.texture.key === 'mplat'); return m.x < 1262 && m.body.velocity.x === 0; }, 1200);
    await step('a2 onto hover platform', 1250, 208, { walkOff: true });
    await h.until(() => { const m = MBG.solids.getChildren().find(s => s.texture && s.texture.key === 'mplat'); return m.x > 1298; }, 1200);
    await step('a2 off hover platform', 83 * 16 + 8, null, { walkOff: true });
    await step('a2 console 3', ...T(89, F));
    await openConsole();
    await con('E'); await con('RRRRRE'); await testResult();       // only the 1/2 cell: 5/8, too short
    await h.shot('a2_console3_short');
    s = await st(); expect(!s.solved.includes('b3'), 'bridge 3: 1/8 + 1/2 is rejected (too short)');
    await con('LLLLE'); await con('RE'); await con('RRRE'); await testResult();   // add 1/4 and one 1/8
    await waitConsoleClosed();
    s = await st(); expect(s.solved.includes('b3'), 'bridge 3 solved with 1/2 + 1/4 + 1/8');
    await step('a2 cross bridge 3', ...T(111, F), {}, 1500);
    await step('a2 step', ...T(120, 10));
    await h.go(...T(127, F), {}, 300);
    await waitArea(2);
    h.log('PASS area 2 complete');
  }

  const hop = async (n) => { await h.down('Space'); await h.frames(n || 24); await h.up('Space'); await h.until(() => MBG.player.onFloor, 200); await h.frames(8); };
  const bump = async (x, floorY, name) => { await step('under block ' + name, x, floorY, { walkOff: true }); await hop(26); await h.frames(30); };
  const lever = async (x, floorY) => { await step('lever', x, floorY); await press('KeyE'); await h.frames(140); await h.talk(); await h.frames(30); };
  const hazardOff = async (key, x) => { // wait for a timed hazard near x to switch off, so the bot crosses in its safe window
    await h.until(([key, x]) => { const z = MBG.updaters.find(u => u.active !== false && Math.abs(u.x - x) < 12 && (key === 'steam' ? u.texture && u.texture.key === 'steam' : u.active2 !== undefined)); if (!z) return true; const on = key === 'steam' ? z.live : z.active2; const was = window.__hz; window.__hz = on; return was === true && on === false; }, 600, [key, x]);
  };

  // ------------------------------------------------------------ AREA 3
  if (START <= 2) {
    const LF = 30, UF = 15, fy = 31 * 16, uy = 16 * 16;
    await step('a3 intro dialogue', ...T(7, LF));
    await bump(160, fy, '+1/4');
    await lever(24 * 16 + 8, fy);                                   // test too early: 1/4 < 3/4
    let s = await st(); expect(!s.solved.includes('r1'), 'reactor 1 stalls at 1/4 (less than 3/4)');
    await h.shot('a3_r1_stall');
    await bump(224, fy, '+2/4');
    await h.shot('a3_r1_filled');
    await lever(24 * 16 + 8, fy);
    s = await st(); expect(s.solved.includes('r1'), 'reactor 1 online at 1/4 + 2/4 = 3/4');
    // ride the lift
    await h.until(() => { const m = MBG.solids.getChildren().find(s => s.texture && s.texture.key === 'mplat'); return m.y > 484 && m.body.velocity.y === 0; }, 2400);
    await step('a3 onto lift', 456, 480, { reach: 40 });
    await h.until(() => MBG.player.y < 262, 1500);
    await h.shot('a3_lift_top');
    await step('a3 upper deck checkpoint', ...T(32, UF), { walkOff: true });
    await hazardOff('steam', 36 * 16 + 8); await step('a3 past steam 1', 37 * 16 + 12, uy, { walkOff: true });
    await hazardOff('steam', 39 * 16 + 8); await step('a3 past steam 2', ...T(42, UF), { walkOff: true });
    await lever(61 * 16 + 8, uy);                                   // 7/8 is too much: vents
    s = await st(); expect(!s.solved.includes('r2'), 'reactor 2 vents at 7/8 (more than 5/8)');
    await h.frames(90);
    await bump(832, uy, '-2/8');
    await h.shot('a3_r2_after_minus');
    await lever(61 * 16 + 8, uy);
    s = await st(); expect(s.solved.includes('r2'), 'reactor 2 online at 7/8 - 2/8 = 5/8');
    await step('a3 through barrier', ...T(69, 19), { walkOff: true, drop: 20 }, 1500);
    await step('a3 down the shaft', ...T(67, LF), { walkOff: true, drop: 20 }, 900);
    await step('a3 checkpoint', ...T(71, LF), { walkOff: true });
    await hazardOff('zap', 74 * 16 + 8); await step('a3 past zap', ...T(76, LF), { walkOff: true });
    await bump(81 * 16 + 16, fy, '+3/8'); await bump(81 * 16 + 16, fy, '+3/8 again');
    await h.shot('a3_r3_filled');
    await lever(92 * 16 + 8, fy);
    s = await st(); expect(s.solved.includes('r3'), 'reactor 3 online at 3/8 + 3/8 = 6/8 = 3/4');
    await h.go(...T(95, LF), {}, 300);
    await waitArea(3);
    h.log('PASS area 3 complete');
  }

  // ------------------------------------------------------------ AREA 4
  if (START <= 3) {
    const S = 22;
    await step('a4 intro', ...T(8, S));
    await step('a4 plat 1', ...T(14, 19));
    await step('a4 block 1', ...T(20, 16));
    await step('a4 plat 2', ...T(26, 18));
    await step('a4 block 2', ...T(31, 15));
    await step('a4 floor before gate', ...T(40, S), { drop: 12 });
    await h.go(...T(46, S), {}, 150);                               // walk into the smaller fraction (1/4)
    let s = await st(); expect(!s.solved.includes('g1') && s.tx < 44, 'gate 1: the 1/4 gate stays shut');
    await h.shot('a4_gate1_wrong');
    await step('a4 climb a', ...T(39, 18));
    await step('a4 climb b', ...T(35, 14));
    await step('a4 ledge', ...T(41, 10));
    await step('a4 through 3/4 gate', ...T(48, S), { walkOff: true, drop: 16 }, 900);
    s = await st(); expect(s.solved.includes('g1'), 'gate 1: the 3/4 gate opened');
    await step('a4 gravity pad up', 52 * 16 + 8, 32, { walkOff: true }, 600);
    s = await st(); expect(s.gdir === -1, 'gravity flipped: Jake is on the ceiling');
    await h.shot('a4_ceiling');
    await step('a4 ceiling run', 73 * 16, 32, {}, 1500);
    await h.go(74 * 16 + 8, 32, {}, 120);
    await h.until(() => MBG.player.gdir === 1 && MBG.player.onFloor, 600);
    s = await st(); expect(s.gdir === 1, 'gravity restored');
    await step('a4 floor to gate 2', ...T(79, S), { walkOff: true, drop: 12 });
    await step('a4 through 1/2 gate', ...T(85, S), {}, 900);
    s = await st(); expect(s.solved.includes('g2'), 'gate 2: the 1/2 gate opened (1/2 > 3/8)');
    await step('a4 catwalk', ...T(89, 19));
    const pod = async (tx, ty, name) => { await step('pod ' + name, tx * 16 + 8, ty * 16, { reach: 26, hold: 44 }, 700); await h.frames(20); h.log('   pods:', JSON.stringify(await h.ev(() => MBG.podGroups[0].debug()))); };
    const down = async (tx) => { await step('catwalk ' + tx, tx * 16 + 8, 320, { walkOff: true, drop: 6 }); };
    await pod(90, 16, '1/2 (wrong first)');
    await h.shot('a4_pod_wrong');
    await down(93); await down(94); await pod(96, 16, '1/8');
    await down(99); await down(106); await pod(108, 16, '1/4');
    await down(105); await down(92); await pod(90, 16, '1/2');
    await down(93); await down(100); await pod(102, 16, '3/4');
    await down(105); await down(112); await pod(114, 16, '7/8');
    await h.shot('a4_pods_done');
    s = await st(); expect(s.solved.includes('pods'), 'number-line pods solved in order 1/8, 1/4, 1/2, 3/4, 7/8');
    await down(111);
    await step('a4 off catwalk', 116 * 16, 23 * 16, { walkOff: true, drop: 6 });
    await step('a4 past barrier', ...T(121, S), { walkOff: true, drop: 6 });
    await step('a4 climb c', ...T(122, 18));
    await step('a4 climb d', ...T(124, 14));
    await step('a4 ledge 3', ...T(128, 10));
    await step('a4 through 3/4 gate (vs 5/8)', ...T(138, S), { walkOff: true, drop: 16 }, 1200);
    s = await st(); expect(s.solved.includes('g3'), 'gate 3: the 3/4 gate opened (3/4 > 5/8)');
    await h.go(...T(145, S), {}, 400);
    await waitArea(4);
    h.log('PASS area 4 complete');
  }

  // ------------------------------------------------------------ AREA 5: boss
  if (START <= 4) {
    const fy = 14 * 16;
    const bs = () => h.ev(() => ({ state: MBG.boss.state, hp: MBG.boss.hp, phase: MBG.boss.phase, v: MBG.boss.value, hearts: MBG.run.hearts, px: Math.round(MBG.player.x) }));
    const untilState = async (name, max) => { for (let i = 0; i < (max || 3000); i += 6) { await h.frames(6); if (await h.ev(() => MBG.hud.dialogue.active)) await h.talk(); if ((await bs()).state === name) return true; } return false; };
    const dodgeUntilThink = async () => { await h.ev(() => { window.BOT.mode = 'boss'; }); const ok = await untilState('think', 4000); await h.ev(() => { window.BOT.mode = null; window.BOT.stop(); }); if (!ok) throw new Error('boss never reached think: ' + JSON.stringify(await bs())); };
    const fire = async () => { await step('boss lever', 196, fy); await press('KeyE'); };
    const stomp = async () => {
      if (!(await h.until(() => MBG.boss.hit.body.enable, 400))) throw new Error('phantom not stompable');
      const hx = await h.ev(() => MBG.boss.sp.x);
      await step('line up stomp', hx - 44, fy, { walkOff: true });
      await h.down('ArrowRight'); await h.down('Space'); await h.frames(22); await h.up('Space');
      await h.frames(40); await h.up('ArrowLeft'); await h.up('ArrowRight');
    };
    for (let phase = 0; phase < 3; phase++) {
      await dodgeUntilThink();
      h.log('  think beat, phase', phase, JSON.stringify(await bs()));
      if (phase === 0) { await bump(80, fy, '+1/4'); await bump(144, fy, '+2/4'); }
      if (phase === 1) {
        await bump(144, fy, '+3/8'); await fire(); await h.frames(60);        // 3/8 is less than 1/2: shield holds
        let b = await bs(); expect(b.hp === 2, 'boss: a non-matching charge (3/8 vs 1/2) does not break the shield');
        await h.shot('boss_wrong');
        await dodgeUntilThink();
        await bump(144, fy, '+3/8'); await bump(80, fy, '+1/8');
      }
      if (phase === 2) { await bump(80, fy, '-1/8'); }
      await h.shot('boss_think_' + phase);
      await fire();
      await h.frames(50); await h.shot('boss_beam_' + phase);
      await stomp();
      const b = await bs();
      h.log('  after stomp', JSON.stringify(b));
      expect(b.hp === 2 - phase, 'boss phase ' + (phase + 1) + ' shield matched and Phantom stomped');
      await h.shot('boss_hit_' + phase);
    }
    // defeat: collect the Missing Quarter
    const okq = await h.until(() => MBG.sensors.getChildren().some(s => s.active && s.texture && s.texture.key === 'missingq' && s.body.enable), 900);
    expect(okq, 'the Missing Quarter dropped');
    await h.shot('boss_quarter');
    const qx = await h.ev(() => MBG.sensors.getChildren().find(s => s.active && s.texture && s.texture.key === 'missingq').x);
    await h.go(qx, fy, { walkOff: true }, 400);
    for (let i = 0; i < 400; i++) { await h.frames(6); await h.talk(); if (await h.ev(() => MB.game.scene.isActive('Victory'))) break; }
    expect(await h.ev(() => MB.game.scene.isActive('Victory')), 'victory scene reached');
    for (let i = 0; i < 80; i++) { await h.frames(10); await h.talk(); if (await h.ev(() => !!MB.game.scene.getScene('Victory').menu)) break; }
    await h.frames(160);
    await h.shot('victory_card');
    h.log('RESULT', JSON.stringify(await h.ev(() => MB.game.scene.getScene('Victory').result)));
    h.log('PASS full playthrough complete');
    return;
  }
  h.log('reached', await st());
}};
