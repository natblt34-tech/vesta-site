/* ==========================================================================
   VESTA — app.js (JavaScript vanilla, zéro dépendance)
   Modules : header, reveal on scroll, slider avant/après, pricing toggle,
             studio d'upload (avec point d'ancrage back-end Python).
   ========================================================================== */

"use strict";

/* --------------------------------------------------------------------------
   CONFIG API — point d'intégration du futur back-end Python (FastAPI/Flask).
   Exemple côté serveur :  POST /api/generate  (multipart/form-data, champ "photos")
   Réponse attendue :      { "job_id": "...", "status_url": "/api/jobs/..." }
   -------------------------------------------------------------------------- */
window.VESTA_API = {
  baseUrl: "http://localhost:8000",
  endpoints: { generate: "/api/generate" },
  enabled: false, // passer à true quand le serveur Python est branché
};

const prefersReducedMotion =
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ==========================================================
   1. HEADER — état "scrolled" + menu mobile
   ========================================================== */
(function initHeader() {
  const header = document.getElementById("header");
  const toggle = document.getElementById("navToggle");

  const onScroll = () =>
    header.classList.toggle("is-scrolled", window.scrollY > 24);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  toggle.addEventListener("click", () => {
    const open = header.classList.toggle("nav-open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  // Ferme le menu mobile après un clic sur un lien
  header.querySelectorAll(".main-nav a").forEach((link) =>
    link.addEventListener("click", () => {
      header.classList.remove("nav-open");
      toggle.setAttribute("aria-expanded", "false");
    })
  );
})();

/* ==========================================================
   2. RÉVÉLATION AU SCROLL (IntersectionObserver)
   ========================================================== */
(function initReveal() {
  const items = document.querySelectorAll(".reveal");
  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    items.forEach((el) => el.classList.add("is-visible"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
  );
  items.forEach((el) => io.observe(el));
})();

/* ==========================================================
   3. SLIDER AVANT / APRÈS (pointer + clavier, accessible)
   ========================================================== */
(function initCompare() {
  const root = document.getElementById("compare");
  if (!root) return;

  const before = document.getElementById("compareBefore");
  const handle = document.getElementById("compareHandle");
  let position = 50; // en %

  function render() {
    before.style.clipPath = `inset(0 ${100 - position}% 0 0)`;
    handle.style.left = `${position}%`;
    root.setAttribute("aria-valuenow", String(Math.round(position)));
  }

  function setFromClientX(clientX) {
    const rect = root.getBoundingClientRect();
    position = Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
    render();
  }

  root.addEventListener("pointerdown", (e) => {
    root.setPointerCapture(e.pointerId);
    setFromClientX(e.clientX);
  });
  root.addEventListener("pointermove", (e) => {
    if (e.buttons === 1) setFromClientX(e.clientX);
  });

  root.addEventListener("keydown", (e) => {
    const step = e.shiftKey ? 10 : 3;
    if (e.key === "ArrowLeft") position = Math.max(0, position - step);
    else if (e.key === "ArrowRight") position = Math.min(100, position + step);
    else return;
    e.preventDefault();
    render();
  });

  render();
})();

/* ==========================================================
   4. PRICING — bascule mensuel / annuel
   ========================================================== */
(function initPricing() {
  const buttons = document.querySelectorAll(".toggle-opt");
  const amounts = document.querySelectorAll(".amount[data-monthly]");
  if (!buttons.length) return;

  buttons.forEach((btn) =>
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.toggle("is-active", b === btn));
      const mode = btn.dataset.billing; // "monthly" | "yearly"
      amounts.forEach((el) => (el.textContent = el.dataset[mode]));
    })
  );
})();

/* ==========================================================
   5. STUDIO — upload drag & drop + génération
   ========================================================== */
(function initStudio() {
  const form = document.getElementById("uploadForm");
  if (!form) return;

  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  const grid = document.getElementById("previewGrid");
  const generateBtn = document.getElementById("generateBtn");
  const status = document.getElementById("studioStatus");
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const progressLabel = document.getElementById("progressLabel");

  const MAX_FILES = 15;
  /** @type {File[]} */
  let files = [];

  /* ----- Sélection & drag/drop ----- */
  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
  input.addEventListener("change", () => addFiles(input.files));

  function addFiles(fileList) {
    for (const file of fileList) {
      if (!file.type.startsWith("image/")) continue;
      if (files.length >= MAX_FILES) break;
      files.push(file);
    }
    input.value = "";
    renderPreviews();
  }

  function removeFile(index) {
    files.splice(index, 1);
    renderPreviews();
  }

  function renderPreviews() {
    grid.innerHTML = "";
    files.forEach((file, i) => {
      const li = document.createElement("li");
      const img = document.createElement("img");
      img.alt = file.name;
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "preview-remove";
      btn.textContent = "✕";
      btn.setAttribute("aria-label", `Retirer ${file.name}`);
      btn.addEventListener("click", () => removeFile(i));

      li.append(img, btn);
      grid.appendChild(li);
    });

    generateBtn.disabled = files.length === 0;
    status.textContent =
      files.length === 0
        ? "Aucune photo pour l'instant. Votre première vidéo est offerte."
        : `${files.length} photo${files.length > 1 ? "s" : ""} prête${files.length > 1 ? "s" : ""}. ` +
          (files.length < 8 ? "Conseil : 8 à 15 images pour un film complet." : "Parfait pour un film complet.");
  }

  /* ----- Soumission ----- */
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!files.length) return;

    generateBtn.disabled = true;
    progressWrap.hidden = false;

    if (window.VESTA_API.enabled) {
      await sendToBackend();
    } else {
      simulateGeneration();
    }
  });

  /* Envoi réel vers le serveur Python — prêt à l'emploi. */
  async function sendToBackend() {
    const { baseUrl, endpoints } = window.VESTA_API;
    const data = new FormData();
    files.forEach((f) => data.append("photos", f, f.name));

    try {
      progressLabel.textContent = "Envoi des photos au studio…";
      progressBar.style.width = "20%";

      const res = await fetch(baseUrl + endpoints.generate, {
        method: "POST",
        body: data,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const job = await res.json();

      progressBar.style.width = "100%";
      progressLabel.textContent =
        "Photos reçues. Vesta compose votre film — suivez le job : " + (job.job_id ?? "");
    } catch (err) {
      progressBar.style.width = "0%";
      progressLabel.textContent =
        "Le serveur ne répond pas. Vérifiez que le back-end tourne sur " +
        window.VESTA_API.baseUrl + " puis relancez.";
      generateBtn.disabled = false;
      console.error("[VESTA] Échec de l'envoi :", err);
    }
  }

  /* Démo front seul : progression simulée. */
  function simulateGeneration() {
    const phases = [
      [15, "Analyse des photos…"],
      [40, "Composition des mouvements de caméra…"],
      [70, "Étalonnage de la lumière…"],
      [92, "Montage et rendu 4K…"],
      [100, "Votre film est prêt. (Démo : branchez le back-end pour le vrai rendu.)"],
    ];
    let i = 0;
    const tick = () => {
      const [pct, label] = phases[i];
      progressBar.style.width = pct + "%";
      progressLabel.textContent = label;
      if (++i < phases.length) setTimeout(tick, 1100);
      else generateBtn.disabled = false;
    };
    tick();
  }
})();
