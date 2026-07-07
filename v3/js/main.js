/* =====================================================================
   VESTA — main.js
   1. Les braises (canvas 2D) : subtiles au repos, attisées pendant la forge
   2. La forge (GSAP ScrollTrigger, scrub) :
      polaroïds -> assemblage -> lueur -> film
   Tout est fonction de la position de scroll : scrub parfait, aller-retour.
   ===================================================================== */
(function () {
  "use strict";
  var reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* Filet : si le CDN GSAP est bloqué, on bascule en mise en page statique */
  if (!window.gsap || !window.ScrollTrigger) {
    document.documentElement.classList.add("statique");
  }

  /* =========================================================
     1. LES BRAISES — window.FORGE_HEAT (0..1) attise le foyer
     ========================================================= */
  window.FORGE_HEAT = 0;
  var cv = document.getElementById("braises");
  var ctx = cv.getContext("2d");
  var W = 0, H = 0, DPR = Math.min(devicePixelRatio || 1, 1.5);
  function taille() {
    W = innerWidth; H = innerHeight;
    cv.width = W * DPR; cv.height = H * DPR;
    cv.style.width = W + "px"; cv.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  taille();
  addEventListener("resize", taille);

  var N = matchMedia("(pointer: coarse)").matches ? 60 : 110;
  var P = [];
  function nait(p, bas) {
    p.x = Math.random() * W;
    p.y = bas ? H + 10 + Math.random() * 40 : Math.random() * H;
    p.vy = 12 + Math.random() * 26;               /* px/s vers le haut */
    p.vx = (Math.random() - 0.5) * 10;
    p.r = 0.6 + Math.random() * 1.7;
    p.ph = Math.random() * Math.PI * 2;
    p.tw = 0.5 + Math.random() * 1.8;
  }
  for (var i = 0; i < N; i++) { var p = {}; nait(p, false); P.push(p); }

  var last = performance.now();
  function braises(now) {
    requestAnimationFrame(braises);
    var dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (reduceMotion) { ctx.clearRect(0, 0, W, H); return; }
    var t = now / 1000;
    var chaleur = window.FORGE_HEAT;               /* 0 = veille, 1 = forge */
    var boost = 1 + chaleur * 2.2;
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < N; i++) {
      var p = P[i];
      p.y -= p.vy * boost * dt;
      p.x += (p.vx + Math.sin(t * 0.8 + p.ph) * 8) * dt;
      if (p.y < -12 || p.x < -12 || p.x > W + 12) nait(p, true);
      var scint = 0.45 + 0.55 * Math.abs(Math.sin(t * p.tw + p.ph));
      var a = scint * (0.35 + chaleur * 0.5);
      var r = p.r * (1 + chaleur * 0.9);
      var g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 4);
      g.addColorStop(0, "rgba(255,214,160," + (a).toFixed(3) + ")");
      g.addColorStop(0.4, "rgba(255,122,53," + (a * 0.55).toFixed(3) + ")");
      g.addColorStop(1, "rgba(255,90,30,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r * 4, 0, 6.2832);
      ctx.fill();
    }
  }
  requestAnimationFrame(braises);

  /* =========================================================
     2. LE HERO — les deux lignes se révèlent à l'arrivée
     ========================================================= */
  if (!reduceMotion && window.gsap) {
    gsap.fromTo(".hero h1 .l > span",
      { yPercent: 115 },
      { yPercent: 0, duration: 1.1, ease: "power4.out", stagger: 0.12, delay: 0.15 });
    gsap.from(".hero .lead, .hero .reassurance", {
      opacity: 0, y: 18, duration: 0.9, ease: "power2.out", stagger: 0.12, delay: 0.55,
    });
  }

  /* =========================================================
     3. LA FORGE — la timeline maîtresse, scrubée par le scroll
     ========================================================= */
  if (reduceMotion || !window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  var polas = gsap.utils.toArray(".pola");
  var film = document.getElementById("film");
  var etape = document.getElementById("etape");

  /* Positions de départ (hors champ, chaque photo depuis son bord)
     et positions "éparses" (l'étalement sur la table de travail).   */
  var DEPART = [
    { x: "-120vw", y: "-16vh", r: -24 },
    { x: "120vw",  y: "-22vh", r: 18 },
    { x: "-120vw", y: "20vh",  r: 16 },
    { x: "120vw",  y: "24vh",  r: -20 },
  ];
  var EPARS = [
    { x: "-24vw", y: "-13vh", r: -7 },
    { x: "23vw",  y: "-15vh", r: 5 },
    { x: "-21vw", y: "15vh",  r: 6 },
    { x: "25vw",  y: "13vh",  r: -5 },
  ];
  /* L'empilement central : un léger éventail, comme des tirages posés. */
  var PILE = [
    { x: "-1.2vw", y: "-.6vh", r: -4 },
    { x: "1vw",    y: ".4vh",  r: 3 },
    { x: "-.6vw",  y: "1vh",   r: 6 },
    { x: ".8vw",   y: "-1vh",  r: -6 },
  ];

  polas.forEach(function (el, i) {
    gsap.set(el, { xPercent: -50, yPercent: -50, x: DEPART[i].x, y: DEPART[i].y, rotation: DEPART[i].r, opacity: 0 });
  });
  gsap.set("#resultat", { xPercent: -50, yPercent: -50, opacity: 0, scale: 0.62 });
  gsap.set("#lueur", { xPercent: -50, yPercent: -50 });

  var tl = gsap.timeline({
    scrollTrigger: {
      trigger: "#forge",
      start: "top top",
      end: "bottom bottom",
      scrub: 0.85,                 /* l'inertie du scrub : le velours */
      onUpdate: function (self) {
        /* le film ne joue que dans son acte */
        if (self.progress > 0.78) { film.play().catch(function () {}); }
        else { film.pause(); }
      },
    },
    defaults: { ease: "power2.inOut" },
  });

  /* --- ACTE 1 (0 -> 3) : les photos glissent depuis les bords --- */
  polas.forEach(function (el, i) {
    tl.to(el, {
      x: EPARS[i].x, y: EPARS[i].y, rotation: EPARS[i].r, opacity: 1,
      duration: 1.6, ease: "power3.out",
    }, i * 0.35);
  });
  tl.call(function () { etape.textContent = "LES PHOTOS DE L'AGENT"; etape.classList.remove("chaud"); }, null, 0.1);

  /* --- ACTE 2 (3.4 -> 5.2) : l'assemblage au centre --- */
  polas.forEach(function (el, i) {
    tl.to(el, {
      x: PILE[i].x, y: PILE[i].y, rotation: PILE[i].r, scale: 0.94,
      duration: 1.5, ease: "power3.inOut",
    }, 3.4 + i * 0.08);
  });
  tl.call(function () { etape.textContent = "VESTA FORGE LE PLAN SÉQUENCE"; etape.classList.add("chaud"); }, null, 3.6);

  /* --- ACTE 3 (5 -> 7) : la lueur engloutit (le traitement IA) --- */
  tl.to("#lueur", { opacity: 1, scale: 1.12, duration: 1.6 }, 5.0);
  tl.to(window, { FORGE_HEAT: 1, duration: 1.4 }, 5.0);           /* les braises s'attisent */
  tl.to(polas, {
    opacity: 0, scale: 0.66, filter: "brightness(2.4)",
    duration: 1.3, stagger: 0.07, ease: "power2.in",
  }, 5.7);

  /* --- ACTE 4 (6.8 -> 9) : le film prend la place --- */
  tl.fromTo("#resultat",
    { opacity: 0, scale: 0.62 },
    { opacity: 1, scale: 1, duration: 1.8, ease: "power3.out" }, 6.8);
  tl.to("#lueur", { opacity: 0.22, scale: 1.35, duration: 1.6 }, 7.2);
  tl.to(window, { FORGE_HEAT: 0.25, duration: 1.6 }, 7.2);
  tl.call(function () { etape.textContent = "VOTRE FILM — LIVRÉ EN 48 H"; }, null, 7.4);
  tl.to({}, { duration: 1.2 });    /* respiration finale : le film se savoure */

})();
