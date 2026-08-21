/*!
 * djadmin — interaction layer for the modern Django admin UI.
 *
 * Deliberately dependency-free and additive: every feature degrades to plain
 * server-rendered HTML if this file fails to load. Django's own admin scripts
 * (actions.js, inlines.js, calendar, select2) keep working untouched.
 */
(function () {
  "use strict";

  var doc = document;
  var body = doc.body;
  var STORE = {
    sidebar: "djadmin.sidebar.mode",
    navGroups: "djadmin.nav.closed",
    filters: "djadmin.filters.open",
  };

  function $(selector, scope) { return (scope || doc).querySelector(selector); }
  function $$(selector, scope) { return Array.prototype.slice.call((scope || doc).querySelectorAll(selector)); }

  function readStore(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (e) { return fallback; }
  }
  function writeStore(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  function isTyping(event) {
    var el = event.target;
    if (!el || !el.tagName) { return false; }
    var tag = el.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || el.isContentEditable;
  }

  function icon(name, extra) {
    return '<svg class="dj-icon dj-icon--sm ' + (extra || "") + '" aria-hidden="true"><use href="#dji-' +
      String(name || "box").replace(/[^a-z-]/g, "") + '"></use></svg>';
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  var isMobile = function () { return window.matchMedia("(max-width: 960px)").matches; };

  /* ----------------------------------------------------------------
   * Sidebar
   * ---------------------------------------------------------------- */
  function initSidebar() {
    var shell = $("#dj-shell");
    if (!shell) { return; }

    function toggle() {
      if (isMobile()) {
        // On small screens the sidebar is an overlay drawer: open or closed.
        shell.classList.toggle("is-sidebar-open");
      } else if (window.djadminSidebar) {
        // On desktop: expanded <-> collapsed (icon rail or fully closed,
        // per DJADMIN["SIDEBAR_TOGGLE"]).
        window.djadminSidebar.toggle();
      }
    }

    $$("[data-dj-sidebar-toggle]").forEach(function (el) {
      el.addEventListener("click", function (event) { event.preventDefault(); toggle(); });
    });

    window.djadminToggleSidebar = toggle;

    // Collapsible app groups, remembered between page loads. With
    // DJADMIN["NAV_ACCORDION"] on, only one group stays open at a time.
    var nav = $(".dj-nav");
    var accordion = !!nav && nav.getAttribute("data-accordion") === "1";
    var closed = readStore(STORE.navGroups, []);
    var groups = $$(".dj-nav-group");

    function titleOf(group) {
      return (($(".dj-nav-group-title", group) || {}).textContent || "").trim();
    }

    function setOpen(group, open) {
      group.classList.toggle("is-open", open);
      var toggler = $("[data-dj-nav-toggle]", group);
      if (toggler) { toggler.setAttribute("aria-expanded", open ? "true" : "false"); }
    }

    groups.forEach(function (group) {
      if (closed.indexOf(titleOf(group)) !== -1) { setOpen(group, false); }
    });

    if (accordion) {
      // Keep the group containing the current page open, close the rest.
      var active = groups.filter(function (group) { return !!$(".dj-nav-link.is-active", group); });
      if (active.length) {
        groups.forEach(function (group) { setOpen(group, group === active[0]); });
      }
    }

    groups.forEach(function (group) {
      var toggler = $("[data-dj-nav-toggle]", group);
      if (!toggler) { return; }
      toggler.addEventListener("click", function () {
        var open = !group.classList.contains("is-open");
        if (accordion && open) {
          groups.forEach(function (other) { if (other !== group) { setOpen(other, false); } });
        }
        setOpen(group, open);
        var list = accordion ? [] : readStore(STORE.navGroups, []);
        if (accordion) {
          groups.forEach(function (other) {
            if (!other.classList.contains("is-open")) { list.push(titleOf(other)); }
          });
        } else {
          var index = list.indexOf(titleOf(group));
          if (open && index !== -1) { list.splice(index, 1); }
          if (!open && index === -1) { list.push(titleOf(group)); }
        }
        writeStore(STORE.navGroups, list);
      });
    });
  }

  /* ----------------------------------------------------------------
   * Copy-to-clipboard buttons (recovery codes, secrets)
   * ---------------------------------------------------------------- */
  function initCopy() {
    $$("[data-dj-copy]").forEach(function (button) {
      button.addEventListener("click", function () {
        var target = $(button.getAttribute("data-dj-copy"));
        if (!target || !navigator.clipboard) { return; }
        var text = Array.prototype.map
          .call(target.children.length ? target.children : [target], function (node) {
            return node.textContent.trim();
          })
          .join("\n");
        navigator.clipboard.writeText(text).then(function () {
          if (window.djadminToast) { window.djadminToast("Copied to clipboard.", "success"); }
        });
      });
    });
  }

  /* ----------------------------------------------------------------
   * Theme toggle + user menu
   * ---------------------------------------------------------------- */
  function initChrome() {
    $$("[data-dj-theme-toggle]").forEach(function (el) {
      el.addEventListener("click", function () {
        if (window.djadminTheme) { window.djadminTheme.cycle(); }
      });
    });

    $$("[data-dj-menu]").forEach(function (menu) {
      var button = $("[data-dj-menu-btn]", menu);
      if (!button) { return; }
      button.addEventListener("click", function (event) {
        event.stopPropagation();
        var open = menu.classList.toggle("is-open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      });
      doc.addEventListener("click", function (event) {
        if (!menu.contains(event.target)) {
          menu.classList.remove("is-open");
          button.setAttribute("aria-expanded", "false");
        }
      });
      doc.addEventListener("keydown", function (event) {
        if (event.key === "Escape") { menu.classList.remove("is-open"); }
      });
    });
  }

  /* ----------------------------------------------------------------
   * Toasts
   * ---------------------------------------------------------------- */
  function initToasts() {
    var host = $("#dj-toasts");
    if (!host) { return; }

    function dismiss(toast) {
      toast.classList.add("is-leaving");
      setTimeout(function () { toast.remove(); }, 220);
    }

    $$(".dj-toast", host).forEach(function (toast) {
      var close = $("[data-dj-toast-close]", toast);
      if (close) { close.addEventListener("click", function () { dismiss(toast); }); }
      if (!toast.classList.contains("dj-toast--error")) {
        setTimeout(function () { dismiss(toast); }, 6000);
      }
    });

    /** Public helper so project code can raise a toast without a page load. */
    window.djadminToast = function (text, level) {
      var toast = doc.createElement("div");
      toast.className = "dj-toast dj-toast--" + (level || "info");
      toast.innerHTML = '<span class="dj-toast-icon">' + icon(level === "error" ? "alert" : "check") + "</span>" +
        '<span class="dj-toast-text">' + escapeHtml(text) + "</span>" +
        '<button type="button" class="dj-toast-close" aria-label="Close">' + icon("x", "dj-icon--xs") + "</button>";
      host.appendChild(toast);
      $(".dj-toast-close", toast).addEventListener("click", function () { dismiss(toast); });
      if (level !== "error") { setTimeout(function () { dismiss(toast); }, 6000); }
      return toast;
    };
  }

  /* ----------------------------------------------------------------
   * Changelist: filters panel and bulk-selection bar
   * ---------------------------------------------------------------- */
  function initChangelist() {
    var changelist = $(".dj-changelist");
    if (changelist) {
      var model = changelist.getAttribute("data-model") || "";
      var openFilters = readStore(STORE.filters, {});
      var hasActiveChips = !!$(".dj-chips");
      var shouldOpen = openFilters[model] !== undefined ? openFilters[model] : (hasActiveChips && !isMobile());

      function setFilters(open) {
        changelist.classList.toggle("is-filters-open", open);
        $$("[data-dj-filters-toggle]").forEach(function (el) {
          if (el.hasAttribute("aria-expanded")) { el.setAttribute("aria-expanded", open ? "true" : "false"); }
        });
        openFilters[model] = open;
        writeStore(STORE.filters, openFilters);
      }

      setFilters(!!shouldOpen);
      $$("[data-dj-filters-toggle]").forEach(function (el) {
        el.addEventListener("click", function (event) {
          event.preventDefault();
          setFilters(!changelist.classList.contains("is-filters-open"));
        });
      });
      window.djadminToggleFilters = function () {
        setFilters(!changelist.classList.contains("is-filters-open"));
      };
    }

    // Reveal the floating action bar as soon as anything is selected.
    var table = $("#result_list");
    if (!table) { return; }
    function sync() {
      var any = $$("tr input.action-select", table).some(function (box) { return box.checked; });
      body.classList.toggle("dj-has-selection", any);
    }
    table.addEventListener("change", sync);
    var toggleAll = $("#action-toggle");
    if (toggleAll) { toggleAll.addEventListener("change", sync); }
    window.addEventListener("pageshow", sync);
    sync();
  }

  /* ----------------------------------------------------------------
   * Change form: warn before losing unsaved edits
   * ---------------------------------------------------------------- */
  function initFormGuard() {
    var form = $("form.dj-form");
    if (!form) { return; }
    var dirty = false;
    var submitting = false;

    form.addEventListener("change", function () { dirty = true; });
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("submit", function () { submitting = true; });

    window.addEventListener("beforeunload", function (event) {
      if (dirty && !submitting) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  /* ----------------------------------------------------------------
   * Command palette
   * ---------------------------------------------------------------- */
  function initPalette() {
    var palette = $("#dj-palette");
    if (!palette) { return; }

    var input = $("#dj-palette-input", palette);
    var results = $("#dj-palette-results", palette);
    var endpoint = palette.getAttribute("data-endpoint");
    var timer = null;
    var items = [];
    var cursor = 0;
    var lastQuery = null;
    var cache = {};

    function open() {
      palette.hidden = false;
      body.style.overflow = "hidden";
      input.value = "";
      input.focus();
      render(cache[""] || null, "");
      search("");
    }

    function close() {
      palette.hidden = true;
      body.style.overflow = "";
    }

    function move(delta) {
      if (!items.length) { return; }
      items[cursor] && items[cursor].classList.remove("is-active");
      cursor = (cursor + delta + items.length) % items.length;
      items[cursor].classList.add("is-active");
      items[cursor].scrollIntoView({ block: "nearest" });
    }

    function group(label, rows) {
      if (!rows.length) { return ""; }
      return '<div class="dj-palette-group">' + escapeHtml(label) + "</div>" + rows.join("");
    }

    function row(entry, meta) {
      return '<a class="dj-palette-item" href="' + escapeHtml(entry.url) + '">' +
        icon(entry.icon) +
        '<span class="dj-palette-item-label">' + escapeHtml(entry.label) + "</span>" +
        (meta ? '<span class="dj-palette-item-meta">' + escapeHtml(meta) + "</span>" : "") +
        "</a>";
    }

    function render(data, query) {
      if (!data) {
        results.innerHTML = '<p class="dj-palette-empty">Searching…</p>';
        return;
      }
      var html =
        group("Records", (data.objects || []).map(function (o) { return row(o, o.model); })) +
        group("Models", (data.models || []).map(function (m) { return row(m, m.app); })) +
        group("Sections", (data.apps || []).map(function (a) {
          return row({ url: a.url, label: a.label, icon: "layers" });
        }));

      results.innerHTML = html || '<p class="dj-palette-empty">Nothing matches “' + escapeHtml(query) + '”.</p>';
      items = $$(".dj-palette-item", results);
      cursor = 0;
      if (items.length) { items[0].classList.add("is-active"); }
    }

    function search(query) {
      if (!endpoint) {
        results.innerHTML = '<p class="dj-palette-empty">Search is unavailable on this admin site.</p>';
        return;
      }
      if (cache[query]) { render(cache[query], query); return; }
      lastQuery = query;
      fetch(endpoint + "?q=" + encodeURIComponent(query), {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (response) { return response.ok ? response.json() : Promise.reject(response.status); })
        .then(function (data) {
          cache[query] = data;
          if (lastQuery === query && !palette.hidden) { render(data, query); }
        })
        .catch(function () {
          results.innerHTML = '<p class="dj-palette-empty">Search failed. Try again.</p>';
        });
    }

    input.addEventListener("input", function () {
      var query = input.value.trim();
      clearTimeout(timer);
      timer = setTimeout(function () { search(query); }, 160);
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
      else if (event.key === "Enter") {
        if (items[cursor]) { event.preventDefault(); window.location.href = items[cursor].href; }
      } else if (event.key === "Escape") { close(); }
    });

    $$("[data-dj-palette-open]").forEach(function (el) {
      el.addEventListener("click", function (event) { event.preventDefault(); open(); });
    });
    $$("[data-dj-palette-close]", palette).forEach(function (el) {
      el.addEventListener("click", close);
    });

    window.djadminPalette = { open: open, close: close, isOpen: function () { return !palette.hidden; } };
  }

  /* ----------------------------------------------------------------
   * Shortcuts dialog
   * ---------------------------------------------------------------- */
  function initShortcutsDialog() {
    var dialog = $("#dj-shortcuts");
    if (!dialog) { return; }
    function open() { dialog.hidden = false; }
    function close() { dialog.hidden = true; }
    $$("[data-dj-shortcuts-open]").forEach(function (el) {
      el.addEventListener("click", function (event) { event.preventDefault(); open(); });
    });
    $$("[data-dj-shortcuts-close]", dialog).forEach(function (el) { el.addEventListener("click", close); });
    window.djadminShortcuts = { open: open, close: close, isOpen: function () { return !dialog.hidden; } };
  }

  /* ----------------------------------------------------------------
   * Delete confirmations in a dialog
   *
   * The confirmation is still Django's: we fetch its page, lift the
   * server-rendered card out of it and show that. Permissions, protected
   * relations and the deletion tree are all computed server-side, and the
   * actual delete is an ordinary form POST. Without JS, or if the fetch
   * fails, the link simply navigates as it always did.
   * ---------------------------------------------------------------- */
  function initConfirmModal() {
    var modal = $("#dj-confirm-modal");
    if (!modal) { return; }
    var box = $(".dj-modal-box", modal);
    var titleEl = $("#dj-modal-title", modal);
    var bodyEl = $("#dj-modal-body", modal);
    var lastFocused = null;

    function open() {
      lastFocused = doc.activeElement;
      modal.hidden = false;
      body.style.overflow = "hidden";
      box.focus();
    }

    function close() {
      modal.hidden = true;
      body.style.overflow = "";
      if (lastFocused && lastFocused.focus) { lastFocused.focus(); }
    }

    function loading(title) {
      titleEl.textContent = title || "Confirm";
      bodyEl.innerHTML = '<div class="dj-modal-loading">…</div>';
      open();
    }

    /** Show the confirmation carried by an HTML response. */
    function show(html, formAction) {
      var parsed = new DOMParser().parseFromString(html, "text/html");
      var card = parsed.querySelector(".dj-confirm");
      if (!card) { return false; }  // not a confirmation page (redirect, error)

      var heading = parsed.querySelector(".dj-title");
      titleEl.textContent = heading ? heading.textContent.trim() : "Confirm";
      bodyEl.innerHTML = card.innerHTML;

      // The fetched form posts to "" — which would mean *this* page. Point it
      // back at the URL it came from.
      var form = $("form", bodyEl);
      if (form && formAction) { form.setAttribute("action", formAction); }
      // "No, take me back" closes the dialog instead of walking history.
      $$(".cancel-link", bodyEl).forEach(function (link) {
        link.addEventListener("click", function (event) { event.preventDefault(); close(); });
      });
      var confirmButton = $('input[type="submit"], button[type="submit"]', bodyEl);
      if (confirmButton) { confirmButton.focus(); }
      return true;
    }

    function request(url, options, fallback) {
      var settings = Object.assign(
        { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } },
        options || {}
      );
      fetch(url, settings)
        .then(function (response) {
          if (!response.ok) { throw new Error(response.status); }
          return response.text();
        })
        .then(function (html) {
          if (!show(html, settings.method === "POST" ? null : url)) { fallback(); }
        })
        .catch(function () { fallback(); });
    }

    // Single object: the Delete link on a change form or a delete URL anywhere.
    doc.addEventListener("click", function (event) {
      var link = event.target.closest ? event.target.closest("a.deletelink") : null;
      if (!link || !link.href || event.metaKey || event.ctrlKey || event.shiftKey) { return; }
      event.preventDefault();
      loading(link.textContent.trim() || "Delete");
      request(link.href, null, function () { window.location.href = link.href; });
    });

    // Bulk action: intercept "delete_selected" before it navigates.
    var changelistForm = $("#changelist-form");
    if (changelistForm) {
      changelistForm.addEventListener("submit", function (event) {
        var action = changelistForm.querySelector("[name=action]");
        var submitter = event.submitter;
        if (!action || action.value !== "delete_selected") { return; }
        if (!submitter || submitter.name !== "index") { return; }
        if (!$$("tr input.action-select", changelistForm).some(function (b) { return b.checked; })) { return; }

        event.preventDefault();
        var data = new FormData(changelistForm);
        data.append("index", submitter.value || "0");
        loading("Delete");
        request(
          changelistForm.getAttribute("action") || window.location.href,
          { method: "POST", body: data },
          function () { changelistForm.submit(); }
        );
      });
    }

    $$("[data-dj-modal-close]", modal).forEach(function (el) { el.addEventListener("click", close); });
    doc.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) { close(); }
    });

    window.djadminConfirm = { open: open, close: close, isOpen: function () { return !modal.hidden; } };
  }

  /* ----------------------------------------------------------------
   * Analytics: auto-submitting range forms, and the "active now" poll
   * ---------------------------------------------------------------- */
  function initAutoSubmit() {
    $$("form[data-dj-autosubmit]").forEach(function (form) {
      form.addEventListener("change", function (event) {
        if (event.target.matches("select, input[type=date]")) { form.submit(); }
      });
    });
  }

  function initRealtime() {
    var host = $(".dj-analytics");
    var counter = $("[data-dj-realtime-count]");
    if (!host || !counter) { return; }
    var url = host.getAttribute("data-realtime-url");
    if (!url) { return; }

    function poll() {
      if (doc.hidden) { return; }  // no work while the tab is in the background
      fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (response) { return response.ok ? response.json() : null; })
        .then(function (data) {
          if (data && typeof data.active === "number") { counter.textContent = data.active; }
        })
        .catch(function () { /* a failed poll is not worth reporting */ });
    }

    setInterval(poll, 30000);
  }

  /* ----------------------------------------------------------------
   * Keyboard shortcuts
   * ---------------------------------------------------------------- */
  function initKeys() {
    doc.addEventListener("keydown", function (event) {
      var meta = event.metaKey || event.ctrlKey;

      if (meta && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (window.djadminPalette) { window.djadminPalette.open(); }
        return;
      }

      if (meta && event.key.toLowerCase() === "s") {
        var form = $("form.dj-form");
        var save = form && form.querySelector('[name="_save"]');
        if (save) { event.preventDefault(); save.click(); }
        return;
      }

      if (event.key === "Escape") {
        if (window.djadminPalette && window.djadminPalette.isOpen()) { window.djadminPalette.close(); }
        if (window.djadminShortcuts && window.djadminShortcuts.isOpen()) { window.djadminShortcuts.close(); }
        return;
      }

      if (isTyping(event) || meta || event.altKey) { return; }

      switch (event.key) {
        case "/":
          var searchbar = $("#searchbar");
          if (searchbar) { event.preventDefault(); searchbar.focus(); searchbar.select(); }
          else if (window.djadminPalette) { event.preventDefault(); window.djadminPalette.open(); }
          break;
        case "c": {
          var add = $("[data-dj-add-link]") || $(".dj-object-tools .addlink");
          if (add) { event.preventDefault(); window.location.href = add.href; }
          break;
        }
        case "f":
          if (window.djadminToggleFilters) { event.preventDefault(); window.djadminToggleFilters(); }
          break;
        case "[":
          if (window.djadminToggleSidebar) { event.preventDefault(); window.djadminToggleSidebar(); }
          break;
        case "{":  // shift+[ — cycle expanded / mini / hidden
          if (window.djadminSidebar) { event.preventDefault(); window.djadminSidebar.cycle(); }
          break;
        case "t":
          if (window.djadminTheme) { event.preventDefault(); window.djadminTheme.cycle(); }
          break;
        case "?":
          if (window.djadminShortcuts) { event.preventDefault(); window.djadminShortcuts.open(); }
          break;
        default:
          break;
      }
    });
  }

  function boot() {
    initSidebar();
    initChrome();
    initToasts();
    initChangelist();
    initFormGuard();
    initPalette();
    initShortcutsDialog();
    initCopy();
    initConfirmModal();
    initAutoSubmit();
    initRealtime();
    initKeys();
    doc.dispatchEvent(new CustomEvent("djadmin:ready"));
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
