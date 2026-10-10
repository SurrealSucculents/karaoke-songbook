/* Temporary scroll test for the songbook (lab.html, not linked from the site). It records what
   the page sees while someone scrolls on a phone: hitches in the frame rate, and what changes
   when the scroll direction flips (Safari's toolbar, safe areas, the viewport, element sizes).
   Switches turn the suspects off one at a time. Results stay on this phone (localStorage). */
(() => {
"use strict";

const KEY = "mdk-lab";
const MODES = [
  ["ownscroll", "Keep Chrome's toolbars still", "Only the songs scroll, in their own area, so the page itself never scrolls and Chrome leaves its toolbars where they are. (The page reloads.)"],
  ["noshut", "Header never shuts", "The tabs and filters stay where they are; nothing slides."],
  ["instant", "Header without the slide", "It still shuts and opens, but in one step."],
  ["oldglow", "Old background glow", "Brings back the glow that resized with the window (and so with the browser's toolbar)."],
  ["olddock", "Old dates strip", "Brings back the dates strip that grew and shrank with the room for the home bar."],
  ["nobg", "No background glow", "Hides the pink and blue glow behind the list."],
  ["nodock", "No dates strip", "Hides the dates along the bottom."],
  ["noglow", "No Tonight pulse", "Stops the pulsing glow on tonight's date."],
  ["nologo", "No logo picture", "Hides the logo picture and the colour on “Karaoke”."],
];

let store;
try { store = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { store = {}; }
store.modes = store.modes || {};
store.runs = store.runs || [];
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch {} };

const root = document.documentElement;
const LAB = window.LAB = {};
const $ = id => document.getElementById(id);
const now = () => performance.now();
const r1 = n => Math.round(n * 10) / 10;

/* ---------------------------------------------------------------- switches */

const css = document.createElement("style");
css.textContent = `
html.lab-instant .more,html.lab-instant .chev{transition:none!important}
html.lab-oldglow body::before{bottom:0!important;height:auto!important}
html.lab-olddock .dock{transform:none!important;padding-bottom:calc(6px + env(safe-area-inset-bottom))!important}
html.lab-olddock .dock::after{display:none!important}
html.lab-nobg body::before{display:none!important}
html.lab-nodock #dock{display:none!important}
html.lab-noglow .night.now::after{display:none!important;animation:none!important}
html.lab-nologo .bar .logo{display:none!important}
html.lab-nologo .bar .mark em{background:none!important;color:var(--part-a)!important}
.lab-probe{position:absolute;left:0;top:0;width:1px;height:0;visibility:hidden;pointer-events:none}
.lab-btn{position:fixed;left:10px;bottom:calc(var(--lab-dock,64px) + 10px);z-index:31;min-height:34px;padding:0 12px;
  border:1px solid var(--edge);border-radius:999px;background:var(--riser);color:var(--ink);font:600 13px/1 var(--ui)}
.lab{position:fixed;inset:0;z-index:60;overflow:auto;background:rgba(8,4,15,.97);color:var(--ink);
  padding:calc(16px + env(safe-area-inset-top)) 16px calc(24px + env(safe-area-inset-bottom));font:15px/1.4 var(--ui)}
.lab h2{margin:0 0 6px;font-size:22px}
.lab p{margin:0 0 12px;color:var(--dim);font-size:14px}
.lab .sw{display:block;width:100%;text-align:left;margin:0 0 8px;padding:10px 12px;border:1px solid var(--rail);border-radius:12px;
  background:transparent;color:var(--ink);font:600 15px/1.3 var(--ui)}
.lab .sw small{display:block;font-weight:400;font-size:13px;color:var(--dim)}
.lab .sw .on{display:none;float:right;font-size:12px;color:var(--part-a)}
.lab .sw[aria-pressed="true"]{border-color:var(--part-a);background:rgba(237,31,97,.14)}
.lab .sw[aria-pressed="true"] .on{display:inline}
.lab pre{white-space:pre-wrap;font:12px/1.45 var(--num);background:var(--riser);border:1px solid var(--rail);border-radius:12px;
  padding:10px;margin:8px 0 12px;color:var(--ink)}
.lab .row2{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.lab .row2 button{flex:1;min-height:44px;border:1px solid var(--edge);border-radius:12px;background:var(--lift);color:var(--ink);
  font:600 15px/1 var(--ui)}
.lab .row2 button.yes{border-color:#3CCB7F}.lab .row2 button.no{border-color:var(--part-a)}
`;
document.head.appendChild(css);

const probes = {};
for (const [name, value] of [["sat", "env(safe-area-inset-top)"], ["sab", "env(safe-area-inset-bottom)"]]) {
  const el = document.createElement("div");
  el.className = "lab-probe";
  el.style.paddingTop = value;
  document.body.appendChild(el);
  probes[name] = el;
}
const insetNow = name => parseFloat(getComputedStyle(probes[name]).paddingTop) || 0;

function applyModes() {
  for (const [k] of MODES) {
    LAB[k] = !!store.modes[k];
    root.classList.toggle("lab-" + k, LAB[k]);
  }
  // The old dates strip grew with the home bar's room, and the page re-fitted to it on every resize.
  if (LAB.olddock) addEventListener("resize", refitDock); else removeEventListener("resize", refitDock);
  refitDock();
  if (LAB.noshut) $("chev")?.click();
}
// The page re-fits its bottom padding to the dates strip only when the width changes; nudge it.
function refitDock() {
  const dock = $("dock");
  if ($("app").hidden || dock.hidden) return;
  padBox().style.paddingBottom = `calc(${dock.offsetHeight}px + ${LAB.olddock ? "0px" : "max(34px, env(safe-area-inset-bottom))"})`;
}
// In own-scroll mode the songs scroll inside #songs, which also carries the header and dock room.
function padBox() { return root.classList.contains("own-scroll") ? $("songs") : $("app"); }
applyModes();

/* ---------------------------------------------------------------- recording */

let frames = [];    // [time, scrollY], null marks a pause between scrolls
let dirs = [];      // {t, down}
let toggles = [];   // {t, shut}
let events = [];    // {t, k, v}
let startedAt = now();
const ev = (k, v) => events.push({t: now(), k, v});

let looping = false, lastScroll = 0;
let lastY = null, runDir = 0, runLen = 0, pending = null;
// In own-scroll mode the songs scroll inside #songs, not the page.
const sc = root.classList.contains("own-scroll") ? $("songs") : null;
function tick(t) {
  const y = sc ? sc.scrollTop : scrollY;
  frames.push([t, y]);
  if (lastY !== null && y !== lastY) {
    const d = Math.sign(y - lastY), step = Math.abs(y - lastY);
    if (d === runDir) {
      runLen += step;
      if (pending && runLen >= 16) { dirs.push(pending); pending = null; }
    } else {
      pending = runDir && runLen >= 40 ? {t, down: d > 0} : null;
      runDir = d; runLen = step;
    }
  }
  lastY = y;
  if (now() - lastScroll < 700) requestAnimationFrame(tick);
  else { looping = false; frames.push(null); }
}
(sc || window).addEventListener("scroll", () => {
  lastScroll = now();
  if (!looping) { looping = true; requestAnimationFrame(tick); }
}, {passive: true});

const topEl = $("top");
let wasShut = topEl.classList.contains("collapsed");
new MutationObserver(() => {
  const s = topEl.classList.contains("collapsed");
  if (s !== wasShut) { wasShut = s; toggles.push({t: now(), shut: s}); }
}).observe(topEl, {attributes: true, attributeFilter: ["class"]});
new MutationObserver(() => ev("bar-var", topEl.style.getPropertyValue("--bar-h")))
  .observe(topEl, {attributes: true, attributeFilter: ["style"]});
new MutationObserver(() => ev("app-pad", `${padBox().style.paddingTop} / ${padBox().style.paddingBottom}`))
  .observe(padBox(), {attributes: true, attributeFilter: ["style"]});

addEventListener("resize", e => { if (e.isTrusted) ev("resize", `${innerWidth}×${innerHeight}`); });
const vv = window.visualViewport;
let vvLast = "";
const vvLog = () => {
  const s = `${Math.round(vv.height)} at ${Math.round(vv.offsetTop)}`;
  if (s !== vvLast) { vvLast = s; ev("viewport", s); }
};
vv?.addEventListener("resize", vvLog);
vv?.addEventListener("scroll", vvLog);

const sizeOf = e => Math.round(e.borderBoxSize?.[0]?.blockSize ?? e.target.getBoundingClientRect().height);
// (#app and #top aren't watched for size: the page's own ResizeObserver resizes them, and
// their padding changes show up as app-pad and bar-var above.)
const watched = new Map([[probes.sat, "safe-top"], [probes.sab, "safe-bottom"], [$("bar"), "logo-row"], [$("dock"), "dates-strip"]]);
const lastSize = new Map();
const sizer = new ResizeObserver(entries => {
  for (const e of entries) {
    const name = watched.get(e.target), h = sizeOf(e);
    // Keep the Test button above the dates strip (outside this callback, so it can't loop).
    if (name === "dates-strip") requestAnimationFrame(() => root.style.setProperty("--lab-dock", h + "px"));
    if (lastSize.get(name) === h) continue;
    if (lastSize.has(name)) ev(name, h);
    lastSize.set(name, h);
  }
});
for (const el of watched.keys()) if (el) sizer.observe(el, {box: "border-box"});

/* ---------------------------------------------------------------- report */

function device() {
  const ua = navigator.userAgent;
  const ios = (ua.match(/OS (\d+)_(\d+)(?:_(\d+))?/) || []).slice(1).filter(Boolean).join(".");
  const browser = /CriOS/.test(ua) ? "Chrome" : /FxiOS/.test(ua) ? "Firefox" : /EdgiOS/.test(ua) ? "Edge" : /Safari/.test(ua) ? "Safari" : "other";
  const home = navigator.standalone || matchMedia("(display-mode: standalone)").matches;
  return `${ios ? "iOS " + ios : ua.slice(0, 60)} · ${browser}${home ? " (Home Screen)" : ""} · ` +
    `${screen.width}×${screen.height} @${devicePixelRatio}x · window ${innerWidth}×${innerHeight}`;
}

function summarise() {
  const dts = [];
  for (let i = 1; i < frames.length; i++) if (frames[i] && frames[i - 1]) dts.push([frames[i - 1][0], frames[i][0] - frames[i - 1][0]]);
  const sorted = dts.map(d => d[1]).sort((a, b) => a - b);
  const med = sorted.length ? sorted[sorted.length >> 1] : 16.7;
  const lim = Math.max(med * 1.5, med + 6);
  const near = t => dirs.some(d => t >= d.t - 100 && t < d.t + 600);
  const c = {near: {n: 0, ms: 0, h: 0, max: 0}, far: {n: 0, ms: 0, h: 0, max: 0}};
  for (const [t, dt] of dts) {
    const k = near(t) ? c.near : c.far;
    k.n++; k.ms += dt; k.max = Math.max(k.max, dt);
    if (dt > lim) k.h++;
  }
  // what the page saw within a moment of each direction change
  const seen = new Map();
  for (const d of dirs) {
    const kinds = new Set();
    for (const e of events) {
      if (e.t < d.t - 150 || e.t > d.t + 900) continue;
      kinds.add(e.k);
      const s = seen.get(e.k) || {n: 0, values: new Set()};
      if (s.values.size < 6) s.values.add(String(e.v));
      seen.set(e.k, s);
    }
    for (const k of kinds) seen.get(k).n++;
  }
  const away = new Map();
  for (const e of events) if (!dirs.some(d => e.t >= d.t - 150 && e.t <= d.t + 900)) away.set(e.k, (away.get(e.k) || 0) + 1);
  return {med, lim, c, seen, away, shuts: toggles.filter(g => g.shut).length, opens: toggles.filter(g => !g.shut).length};
}

function modesOn() { return MODES.filter(([k]) => LAB[k]).map(([k]) => k).join("+") || "as live"; }

function reportText() {
  const s = summarise();
  const rate = k => k.ms ? `${k.h} in ${r1(k.ms / 1000)} s` : "none";
  const lines = [
    `Songbook scroll test · ${new Date().toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit"})}`,
    device(),
    `Switches on: ${modesOn()}`,
    `Safe areas now: top ${insetNow("sat")}, bottom ${insetNow("sab")}`,
    `Scrolled for ${r1((s.c.near.ms + s.c.far.ms) / 1000)} s, frame time ${r1(s.med)} ms`,
    `Direction changes: ${dirs.length} (header shut ${s.shuts}, opened ${s.opens})`,
    `Hitches (frames over ${Math.round(s.lim)} ms):`,
    `  at a direction change: ${rate(s.c.near)}, worst ${Math.round(s.c.near.max)} ms`,
    `  any other time:        ${rate(s.c.far)}, worst ${Math.round(s.c.far.max)} ms`,
    `Seen at direction changes (of ${dirs.length}):`,
  ];
  if (!s.seen.size) lines.push("  nothing");
  for (const [k, v] of s.seen) lines.push(`  ${k.padEnd(12)} ${v.n}×  ${[...v.values].join(", ")}`);
  if (s.away.size) lines.push(`Seen at other times: ${[...s.away].map(([k, n]) => `${k} ${n}×`).join(", ")}`);
  if (store.runs.length) {
    lines.push("Tests so far:");
    for (const r of store.runs) lines.push(`  ${r.verdict.padEnd(9)} ${r.modes} · ${r.dirs} changes · hitches ${r.near} near / ${r.far} other`);
  }
  return lines.join("\n");
}

function reset() {
  frames = []; dirs = []; toggles = []; events = []; startedAt = now();
  lastY = null; runDir = 0; runLen = 0; pending = null;
}
// Start afresh once the songbook has opened, so its first layout isn't counted.
new MutationObserver((_, mo) => {
  if (!$("app").hidden) { mo.disconnect(); requestAnimationFrame(refitDock); setTimeout(reset, 1500); }
}).observe($("app"), {attributes: true, attributeFilter: ["hidden"]});

/* ---------------------------------------------------------------- panel */

const btn = document.createElement("button");
btn.type = "button";
btn.className = "lab-btn";
btn.textContent = "Test";
document.body.appendChild(btn);

let panel = null;
function openPanel() {
  panel = document.createElement("section");
  panel.className = "lab";
  panel.setAttribute("role", "dialog");
  const s = summarise();
  panel.innerHTML = `<h2>Scroll test</h2>
    <p>Close this, then scroll down and back up through the songs 8–10 times, the way you normally would.
    Come back here, tap Smooth or Stutters, then try another switch. When you're done, tap Copy and paste it into the chat
    (or take a screenshot).</p>
    <div class="row2"><button type="button" class="yes" data-v="Smooth">Smooth</button>
      <button type="button" class="no" data-v="Stutters">Stutters</button></div>
    <pre></pre>
    <div class="row2"><button type="button" data-a="copy">Copy</button><button type="button" data-a="close">Close</button></div>
    <p>Switches (each starts a fresh recording):</p>
    ${MODES.map(([k, name, note]) => `<button type="button" class="sw" data-k="${k}" aria-pressed="${!!LAB[k]}">${name}<span class="on">ON</span><small>${note}</small></button>`).join("")}
    <div class="row2"><button type="button" data-a="clear">Forget all tests</button></div>`;
  panel.querySelector("pre").textContent = reportText();
  document.body.appendChild(panel);
  document.body.style.overflow = "hidden";
  panel.addEventListener("click", async e => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.v) {
      store.runs.push({verdict: b.dataset.v, modes: modesOn(), dirs: dirs.length, near: s.c.near.h, far: s.c.far.h});
      save(); reset();
      panel.querySelector("pre").textContent = reportText();
    } else if (b.dataset.k) {
      store.modes[b.dataset.k] = !store.modes[b.dataset.k];
      save();
      // The page picks its scrolling once, as it starts.
      if (b.dataset.k === "ownscroll") { location.reload(); return; }
      applyModes(); reset();
      panel.querySelectorAll(".sw").forEach(x => x.setAttribute("aria-pressed", !!LAB[x.dataset.k]));
      panel.querySelector("pre").textContent = reportText();
    } else if (b.dataset.a === "copy") {
      const text = reportText();
      try { await navigator.clipboard.writeText(text); b.textContent = "Copied"; } catch { window.prompt("Copy this", text); }
    } else if (b.dataset.a === "clear") {
      store.runs = []; save(); reset();
      panel.querySelector("pre").textContent = reportText();
    } else if (b.dataset.a === "close") closePanel();
  });
}
function closePanel() {
  panel?.remove(); panel = null;
  document.body.style.overflow = "";
}
btn.addEventListener("click", () => panel ? closePanel() : openPanel());
})();
