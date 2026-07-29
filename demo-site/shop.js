/*
 * Demo store behaviour: a basket in localStorage, and the two commerce events
 * the marketing system cares about.
 *
 * Only two lines here are about tracking, and both use the tracker's public
 * API exactly as a real shop would:
 *
 *   mos.track("add_to_cart", {...})   when a device is added
 *   mos.track("purchase",    {...})   when checkout completes
 *
 * `purchase` is the conversion event. api/routers/collect.py credits it back
 * to whichever campaign click brought the customer here, which is what turns
 * email tracking into a measured funnel rather than two unrelated numbers.
 */
(function (window, document) {
  "use strict";

  var KEY = "innov8_basket";

  function read() {
    try {
      var raw = window.localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function write(items) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(items));
    } catch (e) {
      /* private mode — the basket just will not survive a reload */
    }
    paintCount(items);
  }

  function total(items) {
    return items.reduce(function (sum, i) {
      return sum + i.price * i.qty;
    }, 0);
  }

  function paintCount(items) {
    var n = (items || read()).reduce(function (sum, i) {
      return sum + i.qty;
    }, 0);
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-cart-count]"),
      function (el) {
        el.textContent = String(n);
      }
    );
  }

  // ── Adding to the basket ─────────────────────────────────────────────────
  function add(button) {
    var sku = button.getAttribute("data-sku");
    var name = button.getAttribute("data-name");
    var price = parseFloat(button.getAttribute("data-price"));

    var items = read();
    var existing = items.filter(function (i) { return i.sku === sku; })[0];
    if (existing) {
      existing.qty += 1;
    } else {
      items.push({ sku: sku, name: name, price: price, qty: 1 });
    }
    write(items);

    if (window.mos) {
      window.mos.track("add_to_cart", {
        sku: sku,
        name: name,
        value: price,
        basket_value: Math.round(total(items) * 100) / 100,
      });
    }

    var original = button.textContent;
    button.textContent = "Added ✓";
    button.disabled = true;
    window.setTimeout(function () {
      button.textContent = original;
      button.disabled = false;
    }, 1200);
  }

  document.addEventListener("click", function (ev) {
    var el = ev.target;
    while (el && el !== document.body) {
      if (el.hasAttribute && el.hasAttribute("data-add-to-cart")) {
        add(el);
        return;
      }
      el = el.parentElement;
    }
  });

  // ── Checkout ─────────────────────────────────────────────────────────────
  // Exposed so cart.html can call it; the purchase event is the conversion.
  window.innov8 = {
    basket: read,
    basketTotal: function () { return total(read()); },
    clear: function () { write([]); },
    checkout: function () {
      var items = read();
      if (!items.length) return null;

      var value = Math.round(total(items) * 100) / 100;
      var order = {
        value: value,
        currency: "USD",
        items: items.length,
        units: items.reduce(function (s, i) { return s + i.qty; }, 0),
        // The store's own loyalty rule: ten points per dollar. This is what
        // the LoyaltyPoints column of the research dataset represents.
        points_earned: Math.round(value * 10),
        skus: items.map(function (i) { return i.sku; }).join(","),
      };

      if (window.mos) {
        window.mos.track("purchase", order);
        window.mos.flush();
      }
      write([]);
      return order;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { paintCount(); });
  } else {
    paintCount();
  }
})(window, document);
