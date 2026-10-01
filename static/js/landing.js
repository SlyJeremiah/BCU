(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // scroll reveal
  var els = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add("in"); });
  }

  if (reduce || !document.querySelector(".hero2")) return;

  // rotating hero word
  var rot = document.querySelector(".rotator");
  if (rot) {
    var words = rot.dataset.words.split("|"), i = 0;
    setInterval(function () {
      rot.classList.add("out");
      setTimeout(function () {
        i = (i + 1) % words.length;
        rot.innerHTML = "<b>" + words[i] + "</b>";
        rot.classList.remove("out");
      }, 350);
    }, 2600);
  }

  // mouse parallax on [data-depth]
  var hero = document.querySelector(".hero2");
  var layers = hero.querySelectorAll("[data-depth]");
  var tx = 0, ty = 0, cx = 0, cy = 0, raf;
  hero.addEventListener("mousemove", function (e) {
    var r = hero.getBoundingClientRect();
    tx = (e.clientX - r.left) / r.width - 0.5;
    ty = (e.clientY - r.top) / r.height - 0.5;
    if (!raf) raf = requestAnimationFrame(tick);
  });
  function tick() {
    cx += (tx - cx) * 0.08; cy += (ty - cy) * 0.08;
    layers.forEach(function (l) {
      var d = parseFloat(l.dataset.depth);
      l.style.setProperty("--px", (cx * d).toFixed(1) + "px");
      l.style.setProperty("--py", (cy * d).toFixed(1) + "px");
    });
    raf = (Math.abs(tx - cx) > 0.001 || Math.abs(ty - cy) > 0.001) ? requestAnimationFrame(tick) : null;
  }

  // scroll parallax for rings
  window.addEventListener("scroll", function () {
    var y = window.scrollY;
    if (y < window.innerHeight * 1.2) hero.style.setProperty("--sy", y * 0.25 + "px");
  }, { passive: true });

  // 3D tilt on cards
  document.querySelectorAll(".tilt").forEach(function (c) {
    c.addEventListener("mousemove", function (e) {
      var r = c.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      c.style.transform = "perspective(800px) rotateX(" + (-y * 8) + "deg) rotateY(" + (x * 10) + "deg) translateY(-6px)";
    });
    c.addEventListener("mouseleave", function () { c.style.transform = ""; });
  });
})();
