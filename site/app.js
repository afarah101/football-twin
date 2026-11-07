"use strict";
// Reads the precomputed files in data/. No distance maths runs here: twins and closeness come from the Build (Q23).

const SHOWN = 5;
const STORED = 10;
const MAX_RESULTS = 20;
const LABELS = {
  shots_per_90: "Shots per 90",
  xa_per_90: "xA per 90",
  key_passes_per_90: "Key passes per 90",
  xg_buildup_per_90: "xGBuildup per 90",
  npxg_per_shot: "npxG per shot",
  six_yard_share: "Six-yard box shots",
  outside_box_share: "Outside box shots",
  header_share: "Headers",
  take_on_share: "Shots after TakeOn",
  through_ball_share: "Shots after Throughball",
};
const SVG = "http://www.w3.org/2000/svg";

const files = new Map();
let names = [];
let current = null;
let showAll = false;

const byId = (id) => document.getElementById(id);
const fold = (text) => text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const seasonLabel = (season) => `${season}/${String((season + 1) % 100).padStart(2, "0")}`;
const minutesLabel = (minutes) => `${minutes.toLocaleString("en-GB")} min`;
// Rounded down, so "closer than" never overstates.
const closenessLabel = (closeness) => `closer than ${(Math.floor(closeness * 10) / 10).toFixed(1)}% of all pairs`;

async function readJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

function svgElement(name, attributes, text) {
  const element = document.createElementNS(SVG, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  if (text !== undefined) element.textContent = text;
  return element;
}

function smallSampleFlag() {
  const flag = document.createElement("span");
  flag.className = "flag";
  flag.textContent = "small sample";
  return flag;
}

function drawFingerprint(metrics, profile) {
  const rowHeight = 24, labelWidth = 190, half = 150, width = labelWidth + 2 * half + 50;
  const svg = svgElement("svg", { id: "fingerprint", viewBox: `0 0 ${width} ${metrics.length * rowHeight + 20}`, role: "img", "aria-label": "Fingerprint: z-score of each metric within its league-season, from -3 to 3" });
  const centre = labelWidth + half;
  svg.append(svgElement("line", { x1: centre, x2: centre, y1: 0, y2: metrics.length * rowHeight, class: "axis" }));
  metrics.forEach((metric, row) => {
    const z = profile[metric], y = row * rowHeight;
    const length = (Math.abs(z) / 3) * half;
    svg.append(svgElement("text", { x: labelWidth - 8, y: y + 16, "text-anchor": "end" }, LABELS[metric] || metric));
    svg.append(svgElement("rect", { class: `bar ${z < 0 ? "below" : "above"}`, x: z < 0 ? centre - length : centre, y: y + 5, width: length, height: rowHeight - 10 }));
    svg.append(svgElement("text", { x: centre + half + 8, y: y + 16, class: "value" }, z.toFixed(2)));
  });
  const scaleY = metrics.length * rowHeight + 14;
  [[-3, centre - half, "start"], [0, centre, "middle"], [3, centre + half, "end"]].forEach(([value, x, anchor]) => svg.append(svgElement("text", { x, y: scaleY, "text-anchor": anchor, class: "scale" }, String(value))));
  return svg;
}

function drawDisplayStats(stats) {
  const rows = [["Goals", String(stats.goals)], ["Assists", String(stats.assists)], ["npG − npxG", `${stats.npg_minus_npxg >= 0 ? "+" : ""}${stats.npg_minus_npxg.toFixed(1)}`]];
  const svg = svgElement("svg", { id: "display-stats", viewBox: `0 0 360 ${rows.length * 28}`, role: "img", "aria-label": "Display stats, never part of the Fingerprint" });
  rows.forEach(([label, value], row) => {
    svg.append(svgElement("text", { x: 0, y: row * 28 + 20 }, label));
    svg.append(svgElement("text", { x: 200, y: row * 28 + 20, class: "value" }, value));
  });
  return svg;
}

function renderTwins() {
  const list = byId("twins");
  const twins = current.entry.twins[byId("same-league").checked ? "same_league" : "all_leagues"];
  list.replaceChildren(...twins.slice(0, showAll ? STORED : SHOWN).map((twin) => {
    const item = document.createElement("li");
    item.append(`${twin.name} · ${twin.league} ${seasonLabel(twin.season)} · ${minutesLabel(twin.minutes)} · ${closenessLabel(twin.closeness)}`);
    if (twin.small_sample) item.append(" ", smallSampleFlag());
    return item;
  }));
  if (!twins.length) list.replaceChildren(Object.assign(document.createElement("li"), { textContent: "No twins in this league." }));
  const more = byId("show-more");
  more.hidden = showAll || twins.length <= SHOWN;
}

function renderPlayer(content, entry) {
  current = { content, entry };
  showAll = false;
  byId("player-name").textContent = entry.name;
  const meta = byId("player-meta");
  meta.textContent = `${content.league} ${seasonLabel(content.season)} · ${entry.clubs.join(", ")} · ${minutesLabel(entry.minutes)}${entry.display_position ? ` · ${entry.display_position}` : ""}`;
  if (entry.small_sample) meta.append(" ", smallSampleFlag());
  byId("fingerprint-box").replaceChildren(drawFingerprint(content.metrics, entry.metric_profile));
  byId("display-stats-box").replaceChildren(drawDisplayStats(entry.display_stats));
  renderTwins();
  byId("player").hidden = false;
}

async function pick(found) {
  byId("status").textContent = "";
  try {
    if (!files.has(found.file)) files.set(found.file, await readJson(`data/${found.file}`));
    const content = files.get(found.file);
    const entry = content.player_seasons.find((player) => player.player_id === found.player_id);
    if (!entry) throw new Error(`${found.name} is missing from ${found.file}`);
    renderPlayer(content, entry);
  } catch (error) {
    byId("status").textContent = `Could not load this season: ${error.message}`;
  }
}

function search() {
  const query = fold(byId("search").value.trim());
  const results = byId("results");
  if (!query) return results.replaceChildren();
  const found = names.filter((entry) => fold(entry.name).includes(query)).slice(0, MAX_RESULTS);
  results.replaceChildren(...found.map((entry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "listitem");
    button.textContent = `${entry.name} · ${entry.league} ${seasonLabel(entry.season)} · ${entry.clubs.join(", ")} · ${minutesLabel(entry.minutes)}`;
    button.addEventListener("click", () => pick(entry));
    return button;
  }));
  byId("status").textContent = found.length ? "" : "No player found.";
}

async function start() {
  byId("search").addEventListener("input", search);
  byId("same-league").addEventListener("change", () => { showAll = false; renderTwins(); });
  byId("show-more").addEventListener("click", () => { showAll = true; renderTwins(); });
  try {
    names = await readJson("data/names.json");
  } catch (error) {
    byId("status").textContent = `Could not load the name index: ${error.message}`;
  }
}

start();
