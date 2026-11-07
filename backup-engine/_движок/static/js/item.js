/* Страница товара: галерея, клавиши, свайп, просмотр на весь экран, «ещё из категории» */
(function () {
  'use strict';
  var RK = window.RK, D = RK.data, BASE = RK.base, esc = RK.esc;
  var page = document.querySelector('.item-page');
  if (!page) return;
  var slug = page.getAttribute('data-slug');
  var item = null, pos = 0;
  D.items.forEach(function (it, i) { if (it.slug === slug) { item = it; pos = i; } });

  // ---------- «Ещё из этой категории»
  if (item) {
    var same = D.items.filter(function (it) { return it.category === item.category && it.slug !== slug; });
    var after = same.filter(function (it) { return D.items.indexOf(it) > pos; });
    var before = same.filter(function (it) { return D.items.indexOf(it) < pos; });
    var rel = after.concat(before).slice(0, 4);
    if (rel.length) {
      document.getElementById('relatedGrid').innerHTML = rel.map(function (it, i) { return RK.cardHTML(it, i); }).join('');
      document.getElementById('related').hidden = false;
      RK.reveal(document.getElementById('relatedGrid'));
    }
  }
  if (!item || !item.media.length) return;

  var media = item.media, cur = 0;
  var stageMedia = document.getElementById('stageMedia');
  var stage = document.getElementById('stage');
  var thumbs = document.querySelectorAll('.thumb');
  var counter = document.getElementById('stageCount');

  function imgTag(m) {
    return '<img src="' + esc(BASE + m.large.src) + '" srcset="' + esc(BASE + m.card.src) + ' ' + m.card.w + 'w, ' +
      esc(BASE + m.large.src) + ' ' + m.large.w + 'w" sizes="(min-width:900px) 55vw, 100vw" alt="' + esc(item.title) +
      '" width="' + m.large.w + '" height="' + m.large.h + '">';
  }
  function videoTag(m) {
    return '<video controls playsinline preload="metadata" poster="' + esc(BASE + m.poster.large.src) +
      '" src="' + esc(BASE + m.src) + '"></video>';
  }
  function pauseVideos(root) {
    var v = (root || document).querySelectorAll('video');
    for (var i = 0; i < v.length; i++) v[i].pause();
  }

  var lb = null, lbView = null, lbCount = null, scale = 1, tx = 0, ty = 0, lastFocus = null;

  function go(i) {
    cur = (i + media.length) % media.length;
    var m = media[cur];
    pauseVideos(stageMedia);
    stageMedia.innerHTML = m.type === 'video' ? videoTag(m) : imgTag(m);
    for (var k = 0; k < thumbs.length; k++) {
      var on = k === cur;
      thumbs[k].classList.toggle('is-active', on);
      if (on) {
        thumbs[k].setAttribute('aria-current', 'true');
        // двигаем только ленту миниатюр, а не всю страницу
        var box = thumbs[k].parentNode;
        if (box.scrollHeight > box.clientHeight + 2)
          box.scrollTop = thumbs[k].offsetTop - box.offsetTop - (box.clientHeight - thumbs[k].offsetHeight) / 2;
        else if (box.scrollWidth > box.clientWidth + 2)
          box.scrollLeft = thumbs[k].offsetLeft - (box.clientWidth - thumbs[k].offsetWidth) / 2;
      } else thumbs[k].removeAttribute('aria-current');
    }
    if (counter) counter.textContent = (cur + 1) + ' / ' + media.length;
    [cur + 1, cur - 1].forEach(function (j) {
      var n = media[(j + media.length) % media.length];
      if (n.type === 'image') { var p = new Image(); p.src = BASE + n.large.src; }
    });
    if (lb) lbRender();
  }

  for (var t = 0; t < thumbs.length; t++) {
    thumbs[t].addEventListener('click', function () { go(+this.getAttribute('data-index')); });
  }
  var prev = document.getElementById('prevBtn'), next = document.getElementById('nextBtn');
  if (prev) prev.addEventListener('click', function () { go(cur - 1); });
  if (next) next.addEventListener('click', function () { go(cur + 1); });

  // клик по фото — полный экран (видео управляется своими кнопками)
  stageMedia.addEventListener('click', function (e) {
    if (media[cur].type === 'image' && e.target.tagName === 'IMG') openLb();
  });

  // свайп по большому фото
  var sx = null, sy = null;
  stage.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
  stage.addEventListener('touchend', function (e) {
    if (sx === null) return;
    var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
    sx = null;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) go(cur + (dx < 0 ? 1 : -1));
  }, { passive: true });

  // ---------- полноэкранный просмотр
  function openLb() {
    if (lb) return;
    lastFocus = document.activeElement;
    lb = document.createElement('div');
    lb.className = 'lb';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', item.title);
    lb.innerHTML = '<div class="lb-view" id="lbView"></div>' +
      '<button class="lb-btn lb-close" type="button" aria-label="Закрыть">✕</button>' +
      (media.length > 1 ? '<button class="lb-btn lb-prev" type="button" aria-label="Предыдущее">‹</button>' +
        '<button class="lb-btn lb-next" type="button" aria-label="Следующее">›</button>' +
        '<div class="lb-count" id="lbCount"></div>' : '');
    document.body.appendChild(lb);
    document.body.classList.add('lb-open');
    lbView = lb.querySelector('#lbView');
    lbCount = lb.querySelector('#lbCount');
    lb.querySelector('.lb-close').addEventListener('click', closeLb);
    var p = lb.querySelector('.lb-prev'), n = lb.querySelector('.lb-next');
    if (p) p.addEventListener('click', function () { go(cur - 1); });
    if (n) n.addEventListener('click', function () { go(cur + 1); });
    bindZoom();
    lbRender();
    lb.querySelector('.lb-close').focus();
  }
  function closeLb() {
    if (!lb) return;
    pauseVideos(lb);
    lb.remove(); lb = null;
    document.body.classList.remove('lb-open');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function applyT(img, animate) {
    img.style.transition = animate === false ? 'none' : '';
    img.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
  }
  function lbRender() {
    var m = media[cur];
    scale = 1; tx = 0; ty = 0;
    if (m.type === 'video') lbView.innerHTML = videoTag(m);
    else lbView.innerHTML = '<img src="' + esc(BASE + m.large.src) + '" alt="' + esc(item.title) + '" draggable="false">';
    if (lbCount) lbCount.textContent = (cur + 1) + ' / ' + media.length;
  }
  function bindZoom() {
    var drag = null, moved = false, tsx = null, tsy = null;
    function img() { return lbView.querySelector('img'); }
    // увеличение 2.6x к точке клика; повторный клик — обратно
    function toggleZoom(cx, cy) {
      var im = img(); if (!im) return;
      if (scale === 1) {
        var r = im.getBoundingClientRect(), s = 2.6;
        im.style.transformOrigin = '0 0';
        tx = (cx - (cx - r.left) * s) - r.left; ty = (cy - (cy - r.top) * s) - r.top;
        scale = s;
        im.classList.add('zoomed');
        im.style.width = r.width + 'px'; im.style.height = r.height + 'px';
      } else {
        scale = 1; tx = 0; ty = 0;
        im.classList.remove('zoomed');
        im.style.width = ''; im.style.height = '';
      }
      applyT(im);
    }
    lbView.addEventListener('click', function (e) {
      if (e.target === lbView) { closeLb(); return; }
      if (e.target.tagName !== 'IMG') return;
      if (moved) { moved = false; return; }
      toggleZoom(e.clientX, e.clientY);
    });
    lbView.addEventListener('pointerdown', function (e) {
      if (scale === 1 || e.target.tagName !== 'IMG') return;
      drag = { x: e.clientX - tx, y: e.clientY - ty }; moved = false;
      e.target.classList.add('dragging');
      try { e.target.setPointerCapture(e.pointerId); } catch (err) { /* не страшно */ }
    });
    lbView.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var nx = e.clientX - drag.x, ny = e.clientY - drag.y;
      if (Math.abs(nx - tx) + Math.abs(ny - ty) > 3) moved = true;
      tx = nx; ty = ny; applyT(e.target, false);
    });
    var end = function (e) { if (drag) { drag = null; if (e.target.classList) e.target.classList.remove('dragging'); } };
    lbView.addEventListener('pointerup', end);
    lbView.addEventListener('pointercancel', end);
    lbView.addEventListener('wheel', function (e) {
      if (media[cur].type !== 'image') return;
      e.preventDefault();
      if ((e.deltaY < 0 && scale === 1) || (e.deltaY > 0 && scale > 1)) toggleZoom(e.clientX, e.clientY);
    }, { passive: false });
    // свайп пальцем, когда фото не увеличено
    lbView.addEventListener('touchstart', function (e) {
      if (e.touches.length === 1 && scale === 1) { tsx = e.touches[0].clientX; tsy = e.touches[0].clientY; }
    }, { passive: true });
    lbView.addEventListener('touchend', function (e) {
      if (tsx === null) return;
      var dx = e.changedTouches[0].clientX - tsx, dy = e.changedTouches[0].clientY - tsy;
      tsx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) go(cur + (dx < 0 ? 1 : -1));
      else if (dy > 90 && Math.abs(dy) > Math.abs(dx) * 1.5) closeLb();
    }, { passive: true });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && lb) { closeLb(); return; }
    if (e.key === 'ArrowLeft') go(cur - 1);
    else if (e.key === 'ArrowRight') go(cur + 1);
    else if (e.key === 'Tab' && lb) {
      var f = lb.querySelectorAll('button');
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
})();
