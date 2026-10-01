(function () {
  var root = document.documentElement;
  function set(lang) {
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang);
    try { localStorage.setItem('agrownex-lang', lang); } catch (e) {}
  }
  var q = new URLSearchParams(location.search).get('lang');
  var saved = null;
  try { saved = localStorage.getItem('agrownex-lang'); } catch (e) {}
  set(q === 'ta' || q === 'en' ? q : saved || ((navigator.language || '').indexOf('ta') === 0 ? 'ta' : 'en'));
  var btn = document.querySelector('[data-lang-toggle]');
  if (btn) btn.addEventListener('click', function () { set(root.getAttribute('data-lang') === 'ta' ? 'en' : 'ta'); });
})();
