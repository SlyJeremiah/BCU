/*
 * fluid.js: small physics toolkit for interruptible, velocity-aware UI.
 *
 *  - Spring:  one persistent animator per value. It always continues from its
 *             CURRENT value and velocity, so it can be grabbed and re-targeted
 *             mid-flight with no jump (interruptibility + velocity blending).
 *             Tuned with Apple's two designer parameters: damping ratio and
 *             response (seconds), not mass/stiffness/duration.
 *  - project():    where a release velocity will come to rest (momentum projection).
 *  - rubberband(): progressive resistance past a boundary.
 *  - VelocityTracker: release velocity from a short window of pointer samples.
 */
(function (global) {
  "use strict";

  var reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  function reducedMotion() { return reducedQuery.matches; }

  function Spring(value, onUpdate, opts) {
    this.x = value;
    this.v = 0;
    this.target = value;
    this.onUpdate = onUpdate || function () {};
    this.eps = (opts && opts.eps) || 0.01;
    this.damping = 1;
    this.response = 0.4;
    this.onDone = null;
    this.raf = 0;
    this.last = 0;
    this._tick = this._tick.bind(this);
  }

  Spring.prototype.to = function (target, o) {
    o = o || {};
    this.target = target;
    this.damping = o.damping == null ? 1 : o.damping;      // 1 = no overshoot
    this.response = o.response == null ? 0.4 : o.response; // seconds; lower = snappier
    this.onDone = o.onDone || null;
    if (o.velocity != null) this.v = o.velocity;           // hand off gesture velocity
    if (reducedMotion() && !o.force) { this.set(target); if (this.onDone) this.onDone(); return this; }
    if (!this.raf) { this.last = performance.now(); this.raf = requestAnimationFrame(this._tick); }
    return this;
  };

  Spring.prototype.set = function (x) {
    this.stop();
    this.x = x; this.target = x; this.v = 0;
    this.onUpdate(x, 0);
    return this;
  };

  Spring.prototype.stop = function () {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    return this;
  };

  Spring.prototype._tick = function (now) {
    var dt = Math.min((now - this.last) / 1000, 1 / 30);
    this.last = now;
    var omega = (2 * Math.PI) / this.response;
    var k = omega * omega, c = 2 * this.damping * omega;
    var steps = Math.max(1, Math.ceil(dt * 240)), h = dt / steps;
    for (var i = 0; i < steps; i++) {            // semi-implicit Euler, sub-stepped for stability
      this.v += (-k * (this.x - this.target) - c * this.v) * h;
      this.x += this.v * h;
    }
    if (Math.abs(this.x - this.target) < this.eps && Math.abs(this.v) < this.eps * 8) {
      this.x = this.target; this.v = 0; this.raf = 0;
      this.onUpdate(this.x, 0);
      var done = this.onDone; this.onDone = null;
      if (done) done();
      return;
    }
    this.onUpdate(this.x, this.v);
    this.raf = requestAnimationFrame(this._tick);
  };

  // Where does a flick with this release velocity (units/s) come to rest?
  // Apple's exponential-decay form, same as scroll deceleration.
  function project(velocity, decelerationRate) {
    var d = decelerationRate == null ? 0.998 : decelerationRate;
    return (velocity / 1000) * d / (1 - d);
  }

  // The further past a bound, the less the content follows.
  function rubberband(overshoot, dimension, constant) {
    var c = constant == null ? 0.55 : constant;
    if (!overshoot) return 0;
    var sign = overshoot < 0 ? -1 : 1, o = Math.abs(overshoot);
    return sign * (o * dimension * c) / (dimension + c * o);
  }

  function VelocityTracker() { this.samples = []; }
  VelocityTracker.prototype.reset = function () { this.samples.length = 0; };
  VelocityTracker.prototype.push = function (x) {
    var t = performance.now();
    this.samples.push([x, t]);
    while (this.samples.length > 1 && t - this.samples[0][1] > 100) this.samples.shift();
  };
  VelocityTracker.prototype.velocity = function () {
    var s = this.samples;
    if (s.length < 2) return 0;
    var a = s[0], b = s[s.length - 1];
    if (performance.now() - b[1] > 80) return 0;   // finger paused before lifting
    var dt = (b[1] - a[1]) / 1000;
    return dt > 0 ? (b[0] - a[0]) / dt : 0;
  };

  function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)); }

  global.Fluid = {
    Spring: Spring, VelocityTracker: VelocityTracker,
    project: project, rubberband: rubberband, clamp: clamp, reducedMotion: reducedMotion,
  };
})(window);
