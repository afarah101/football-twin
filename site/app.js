"use strict";
// Reads the precomputed files in data/. No distance maths runs here: twins and closeness come from the Build (Q23).

const SHOWN = 5;
const STORED = 10;
const MAX_RESULTS = 20;
// D30-12: plain English, one label per metric of the model.
const LABELS = {
  shots_per_90: "Shots per 90 minutes",
  xa_per_90: "Expected assists (xA) per 90",
  xg_buildup_per_90: "Build-up play (xGBuildup) per 90",
  npxg_per_shot: "Chance quality (xG per shot)",
  finishing: "Finishing (goals vs xG per shot)",
  six_yard_share: "Shots from the six-yard box",
  outside_box_share: "Shots from outside the box",
  header_share: "Headed shots",
  take_on_share: "Shots after beating a player",
  through_ball_share: "Shots after a through ball",
};
const PERCENTILE_SCALE = { low: 0, high: 100, origin: 0, digits: 0, label: "Fingerprint: percentile of each metric among all careers, from 0 to 100" };
const SVG = "http://www.w3.org/2000/svg";

const files = new Map();
let names = [];
let current = null;
let currentCareer = null;
let showAll = false;
let lastPick = null;  // the last player or season clicked: only it may render, so a slow earlier file never overwrites it

const byId = (id) => document.getElementById(id);
const fold = (text) => text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const seasonLabel = (season) => `${season}/${String((season + 1) % 100).padStart(2, "0")}`;
const seasonsLabel = (career) => career.first_season === career.last_season ? seasonLabel(career.first_season) : `${seasonLabel(career.first_season)}-${seasonLabel(career.last_season)}`;
const minutesLabel = (minutes) => `${minutes.toLocaleString("en-GB")} min`;
// Rounded down, so "closer than" never overstates.
const closenessLabel = (closeness, reference) => `closer than ${(Math.floor(closeness * 10) / 10).toFixed(1)}% ${reference}`;

async function readJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

