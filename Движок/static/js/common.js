/* Общие функции: шапка, карточки, плавное появление */
(function () {
  'use strict';
  var D = window.REDKISS_DATA || { items: [], categories: [], site: {} };
  var BASE = document.documentElement.getAttribute('data-base') || '';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function srcset(v) {
    return esc(BASE + v.card.src) + ' ' + v.card.w + 'w, ' + esc(BASE + v.large.src) + ' ' + v.large.w + 'w';
  }

  function cardHTML(it, i) {
    var c = it.cover, badges = '';
    if (it.isNew) badges += '<span class="badge badge-new">✦ Новинка</span>';
    if (it.status === 'Продано') badges += '<span class="badge badge-sold">Продано</span>';
    if (it.status === 'Под заказ') badges += '<span class="badge badge-order">Под заказ</span>';
    var sizes = '(min-width:1200px) 25vw, (min-width:720px) 33vw, 50vw';
    var alt = it.cover2
      ? '<img class="img-alt" src="' + esc(BASE + it.cover2.card.src) + '" srcset="' + srcset(it.cover2) +
        '" sizes="' + sizes + '" alt="" aria-hidden="true" loading="lazy" decoding="async">'
      : '';
    var meta = '';
    if (it.price) meta += esc(it.price);
    if (it.status === 'В наличии') meta += (meta ? '<small>В наличии</small>' : 'В наличии');
    return '<a class="card reveal' + (it.status === 'Продано' ? ' is-sold' : '') + '" href="' + BASE + 'item/' +
      esc(it.slug) + '/" data-i="' + i + '">' +
      '<div class="card-img">' +
      '<img class="img-main" src="' + esc(BASE + c.card.src) + '" srcset="' + srcset(c) + '" sizes="' + sizes +
      '" width="' + c.card.w + '" height="' + c.card.h + '" alt="' + esc(it.title) + '" loading="lazy" decoding="async">' +
      alt +
      (badges ? '<div class="badges">' + badges + '</div>' : '') +
      (it.hasVideo ? '<span class="video-mark" title="Есть видео" aria-label="Есть видео">▶</span>' : '') +
      '</div><div class="card-body"><div><h3 class="card-title">' + esc(it.title) + '</h3>' +
      '<p class="card-cat">' + esc(it.categoryName) + '</p></div>' +
      (meta ? '<div class="card-meta">' + meta + '</div>' : '') + '</div></a>';
  }

  var io = null;
  function reveal(root) {
    var els = (root || document).querySelectorAll('.card:not(.in)');
    if (!('IntersectionObserver' in window)) {
      for (var k = 0; k < els.length; k++) els[k].classList.add('in');
      return;
    }
    if (!io) {
      io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { rootMargin: '0px 0px -6% 0px', threshold: 0.05 });
    }
    for (var i = 0; i < els.length; i++) {
      els[i].style.transitionDelay = (i % 8) * 70 + 'ms';
      io.observe(els[i]);
    }
  }

  // шапка сжимается при прокрутке (с «гистерезисом», чтобы не дёргалась)
  var header = document.getElementById('siteHeader');
  if (header) {
    var compact = false;
    var onScroll = function () {
      var y = window.pageYOffset || document.documentElement.scrollTop;
      if (!compact && y > 70) { compact = true; header.classList.add('is-compact'); }
      else if (compact && y < 20) { compact = false; header.classList.remove('is-compact'); }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  window.RK = { data: D, base: BASE, esc: esc, cardHTML: cardHTML, reveal: reveal };
})();
