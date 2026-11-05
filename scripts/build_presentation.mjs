#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "/Users/ahmad/Documents/Qeema Internship/Final Project";
const SKILL_DIR = "/Users/ahmad/.codex/plugins/cache/openai-primary-runtime/presentations/26.1030.10813/skills/presentations";
const RUNTIME_PYTHON = "/Users/ahmad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const buildDir = path.join(workspaceDir, ".presentation-build");
const previewDir = path.join(buildDir, "previews");
const FINAL_PPTX = path.join(workspaceDir, "output", "presentation", "nyc_mobility_final_presentation_v2.pptx");
const { finalizePresentation, resolvePresentationFont, applyPresentationChartFont } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href
);

const FONT = resolvePresentationFont();
const W = 1280;
const H = 720;
const C = {
  navy: "#12233F",
  blue: "#168AAD",
  cyan: "#69C6D4",
  orange: "#D97706",
  green: "#2F855A",
  ink: "#27364D",
  muted: "#607087",
  pale: "#E8F4FB",
  light: "#F5F8FC",
  line: "#D6E0EC",
  white: "#FFFFFF",
};

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, text, left, top, width, height, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: opts.fontSize ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.alignment ?? "left",
    verticalAlignment: opts.verticalAlignment ?? "middle",
  };
  return shape;
}

function addRect(slide, left, top, width, height, opts = {}) {
  return slide.shapes.add({
    geometry: opts.geometry ?? "roundRect",
    position: { left, top, width, height },
    fill: opts.fill ?? C.white,
    line: { style: "solid", fill: opts.line ?? C.line, width: opts.lineWidth ?? 1 },
  });
}

function addLine(slide, left, top, width, height, color = C.muted, lineWidth = 2) {
  return slide.shapes.add({
    geometry: "line",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: color, width: lineWidth },
  });
}

function addHeader(slide, title, subtitle, number) {
  addText(slide, title, 64, 38, 930, 54, { fontSize: 34, bold: true, color: C.navy });
  if (subtitle) addText(slide, subtitle, 66, 91, 1020, 32, { fontSize: 16, color: C.muted });
  addText(slide, String(number).padStart(2, "0"), 1160, 43, 54, 30, { fontSize: 14, bold: true, color: C.blue, alignment: "right" });
  addLine(slide, 64, 126, 1150, 0, C.line, 1);
}

function addKpi(slide, left, top, width, value, label, accent = C.blue) {
  addRect(slide, left, top, width, 132, { fill: C.white, line: C.line, lineWidth: 1.2 });
  addRect(slide, left, top, 7, 132, { geometry: "rect", fill: accent, line: accent, lineWidth: 0 });
  addText(slide, value, left + 28, top + 22, width - 44, 50, { fontSize: 31, bold: true, color: C.navy });
  addText(slide, label, left + 28, top + 76, width - 44, 32, { fontSize: 15, color: C.muted });
}

function styleChart(chart) {
  applyPresentationChartFont(chart, { fontFamily: FONT });
  return chart;
}

function note(slide, body) {
  slide.speakerNotes.text = `${body}\nSources: September 2026 Internship (Qeema).pdf; artifacts/analytics/*.csv; warehouse/nyc_mobility.duckdb; docs/technical_report.md.`;
  slide.speakerNotes.setVisible(true);
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.map((line) => {
    const cells = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [header, cells[index]]));
  });
}

const analyticsDir = path.join(workspaceDir, "artifacts", "analytics");
const monthly = parseCsv(await fs.readFile(path.join(analyticsDir, "01_monthly_trends.csv"), "utf8"));
const providers = parseCsv(await fs.readFile(path.join(analyticsDir, "02_provider_comparison.csv"), "utf8"));
const zones = parseCsv(await fs.readFile(path.join(analyticsDir, "03_top_pickup_zones.csv"), "utf8"));
const hourly = parseCsv(await fs.readFile(path.join(analyticsDir, "04_hourly_demand.csv"), "utf8"));
const boroughs = parseCsv(await fs.readFile(path.join(analyticsDir, "05_borough_comparison.csv"), "utf8"));
const sharing = parseCsv(await fs.readFile(path.join(analyticsDir, "09_shared_ride_analysis.csv"), "utf8"));

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

