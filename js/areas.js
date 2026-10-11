/* Math Blast Arcade - the five areas of Space Arc, Level 1: The Missing Quarter.
 * Coordinates are tiles (16 px). See level.js for the builder and the
 * placement convention (things that stand on the floor use the tile ABOVE it). */
(function () {
  'use strict';
  var AB = MB.AreaBuilder;

  function deco(A, list) { list.forEach(function (d) { A.add('decor', d[1], d[2], { name: d[0], flip: !!d[3], front: !!d[4] }); }); }
  function lamps(A, xs, ty, color) { xs.forEach(function (x) { A.add('lamp', x, ty, { color: color }); }); }

  MB.AREAS = [

    // ====================================================================
    // AREA 1 - DOCKING BAY: movement, jumping, robots, "4 quarters = 1 whole"
    // ====================================================================
    {
      key: 'dock', name: 'DOCKING BAY', sub: 'AREA 1', skin: 'dock', music: 'dock',
      ambient: 'dust',
      bg: { far: 'dock_far', mid: 'dock_mid', planet: { x: 120, y: 18 }, nebula: true },
      build: function () {
        var A = new AB(152, 17, 'dock'), F = 14, S = F - 1;
        A.fill(0, 0, 151, 0);                       // ceiling
        A.fill(0, F, 151, 16);                      // deck
        A.fill(0, 0, 1, 16); A.fill(150, 0, 151, 16);
        A.spawn(8, S);
        A.add('shuttle', 4, S);
        A.add('npc', 15, S, { name: 'priya' });
        A.add('trigger', 11, S, { w: 2, h: 6, fn: 'intro', key: 'intro', ground: true });
        A.add('tip', 20, 10, { icons: ['key_left', 'key_right'], touchIcons: ['arrow_l', 'arrow_r'], text: 'Move' });
        A.chips(19, 12, 4);
        // first jump
        A.fill(26, 12, 31, 13);
        A.add('tip', 24, 9, { icons: ['key_space'], touchIcons: ['arrow_u'], text: 'Jump' });
        A.chips(27, 10, 4);
        A.clear(34, 14, 36, 15);                    // harmless dip
        A.chipArc(33, 12, 4, 4, 1.4);
        // the fuel tanks: every one is three quarters full
        A.add('decor', 39, S, { name: 'sign_fuel' });
        A.add('tank', 42, S, { level: 3 }); A.add('tank', 45, S, { level: 3 }); A.add('tank', 48, S, { level: 3 });
        A.add('trigger', 41, S, { w: 2, h: 6, key: 'tanks', toast: 'Each tank has 4 sections, but only 3 are full. Three quarters. One quarter is missing from every tank!', face: 'jake_worried' });
        A.add('trigger', 51, S, { w: 2, h: 6, key: 'gatehint', say: ['p05'], ground: true });
        // quarter cell 1
        A.plat(54, 12, 4);
        A.add('qkey', 55, 10);
        A.chips(54, 11, 1); A.chips(57, 11, 1);
        // first robot
        A.add('crawler', 62, S, { x0: 59, x1: 66 });
        A.add('tip', 62, 9, { icons: [], text: 'Jump on robots to switch them off' });
        A.chips(60, 12, 3, 2);
        // first real pit
        A.clear(69, 14, 71, 16);
        A.chipArc(68, 12, 5, 4, 1.6);
        // raised deck with quarter cell 2
        A.fill(74, 12, 77, 13); A.fill(78, 10, 87, 13);
        A.chips(74, 10, 3);
        A.add('crawler', 83, 9, { x0: 79, x1: 86 });
        A.add('qkey', 83, 6);
        A.chips(80, 8, 2); A.chips(85, 8, 2);
        A.add('checkpoint', 91, S);
        // drone pit with quarter cell 3
        A.clear(95, 14, 104, 16);
        A.plat(97, 12, 2); A.plat(101, 12, 2);
        A.add('drone', 97, 7, { x0: 96, x1: 103, speed: 22 });
        A.add('qkey', 101, 9);
        A.chips(97, 10, 2); A.chips(101, 10, 2);
        // spring to the high ledge with quarter cell 4 (and a secret)
        A.add('spring', 109, S);
        A.add('tip', 109, 10, { icons: [], text: 'Bounce!' });
        A.fill(111, 9, 116, 10);
        A.add('qkey', 114, 7);
        A.chips(112, 8, 2);
        A.plat(118, 7, 2);
        A.add('starcell', 119, 5);
        A.add('crawler', 123, S, { x0: 119, x1: 127 });
        A.add('heart', 121, 11);
        A.chips(120, 12, 4, 2);
        A.add('checkpoint', 129, S);
        // the quarter gate
        A.fill(132, 1, 133, 10);
        A.add('qgate', 132, S);
        // beyond the gate: the Phantom's first message, then the exit
        A.add('holo', 141, S, { name: 'h1' });
        A.add('trigger', 137, S, { w: 2, h: 6, fn: 'phantom1', key: 'phantom1', ground: true });
        A.chips(143, 12, 3);
        A.add('door', 147, S, { to: 1 });
        // dressing
        A.wallRect(130, 1, 149, 13); A.wallWindow(138, 3, 144, 8);
        deco(A, [['crate_stack', 11, S], ['toolbox', 13, S], ['cone', 32, S], ['cone', 37, S], ['barrel_cyan', 51, S], ['crate', 67, S],
          ['lamp_post', 73, S], ['fuel_hose', 89, S], ['barrel', 93, S], ['cone', 94, S], ['cone', 105, S], ['crate_stack', 107, S],
          ['sign_up', 110, S], ['robot_parts', 118, S], ['bench', 126, S], ['sign_right', 131, S], ['monitor_wall', 136, 9],
          ['plant_pot', 145, S], ['terminal_small', 144, S], ['cable_coil', 80, 9], ['crate', 86, 9]]);
        lamps(A, [9, 28, 46, 64, 82, 100, 118, 140], 1);
        return A;
      },
      on: {
        intro: function (scene) {
          var p = scene.npcs.priya;
          if (p) p.play('priya_talk');
          scene.say(['p01', 'p02', 'j02', 'p03', 'p04', 'j03'], function () { if (p) p.play('priya_idle'); });
        },
        phantom1: function (scene) {
          var h = scene.holos.h1;
          scene.player.freeze();
          h.show();
          scene.time.delayedCall(700, function () {
            scene.say(['f01', 'f02', 'j05', 'f03'], function () { h.hide(); });
          });
        }
      }
    },

    // ====================================================================
    // AREA 2 - FRACTION BRIDGE: add cells until the bridge is exactly 1 whole
    // ====================================================================
    {
      key: 'bridge', name: 'FRACTION BRIDGE', sub: 'AREA 2', skin: 'bridge', music: 'bridge', kindPits: true,
      ambient: 'stars',
      bg: { far: 'bridge_far', mid: 'bridge_mid', planet: { x: 236, y: 6 }, nebula: true },
      build: function () {
        var A = new AB(132, 17, 'bridge'), F = 13, S = F - 1;
        // four station modules separated by three 16-tile gaps
        A.fill(0, F, 14, 16); A.fill(31, F, 52, 16); A.fill(69, F, 92, 16); A.fill(109, F, 131, 16);
        A.fill(0, 3, 1, 16); A.fill(130, 3, 131, 16);
        A.spawn(5, S);
        A.add('door', 3, S, { entry: true });
        A.add('trigger', 7, S, { w: 2, h: 6, key: 'b_intro', say: ['p06', 'j06', 'p07'], ground: true });
        A.add('bridge', 10, S, {
          pid: 'b1', gapX: 15, gapW: 16, row: F, den: 4, start: { n: 3, d: 4 },
          cells: [{ n: 1, d: 4, c: 1 }, { n: 2, d: 4, c: 1 }, { n: 3, d: 4, c: 1 }],
          goal: 'The bridge reaches 3/4. Add ONE cell to make it exactly 1 whole.',
          hints: ['The bridge already reaches 3 quarters. How many quarters are there in 1 whole?',
            '4 quarters make 1 whole. You have 3 quarters. How many more do you need?',
            'Add the 1/4 cell. 3/4 + 1/4 = 4/4, and 4/4 is 1 whole.'],
          sayDone: ['j07']
        });
        A.chips(18, 11, 4, 3);
        // module 2
        A.add('checkpoint', 33, S);
        A.fill(38, 11, 41, 12);
        A.chips(38, 9, 4);
        A.plat(44, 9, 3);
        A.chips(44, 7, 3);
        A.plat(40, 7, 2);
        A.add('starcell', 40, 5);
        A.add('drone', 36, 7, { x0: 35, x1: 47, speed: 24 });
        A.add('crawler', 44, S, { x0: 42, x1: 46 });
        A.add('trigger', 46, S, { w: 2, h: 6, key: 'b2_intro', say: ['p08'], ground: true });
        A.add('bridge', 49, S, {
          pid: 'b2', gapX: 53, gapW: 16, row: F, den: 8, start: { n: 6, d: 8 },
          cells: [{ n: 1, d: 2, c: 1 }, { n: 1, d: 4, c: 1 }, { n: 3, d: 4, c: 1 }],
          goal: 'The bridge reaches 6/8. Which cell is worth the same as the gap?',
          hints: ['The gap is marked in eighths, but the cells are halves and quarters. How many eighths are missing?',
            'The bridge needs 2/8 more. On the bar, 2 eighths are exactly as long as 1 quarter.',
            'Add the 1/4 cell. 1/4 is equivalent to 2/8, so 6/8 + 2/8 = 8/8.'],
          sayDone: ['j08']
        });
        A.chips(56, 11, 4, 3);
        // module 3
        A.add('checkpoint', 71, S);
        A.clear(77, F, 82, 16);
        A.add('mplat', 78, F, { dx: 3, speed: 30 });
        A.chipArc(77, 10, 5, 5, 1.2);
        A.add('crawler', 86, S, { x0: 84, x1: 87 });
        A.add('heart', 85, 9);
        A.plat(84, 10, 3);
        A.add('trigger', 86, S, { w: 2, h: 6, key: 'b3_intro', say: ['p18'], ground: true });
        A.add('bridge', 89, S, {
          pid: 'b3', gapX: 93, gapW: 16, row: F, den: 8, start: { n: 1, d: 8 },
          cells: [{ n: 1, d: 2, c: 1 }, { n: 1, d: 4, c: 1 }, { n: 1, d: 8, c: 2 }],
          goal: 'The bridge only reaches 1/8. Use several cells to make exactly 1 whole.',
          hints: ['You need 7/8 more. Try the biggest cell first and see how much is left.',
            '1/2 is the same as 4/8, and 1/4 is the same as 2/8. What is still missing after those?',
            'Use the 1/2 cell, the 1/4 cell and one 1/8 cell: 1/8 + 4/8 + 2/8 + 1/8 = 8/8.'],
          sayDone: ['j14']
        });
        A.chips(96, 11, 4, 3);
        // module 4 and the way in to the reactor
        A.add('checkpoint', 111, S);
        A.chips(114, 11, 6, 2);
        A.fill(118, 11, 121, 12);
        A.add('crawler', 124, S, { x0: 122, x1: 125 });
        A.add('door', 127, S, { to: 2 });
        deco(A, [['sign_right', 8, S], ['crate', 13, S, false], ['lamp_post', 32, S], ['pipe_valve', 36, S], ['crate_stack', 51, S],
          ['lamp_post', 70, S], ['barrel_cyan', 75, S], ['cone', 76, S], ['cone', 83, S], ['toolbox', 91, S], ['lamp_post', 110, S],
          ['sign_right', 116, S], ['fan_vent', 129, 9], ['cable_coil', 119, 10], ['crate', 120, 10]]);
        A.wallRect(0, 4, 4, 12);
        return A;
      },
      on: {}
    },

    // ====================================================================
    // AREA 3 - REACTOR CORE: bump blocks to add and take away energy
    // ====================================================================
    {
      key: 'reactor', name: 'REACTOR CORE', sub: 'AREA 3', skin: 'reactor', music: 'reactor',
      ambient: 'embers',
      bg: { far: 'reactor_far', mid: 'reactor_mid', noSpace: true },
      build: function () {
        var A = new AB(100, 34, 'reactor'), LF = 31, UF = 16;
        A.fill(0, 0, 99, 0); A.fill(0, LF, 99, 33); A.fill(0, 0, 1, 33); A.fill(98, 0, 99, 33);
        A.fill(30, UF, 66, 30);                     // the upper deck sits on a big block of hull
        // ---- chamber A (lower left): reactor 1 powers the lift ----
        A.spawn(5, LF - 1);
        A.add('door', 3, LF - 1, { entry: true });
        A.add('trigger', 6, LF - 1, { w: 2, h: 6, key: 'r_intro', say: ['p09', 'p10'], ground: true });
        A.add('fblock', 9, 26, { tank: 'r1', n: 1, d: 4, sign: 1 });
        A.add('fblock', 13, 26, { tank: 'r1', n: 2, d: 4, sign: 1 });
        A.add('reactor', 19, LF - 1, { pid: 'r1', den: 4, start: { n: 0, d: 4 }, target: { n: 3, d: 4 }, sayDone: ['j09'], after: 'liftOn',
          hints: ['The target is 3/4. Each bump adds the fraction shown above the block.', '1/4 + 2/4 = 3/4. Bump each block once, then pull the lever.'] });
        A.add('lever', 24, LF - 1, { tank: 'r1' });
        A.add('tip', 11, 22, { icons: [], text: 'Bump the blocks from below' });
        A.add('mplat', 28, LF - 1, { dy: -14, speed: 46, power: 'r1', wait: 1300 });
        A.chips(28, 20, 4, 0, 2);
        // optional climb to a secret
        A.plat(20, 17, 4); A.plat(14, 15, 3); A.plat(9, 13, 3);
        A.chips(21, 15, 2); A.chips(14, 13, 3);
        A.add('starcell', 10, 11);
        // ---- upper deck: hazards, then reactor 2 (take away) opens the barrier ----
        A.add('checkpoint', 32, UF - 1);
        A.add('steam', 36, UF - 1, { phase: 0 }); A.add('steam', 39, UF - 1, { phase: 0.5 });
        A.chips(35, 12, 3, 2);
        A.add('trigger', 41, UF - 1, { w: 2, h: 6, key: 'r2_intro', say: ['f04'], ground: true });
        A.add('fblock', 43, 11, { tank: 'r2', n: 1, d: 8, sign: 1 });
        A.add('fblock', 47, 11, { tank: 'r2', n: 1, d: 8, sign: -1 });
        A.add('fblock', 51, 11, { tank: 'r2', n: 2, d: 8, sign: -1 });
        A.add('reactor', 56, UF - 1, { pid: 'r2', den: 8, start: { n: 7, d: 8 }, target: { n: 5, d: 8 }, sayDone: ['j10'],
          hints: ['The reactor has 7/8 but the target is 5/8. Is that too much or too little?', '7/8 take away 2/8 leaves 5/8. Bump the red 2/8 block once.'] });
        A.add('lever', 61, UF - 1, { tank: 'r2' });
        A.fill(63, 1, 65, 11);
        A.add('barrier', 64, 12, { h: 4, power: 'r2' });
        // ---- chamber C (lower right): reactor 3 (equivalent fractions) unlocks the exit ----
        A.plat(68, 20, 3); A.plat(73, 24, 3); A.plat(68, 27, 3);
        A.chips(68, 18, 3); A.chips(73, 22, 3);
        A.add('checkpoint', 70, LF - 1);
        A.add('zap', 74, 26, { h: 3, phase: 0.3 });
        A.fill(74, 25, 74, 25);
        A.add('fblock', 77, 26, { tank: 'r3', n: 1, d: 8, sign: 1 });
        A.add('fblock', 81, 26, { tank: 'r3', n: 3, d: 8, sign: 1 });
        A.add('reactor', 87, LF - 1, { pid: 'r3', den: 8, start: { n: 0, d: 8 }, target: { n: 3, d: 4 }, sayDone: ['j15'],
          hints: ['The target is 3/4 but the blocks count in eighths. Find the target line on the tube. How many eighths high is it?', '3/4 is the same as 6/8, and 3/8 + 3/8 = 6/8.'] });
        A.add('lever', 92, LF - 1, { tank: 'r3' });
        A.add('door', 95, LF - 1, { to: 3, lock: 'r3', lockMsg: 'The exit has no power. Get the reactor running at exactly 3/4.' });
        A.add('drone', 84, 21, { x0: 77, x1: 92, speed: 20 });
        A.add('heart', 90, 27);
        deco(A, [['pipe_valve', 7, LF - 1], ['barrel', 16, LF - 1], ['toolbox', 23, LF - 1], ['sign_up', 25, LF - 1], ['sign_warning', 34, UF - 1],
          ['pipe_valve', 53, UF - 1], ['sign_right', 62, UF - 1], ['barrel', 72, LF - 1], ['cable_coil', 84, LF - 1], ['sign_warning', 73, LF - 1],
          ['fan_vent', 4, 22], ['monitor_wall', 16, 24], ['monitor_wall', 61, 9], ['monitor_wall', 93, 23]]);
        lamps(A, [6, 16, 26, 38, 48, 58, 72, 82, 92], 1, 0xffc46b);
        lamps(A, [10, 22], 1, 0xffc46b);
        A.wallRect(2, 20, 6, 30); A.wallRect(93, 20, 97, 30);
        return A;
      },
      on: {
        liftOn: function (scene) { scene.toast('The lift is running! Ride it up to the next reactor.', 'priya_smile'); }
      }
    },

    // ====================================================================
    // AREA 4 - ZERO-GRAVITY SECTOR: compare fractions, order a number line
    // ====================================================================
    {
      key: 'zerog', name: 'ZERO-GRAVITY SECTOR', sub: 'AREA 4', skin: 'zerog', music: 'zerog', lowG: true,
      ambient: 'motes',
      bg: { far: 'zerog_far', mid: 'zerog_mid', planet: { x: 150, y: 40 }, nebula: true },
      build: function () {
        var A = new AB(150, 26, 'zerog'), F = 23, S = F - 1;
        A.fill(0, 0, 149, 1); A.fill(0, F, 149, 25); A.fill(0, 0, 1, 25); A.fill(148, 0, 149, 25);
        A.spawn(5, S);
        A.add('door', 3, S, { entry: true });
        A.add('trigger', 7, S, { w: 2, h: 6, key: 'z_intro', say: ['p11'], ground: true });
        A.add('tip', 9, 16, { icons: [], text: 'Low gravity: hold jump to float further' });
        // ---- floaty platforming over an energy field ----
        A.add('spikes', 16, S, { n: 20 });
        A.plat(13, 20, 3);
        A.fill(19, 17, 21, 18);
        A.plat(25, 19, 3);
        A.fill(30, 16, 32, 17);
        A.chipArc(14, 18, 4, 5, 1.5); A.chipArc(20, 15, 4, 5, 1.2); A.chipArc(26, 17, 4, 4, 1.6); A.chips(30, 14, 3);
        A.add('mine', 23, 13, { dy: 5, period: 4 });
        A.add('mine', 28, 12, { dx: 0, dy: 4, period: 3.4, phase: 0.5 });
        A.add('starcell', 31, 10);
        A.plat(30, 12, 3);
        // ---- gate 1: 3/4 (upper) or 1/4 (lower)? ----
        A.add('trigger', 36, S, { w: 2, h: 18, key: 'g_intro', say: ['p12'] });
        A.plat(38, 19, 3); A.plat(34, 15, 3);
        A.fill(40, 11, 42, 11);
        A.fill(43, 2, 45, 22); A.clear(43, 7, 45, 10); A.clear(43, 19, 45, 22);
        A.add('cmpgate', 44, 0, { pid: 'g1', a: { n: 3, d: 4, y0: 7, h: 4 }, b: { n: 1, d: 4, y0: 19, h: 4 },
          hints: ['Both fractions are quarters, so the pieces are the same size. Which one has more quarters?', '3 quarters is more than 1 quarter. Climb up to the 3/4 gate.'] });
        A.chips(46, 9, 3); A.chips(47, 13, 1); A.chips(48, 17, 1);
        A.add('checkpoint', 48, S);
        // ---- gravity pads: cross the ceiling ----
        A.add('tip', 51, 18, { icons: [], text: 'Gravity pad: walk on the ceiling!' });
        A.add('gpad', 52, S, { dir: 'up' });
        A.add('gpad', 49, 2, { dir: 'down' });
        A.add('spikes', 55, S, { n: 17 });
        A.add('spikes', 60, 2, { n: 2, flip: true });
        A.add('spikes', 67, 2, { n: 2, flip: true });
        A.chips(55, 3, 4); A.chips(62, 3, 4); A.chips(69, 3, 3);
        A.add('gpad', 74, 2, { dir: 'down' });
        // ---- gate 2: 3/8 (upper) or 1/2 (lower)? ----
        A.plat(76, 19, 2); A.plat(73, 15, 2);
        A.fill(78, 11, 80, 11);
        A.fill(81, 2, 83, 22); A.clear(81, 7, 83, 10); A.clear(81, 19, 83, 22);
        A.add('cmpgate', 82, 0, { pid: 'g2', a: { n: 3, d: 8, y0: 7, h: 4 }, b: { n: 1, d: 2, y0: 19, h: 4 }, sayDone: ['j11'],
          hints: ['The pieces are different sizes this time. Look at the bars: which one is filled further?', 'Change 1/2 into eighths: 1/2 is the same as 4/8. Now compare 4/8 with 3/8.'] });
        A.add('checkpoint', 85, S);
        // ---- the number-line pods ----
        A.add('trigger', 87, S, { w: 2, h: 8, key: 'p_intro', say: ['p13'], ground: true });
        A.plat(88, 20, 27);
        A.add('pods', 0, 0, { pid: 'pods', list: [
          { tx: 90, ty: 16, n: 1, d: 2 }, { tx: 96, ty: 16, n: 1, d: 8 }, { tx: 102, ty: 16, n: 3, d: 4 },
          { tx: 108, ty: 16, n: 1, d: 4 }, { tx: 114, ty: 16, n: 7, d: 8 }],
          hints: ['Compare the bars on the pods. The shortest bar is the smallest fraction, so start there.', 'In eighths the pods are 1/8, 2/8, 4/8, 6/8 and 7/8. So hop on 1/8, then 1/4, 1/2, 3/4 and 7/8.'] });
        A.fill(117, 2, 119, 22); A.clear(117, 19, 119, 22);
        A.add('barrier', 118, 19, { h: 4, power: 'pods', color: 0xffcf33 });
        A.chips(90, 21, 12, 2);
        // ---- gate 3: 3/4 (upper) or 5/8 (lower)? ----
        A.add('checkpoint', 121, S);
        A.plat(121, 19, 3); A.plat(124, 15, 2);
        A.fill(127, 11, 129, 11);
        A.fill(130, 2, 132, 22); A.clear(130, 7, 132, 10); A.clear(130, 19, 132, 22);
        A.add('cmpgate', 131, 0, { pid: 'g3', a: { n: 3, d: 4, y0: 7, h: 4 }, b: { n: 5, d: 8, y0: 19, h: 4 },
          hints: ['Look closely at the two bars. Which is filled further?', 'Change 3/4 into eighths: 3/4 is the same as 6/8. Now compare 6/8 with 5/8.'] });
        A.chips(133, 9, 3); A.chips(134, 13, 1); A.chips(135, 17, 1);
        A.add('holo', 140, S, { name: 'h4' });
        A.add('trigger', 136, S, { w: 2, h: 8, fn: 'phantom4', key: 'phantom4', ground: true });
        A.add('heart', 143, 20);
        A.add('door', 145, S, { to: 4 });
        deco(A, [['sign_right', 9, S], ['crate', 12, S], ['sign_up', 37, S], ['barrel_cyan', 47, S], ['sign_up', 51, S, false],
          ['crate_stack', 86, S], ['terminal_small', 89, S], ['sign_up', 120, S], ['plant_pot', 142, S], ['monitor_wall', 139, 17]]);
        lamps(A, [8, 24, 40, 58, 76, 94, 112, 128, 142], 2, 0xcfa8ff);
        return A;
      },
      on: {
        phantom4: function (scene) {
          var h = scene.holos.h4;
          scene.player.freeze();
          h.show();
          scene.time.delayedCall(700, function () { scene.say(['f05'], function () { h.hide(); }); });
        }
      }
    },

    // ====================================================================
    // AREA 5 - FRACTION PHANTOM SHOWDOWN
    // ====================================================================
    {
      key: 'boss', name: 'CONTROL CORE', sub: 'AREA 5', skin: 'boss', music: null, boss: true,
      ambient: 'data',
      bg: { far: 'boss_far', mid: 'boss_mid', planet: { x: 150, y: 14 }, nebula: true },
      build: function () {
        var A = new AB(30, 17, 'boss'), F = 14;
        A.fill(0, 0, 29, 0); A.fill(0, F, 29, 16); A.fill(0, 0, 0, 16); A.fill(29, 0, 29, 16);
        A.spawn(3, F - 1);
        A.add('boss', 15, F - 1, {});
        return A;
      },
      on: {}
    }
  ];
})();
