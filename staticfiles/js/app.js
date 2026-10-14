(function () {
  "use strict";
  var F = window.Fluid, Spring = F.Spring, clamp = F.clamp;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

  /* ------------------------------------------------------------------ *
   * Header: a translucent material; the edge fades in once content
   * scrolls underneath (scroll-edge effect instead of a hard divider).
   * ------------------------------------------------------------------ */
  var header = $("#site-header");
  function onScroll() { header.classList.toggle("is-scrolled", window.scrollY > 6); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ------------------------------------------------------------------ *
   * Menu: bottom sheet on phones, anchored popover on larger screens.
   * One spring (progress p: 0 closed, 1 open). It follows the finger 1:1,
   * hands release velocity to the spring, projects momentum to decide
   * where to settle, rubber-bands upward, and can be grabbed mid-flight.
   * Enters and leaves along the same path, from/to its trigger.
   * ------------------------------------------------------------------ */
  var menu = $("#menu"), burger = $("#burger"), scrim = $("#scrim"), page = $("#page");
  if (menu && burger && scrim) {
    var sheetQuery = window.matchMedia("(max-width: 700px)");
    var isOpen = false, H = 1;
    menu.inert = true;

    var p = new Spring(0, render, { eps: 0.0015 });
    function sheet() { return sheetQuery.matches; }

    function render(v) {
      var c = clamp(v, 0, 1);
      if (F.reducedMotion()) {                      // gentler equivalent: cross-fade only
        menu.style.transform = "none";
        menu.style.opacity = c;
      } else if (sheet()) {
        menu.style.transform = "translate3d(0," + ((1 - v) * H).toFixed(1) + "px,0)";
        menu.style.opacity = "";
      } else {                                      // popover grows out of the trigger
        menu.style.transform = "translate3d(0," + (-8 * (1 - c)).toFixed(2) + "px,0) scale(" + (0.92 + 0.08 * c).toFixed(4) + ")";
        menu.style.opacity = c;
      }
      scrim.style.opacity = sheet() || F.reducedMotion() ? c : 0;
      document.documentElement.style.setProperty("--push", sheet() ? c.toFixed(3) : 0);
      menu.classList.toggle("is-visible", v > 0.001);
      scrim.classList.toggle("is-visible", v > 0.001);
    }

    function measure() { H = menu.offsetHeight || 1; }

    function openMenu(opts) {
      if (isOpen && !(opts && opts.velocity)) return;
      isOpen = true; measure();
      burger.setAttribute("aria-expanded", "true");
      burger.setAttribute("aria-label", "Close menu");
      menu.inert = false;
      if (sheet() && page) page.inert = true;
      p.to(1, { damping: opts && opts.velocity ? 0.8 : 1, response: opts && opts.velocity ? 0.3 : 0.36, velocity: opts && opts.velocity });
      var first = $("a, button", menu);
      if (first && !(opts && opts.fromDrag)) setTimeout(function () { first.focus({ preventScroll: true }); }, 60);
    }

    function closeMenu(opts) {
      isOpen = false; measure();
      burger.setAttribute("aria-expanded", "false");
      burger.setAttribute("aria-label", "Open menu");
      if (page) page.inert = false;
      p.to(0, {
        damping: opts && opts.velocity ? 0.8 : 1, response: opts && opts.velocity ? 0.3 : 0.32,
        velocity: opts && opts.velocity,
        onDone: function () { if (!isOpen) menu.inert = true; },
      });
      if (!(opts && opts.noFocus)) burger.focus({ preventScroll: true });
    }

    burger.addEventListener("click", function (e) { e.stopPropagation(); isOpen ? closeMenu() : openMenu(); });
    scrim.addEventListener("click", function () { closeMenu(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && isOpen) closeMenu(); });
    document.addEventListener("click", function (e) {      // outside tap closes the popover
      if (isOpen && !sheet() && !menu.contains(e.target) && !burger.contains(e.target)) closeMenu({ noFocus: true });
    });
    menu.addEventListener("click", function (e) { if (e.target.closest("a")) closeMenu({ noFocus: true }); });
    sheetQuery.addEventListener("change", function () { if (page) page.inert = false; p.set(isOpen ? 1 : 0); });

    // Drag the sheet (from the grabber, or anywhere if the content doesn't scroll).
    var dragging = false, startY = 0, startP = 0, pid = 0, vt = new F.VelocityTracker();
    menu.addEventListener("pointerdown", function (e) {
      if (!sheet() || (e.pointerType === "mouse" && e.button !== 0)) return;
      var scrolls = menu.scrollHeight > menu.clientHeight + 1;
      if (scrolls && !e.target.closest(".grabber")) return;
      measure();
      p.stop();                                     // grab it, even mid-flight: start from where it IS
      dragging = true; pid = e.pointerId; startY = e.clientY; startP = p.x;
      vt.reset(); vt.push(e.clientY);
      menu.setPointerCapture(pid);
      menu.classList.add("is-dragging");
    });
    menu.addEventListener("pointermove", function (e) {
      if (!dragging || e.pointerId !== pid) return;
      var dy = e.clientY - startY;                  // 1:1 with the finger
      var next = startP - dy / H;
      if (next > 1) next = 1 + F.rubberband(next - 1, 0.6); // resist upward
      p.set(next);
      vt.push(e.clientY);
    });
    function endDrag(e) {
      if (!dragging || (e && e.pointerId !== pid)) return;
      dragging = false;
      menu.classList.remove("is-dragging");
      var vy = vt.velocity();                       // px/s, positive = downward
      var vp = -vy / H;                             // progress per second
      var projected = p.x + F.project(vp);          // where this flick is headed
      var target = projected > 0.5 ? 1 : 0;
      var moving = Math.abs(vy) > 250;
      if (target === 1) { isOpen = true; burger.setAttribute("aria-expanded", "true"); p.to(1, { damping: moving ? 0.8 : 1, response: moving ? 0.3 : 0.34, velocity: vp }); }
      else closeMenu({ velocity: vp, noFocus: true });
    }
    menu.addEventListener("pointerup", endDrag);
    menu.addEventListener("pointercancel", endDrag);
  }

  /* ------------------------------------------------------------------ *
   * Rails: draggable, momentum-projected, rubber-banded, snap to items.
   * Without JS they stay native horizontally scrolling lists.
   * ------------------------------------------------------------------ */
  function initRail(root) {
    var track = $(".rail-track", root);
    if (!track) return;
    var wrap = root.parentNode;
    root.classList.add("rail--js");
    var min = 0, snaps = [0], vw = 1;

    var sp = new Spring(0, function (x) { track.style.transform = "translate3d(" + x.toFixed(2) + "px,0,0)"; }, { eps: 0.15 });

    root.addEventListener("scroll", function () { if (root.scrollLeft) root.scrollLeft = 0; }); // our transform owns horizontal position
    function measure() {
      root.scrollLeft = 0;
      vw = root.clientWidth;
      var padL = parseFloat(getComputedStyle(track).paddingLeft) || 0;
      min = Math.min(0, vw - track.scrollWidth);
      var s = $$(".rail-track > *", root).map(function (c) { return clamp(-(c.offsetLeft - padL), min, 0); });
      snaps = s.filter(function (v, i) { return s.indexOf(v) === i; });
      if (!snaps.length) snaps = [0];
      updateButtons();
    }
    function nearest(x) {
      return snaps.reduce(function (a, b) { return Math.abs(b - x) < Math.abs(a - x) ? b : a; }, snaps[0]);
    }
    function updateButtons() {
      var prev = $("[data-rail-prev]", wrap), next = $("[data-rail-next]", wrap);
      var x = sp.target;
      if (prev) prev.disabled = x >= -1;
      if (next) next.disabled = x <= min + 1;
    }
    function go(x, o) { sp.to(x, o || { damping: 1, response: 0.42 }); updateButtons(); }
    function step(dir) {
      var i = snaps.indexOf(nearest(sp.target));
      go(snaps[clamp(i + dir, 0, snaps.length - 1)]);
    }

    var down = false, lock = null, id = 0, sx = 0, sy = 0, base = 0, moved = 0, suppress = false;
    var vt = new F.VelocityTracker();

    root.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      down = true; lock = null; id = e.pointerId; sx = e.clientX; sy = e.clientY;
      sp.stop(); base = sp.x; moved = 0;             // grab mid-flight, from the live position
      vt.reset(); vt.push(e.clientX);
    });
    root.addEventListener("pointermove", function (e) {
      if (!down || e.pointerId !== id) return;
      var dx = e.clientX - sx, dy = e.clientY - sy;
      if (!lock) {                                   // ~8px of hysteresis before committing to a direction
        if (Math.hypot(dx, dy) < 8) return;
        lock = Math.abs(dx) > Math.abs(dy) ? "x" : "y";
        if (lock === "y") { down = false; return; }
        root.setPointerCapture(id);
        root.classList.add("is-dragging");
      }
      var raw = base + dx, x = raw;
      if (raw > 0) x = F.rubberband(raw, vw);
      else if (raw < min) x = min + F.rubberband(raw - min, vw);
      sp.set(x);
      moved = Math.max(moved, Math.abs(dx));
      vt.push(e.clientX);
    });
    function end(e) {
      if (!down || (e && e.pointerId !== id)) return;
      down = false;
      root.classList.remove("is-dragging");
      if (lock !== "x") return;
      try { root.releasePointerCapture(id); } catch (err) { /* already released */ }
      suppress = moved > 8;                          // don't turn a drag into a click
      var v = vt.velocity();
      var landing = nearest(clamp(sp.x + F.project(v), min, 0));
      go(landing, { velocity: v, damping: Math.abs(v) > 300 ? 0.82 : 1, response: 0.4 });
    }
    root.addEventListener("pointerup", end);
    root.addEventListener("pointercancel", end);
    root.addEventListener("click", function (e) { if (suppress) { e.preventDefault(); e.stopPropagation(); suppress = false; } }, true);
    root.addEventListener("dragstart", function (e) { e.preventDefault(); });

    var wheelTimer;
    root.addEventListener("wheel", function (e) {    // trackpad horizontal scroll
      if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
      e.preventDefault();
      sp.set(clamp(sp.x - e.deltaX, min - vw * 0.1, vw * 0.1));
      clearTimeout(wheelTimer);
      wheelTimer = setTimeout(function () { go(nearest(clamp(sp.x, min, 0))); }, 90);
    }, { passive: false });

    root.addEventListener("focusin", function (e) {  // keyboard focus brings the item into view
      root.scrollLeft = 0;
      var item = e.target.closest(".rail-track > *");
      if (!item) return;
      var padL = parseFloat(getComputedStyle(track).paddingLeft) || 0;
      var off = item.offsetLeft - padL, x = -sp.target;
      if (off < x || off + item.offsetWidth > x + vw) go(clamp(-off, min, 0));
    });
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { step(1); }
      else if (e.key === "ArrowLeft") { step(-1); }
    });

    var prevB = $("[data-rail-prev]", wrap), nextB = $("[data-rail-next]", wrap);
    if (prevB) prevB.addEventListener("click", function () { step(-1); });
    if (nextB) nextB.addEventListener("click", function () { step(1); });

    var ro = "ResizeObserver" in window ? new ResizeObserver(function () { measure(); sp.set(clamp(sp.x, min, 0)); }) : null;
    if (ro) ro.observe(root);
    window.addEventListener("load", measure);
    measure();
  }
  $$("[data-rail]").forEach(initRail);

  /* ------------------------------------------------------------------ *
   * Add to cart: the item travels to the cart. X and Y are independent
   * springs (so the path arcs), the cart answers with a bounce on the
   * same frame the haptic fires.
   * ------------------------------------------------------------------ */
  var cartLink = $("#cart-link");
  document.body.addEventListener("htmx:afterRequest", function (e) {
    var form = e.detail.elt;
    if (!form || !form.matches || !form.matches('form[action*="/cart/add/"]') || !e.detail.successful) return;
    if (!cartLink) return;
    var btn = form.querySelector("button") || form;
    var a = btn.getBoundingClientRect(), b = cartLink.getBoundingClientRect();
    var sx0 = a.left + a.width / 2, sy0 = a.top + a.height / 2;
    var ex = b.left + b.width / 2, ey = b.top + b.height / 2;

    function arrive() {
      if (navigator.vibrate) navigator.vibrate(8);   // haptic lands with the visual
      if (F.reducedMotion()) return;
      new Spring(1.35, function (s) { cartLink.style.transform = "scale(" + s.toFixed(3) + ")"; }, { eps: 0.002 })
        .to(1, { damping: 0.55, response: 0.34 });
    }
    if (F.reducedMotion()) { arrive(); return; }

    var dot = document.createElement("span");
    dot.className = "fly"; dot.setAttribute("aria-hidden", "true");
    document.body.appendChild(dot);
    var left = 2, finished = function () { if (--left === 0) { dot.remove(); arrive(); } };
    function place(x, y) { dot.style.transform = "translate3d(" + (x - 9) + "px," + (y - 9) + "px,0)"; }
    var cx = sx0, cy = sy0; place(cx, cy);
    new Spring(sx0, function (x) { cx = x; place(cx, cy); }, { eps: 0.4 }).to(ex, { damping: 1, response: 0.55, onDone: finished });
    new Spring(sy0, function (y) { cy = y; place(cx, cy); }, { eps: 0.4 }).to(ey, { velocity: -520, damping: 0.9, response: 0.5, onDone: finished });
  });

  /* ------------------------------------------------------------------ *
   * Toast (forgiveness: undo instead of "are you sure?").
   * ------------------------------------------------------------------ */
  var toast = $("#toast");
  if (toast) {
    var toastTimer;
    new MutationObserver(function () {
      clearTimeout(toastTimer);
      if (toast.firstElementChild) {
        toast.classList.add("is-visible");
        toastTimer = setTimeout(function () {
          toast.classList.remove("is-visible");
          setTimeout(function () { toast.innerHTML = ""; }, 350);
        }, 7000);
      } else toast.classList.remove("is-visible");
    }).observe(toast, { childList: true });
  }

  /* ------------------------------------------------------------------ *
   * Hero: depth that follows the pointer through springs (X and Y are
   * separate springs), and the backdrop rings drift slightly on scroll.
   * No looping background motion.
   * ------------------------------------------------------------------ */
  var hero = $(".hero");
  if (hero && finePointer.matches && !F.reducedMotion()) {
    var layers = $$("[data-depth]", hero);
    var px = new Spring(0, apply, { eps: 0.002 }), py = new Spring(0, apply, { eps: 0.002 });
    function apply() {
      layers.forEach(function (l) {
        var d = parseFloat(l.dataset.depth);
        l.style.transform = "translate3d(" + (px.x * d).toFixed(2) + "px," + (py.x * d).toFixed(2) + "px,0)";
      });
    }
    hero.addEventListener("pointermove", function (e) {
      var r = hero.getBoundingClientRect();
      px.to((e.clientX - r.left) / r.width - 0.5, { damping: 1, response: 0.7 });
      py.to((e.clientY - r.top) / r.height - 0.5, { damping: 1, response: 0.7 });
    });
    hero.addEventListener("pointerleave", function () {
      px.to(0, { damping: 1, response: 0.7 }); py.to(0, { damping: 1, response: 0.7 });
    });
  }
  var rings = $$(".backdrop .ring");
  if (rings.length && !F.reducedMotion()) {
    var scrollSpring = new Spring(0, function (y) {
      rings.forEach(function (r, i) { r.style.transform = "translate3d(0," + (y * (i ? -0.12 : 0.18)).toFixed(1) + "px,0)"; });
    }, { eps: 0.3 });
    window.addEventListener("scroll", function () {
      scrollSpring.to(Math.min(window.scrollY, 1600), { damping: 1, response: 0.6 });
    }, { passive: true });
  }

  /* ------------------------------------------------------------------ *
   * Reveal on scroll (one-shot, not gesture-driven, so CSS handles it).
   * ------------------------------------------------------------------ */
  var reveals = $$(".reveal");
  if ("IntersectionObserver" in window && !F.reducedMotion()) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else reveals.forEach(function (el) { el.classList.add("in"); });
})();