// 1 — Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addRect(slide, 0, 0, 20, H, { geometry: "rect", fill: C.blue, line: C.blue, lineWidth: 0 });
  addRect(slide, 20, 0, 7, H, { geometry: "rect", fill: C.orange, line: C.orange, lineWidth: 0 });
  addText(slide, "NYC Mobility\nAnalytics Platform", 86, 150, 720, 190, { fontSize: 52, bold: true, color: C.white });
  addText(slide, "411.7M accepted HVFHV trips · DuckDB · Airflow · Superset", 90, 365, 760, 48, { fontSize: 21, color: "#C8D8E8" });
  addText(slide, "January 2025 – August 2026", 90, 445, 430, 38, { fontSize: 18, bold: true, color: C.cyan });
  addText(slide, "Final presentation · 5 November 2026", 90, 610, 560, 30, { fontSize: 14, color: "#A8BACE" });
  addRect(slide, 932, 130, 250, 400, { fill: "#1C3559", line: "#315274", lineWidth: 1 });
  addText(slide, "20", 968, 176, 178, 70, { fontSize: 58, bold: true, color: C.orange, alignment: "center" });
  addText(slide, "official monthly files", 956, 244, 202, 36, { fontSize: 16, color: C.white, alignment: "center" });
  addLine(slide, 966, 305, 182, 0, "#45627F", 1);
  addText(slide, "10.042 GB", 962, 330, 190, 48, { fontSize: 28, bold: true, color: C.cyan, alignment: "center" });
  addText(slide, "verified source volume", 950, 378, 214, 32, { fontSize: 15, color: C.white, alignment: "center" });
  addLine(slide, 966, 435, 182, 0, "#45627F", 1);
  addText(slide, "0", 968, 458, 178, 42, { fontSize: 30, bold: true, color: "#70D6A0", alignment: "center" });
  addText(slide, "reconciliation difference", 944, 500, 226, 30, { fontSize: 14, color: C.white, alignment: "center" });
  note(slide, "Opening: a reproducible NYC HVFHV analytics platform built from the official project brief and verified production warehouse.");
}

// 2 — Outcome
{
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addHeader(slide, "A complete, reconciled analytical platform", "The project is ready for repeatable demonstration—not a one-off notebook.", 2);
  addKpi(slide, 64, 172, 268, "411,776,395", "raw source rows", C.orange);
  addKpi(slide, 352, 172, 268, "411,739,486", "accepted trips", C.blue);
  addKpi(slide, 640, 172, 268, "36,909", "quarantined records", C.green);
  addKpi(slide, 928, 172, 286, "0", "reconciliation difference", C.cyan);
  addText(slide, "What is now demonstrable", 68, 352, 420, 38, { fontSize: 24, bold: true, color: C.navy });
  const items = [
    ["Repeatable ETL", "Transactional monthly replacement with explicit quarantine reasons"],
    ["Operational orchestration", "Scheduled monthly DAG plus sequential historical backfill"],
    ["Measured performance", "Two optimizations, identical results, 187.8× and 43.7× median speedups"],
    ["Interactive delivery", "Read-only Superset dashboard recreated from repository code"],
  ];
  items.forEach(([title, body], index) => {
    const top = 407 + index * 62;
    addRect(slide, 68, top + 5, 10, 10, { geometry: "ellipse", fill: index % 2 ? C.orange : C.blue, line: "none", lineWidth: 0 });
    addText(slide, title, 96, top - 6, 260, 26, { fontSize: 17, bold: true, color: C.navy });
    addText(slide, body, 360, top - 6, 810, 34, { fontSize: 16, color: C.ink });
  });
  note(slide, "Lead with reconciliation, reproducibility, measured optimization, and repository-defined delivery.");
}

