/*!
 * mos.js — Marketing OS visitor tracker
 * Team Binary · University of Moratuwa · 2026
 *
 * Install on the client website:
 *   <script defer src="https://your-api/mos.js" data-site="mos_XXXXXXXX"></script>
 *
 * What it collects (first-party, this site only):
 *   page_view, click, scroll depth, form_submit, time on page.
 * What it never collects:
 *   keystrokes, form field values, cross-site history, cookies.
 *
 * Identity model
 *   - Every browser gets a random anonymous id in localStorage.
 *   - mos.identify(email) upgrades that visitor to "known".
 *   - Email marketing requires explicit consent: mos.identify(email, {consent:true}).
 *
 * Do Not Track is honoured by default. Set data-respect-dnt="false" to override
 * (not recommended).
 *
 * Public API
 *   mos.track(type, props)                 — custom event
 *   mos.identify(email, {name, consent})   — attach an email to this visitor
 *   mos.consent(true|false)                — update email opt-in
 *   mos.status()                           — {active, uid, queued}
 */
(function (window, document) {
  "use strict";

  // ── Locate our own <script> tag to read configuration ────────────────────
  var script =
    document.currentScript ||
    (function () {
      var all = document.getElementsByTagName("script");
      for (var i = all.length - 1; i >= 0; i--) {
        if (all[i].src && all[i].src.indexOf("mos.js") !== -1) return all[i];
      }
      return null;
    })();

  if (!script) return;

  var SITE_KEY = script.getAttribute("data-site");
  var API = script.src.replace(/\/mos\.js(\?.*)?$/, "");
  var RESPECT_DNT = script.getAttribute("data-respect-dnt") !== "false";

  if (!SITE_KEY) {
    console.warn("[mos] missing data-site attribute — tracking disabled");
    return;
  }

  // ── Do Not Track ─────────────────────────────────────────────────────────
  var dnt =
    window.doNotTrack === "1" ||
    navigator.doNotTrack === "1" ||
    navigator.doNotTrack === "yes" ||
    window.navigator.msDoNotTrack === "1";

  var ACTIVE = !(RESPECT_DNT && dnt);

  // ── Identity ─────────────────────────────────────────────────────────────
  var UID_KEY = "mos_uid";
  var SID_KEY = "mos_sid";

  function randomId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "v-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  function stored(storage, key) {
    try {
      var v = storage.getItem(key);
      if (!v) {
        v = randomId();
        storage.setItem(key, v);
      }
      return v;
    } catch (e) {
      // Private mode or storage disabled — fall back to a per-page id.
      return randomId();
    }
  }

  var uid = ACTIVE ? stored(window.localStorage, UID_KEY) : null;
  var sid = ACTIVE ? stored(window.sessionStorage, SID_KEY) : null;

  // ── Context (sent with every batch) ──────────────────────────────────────
  function queryParam(name) {
    var m = new RegExp("[?&]" + name + "=([^&#]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : null;
  }

  function deviceType() {
    var w = window.innerWidth || document.documentElement.clientWidth;
    if (w < 768) return "mobile";
    if (w < 1024) return "tablet";
    return "desktop";
  }

  function context() {
    return {
      path: window.location.pathname + window.location.search,
      referrer: document.referrer || null,
      utm_source: queryParam("utm_source"),
      utm_medium: queryParam("utm_medium"),
      utm_campaign: queryParam("utm_campaign"),
      device: deviceType(),
      language: navigator.language || null,
      screen: (window.screen && window.screen.width + "x" + window.screen.height) || null,
      title: document.title || null,
    };
  }

  // ── Event queue with batched delivery ────────────────────────────────────
  var queue = [];
  var timer = null;
  var FLUSH_MS = 3000;
  var MAX_BATCH = 20;

  function enqueue(type, props) {
    if (!ACTIVE) return;
    queue.push({
      type: type,
      path: window.location.pathname,
      props: props || {},
      ts: new Date().toISOString(),
    });
    if (queue.length >= MAX_BATCH) {
      flush();
    } else if (!timer) {
      timer = window.setTimeout(flush, FLUSH_MS);
    }
  }

  function flush(useBeacon) {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    if (!ACTIVE || queue.length === 0) return;

    var payload = JSON.stringify({
      site_key: SITE_KEY,
      visitor_uid: uid,
      session_id: sid,
      context: context(),
      events: queue.splice(0, queue.length),
    });

    var url = API + "/collect";

    // text/plain keeps this a CORS "simple request" — no preflight round-trip.
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([payload], { type: "text/plain" }));
      return;
    }

    try {
      window
        .fetch(url, {
          method: "POST",
          headers: { "Content-Type": "text/plain" },
          body: payload,
          keepalive: true,
          mode: "cors",
        })
        .catch(function () {
          /* offline or blocked — events for this batch are dropped */
        });
    } catch (e) {
      /* fetch unavailable */
    }
  }

  // ── Automatic events ─────────────────────────────────────────────────────
  var pageEnteredAt = Date.now();
  var lastPath = null;
  var exitSent = false;

  // The path WITHOUT the hash. A fragment jump (#features) is not a new page,
  // but it does fire popstate — so comparing on this is what stops one visit
  // being counted several times.
  function currentPath() {
    return window.location.pathname + window.location.search;
  }

  function trackPageView() {
    var path = currentPath();
    if (path === lastPath) return;
    lastPath = path;

    pageEnteredAt = Date.now();
    exitSent = false;
    scrollMarks = {};
    enqueue("page_view", { title: document.title });
  }

  // Scroll depth — one event per quarter, at most once per page.
  var scrollMarks = {};
  function onScroll() {
    var doc = document.documentElement;
    var height = doc.scrollHeight - doc.clientHeight;
    if (height <= 0) return;
    var pct = Math.round(((window.scrollY || doc.scrollTop) / height) * 100);
    [25, 50, 75, 100].forEach(function (mark) {
      if (pct >= mark && !scrollMarks[mark]) {
        scrollMarks[mark] = true;
        enqueue("scroll", { depth: mark });
      }
    });
  }

  // Clicks on links, buttons, and anything marked data-mos-track.
  function onClick(ev) {
    var el = ev.target;
    while (el && el !== document.body) {
      var tracked =
        el.hasAttribute && el.hasAttribute("data-mos-track")
          ? el.getAttribute("data-mos-track")
          : null;
      var tag = el.tagName ? el.tagName.toLowerCase() : "";

      if (tracked || tag === "a" || tag === "button") {
        enqueue("click", {
          label: tracked || (el.innerText || "").trim().slice(0, 80),
          href: el.getAttribute ? el.getAttribute("href") : null,
          tag: tag,
        });
        return;
      }
      el = el.parentElement;
    }
  }

  // Form submissions — we record THAT a form was submitted and its name only.
  // Field values are never read, except an explicit data-mos-email field.
  function onSubmit(ev) {
    var form = ev.target;
    if (!form || form.tagName !== "FORM") return;

    var name = form.getAttribute("name") || form.getAttribute("id") || "form";
    enqueue("form_submit", { form: name });

    var emailField = form.querySelector("[data-mos-email]");
    if (emailField && emailField.value) {
      var consentBox = form.querySelector("[data-mos-consent]");
      identify(emailField.value, {
        consent: consentBox ? !!consentBox.checked : false,
        source: name,
      });
    }
  }

  // Both `pagehide` and `visibilitychange` fire when a page goes away, so this
  // is guarded: emitting page_exit twice would double-count time on site, and
  // time on site is a segmentation feature in Module 1.
  function onHide() {
    if (!exitSent) {
      var seconds = Math.round((Date.now() - pageEnteredAt) / 1000);
      if (seconds > 0) {
        exitSent = true;
        enqueue("page_exit", { seconds: seconds });
      }
    }
    flush(true);
  }

  // ── Public API ───────────────────────────────────────────────────────────
  function identify(email, options) {
    if (!ACTIVE || !email) return;
    options = options || {};
    enqueue("identify", {
      email: String(email).trim().toLowerCase(),
      name: options.name || null,
      consent: options.consent === true,
      source: options.source || "api",
    });
    flush();
  }

  var mos = {
    track: function (type, props) {
      enqueue(String(type), props);
    },
    identify: identify,
    consent: function (granted) {
      if (!ACTIVE) return;
      enqueue("consent", { consent: granted === true });
      flush();
    },
    status: function () {
      return { active: ACTIVE, uid: uid, queued: queue.length, dnt: dnt };
    },
    flush: function () {
      flush();
    },
  };

  window.mos = mos;

  if (!ACTIVE) {
    console.info("[mos] Do Not Track is enabled — tracking is off by design.");
    return;
  }

  // ── Wire up ──────────────────────────────────────────────────────────────
  document.addEventListener("click", onClick, true);
  document.addEventListener("submit", onSubmit, true);
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("pagehide", onHide);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") onHide();
  });

  // Single-page-app navigation: patch history and listen for back/forward.
  ["pushState", "replaceState"].forEach(function (method) {
    var original = window.history[method];
    if (!original) return;
    window.history[method] = function () {
      var result = original.apply(this, arguments);
      trackPageView();
      return result;
    };
  });
  window.addEventListener("popstate", trackPageView);

  trackPageView();
})(window, document);
