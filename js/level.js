/* Math Blast Arcade - AreaBuilder: a tiny level-construction kit.
 * Areas are written as code (see areas.js) using fill/plat/add calls in TILE
 * coordinates; build() turns the grid into an auto-tiled Phaser tilemap.
 *
 * Placement convention for add(type, tx, ty):
 *   e.bx, e.by = bottom-centre of tile (tx,ty)  -> things that stand on the floor
 *   e.cx, e.cy = centre of tile (tx,ty)         -> things that float
 */
(function () {
  'use strict';
  var T = 16;

  var AB = MB.AreaBuilder = function (w, h, skin) {
    this.w = w; this.h = h; this.skin = skin;
    this.solid = new Uint8Array(w * h);        // 0 empty, 1 solid hull, 2 one-way catwalk
    this.wall = new Int16Array(w * h);         // back-wall tile index or -1
    for (var i = 0; i < w * h; i++) this.wall[i] = -1;
    this.ents = [];
    this.nextId = 0;
    this.rnd = MB.rng(w * 7919 + h * 104729);
  };
  AB.prototype.inb = function (x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h; };
  AB.prototype.get = function (x, y) { return this.inb(x, y) ? this.solid[y * this.w + x] : 1; };
  AB.prototype.isHull = function (x, y) { return this.get(x, y) === 1; };
  AB.prototype.fill = function (x0, y0, x1, y1, v) {
    v = v == null ? 1 : v;
    for (var y = Math.min(y0, y1); y <= Math.max(y0, y1); y++)
      for (var x = Math.min(x0, x1); x <= Math.max(x0, x1); x++)
        if (this.inb(x, y)) this.solid[y * this.w + x] = v;
    return this;
  };
  AB.prototype.clear = function (x0, y0, x1, y1) { return this.fill(x0, y0, x1, y1, 0); };
  AB.prototype.plat = function (x, y, len) { return this.fill(x, y, x + len - 1, y, 2); };
  // back wall panels
  AB.prototype.wallRect = function (x0, y0, x1, y1, tile) {
    for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) {
      if (!this.inb(x, y)) continue;
      var t = tile;
      if (t == null) { var r = this.rnd(); t = r < 0.72 ? 48 : r < 0.86 ? 49 : r < 0.95 ? 50 : 71; }
      this.wall[y * this.w + x] = t;
    }
    return this;
  };
  AB.prototype.wallTile = function (x, y, t) { if (this.inb(x, y)) this.wall[y * this.w + x] = t; return this; };
  AB.prototype.wallWindow = function (x0, y0, x1, y1) {
    for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) {
      var l = x === x0, r = x === x1, t = y === y0, b = y === y1, v = -1;
      if (t && l) v = 58; else if (t && r) v = 60; else if (b && l) v = 63; else if (b && r) v = 65;
      else if (t) v = 59; else if (b) v = 64; else if (l) v = 61; else if (r) v = 62;
      this.wallTile(x, y, v);
    }
    return this;
  };
  AB.prototype.add = function (type, tx, ty, props) {
    var e = { type: type, id: this.nextId++, tx: tx, ty: ty,
      cx: tx * T + T / 2, cy: ty * T + T / 2, bx: tx * T + T / 2, by: (ty + 1) * T };
    if (props) for (var k in props) e[k] = props[k];
    this.ents.push(e);
    return e;
  };
  // a row of fuel quarters
  AB.prototype.chips = function (tx, ty, n, dx, dy) {
    for (var i = 0; i < n; i++) this.add('chip', tx + i * (dx == null ? 1 : dx), ty + i * (dy || 0));
    return this;
  };
  // an arc of fuel quarters (follows a jump)
  AB.prototype.chipArc = function (tx, ty, n, width, height) {
    for (var i = 0; i < n; i++) {
      var t = n === 1 ? 0.5 : i / (n - 1);
      var e = this.add('chip', tx, ty);
      e.cx = tx * T + T / 2 + t * width * T; e.cy = ty * T + T / 2 - Math.sin(t * Math.PI) * height * T;
    }
    return this;
  };
  AB.prototype.spawn = function (tx, ty) { this.spawnPt = { x: tx * T + T / 2, y: (ty + 1) * T }; return this; };

  // ------------------------------------------------------------------ build
  AB.prototype.build = function (scene) {
    var w = this.w, h = this.h, x, y, self = this;
    var key = 'tiles_' + this.skin;
    var map = scene.make.tilemap({ tileWidth: T, tileHeight: T, width: w, height: h });
    var ts = map.addTilesetImage(key, key, T, T, 0, 0);
    var wall = map.createBlankLayer('wall', ts, 0, 0);
    var layer = map.createBlankLayer('solid', ts, 0, 0);
    var hull = function (xx, yy) { return self.get(xx, yy) === 1 ? 1 : 0; };
    var rnd = MB.rng(1234 + w);
    for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
      var wv = this.wall[y * w + x];
      if (wv >= 0) wall.putTileAt(wv, x, y);
      var s = this.solid[y * w + x];
      if (s === 1) {
        var m = hull(x, y - 1) + hull(x + 1, y) * 2 + hull(x, y + 1) * 4 + hull(x - 1, y) * 8;
        var t = m;
        if (m === 15) {
          var deep = hull(x - 1, y - 1) && hull(x + 1, y - 1) && hull(x - 1, y + 1) && hull(x + 1, y + 1);
          if (deep) {
            // deep interior only once we are two tiles from any open space
            var far = hull(x, y - 2) && hull(x, y + 2) && hull(x - 2, y) && hull(x + 2, y);
            t = far ? (rnd() < 0.5 ? 16 : 17) : 15;
          }
          if (t === 15) { var r = rnd(); if (r < 0.06) t = 18; else if (r < 0.12) t = 19; }
        } else if (m === 14) {
          var nearGap = !hull(x + 1, y) || !hull(x - 1, y) || !hull(x + 2, y) || !hull(x - 2, y);
          if (nearGap) t = 21;
          else if (x % 9 === 4) t = 20;
          else { var r2 = rnd(); if (r2 < 0.12) t = 22; else if (r2 < 0.22) t = 23; }
        }
        layer.putTileAt(t, x, y);
      } else if (s === 2) {
        var L = this.get(x - 1, y) !== 0 && this.inb(x - 1, y), R = this.get(x + 1, y) !== 0 && this.inb(x + 1, y);
        layer.putTileAt(L && R ? 33 : L ? 34 : R ? 32 : 35, x, y);
      }
    }
    layer.setCollisionBetween(0, 23);
    layer.forEachTile(function (tile) {
      if (tile.index >= 32 && tile.index <= 35) { tile.setCollision(false, false, true, false, false); tile.oneWay = true; }
    });
    layer.calculateFacesWithin(0, 0, w, h);
    // one-way tiles: only the top face is interesting
    layer.forEachTile(function (tile) {
      if (tile.oneWay) { tile.faceTop = true; tile.faceBottom = false; tile.faceLeft = false; tile.faceRight = false; }
    });
    wall.setDepth(5); layer.setDepth(20);
    return { map: map, layer: layer, wall: wall, pxW: w * T, pxH: h * T };
  };
})();