// 3 — Data and reconciliation
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "Official data, explicit quality outcomes", "20 NYC TLC HVFHV Parquet files cover January 2025 through August 2026.", 3);
  const table = slide.tables.add({
    rows: 5, columns: 2, left: 64, top: 174, width: 500, height: 330,
    values: [
      ["Outcome", "Rows"],
      ["Raw", "411,776,395"],
      ["Accepted", "411,739,486"],
      ["Quarantined", "36,909"],
      ["Difference", "0"],
    ],
    columnWidths: [285, 215],
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 2 }).assign({ fill: C.navy, textStyle: { typeface: FONT, color: C.white, fontSize: 17, bold: true }, margins: { left: 14, right: 14, top: 8, bottom: 8 } });
  table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 2 }).assign({ textStyle: { typeface: FONT, color: C.ink, fontSize: 17 }, margins: { left: 14, right: 14, top: 8, bottom: 8 } });
  addText(slide, "Quarantine is evidence, not deletion", 640, 176, 540, 42, { fontSize: 26, bold: true, color: C.navy });
  const reasons = [
    ["24,657", "inconsistent sharing flags"],
    ["12,237", "invalid trip durations"],
    ["17", "exact duplicate occurrences"],
  ];
  reasons.forEach(([value, label], index) => {
    const top = 248 + index * 92;
    addText(slide, value, 642, top, 170, 45, { fontSize: 30, bold: true, color: index === 0 ? C.orange : index === 1 ? C.blue : C.green });
    addText(slide, label, 818, top + 4, 350, 36, { fontSize: 17, color: C.ink });
  });
  addRect(slide, 640, 542, 540, 94, { fill: C.pale, line: "#B9DCE8", lineWidth: 1 });
  addText(slide, "Reasons may overlap. Every rejected source record and every applicable reason are retained for audit and recovery.", 664, 558, 494, 62, { fontSize: 16, color: C.ink });
  note(slide, "Explain that exact-duplicate logic keeps the first valid occurrence and quarantines later copies; reason counts are not additive because conditions can overlap.");
}

