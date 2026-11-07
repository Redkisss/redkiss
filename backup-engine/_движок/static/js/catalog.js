/* Каталог: фильтр по категориям без перезагрузки, адрес ?cat=... */
(function () {
  'use strict';
  var RK = window.RK, D = RK.data;
  var grid = document.getElementById('grid');
  var empty = document.getElementById('empty');
  var links = document.querySelectorAll('.cats a');
  var TITLE = 'РЕДКИСС — авторские фигурки из смолы';
  var current = null;

  function validCat(c) {
    if (!c || c === 'all') return 'all';
    for (var i = 0; i < D.categories.length; i++) if (D.categories[i].slug === c) return c;
    return 'all';
  }
  function fromUrl() {
    var m = /[?&]cat=([^&#]*)/.exec(location.search);
    return validCat(m ? decodeURIComponent(m[1]) : 'all');
  }
  function setActive(cat) {
    for (var i = 0; i < links.length; i++) {
      var on = links[i].getAttribute('data-cat') === cat;
      links[i].classList.toggle('is-active', on);
      if (on) links[i].setAttribute('aria-current', 'page'); else links[i].removeAttribute('aria-current');
    }
    var name = '';
    D.categories.forEach(function (c) { if (c.slug === cat) name = c.name; });
    document.title = name ? name + ' — РЕДКИСС' : TITLE;
  }
  function fill(cat) {
    var list = D.items.filter(function (it) { return cat === 'all' || it.category === cat; });
    grid.innerHTML = list.map(function (it, i) { return RK.cardHTML(it, i); }).join('');
    empty.hidden = list.length > 0;
    RK.reveal(grid);
  }
  function show(cat, animate) {
    cat = validCat(cat);
    if (cat === current) return;
    current = cat;
    setActive(cat);
    if (!animate) { fill(cat); return; }
    grid.classList.add('is-switching');
    setTimeout(function () { fill(cat); grid.classList.remove('is-switching'); }, 230);
  }

  for (var i = 0; i < links.length; i++) {
    links[i].addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
      e.preventDefault();
      var cat = this.getAttribute('data-cat');
      history.pushState({ cat: cat }, '', cat === 'all' ? location.pathname : '?cat=' + cat);
      show(cat, true);
    });
  }
  window.addEventListener('popstate', function () { show(fromUrl(), true); });
  show(fromUrl(), false);
})();
