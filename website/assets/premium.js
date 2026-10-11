(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var saveData = navigator.connection && navigator.connection.saveData;

  // Header turns solid once the page scrolls.
  var header = document.querySelector('.site-header');
  function onScroll() { if (header) header.classList.toggle('scrolled', window.scrollY > 40); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Solutions dropdown: click to open on touch / small screens.
  document.querySelectorAll('.has-menu > button').forEach(function (b) {
    b.addEventListener('click', function () {
      var li = b.parentElement;
      var open = li.classList.toggle('open');
      b.setAttribute('aria-expanded', String(open));
    });
  });
  document.addEventListener('click', function (e) {
    document.querySelectorAll('.has-menu.open').forEach(function (li) {
      if (!li.contains(e.target)) { li.classList.remove('open'); li.querySelector('button').setAttribute('aria-expanded', 'false'); }
    });
  });

  // Page films: background loops that load only when allowed.
  if (!reduce && !saveData) {
    document.querySelectorAll('video[data-loop]').forEach(function (v) {
      var m = v.getAttribute('data-loop-mobile');
      v.src = (m && window.matchMedia('(max-width: 760px)').matches) ? m : v.getAttribute('data-loop');
      var p = v.play();
      if (p && p.catch) p.catch(function () {});
    });
  }

  // Count-up numbers.
  var nums = document.querySelectorAll('[data-count]');
  function run(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var suffix = el.getAttribute('data-suffix') || '';
    if (reduce) { el.textContent = target.toLocaleString('en-IN') + suffix; return; }
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / 1400, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString('en-IN') + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } });
    }, { threshold: .4 });
    nums.forEach(function (n) { io.observe(n); });
  } else {
    nums.forEach(run);
  }
})();
