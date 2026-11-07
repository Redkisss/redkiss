/* Заставка: отпечатки поцелуев на фоне */
(function () {
  'use strict';
  var layer = document.getElementById('kisses');
  var logo = document.getElementById('splashLogo');
  var btn = document.getElementById('goBtn');
  if (!layer) return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var COLOR = '#C4001F', uid = 0;
  var LIPS = 'M4 32 C14 24 26 11 38 10 C43.5 9.5 47 13 50 16 C53 13 56.5 9.5 62 10 C74 11 86 24 96 32 ' +
             'C86 50 68 55 50 55 C32 55 14 50 4 32 Z';
  var MOUTH = 'M5 32.5 C20 36.5 34 30 50 33.5 C66 30 80 36.5 95 32.5';

  function rnd(a, b) { return a + Math.random() * (b - a); }

  // «отпечаток»: контур губ, из которого вычитаются случайные прожилки и крупинки
  function kissSVG() {
    var id = 'km' + (++uid), g = '', i, j;
    for (i = 0; i < 26; i++) {
      var x = rnd(5, 95), y1 = rnd(6, 48), len = rnd(4, 20);
      g += '<line x1="' + x.toFixed(1) + '" y1="' + y1.toFixed(1) + '" x2="' + (x + rnd(-1.5, 1.5)).toFixed(1) +
           '" y2="' + (y1 + len).toFixed(1) + '" stroke-width="' + rnd(0.25, 0.9).toFixed(2) +
           '" opacity="' + rnd(0.5, 1).toFixed(2) + '"/>';
    }
    for (j = 0; j < 30; j++) {
      g += '<circle cx="' + rnd(4, 96).toFixed(1) + '" cy="' + rnd(8, 54).toFixed(1) + '" r="' +
           rnd(0.2, 0.8).toFixed(2) + '" fill="#000" stroke="none" opacity="' + rnd(0.4, 1).toFixed(2) + '"/>';
    }
    return '<svg viewBox="0 0 100 62" xmlns="http://www.w3.org/2000/svg"><defs>' +
      '<mask id="' + id + '" maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="62">' +
      '<rect width="100" height="62" fill="#fff"/><g stroke="#000" stroke-linecap="round">' + g +
      '<path d="' + MOUTH + '" fill="none" stroke-width="1.7"/></g></mask></defs>' +
      '<path d="' + LIPS + '" fill="' + COLOR + '" mask="url(#' + id + ')"/></svg>';
  }

  // зоны, куда поцелуи не должны попадать: логотип и кнопка
  function blocked() {
    var out = [];
    [logo, btn].forEach(function (el) {
      if (!el) return;
      var r = el.getBoundingClientRect(), pad = 28;
      out.push({ l: r.left - pad, t: r.top - pad, r: r.right + pad, b: r.bottom + pad });
    });
    return out;
  }
  function hits(box, list) {
    return list.some(function (o) { return !(box.r < o.l || box.l > o.r || box.b < o.t || box.t > o.b); });
  }
  function boxOf(x, y, size) {
    return { l: x - size * 0.55, r: x + size * 0.55, t: y - size * 0.4, b: y + size * 0.4 };
  }

  function make(x, y, size, rot, op) {
    var el = document.createElement('div');
    el.className = 'kiss';
    el.style.width = size + 'px';
    el.style.left = (x - size / 2) + 'px';
    el.style.top = (y - size * 0.31) + 'px';
    el.style.transform = 'rotate(' + rot + 'deg)';
    el.style.opacity = op;
    el.innerHTML = kissSVG();
    layer.appendChild(el);
    return el;
  }

  function fadeKiss(el, peak, life, delay, onDone, rot) {
    if (!el.animate) { setTimeout(function () { el.remove(); if (onDone) onDone(); }, life); return; }
    var a = el.animate([
      { opacity: 0, transform: 'rotate(' + rot + 'deg) scale(.82)' },
      { opacity: peak, transform: 'rotate(' + rot + 'deg) scale(1)', offset: 0.28 },
      { opacity: peak * 0.8, transform: 'rotate(' + rot + 'deg) scale(1.03)', offset: 0.6 },
      { opacity: 0, transform: 'rotate(' + rot + 'deg) scale(1.07)' }
    ], { duration: life, delay: delay || 0, easing: 'ease-in-out', fill: 'both' });
    a.onfinish = function () { el.remove(); if (onDone) onDone(); };
  }

  function spawnRandom(delay) {
    var W = layer.clientWidth, H = layer.clientHeight, list = blocked();
    for (var tries = 0; tries < 30; tries++) {
      var size = rnd(40, 140), x = rnd(size / 2, W - size / 2), y = rnd(size * 0.35, H - size * 0.35);
      if (hits(boxOf(x, y, size), list)) continue;
      var rot = Math.round(rnd(-25, 25)), peak = +rnd(0.15, 0.6).toFixed(2);
      var el = make(x, y, size, rot, 0);
      fadeKiss(el, peak, rnd(6500, 11000), delay, function () { spawnRandom(rnd(0, 600)); }, rot);
      return;
    }
    setTimeout(function () { spawnRandom(0); }, 500);
  }

  if (reduce) {
    // без анимации: несколько статичных отпечатков
    var W = layer.clientWidth, H = layer.clientHeight, list = blocked(), placed = 0, n = 0;
    while (placed < 8 && n++ < 200) {
      var size = rnd(40, 130), x = rnd(size / 2, W - size / 2), y = rnd(size * 0.35, H - size * 0.35);
      if (hits(boxOf(x, y, size), list)) continue;
      make(x, y, size, Math.round(rnd(-25, 25)), +rnd(0.15, 0.4).toFixed(2));
      placed++;
    }
    return;
  }

  var count = Math.round(rnd(6, 10));
  for (var i = 0; i < count; i++) spawnRandom(i * 450);

  // клик по пустому месту оставляет поцелуй, который через несколько секунд тает
  var clicks = 0;
  document.addEventListener('pointerdown', function (e) {
    if (e.target.closest && e.target.closest('a, button')) return;
    var r = logo.getBoundingClientRect();
    if (e.clientX > r.left && e.clientX < r.right && e.clientY > r.top && e.clientY < r.bottom) return;
    if (clicks > 40) return;
    clicks++;
    var size = rnd(60, 120), rot = Math.round(rnd(-25, 25));
    var el = make(e.clientX, e.clientY, size, rot, 0);
    fadeKiss(el, 0.6, 4200, 0, function () { clicks--; }, rot);
  });
})();
