/* Collapsible sidebar groups.

   "is there a way ... the left side bar menu collapsable. it is too much
   scrolling, group it by categories and i could expand or collapse"
   (2026-08-30). The categories were already there and every one of them
   was always open, so the drawer ran to about forty-five links and
   reaching Money meant scrolling past all of Knowledge, every time.

   A FILE rather than another inline block in _top_nav.html, for one
   reason: an inline script cannot be run by the jsdom harness, and this
   is exactly the sort of DOM surgery that source-reading tests cannot
   check. tests/js/nav_groups.test.js runs it against the real rendered
   page.

   Loaded with `defer` AFTER the inline highlightActiveNav() has marked
   the current page, because which group is open depends on it. */
(function collapsibleNavGroups(){
  const KEY = 'dp-nav-groups-v1';
  const nav = document.querySelector('.sidebar-nav');
  if (!nav) return;

  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (_) {}
  const remember = () => {
    try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (_) {}
  };

  const groups = [...nav.querySelectorAll('.nav-group')]
    .filter(g => !g.classList.contains('nav-footer') && g.querySelector('.nav-group-title'));
  if (!groups.length) return;

  const setOpen = (g, open) => {
    g.dataset.open = open ? '1' : '0';
    const btn = g.querySelector('.nav-group-title');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  let anyOpen = false;
  groups.forEach((g, i) => {
    const heading = g.querySelector('.nav-group-title');
    const name = (heading.textContent || 'Group ' + i).trim();
    const id = 'navgrp-' + name.toLowerCase().replace(/[^a-z0-9]+/g, '-');

    // Everything after the heading becomes the collapsible part.
    const items = document.createElement('div');
    items.className = 'nav-group-items';
    items.id = id;
    let node = heading.nextSibling;
    while (node) { const next = node.nextSibling; items.appendChild(node); node = next; }
    g.appendChild(items);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-group-title';
    btn.id = id + '-btn';
    btn.setAttribute('aria-controls', id);
    const chev = document.createElement('span');
    chev.className = 'nav-group-chev';
    chev.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.textContent = name;
    const count = document.createElement('span');
    count.className = 'nav-group-count';
    count.textContent = String(items.querySelectorAll('a').length);
    btn.append(chev, label, count);
    heading.replaceWith(btn);

    g.dataset.navName = name;
    const here = !!items.querySelector('a.active, a.match');
    if (here) g.dataset.here = '1';
    // ON A FRESH DEVICE, ONLY THE GROUP YOU ARE IN OPENS. An earlier
    // version also opened the first group, which meant two open at once
    // and half the point lost — and after the menu was regrouped, the
    // first group was rarely the one you were standing in. A page that
    // matches no group falls back to opening the first, below.
    const open = here || (Object.prototype.hasOwnProperty.call(saved, name)
      ? !!saved[name]
      : false);
    setOpen(g, open);
    anyOpen = anyOpen || open;

    btn.addEventListener('click', () => {
      const nowOpen = g.dataset.open !== '1';
      setOpen(g, nowOpen);
      saved[name] = nowOpen;
      remember();
    });
  });

  // A page that matches nothing must not leave every group shut — that
  // looks like a broken menu rather than a tidy one.
  if (!anyOpen) setOpen(groups[0], true);

  /* One control for "show me everything" / "put it all away", because
     hunting for a page you cannot name means opening several groups. */
  const all = document.createElement('button');
  all.type = 'button';
  all.className = 'nav-allbtn';
  /* "Everything is put away" means every group EXCEPT the one you are
     in, because collapse-all deliberately leaves that one open. Judging
     it by "no group is open" made the button read Collapse all straight
     after a collapse, and the next press collapsed again — a control
     that cannot undo itself. */
  const allShut = () =>
    groups.every(g => g.dataset.open !== '1' || g.dataset.here === '1');
  const paintAll = () => {
    all.textContent = allShut() ? 'Expand all' : 'Collapse all';
  };
  all.addEventListener('click', () => {
    const opening = allShut();
    groups.forEach(g => {
      // Collapse-all still leaves the group you are in open.
      const open = opening || g.dataset.here === '1';
      setOpen(g, open);
      if (g.dataset.navName) saved[g.dataset.navName] = open;
    });
    remember();
    paintAll();
  });
  paintAll();
  nav.prepend(all);
  groups.forEach(g => g.querySelector('.nav-group-title')
    .addEventListener('click', paintAll));
})();