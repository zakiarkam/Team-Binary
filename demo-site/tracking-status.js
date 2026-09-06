/*
 * Demo-only helper: shows whether the tracker is active in the footer.
 *
 * This is not part of the product — it exists so that during the viva you can
 * point at the badge and show, live, that Do Not Track really does switch the
 * tracker off, and that consent is separate from tracking.
 */
(function () {
  function paint() {
    var badge = document.getElementById("mos-status");
    if (!badge) return;

    if (!window.mos) {
      badge.textContent = "tracking: snippet not loaded";
      badge.className = "tracking-badge off";
      return;
    }

    var s = window.mos.status();
    if (!s.active) {
      badge.textContent = "tracking: off (Do Not Track)";
      badge.className = "tracking-badge off";
      return;
    }
    badge.textContent = "tracking: on · " + String(s.uid).slice(0, 8);
    badge.className = "tracking-badge on";
  }

  // The snippet is deferred, so wait for it before reading window.mos.
  if (document.readyState === "complete") setTimeout(paint, 150);
  else window.addEventListener("load", function () { setTimeout(paint, 150); });
})();