async function cachedJson(path) {
  if (!files.has(path)) files.set(path, await readJson(`data/${path}`));
  return files.get(path);
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

function drawFingerprint(id, metrics, values, scale) {
  const rowHeight = 24, labelWidth = 250, half = 150, width = labelWidth + 2 * half + 50;
  const x = (value) => labelWidth + ((value - scale.low) / (scale.high - scale.low)) * 2 * half;
  const svg = svgElement("svg", { id, viewBox: `0 0 ${width} ${metrics.length * rowHeight + 20}`, role: "img", "aria-label": scale.label });
  svg.append(svgElement("line", { x1: x(scale.origin), x2: x(scale.origin), y1: 0, y2: metrics.length * rowHeight, class: "axis" }));
  metrics.forEach((metric, row) => {
    const value = values[metric], y = row * rowHeight;
    svg.append(svgElement("text", { x: labelWidth - 8, y: y + 16, "text-anchor": "end", class: "metric" }, LABELS[metric] || metric));
    svg.append(svgElement("rect", { class: `bar ${value < scale.origin ? "below" : "above"}`, x: Math.min(x(value), x(scale.origin)), y: y + 5, width: Math.abs(x(value) - x(scale.origin)), height: rowHeight - 10 }));
    svg.append(svgElement("text", { x: x(scale.high) + 8, y: y + 16, class: "value" }, value.toFixed(scale.digits)));
  });
  const scaleY = metrics.length * rowHeight + 14;
  [[scale.low, "start"], [(scale.low + scale.high) / 2, "middle"], [scale.high, "end"]].forEach(([value, anchor]) => svg.append(svgElement("text", { x: x(value), y: scaleY, "text-anchor": anchor, class: "scale" }, String(value))));
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

function showView(id) {
  byId("player").hidden = id !== "player";
  byId("career").hidden = id !== "career";
}

// #12: the Pool map, PCA on every Pool season. Points only: no axis is named.
let poolMap = null;
const MAP_SIZE = 360;

function drawMap(entry, content, twins) {
  if (!poolMap || !poolMap.points.length) return document.createTextNode("Map not available.");
  const xs = poolMap.points.map((point) => point[3]);
  const ys = poolMap.points.map((point) => point[4]);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const scale = (value, low, high) => 8 + ((value - low) / ((high - low) || 1)) * (MAP_SIZE - 16);
  const at = (point) => [scale(point[3], minX, maxX), MAP_SIZE - scale(point[4], minY, maxY)];
  const key = (league, season, playerId) => `${league}|${season}|${playerId}`;
  const twinKeys = new Set(twins.map((twin) => key(twin.league, twin.season, twin.player_id)));
  const own = key(content.league, content.season, entry.player_id);
  const svg = svgElement("svg", { id: "pool-map", viewBox: `0 0 ${MAP_SIZE} ${MAP_SIZE}`, role: "img",
    "aria-label": `Map of every attacker by style: ${entry.name} and ${twins.length} twins marked` });
  const marked = [];
  for (const point of poolMap.points) {
    const id = key(point[0], point[1], point[2]);
    const [x, y] = at(point);
    if (id === own || twinKeys.has(id)) marked.push([id === own ? "map-player" : "map-twin", x, y]);
    else svg.append(svgElement("circle", { cx: x, cy: y, r: 1.5, class: "map-point" }));
  }
  marked.sort((a, b) => (a[0] === "map-player") - (b[0] === "map-player"));  // the player on top
  for (const [cls, x, y] of marked) svg.append(svgElement("circle", { cx: x, cy: y, r: cls === "map-player" ? 6 : 4, class: cls }));
  return svg;
}

function renderTwins() {
  const list = byId("twins");
  const sameLeague = byId("same-league").checked;
  const twins = current.entry.twins[sameLeague ? "same_league" : "all_leagues"];
  list.replaceChildren(...twins.slice(0, showAll ? STORED : SHOWN).map((twin) => {
    const item = document.createElement("li");
    item.append(`${twin.name} · ${twin.league} ${seasonLabel(twin.season)} · ${minutesLabel(twin.minutes)} · ${closenessLabel(twin.closeness, sameLeague ? "of same-league pairs" : "of all pairs")}`);
    if (twin.small_sample) item.append(" ", smallSampleFlag());
    return item;
  }));
  if (!twins.length) list.replaceChildren(Object.assign(document.createElement("li"), { textContent: "No twins in this league." }));
  const more = byId("show-more");
  more.hidden = showAll || twins.length <= SHOWN;
  byId("map-box").replaceChildren(drawMap(current.entry, current.content, twins.slice(0, showAll ? STORED : SHOWN)));
}

// D30-13: one link per Pool PlayerSeason, so a two-stint season shows as two links (#11).
function seasonLinks(player) {
  return player.player_seasons.map((season) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${season.league} ${seasonLabel(season.season)} · ${minutesLabel(season.minutes)}`;
    button.addEventListener("click", () => pick({ player_id: player.player_id, name: player.name, file: season.file, career: false }));
    return button;
  });
}

function renderPlayer(content, entry) {
  current = { content, entry };
  showAll = false;
  byId("player-name").textContent = entry.name;
  const meta = byId("player-meta");
  meta.textContent = `${content.league} ${seasonLabel(content.season)} · ${entry.clubs.join(", ")} · ${minutesLabel(entry.minutes)}${entry.display_position ? ` · ${entry.display_position}` : ""}`;
  if (entry.small_sample) meta.append(" ", smallSampleFlag());
  // D30-14: percentiles from the Build, within this league-season.
  const label = `Percentile within ${content.league} ${seasonLabel(content.season)}, from 0 to 100`;
  byId("fingerprint-label").textContent = label;
  byId("fingerprint-box").replaceChildren(drawFingerprint("fingerprint", content.metrics, entry.percentiles, { ...PERCENTILE_SCALE, label }));
  const player = names.find((found) => found.player_id === entry.player_id);
  byId("player-seasons").replaceChildren(...(player ? seasonLinks(player) : []));
  byId("display-stats-box").replaceChildren(drawDisplayStats(entry.display_stats));
  renderTwins();
  showView("player");
}

function renderCareerTwins() {
  const twins = currentCareer.twins[byId("same-role").checked ? "same_role" : "all_roles"];
  const list = byId("career-twins");
  // D30-9: closeness is against all career pairs whichever list is shown, so the label never changes with the filter.
  list.replaceChildren(...twins.slice(0, showAll ? STORED : SHOWN).map((twin) => Object.assign(document.createElement("li"), {
    textContent: `${twin.name} · ${twin.role_group} · ${seasonsLabel(twin)} · ${minutesLabel(twin.minutes)} · ${closenessLabel(twin.closeness, "of all careers")}`,
  })));
  if (!twins.length) list.replaceChildren(Object.assign(document.createElement("li"), { textContent: "No other career in this role." }));
  byId("career-show-more").hidden = showAll || twins.length <= SHOWN;
}

function renderCareer(career) {
  currentCareer = career;
  showAll = false;
  byId("career-name").textContent = career.name;
  const count = career.season_count === 1 ? "1 season" : `${career.season_count} seasons`;
  byId("career-meta").textContent = `${career.role_group} · Seasons covered: ${seasonsLabel(career)} (${count}) · ${minutesLabel(career.minutes)}`;
  byId("career-fingerprint-box").replaceChildren(drawFingerprint("career-fingerprint", career.metrics, career.percentiles, PERCENTILE_SCALE));
  byId("career-seasons").replaceChildren(...seasonLinks(career));
  renderCareerTwins();
  showView("career");
}

async function pick(found) {
  lastPick = found;
  byId("status").textContent = "";
  try {
    // A player with a career opens the career view (#30 decision 3); any other opens the season view (D30-8).
    const content = await cachedJson(found.career ? `careers/${found.player_id}.json` : found.file);
    if (lastPick !== found) return;
    if (found.career) return renderCareer(content);
    const entry = content.player_seasons.find((player) => player.player_id === found.player_id);
    if (!entry) throw new Error(`${found.name} is missing from ${found.file}`);
    renderPlayer(content, entry);
  } catch (error) {
    if (lastPick === found) byId("status").textContent = `Could not load this ${found.career ? "career" : "season"}: ${error.message}`;
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
    // D30-13: one row per player; a career row names its role group.
    button.textContent = [entry.name, ...(entry.career ? [entry.role_group] : []), seasonsLabel(entry), minutesLabel(entry.minutes), entry.clubs.join(", ")].join(" · ");
    button.addEventListener("click", () => pick(entry));
    return button;
  }));
  byId("status").textContent = found.length ? "" : "No player found.";
}

async function start() {
  byId("metric-list").replaceChildren(...Object.values(LABELS).map((label) => Object.assign(document.createElement("li"), { textContent: label })));
  byId("search").addEventListener("input", search);
  byId("same-league").addEventListener("change", () => { showAll = false; renderTwins(); });
  byId("show-more").addEventListener("click", () => { showAll = true; renderTwins(); });
  byId("same-role").addEventListener("change", () => { showAll = false; renderCareerTwins(); });
  byId("career-show-more").addEventListener("click", () => { showAll = true; renderCareerTwins(); });
  readJson("data/map.json").then((found) => { poolMap = found; if (current) renderTwins(); }).catch(() => { poolMap = null; });
  try {
    names = await readJson("data/names.json");
  } catch (error) {
    byId("status").textContent = `Could not load the name index: ${error.message}`;
  }
}

start();
