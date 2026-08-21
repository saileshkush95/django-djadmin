/*!
 * djadmin theme boot — loaded synchronously in <head> so the correct palette
 * is on the document before first paint (no white flash in dark mode).
 *
 * Modes: "auto" (follow the OS), "light", "dark". The choice is stored under
 * the same localStorage key Django's admin uses, so switching between the two
 * UIs keeps the preference.
 */
(function () {
  "use strict";

  var KEY = "theme";
  var MODES = ["auto", "light", "dark"];
  var root = document.documentElement;

  function stored() {
    try {
      var value = localStorage.getItem(KEY);
      return MODES.indexOf(value) === -1 ? null : value;
    } catch (e) {
      return null;
    }
  }

  function set(mode) {
    if (MODES.indexOf(mode) === -1) {
      mode = "auto";
    }
    root.dataset.theme = mode;
    try {
      localStorage.setItem(KEY, mode);
    } catch (e) {
      /* private mode — the class on <html> still applies for this page */
    }
    document.dispatchEvent(new CustomEvent("djadmin:theme", { detail: { mode: mode } }));
    return mode;
  }

  function cycle() {
    var order = ["auto", "light", "dark"];
    var current = root.dataset.theme || "auto";
    return set(order[(order.indexOf(current) + 1) % order.length]);
  }

  // The template renders the project default; a stored choice wins over it.
  set(stored() || root.dataset.theme || "auto");

  window.djadminTheme = { set: set, cycle: cycle, current: function () { return root.dataset.theme; } };

  /* --- Sidebar mode: expanded | mini | hidden ---------------------------
   * Applied here, in <head>, for the same reason as the theme: so the shell
   * is laid out correctly on the very first frame.
   */
  var SIDEBAR_KEY = "djadmin.sidebar.mode";
  var SIDEBAR_MODES = ["expanded", "mini", "hidden"];
  var sidebarAnimationTimer = null;

  function animateSidebar() {
    root.classList.add("dj-animating");
    clearTimeout(sidebarAnimationTimer);
    sidebarAnimationTimer = setTimeout(function () {
      root.classList.remove("dj-animating");
    }, 320);
  }

  function setSidebar(mode) {
    if (SIDEBAR_MODES.indexOf(mode) === -1) {
      mode = "expanded";
    }
    root.dataset.sidebar = mode;
    try {
      localStorage.setItem(SIDEBAR_KEY, mode);
    } catch (e) { /* ignore */ }
    return mode;
  }

  function cycleSidebar() {
    var current = root.dataset.sidebar || "expanded";
    animateSidebar();
    return setSidebar(SIDEBAR_MODES[(SIDEBAR_MODES.indexOf(current) + 1) % SIDEBAR_MODES.length]);
  }

  /* The button is a two-state toggle: expanded <-> the collapsed mode chosen by
   * DJADMIN["SIDEBAR_TOGGLE"] ("mini" by default, "hidden" to close fully). */
  function toggleSidebar() {
    var collapsed = root.dataset.sidebarToggle === "hidden" ? "hidden" : "mini";
    var current = root.dataset.sidebar || "expanded";
    animateSidebar();
    return setSidebar(current === "expanded" ? collapsed : "expanded");
  }

  var storedSidebar = null;
  try {
    storedSidebar = localStorage.getItem(SIDEBAR_KEY);
  } catch (e) { /* ignore */ }
  root.dataset.sidebar =
    SIDEBAR_MODES.indexOf(storedSidebar) === -1 ? (root.dataset.sidebar || "expanded") : storedSidebar;

  window.djadminSidebar = {
    set: setSidebar,
    toggle: toggleSidebar,
    cycle: cycleSidebar,
    modes: SIDEBAR_MODES,
    current: function () { return root.dataset.sidebar; },
  };
})();
