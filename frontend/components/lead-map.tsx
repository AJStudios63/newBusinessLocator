"use client";

import { MapContainer, TileLayer, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapLead, Stage, GeocodeStatus } from "@/lib/types";

interface LeadMapProps {
  leads: MapLead[];
  onLeadClick: (leadId: number) => void;
  geocodeStatus: GeocodeStatus | null;
  totalWithoutCoords: number;
  onStartGeocode: () => void;
  isStarting: boolean;
}

const STAGE_COLORS: Record<Stage, string> = {
  New: "#4f7cf6",
  Qualified: "#8b5cf6",
  Contacted: "#14b8a6",
  "Follow-up": "#f59e0b",
  "Closed-Won": "#22c55e",
  "Closed-Lost": "#6b7280",
};

function createMarkerIcon(stage: Stage): L.DivIcon {
  const color = STAGE_COLORS[stage];
  return L.divIcon({
    html: `<div style="
      width: 12px;
      height: 12px;
      background-color: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    "></div>`,
    className: "",
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function formatEta(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return "";
  const mins = Math.ceil(seconds / 60);
  if (mins < 2) return "~1 min";
  return `~${mins} min`;
}

export default function LeadMap({
  leads,
  onLeadClick,
  geocodeStatus,
  totalWithoutCoords,
  onStartGeocode,
  isStarting,
}: LeadMapProps) {
  const isRunning = geocodeStatus?.running === true;
  const showIdleOverlay = !isRunning && totalWithoutCoords > 0;
  const estimatedMinutes = Math.ceil((totalWithoutCoords * 1.1) / 60);

  return (
    <MapContainer
      center={[36.1627, -86.7816]}
      zoom={9}
      className="h-full w-full z-0"
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {leads.map((lead) => (
        <Marker
          key={lead.id}
          position={[lead.latitude, lead.longitude]}
          icon={createMarkerIcon(lead.stage)}
          eventHandlers={{
            click: () => onLeadClick(lead.id),
          }}
        >
          <Tooltip>
            <div className="text-xs">
              <div className="font-semibold">{lead.business_name}</div>
              <div className="text-muted-foreground">
                {lead.business_type || "other"} • Score: {lead.pos_score}
              </div>
            </div>
          </Tooltip>
        </Marker>
      ))}

      {/* Empty state — shown when filters produce no mapped leads */}
      {leads.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[999]">
          <div className="glass-strong rounded-xl p-6 text-center">
            <p className="text-lg font-semibold">No leads match these filters</p>
            <p className="text-sm text-muted-foreground mt-1">Try adjusting your filters</p>
          </div>
        </div>
      )}

      {/* Idle overlay — top-right floating button, positioned below the filter bar */}
      {showIdleOverlay && (
        <div
          className="absolute top-36 right-4 z-[1001] glass-strong rounded-lg border border-gray-200 dark:border-indigo-900/50 shadow-lg"
          style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "10px" }}
        >
          <div>
            <div className="text-xs font-semibold text-gray-900 dark:text-indigo-200">
              {totalWithoutCoords.toLocaleString()} leads unplotted
            </div>
            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 mt-px">
              OpenStreetMap · free · ~{estimatedMinutes} min
            </div>
          </div>
          <div className="w-px h-6 bg-gray-200 dark:bg-white/10" />
          <button
            onClick={onStartGeocode}
            disabled={isStarting}
            aria-label="Start geocoding all leads"
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "6px 14px",
              borderRadius: "6px",
              border: "none",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff",
              cursor: isStarting ? "not-allowed" : "pointer",
              opacity: isStarting ? 0.6 : 1,
              boxShadow: "0 2px 8px rgba(99,102,241,0.4)",
              whiteSpace: "nowrap",
            }}
          >
            {isStarting ? "Starting..." : "Geocode All"}
          </button>
        </div>
      )}

      {/* Running toast — bottom floating overlay */}
      {isRunning && geocodeStatus && (
        <div
          role="status"
          aria-live="polite"
          className="absolute bottom-4 left-4 right-4 z-[1001] glass-strong rounded-xl border border-gray-200 dark:border-emerald-900/40 shadow-2xl"
          style={{ padding: "14px 16px" }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginBottom: "10px" }}>
            <div
              className="bg-emerald-500/10 dark:bg-emerald-500/10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ width: "32px", height: "32px", fontSize: "15px", marginTop: "1px" }}
            >
              ⏳
            </div>
            <div style={{ flex: 1 }}>
              <div className="text-xs font-bold text-emerald-600 dark:text-emerald-300">
                Geocoding in progress
              </div>
              <div className="text-[10px] text-emerald-700 dark:text-emerald-600 mt-0.5">
                OpenStreetMap · 1 req/sec · new pins appear as leads resolve
              </div>
              <div style={{ display: "flex", gap: "18px", marginTop: "8px" }}>
                <div>
                  <div className="text-lg font-extrabold text-emerald-500 dark:text-emerald-400" style={{ lineHeight: 1 }}>
                    {geocodeStatus.succeeded.toLocaleString()}
                  </div>
                  <div className="text-[9px] uppercase tracking-widest text-muted-foreground mt-0.5">
                    Geocoded
                  </div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-red-500 dark:text-red-400" style={{ lineHeight: 1 }}>
                    {geocodeStatus.failed.toLocaleString()}
                  </div>
                  <div className="text-[9px] uppercase tracking-widest text-muted-foreground mt-0.5">
                    Failed
                  </div>
                </div>
                <div>
                  <div className="text-lg font-extrabold text-gray-500 dark:text-slate-400" style={{ lineHeight: 1 }}>
                    {(geocodeStatus.total - geocodeStatus.done).toLocaleString()}
                  </div>
                  <div className="text-[9px] uppercase tracking-widest text-muted-foreground mt-0.5">
                    Remaining
                  </div>
                </div>
              </div>
            </div>
            <button
              disabled
              aria-label="Geocoding in progress"
              aria-disabled="true"
              className="text-[10px] font-semibold px-3 py-1.5 rounded-md border border-gray-200 dark:border-white/10 bg-gray-100 dark:bg-white/5 text-gray-400 dark:text-slate-500 cursor-not-allowed self-start"
              style={{ whiteSpace: "nowrap" }}
            >
              Running...
            </button>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span className="text-[10px] text-muted-foreground">
                {geocodeStatus.done.toLocaleString()} / {geocodeStatus.total.toLocaleString()}
              </span>
              <span className="text-[11px] font-extrabold text-emerald-500 dark:text-emerald-400">
                {geocodeStatus.pct}%
              </span>
            </div>
            <div
              className="bg-gray-200 dark:bg-white/10 rounded-full overflow-hidden"
              style={{ height: "6px" }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${geocodeStatus.pct}%`,
                  borderRadius: "3px",
                  background: "linear-gradient(90deg, #059669, #10b981, #34d399)",
                  boxShadow: "0 0 8px rgba(16,185,129,0.4)",
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
              <span className="text-[9px] text-muted-foreground">
                {geocodeStatus.started_at ? `Started ${geocodeStatus.started_at}` : ""}
              </span>
              <span className="text-[9px] text-muted-foreground">
                {geocodeStatus.eta_seconds !== null && (
                  <>{formatEta(geocodeStatus.eta_seconds)} remaining</>
                )}
              </span>
            </div>
          </div>
        </div>
      )}
    </MapContainer>
  );
}
