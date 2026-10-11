(function () {
  var root = document.documentElement;
  root.classList.remove('no-js');

  // Language: Tamil by default, remembered per visitor.
  var KEY = 'agrownex-lang';
  function setLang(lang) {
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang);
    document.querySelectorAll('[data-set-lang]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-set-lang') === lang));
    });
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  setLang(saved === 'en' || saved === 'ta' ? saved : 'ta');
  document.querySelectorAll('[data-set-lang]').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-set-lang')); });
  });

  // Mobile menu.
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { nav.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); });
    });
  }

  // Hero film: phone-shaped clip on narrow screens, none when motion is reduced or data saver is on.
  var video = document.querySelector('.hero-media video[data-src]');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var saveData = navigator.connection && navigator.connection.saveData;
  if (video && !reduce && !saveData) {
    var narrow = window.matchMedia('(max-width: 760px)').matches;
    video.src = video.getAttribute(narrow ? 'data-src-mobile' : 'data-src');
    if (narrow) video.poster = video.getAttribute('data-poster-mobile');
    var play = video.play();
    if (play && play.catch) play.catch(function () {});
  }

  // One gentle entrance per block.
  var items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add('in'); });
  }

  // Enquiry forms: nothing is stored here. The visitor's own email app or
  // WhatsApp opens with the message written out, and they choose to send it.
  var EMAIL = 'agrowai.tn@gmail.com';
  var WHATSAPP = '918667237404';
  document.querySelectorAll('form[data-enquiry]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      var lines = [form.getAttribute('data-enquiry'), ''];
      form.querySelectorAll('input, select, textarea').forEach(function (f) {
        if (!f.name || !f.value.trim()) return;
        var label = form.querySelector('label[for="' + f.id + '"] [lang="en"]');
        lines.push((label ? label.textContent : f.name) + ': ' + f.value.trim());
      });
      var text = lines.join('\n');
      var via = e.submitter && e.submitter.value;
      if (via === 'whatsapp') {
        window.open('https://wa.me/' + WHATSAPP + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
      } else {
        window.location.href = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent(form.getAttribute('data-enquiry')) +
          '&body=' + encodeURIComponent(text);
      }
    });
  });

  var y = document.getElementById('year');
  if (y) y.textContent = String(new Date().getFullYear());
})();
