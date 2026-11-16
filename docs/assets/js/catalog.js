/* Независимые фильтры и поиск; состояние в URL. */
(function () {
  'use strict';
  var RK = window.RK, D = RK.data;
  var grid = document.getElementById('grid'), empty = document.getElementById('empty');
  var input = document.getElementById('catalogSearch'), clear = document.getElementById('clearSearch');
  var links = document.querySelectorAll('.cats a'), state;
  function normalize(s) { return String(s || '').toLowerCase().replace(/ё/g, 'е').replace(/\s+/g, ' ').trim(); }
  function valid(value, list) {
    return list.some(function (c) { return c.slug === value; }) ? value : 'all';
  }
  function fromUrl() {
    var p = new URLSearchParams(location.search);
    return { cat: valid(p.get('cat'), D.categories), collection: valid(p.get('collection'), D.collections || []), q: p.get('q') || '' };
  }
  function url(next) {
    var u = new URL(location.href);
    ['cat', 'collection', 'q'].forEach(function (k) {
      if (next[k] && next[k] !== (k === 'q' ? '' : 'all')) u.searchParams.set(k, next[k]);
      else u.searchParams.delete(k);
    });
    return u;
  }
  function draw() {
    input.value = state.q;
    clear.hidden = !state.q;
    var names = [];
    D.categories.concat(D.collections || []).forEach(function (c) {
      if (c.slug === state.cat || c.slug === state.collection) names.push(c.name);
    });
    document.title = names.length ? names.join(' · ') + ' — РЕДКИСС' : 'РЕДКИСС — авторские фигурки из смолы';
    for (var i = 0; i < links.length; i++) {
      var key = links[i].hasAttribute('data-cat') ? 'cat' : 'collection';
      var attr = key === 'cat' ? 'data-cat' : 'data-collection';
      var value = links[i].getAttribute(attr), next = Object.assign({}, state);
      var on = value === state[key];
      links[i].classList.toggle('is-active', on);
      if (on) links[i].setAttribute('aria-current', 'page'); else links[i].removeAttribute('aria-current');
      next[key] = value;
      links[i].href = url(next).href;
    }
    var words = normalize(state.q).split(' ').filter(Boolean);
    var list = D.items.filter(function (it) {
      var text = normalize([it.title, it.description, it.categoryName, it.collectionName].join(' '));
      return (state.cat === 'all' || it.category === state.cat) &&
        (state.collection === 'all' || it.collection === state.collection) &&
        words.every(function (word) { return text.indexOf(word) !== -1; });
    });
    grid.innerHTML = list.map(function (it, i) { return RK.cardHTML(it, i); }).join('');
    // Carry the catalog state in each product link, including opening in a new tab.
    grid.querySelectorAll('.card').forEach(function (a) {
      var u = new URL(a.href, location.href);
      u.searchParams.set('catalog', url(state).search);
      a.href = u.href;
    });
    empty.hidden = list.length > 0;
    RK.reveal(grid);
  }
  function update(replace) {
    var target = url(state);
    if (target.href !== location.href) history[replace ? 'replaceState' : 'pushState'](null, '', target.href);
    draw();
  }
  links.forEach(function (a) {
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
      e.preventDefault();
      var key = a.hasAttribute('data-cat') ? 'cat' : 'collection';
      state[key] = a.getAttribute(key === 'cat' ? 'data-cat' : 'data-collection');
      update(false);
    });
  });
  input.addEventListener('input', function () { state.q = input.value; update(true); });
  clear.addEventListener('click', function () { state.q = ''; update(false); input.focus(); });
  document.getElementById('resetCatalog').addEventListener('click', function () {
    state = { cat: 'all', collection: 'all', q: '' }; update(false);
  });
  window.addEventListener('popstate', function () { state = fromUrl(); draw(); });
  state = fromUrl(); draw();
})();
