const COLORS = ["#FF385C", "#2563EB", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#64748B"];
const ROOM_TYPES = ["Entire home/apt", "Private room", "Shared room"];
const eur = (v, d = 0) => "€" + Number(v).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });

const PLOT_LAYOUT = {
  margin: { l: 50, r: 16, t: 10, b: 40 },
  font: { family: "Inter, sans-serif", size: 12, color: "#374151" },
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  xaxis: { gridcolor: "#F3F4F6", zeroline: false }, yaxis: { gridcolor: "#F3F4F6", zeroline: false },
  legend: { orientation: "h", y: -0.18 }, hoverlabel: { font: { family: "Inter" } },
};
const PLOT_CFG = { displayModeBar: false, responsive: true };
function plot(id, data, layout = {}) {
  Plotly.newPlot(id, data, { ...PLOT_LAYOUT, ...layout,
    xaxis: { ...PLOT_LAYOUT.xaxis, ...(layout.xaxis || {}) }, yaxis: { ...PLOT_LAYOUT.yaxis, ...(layout.yaxis || {}) } }, PLOT_CFG);
}

function baseMap(id, center, zoom) {
  const map = L.map(id, { preferCanvas: true, zoomControl: true }).setView(center, zoom);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19, className: "soft-tiles",
  }).addTo(map);
  return map;
}

// price -> colour on a blue -> green -> yellow -> orange -> red scale using quantiles
const SCALE = ["#2563EB", "#10B981", "#FACC15", "#F97316", "#E11D48"];
function priceColor(p, q) {
  for (let i = 0; i < q.length; i++) if (p <= q[i]) return SCALE[i];
  return SCALE[SCALE.length - 1];
}
function quantiles(arr, qs) {
  const s = [...arr].sort((a, b) => a - b);
  return qs.map(q => s[Math.min(s.length - 1, Math.floor(q * s.length))]);
}