// 4 — Architecture
{
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addHeader(slide, "Simple architecture, deliberate boundaries", "Each component has one responsibility and every dependency is containerized.", 4);
  const nodes = [
    [64, 214, 190, 104, "NYC TLC", "official Parquet", C.orange],
    [302, 214, 190, 104, "Downloader", "validated + atomic", C.blue],
    [540, 214, 190, 104, "Airflow", "schedule / backfill", C.blue],
    [778, 214, 190, 104, "DuckDB", "facts + dimensions", C.orange],
    [1016, 214, 198, 104, "Superset", "read-only analytics", C.green],
  ];
  nodes.forEach(([left, top, width, height, title, subtitle, color], index) => {
    if (index < nodes.length - 1) addLine(slide, left + width, top + 52, 48, 0, C.muted, 2);
    addRect(slide, left, top, width, height, { fill: C.white, line: color, lineWidth: 2.2 });
    addText(slide, title, left + 12, top + 18, width - 24, 34, { fontSize: 21, bold: true, color: C.navy, alignment: "center" });
    addText(slide, subtitle, left + 12, top + 56, width - 24, 26, { fontSize: 14, color: C.muted, alignment: "center" });
  });
  addLine(slide, 873, 318, 0, 96, C.muted, 2);
  addRect(slide, 676, 414, 394, 92, { fill: C.white, line: C.green, lineWidth: 2 });
  addText(slide, "10 SQL analyses + dashboard aggregates", 700, 432, 346, 30, { fontSize: 19, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "measured findings and fast interactive slices", 700, 466, 346, 24, { fontSize: 14, color: C.muted, alignment: "center" });
  addText(slide, "PostgreSQL supports Airflow metadata and LocalExecutor; the production analytical warehouse remains DuckDB. The warehouse is mounted read-only into Superset, preventing dashboard users from mutating analytical state.", 96, 560, 1088, 78, { fontSize: 17, color: C.ink, alignment: "center" });
  note(slide, "Walk left to right. Emphasize container boundaries and the single-writer analytical warehouse.");
}

// 5 — Model and ETL
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "Star schema with transactional monthly replacement", "One accepted trip is the fact grain; rejected records remain independently auditable.", 5);
  addRect(slide, 490, 232, 300, 218, { fill: "#FFF8EE", line: C.orange, lineWidth: 2.5 });
  addText(slide, "fact_trips", 522, 262, 236, 42, { fontSize: 29, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "one accepted trip\n21 analytical columns", 520, 325, 240, 62, { fontSize: 17, color: C.muted, alignment: "center" });
  const dims = [
    [70, 190, "dim_zone", "zone · borough · name"],
    [70, 392, "dim_provider", "license · base · provider"],
    [910, 190, "dim_ride_features", "sharing · AAR · WAV"],
  ];
  dims.forEach(([left, top, title, body]) => {
    addRect(slide, left, top, 286, 118, { fill: C.pale, line: C.blue, lineWidth: 2 });
    addText(slide, title, left + 22, top + 20, 242, 34, { fontSize: 22, bold: true, color: C.navy, alignment: "center" });
    addText(slide, body, left + 22, top + 66, 242, 28, { fontSize: 14, color: C.muted, alignment: "center" });
  });
  addLine(slide, 356, 249, 134, 48, C.muted, 2);
  addLine(slide, 356, 399, 134, 52, C.muted, 2);
  addLine(slide, 790, 249, 120, 49, C.muted, 2);
  addRect(slide, 426, 530, 428, 84, { fill: "#EAF7EF", line: C.green, lineWidth: 2 });
  addText(slide, "quarantined_trips", 452, 544, 376, 28, { fontSize: 21, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "source row + complete reason list", 452, 574, 376, 24, { fontSize: 14, color: C.muted, alignment: "center" });
  addLine(slide, 640, 450, 0, 80, C.muted, 2);
  addText(slide, "BEGIN → replace selected month → validate → COMMIT", 150, 646, 980, 30, { fontSize: 18, bold: true, color: C.blue, alignment: "center" });
  note(slide, "The monthly transaction makes reruns safe. Unresolved dimension keys and validation failures prevent commit.");
}

// 6 — Demand and providers
{
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addHeader(slide, "Demand is steady; provider concentration is not", "The 20-month series averages about 20.6M accepted trips per month.", 6);
  const monthLabels = monthly.map((row) => row.month.slice(0, 7));
  const tripValues = monthly.map((row) => Number(row.total_trips) / 1_000_000);
  const trend = slide.charts.add("line", {
    position: { left: 54, top: 164, width: 760, height: 430 },
    title: "Monthly accepted trips (millions)",
    titleTextStyle: { fontSize: 18, fill: C.navy, bold: true },
    categories: monthLabels,
    series: [{ name: "Trips", values: tripValues, line: { style: "solid", fill: C.blue, width: 3 }, marker: { symbol: "circle", size: 4, fill: C.orange } }],
    hasLegend: false,
    xAxis: { textStyle: { fill: C.muted, fontSize: 10 }, labelOffsetPercent: 70, line: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { min: 0, max: 25, majorUnit: 5, numberFormatCode: "0.0", textStyle: { fill: C.muted, fontSize: 11 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    chartFill: C.white, plotAreaFill: C.white,
  });
  styleChart(trend);
  const provider = slide.charts.add("doughnut", {
    position: { left: 848, top: 170, width: 370, height: 350 },
    title: "Trip share by provider",
    titleTextStyle: { fontSize: 18, fill: C.navy, bold: true },
    categories: providers.map((row) => row.provider_name),
    series: [{ name: "Share", values: providers.map((row) => Number(row.trip_share_pct)), points: [{ idx: 0, fill: C.blue }, { idx: 1, fill: C.orange }] }],
    doughnutOptions: { holeSize: 58 },
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fill: C.ink, fontSize: 13 } },
    dataLabels: { showPercent: true, position: "bestFit", textStyle: { fill: C.navy, fontSize: 13, bold: true } },
    chartFill: C.white,
  });
  styleChart(provider);
  addRect(slide, 846, 540, 374, 90, { fill: C.white, line: C.line, lineWidth: 1 });
  addText(slide, "Uber: 297.4M trips · 72.22%", 872, 553, 324, 28, { fontSize: 17, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "Lyft: 114.4M trips · 27.78%", 872, 587, 324, 25, { fontSize: 15, color: C.muted, alignment: "center" });
  note(slide, "Monthly volume is relatively stable across the selected period, while provider share is highly concentrated.");
}

// 7 — Geography
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "Manhattan leads volume; airports anchor zone demand", "Geographic analyses combine borough totals, top pickup zones, routes, and cross-borough movement.", 7);
  const boroughChart = slide.charts.add("bar", {
    position: { left: 56, top: 158, width: 640, height: 450 },
    title: "Pickup share by borough",
    titleTextStyle: { fontSize: 18, fill: C.navy, bold: true },
    categories: boroughs.map((row) => row.borough),
    series: [{ name: "Share", values: boroughs.map((row) => Number(row.pickup_share_pct)), fill: C.blue, points: boroughs.map((_, idx) => ({ idx, fill: [C.blue, "#3EA5B5", C.orange, "#86B8C1", C.green][idx] })) }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 42 },
    hasLegend: false,
    xAxis: { min: 0, max: 40, majorUnit: 10, numberFormatCode: "0%", textStyle: { fill: C.muted, fontSize: 11 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { textStyle: { fill: C.ink, fontSize: 13 }, line: { style: "solid", fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.00", textStyle: { fill: C.navy, fontSize: 12, bold: true } },
    chartFill: C.white,
  });
  styleChart(boroughChart);
  addText(slide, "Top pickup zones", 756, 170, 430, 38, { fontSize: 24, bold: true, color: C.navy });
  zones.slice(0, 5).forEach((row, index) => {
    const top = 228 + index * 69;
    addText(slide, String(index + 1), 756, top, 36, 34, { fontSize: 18, bold: true, color: index < 2 ? C.orange : C.blue, alignment: "center" });
    addText(slide, row.zone_name, 804, top - 2, 260, 32, { fontSize: 16, bold: true, color: C.ink });
    addText(slide, `${(Number(row.total_pickups) / 1_000_000).toFixed(2)}M`, 1080, top - 2, 102, 32, { fontSize: 16, bold: true, color: C.navy, alignment: "right" });
    addLine(slide, 804, top + 43, 378, 0, C.line, 1);
  });
  addRect(slide, 754, 596, 430, 66, { fill: C.pale, line: "#B9DCE8", lineWidth: 1 });
  addText(slide, "LaGuardia: 8.16M · JFK: 6.80M pickups", 772, 611, 394, 32, { fontSize: 17, bold: true, color: C.navy, alignment: "center" });
  note(slide, "Manhattan accounts for 36.23% of pickups. LaGuardia and JFK are the two highest-volume pickup zones in the entire dataset.");
}

// 8 — Time and ride behavior
{
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addHeader(slide, "Demand timing changes by day type", "Weekdays peak in the morning; weekends peak in the early evening.", 8);
  const weekdays = hourly.filter((row) => row.day_type === "Weekday");
  const weekends = hourly.filter((row) => row.day_type === "Weekend");
  const hourlyChart = slide.charts.add("line", {
    position: { left: 54, top: 162, width: 780, height: 440 },
    title: "Average daily trips by pickup hour",
    titleTextStyle: { fontSize: 18, fill: C.navy, bold: true },
    categories: weekdays.map((row) => row.pickup_hour),
    series: [
      { name: "Weekday", values: weekdays.map((row) => Number(row.avg_daily_trips)), line: { style: "solid", fill: C.blue, width: 3 } },
      { name: "Weekend", values: weekends.map((row) => Number(row.avg_daily_trips)), line: { style: "solid", fill: C.orange, width: 3 } },
    ],
    hasLegend: true,
    legend: { position: "bottom", textStyle: { fill: C.ink, fontSize: 13 } },
    xAxis: { title: { text: "Hour", textStyle: { fill: C.muted, fontSize: 12 } }, textStyle: { fill: C.muted, fontSize: 10 }, line: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { min: 0, max: 45000, majorUnit: 10000, numberFormatCode: "0,000", textStyle: { fill: C.muted, fontSize: 11 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    chartFill: C.white, plotAreaFill: C.white,
  });
  styleChart(hourlyChart);
  addKpi(slide, 864, 172, 340, "08:00", "weekday peak · 40,013 avg trips", C.blue);
  addKpi(slide, 864, 324, 340, "18:00", "weekend peak · 40,081 avg trips", C.orange);
  addRect(slide, 864, 486, 340, 136, { fill: C.white, line: C.line, lineWidth: 1 });
  addText(slide, "Sharing outcome", 892, 502, 284, 32, { fontSize: 20, bold: true, color: C.navy, alignment: "center" });
  addText(slide, `${sharing[0].trip_share_pct}%`, 892, 538, 284, 45, { fontSize: 31, bold: true, color: C.green, alignment: "center" });
  addText(slide, "of trips did not request sharing", 892, 580, 284, 28, { fontSize: 14, color: C.muted, alignment: "center" });
  note(slide, "Weekday peak is 08:00 at 40,013 average daily trips; weekend peak is 18:00 at 40,081. Sharing was not requested on 97.62% of trips.");
}

// 9 — Performance
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addHeader(slide, "Two measured optimizations, identical results", "Cold-cache effects were excluded from the claim: medians use three controlled executions per approach.", 9);
  addKpi(slide, 64, 164, 350, "187.8×", "timestamp range predicate", C.blue);
  addKpi(slide, 465, 164, 350, "43.7×", "dashboard aggregate", C.orange);
  addKpi(slide, 866, 164, 348, "100%", "result equality verified", C.green);
  const table = slide.tables.add({
    rows: 3, columns: 5, left: 64, top: 344, width: 1150, height: 210,
    values: [
      ["Optimization", "Baseline median", "Optimized median", "Speedup", "Equality check"],
      ["Half-open timestamp range", "1.878 s", "0.010 s", "187.8×", "20,490,900 trips / $552,408,127.14"],
      ["Persistent dashboard aggregate", "2.009 s", "0.046 s", "43.7×", "411,739,486 trips / $11,168,662,827.90"],
    ],
    columnWidths: [248, 170, 170, 132, 430],
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 5 }).assign({ fill: C.navy, textStyle: { typeface: FONT, color: C.white, fontSize: 14, bold: true }, margins: { left: 10, right: 10, top: 7, bottom: 7 } });
  table.cells.block({ row: 1, column: 0, rowCount: 2, columnCount: 5 }).assign({ textStyle: { typeface: FONT, color: C.ink, fontSize: 14 }, margins: { left: 10, right: 10, top: 7, bottom: 7 } });
  addText(slide, "The first optimization enables zone-map pruning; the second moves repeated joins and grouping to a refreshed 11.0M-row aggregate. Caching is not counted as an optimization.", 96, 592, 1088, 68, { fontSize: 16, color: C.ink, alignment: "center" });
  note(slide, "Explain both mechanisms and the exact totals used to prove result equality. Aggregate refresh took about 76 seconds as an explicit build cost.");
}

// 10 — Airflow and deployment
{
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addHeader(slide, "Operational by design", "The normal path and the recovery path use the same repeatable monthly unit of work.", 10);
  const steps = [
    [80, "Download", "official files"],
    [318, "Initialize", "schema + zones"],
    [556, "Backfill", "20 months"],
    [794, "Optimize", "refresh aggregates"],
    [1032, "Explore", "Superset"],
  ];
  steps.forEach(([left, title, body], index) => {
    if (index < steps.length - 1) addLine(slide, left + 166, 246, 72, 0, C.muted, 2);
    addRect(slide, left, 196, 166, 100, { fill: C.white, line: index === 4 ? C.green : C.blue, lineWidth: 2 });
    addText(slide, title, left + 12, 214, 142, 30, { fontSize: 19, bold: true, color: C.navy, alignment: "center" });
    addText(slide, body, left + 12, 252, 142, 24, { fontSize: 14, color: C.muted, alignment: "center" });
  });
  addText(slide, "Airflow controls", 82, 356, 360, 38, { fontSize: 24, bold: true, color: C.navy });
  addText(slide, "• Monthly schedule: 06:00 on day 5\n• One active run protects DuckDB's single-writer path\n• One retry after one minute\n• Parameterized manual runs and inclusive backfills", 86, 407, 540, 154, { fontSize: 17, color: C.ink });
  addText(slide, "Laptop portability", 704, 356, 360, 38, { fontSize: 24, bold: true, color: C.navy });
  addText(slide, "• Docker Compose only; no host-language installs\n• Windows ThinkPad T470p: Docker Desktop + WSL2\n• Default DuckDB cap: 8 GB / 2 threads\n• Bind mounts make data and warehouse state explicit", 708, 407, 500, 154, { fontSize: 17, color: C.ink });
  addRect(slide, 80, 600, 1128, 62, { fill: C.navy, line: C.navy, lineWidth: 0 });
  addText(slide, "make download → make init → Airflow backfill → make optimize → make up", 112, 612, 1064, 34, { fontSize: 19, bold: true, color: C.white, alignment: "center" });
  note(slide, "The monthly DAG and historical backfill DAG are parsed without errors. PostgreSQL backs LocalExecutor metadata.");
}

// 11 — Dashboard
{
  const slide = presentation.slides.add();
  slide.background.fill = "#F2F5F8";
  addHeader(slide, "Superset makes the warehouse explorable", "Repository code recreates the database connection, datasets, charts, filters, and dashboard layout.", 11);
  addRect(slide, 58, 156, 1164, 492, { fill: C.white, line: C.line, lineWidth: 1 });
  addText(slide, "NYC HVFHV Mobility Analytics", 86, 176, 530, 36, { fontSize: 24, bold: true, color: C.navy });
  addRect(slide, 846, 172, 104, 34, { fill: C.pale, line: "#B9DCE8", lineWidth: 1 });
  addText(slide, "Date", 862, 176, 72, 24, { fontSize: 13, color: C.ink, alignment: "center" });
  addRect(slide, 962, 172, 104, 34, { fill: C.pale, line: "#B9DCE8", lineWidth: 1 });
  addText(slide, "Provider", 976, 176, 76, 24, { fontSize: 13, color: C.ink, alignment: "center" });
  addRect(slide, 1078, 172, 116, 34, { fill: C.pale, line: "#B9DCE8", lineWidth: 1 });
  addText(slide, "Borough", 1094, 176, 84, 24, { fontSize: 13, color: C.ink, alignment: "center" });
  addKpi(slide, 86, 234, 246, "412M", "accepted trips", C.blue);
  addKpi(slide, 350, 234, 246, "$11.2B", "base fare", C.orange);
  const miniLine = slide.charts.add("line", {
    position: { left: 620, top: 222, width: 566, height: 210 },
    title: "Monthly demand",
    titleTextStyle: { fontSize: 15, fill: C.navy, bold: true },
    categories: monthly.map((row) => row.month.slice(2, 7)),
    series: [{ name: "Trips", values: monthly.map((row) => Number(row.total_trips) / 1_000_000), line: { style: "solid", fill: C.blue, width: 2.5 } }],
    hasLegend: false,
    xAxis: { visible: false },
    yAxis: { visible: false },
    chartFill: C.white,
  });
  styleChart(miniLine);
  const miniBar = slide.charts.add("bar", {
    position: { left: 86, top: 436, width: 510, height: 180 },
    title: "Borough demand",
    titleTextStyle: { fontSize: 15, fill: C.navy, bold: true },
    categories: boroughs.map((row) => row.borough),
    series: [{ name: "Trips", values: boroughs.map((row) => Number(row.total_trips) / 1_000_000), fill: C.blue }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 34 },
    hasLegend: false,
    xAxis: { visible: false },
    yAxis: { textStyle: { fill: C.muted, fontSize: 10 } },
    chartFill: C.white,
  });
  styleChart(miniBar);
  addText(slide, "Dashboard coverage", 664, 458, 250, 30, { fontSize: 19, bold: true, color: C.navy });
  addText(slide, "KPIs · trends · provider comparison\nhourly demand · boroughs · top zones\nsharing outcomes · native filters", 668, 500, 430, 96, { fontSize: 16, color: C.ink });
  addRect(slide, 1090, 480, 86, 86, { geometry: "ellipse", fill: C.green, line: C.green, lineWidth: 0 });
  addText(slide, "READ\nONLY", 1102, 493, 62, 58, { fontSize: 14, bold: true, color: C.white, alignment: "center" });
  note(slide, "The live dashboard was visually verified in Superset. Bootstrap is idempotent and does not depend on a local Docker volume.");
}

// 12 — Close
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addText(slide, "Ready for demonstration and review", 82, 74, 820, 62, { fontSize: 42, bold: true, color: C.white });
  addText(slide, "The deliverable now connects official source data to a verified, optimized, orchestrated, and reproducible analytical experience.", 86, 154, 980, 80, { fontSize: 21, color: "#C8D8E8" });
  const bullets = [
    ["Evidence", "20 files · 411.8M rows · zero reconciliation difference"],
    ["Performance", "187.8× predicate speedup · 43.7× aggregate speedup"],
    ["Operations", "transactional ETL · Airflow schedule/backfill · Docker portability"],
    ["Delivery", "10 SQL analyses · live Superset dashboard · report and runbooks"],
  ];
  bullets.forEach(([title, body], index) => {
    const top = 284 + index * 78;
    addRect(slide, 90, top + 6, 14, 14, { geometry: "ellipse", fill: index % 2 ? C.orange : C.cyan, line: "none", lineWidth: 0 });
    addText(slide, title, 126, top - 8, 190, 34, { fontSize: 20, bold: true, color: C.white });
    addText(slide, body, 330, top - 8, 810, 34, { fontSize: 18, color: "#D6E2EF" });
  });
  addRect(slide, 88, 620, 1098, 3, { geometry: "rect", fill: "#36516F", line: "#36516F", lineWidth: 0 });
  addText(slide, "Next: demonstrate the downloader, trigger a one-month DAG run, and explore the dashboard filters.", 90, 638, 1094, 36, { fontSize: 17, bold: true, color: C.cyan, alignment: "center" });
  note(slide, "Close with a short live demo: downloader skip check, Airflow graph, and dashboard filtering.");
}

await fs.mkdir(previewDir, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(path.join(previewDir, `slide-${String(index + 1).padStart(2, "0")}.png`), png);
}
await writeBlob(path.join(buildDir, "montage.webp"), await presentation.export({ format: "webp", montage: true }));

const requirements = {
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: [3, 9],
  requiredNativeChartOwnerSlides: [6, 7, 8, 11],
  materializeLiteralChartWorkbooks: true,
};
const fontPolicy = { basis: "design", families: [FONT] };
const expectedSlideSizeEmu = "12192000,6858000";
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(stagingDir, "nyc_mobility_candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", expectedSlideSizeEmu,
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "3",
    "--require-native-table-slide", "9",
  ],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "nyc_mobility_final_presentation_v2.validation.json"),
});
console.log(JSON.stringify({ final: FINAL_PPTX, font: FONT, result }, null, 2));
