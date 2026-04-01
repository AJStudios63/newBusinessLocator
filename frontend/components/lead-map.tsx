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

      {/* Idle overlay — top-right floating button */}
      {showIdleOverlay && (
        <div
          className="absolute top-16 right-4 z-[1000]"
          style={{
            background: "rgba(8, 13, 26, 0.88)",
            border: "1px solid rgba(99, 102, 241, 0.35)",
            borderRadius: "8px",
            padding: "8px 14px",
            backdropFilter: "blur(16px)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <div>
            <div style={{ fontSize: "11px", color: "#c7d2fe", fontWeight: 600 }}>
              {totalWithoutCoords.toLocaleString()} leads unplotted
            </div>
            <div style={{ fontSize: "10px", color: "#4f46e5", marginTop: "1px" }}>
              OpenStreetMap · free · ~{estimatedMinutes} min
            </div>
          </div>
          <div style={{ width: "1px", height: "24px", background: "rgba(255,255,255,0.08)" }} />
          <button
            onClick={onStartGeocode}
            disabled={isStarting}
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
          className="absolute bottom-4 left-4 right-4 z-[1000]"
          style={{
            background: "rgba(8, 13, 26, 0.92)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "10px",
            padding: "14px 16px",
            backdropFilter: "blur(20px)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginBottom: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(16, 185, 129, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "15px",
                flexShrink: 0,
                marginTop: "1px",
              }}
            >
              ⏳
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#6ee7b7" }}>
                Geocoding in progress
              </div>
              <div style={{ fontSize: "10px", color: "#059669", marginTop: "2px" }}>
                OpenStreetMap · 1 req/sec · new pins appear as leads resolve
              </div>
              <div style={{ display: "flex", gap: "18px", marginTop: "8px" }}>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#34d399", lineHeight: 1 }}>
                    {geocodeStatus.succeeded.toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Geocoded
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#f87171", lineHeight: 1 }}>
                    {geocodeStatus.failed.toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Failed
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#64748b", lineHeight: 1 }}>
                    {(geocodeStatus.total - geocodeStatus.done).toLocaleString()}
                  </div>
                  <div style={{ fontSize: "9px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#334155", marginTop: "2px" }}>
                    Remaining
                  </div>
                </div>
              </div>
            </div>
            <button
              disabled
              style={{
                fontSize: "10px",
                fontWeight: 600,
                padding: "6px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(255,255,255,0.05)",
                color: "#64748b",
                cursor: "not-allowed",
                whiteSpace: "nowrap",
                alignSelf: "flex-start",
              }}
            >
              Running...
            </button>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span style={{ fontSize: "10px", color: "#475569" }}>
                {geocodeStatus.done.toLocaleString()} / {geocodeStatus.total.toLocaleString()}
              </span>
              <span style={{ fontSize: "11px", fontWeight: 800, color: "#34d399" }}>
                {geocodeStatus.pct}%
              </span>
            </div>
            <div
              style={{
                height: "6px",
                background: "rgba(255,255,255,0.06)",
                borderRadius: "3px",
                overflow: "hidden",
              }}
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
              <span style={{ fontSize: "9px", color: "#334155" }}>
                {geocodeStatus.started_at ? `Started ${geocodeStatus.started_at}` : ""}
              </span>
              <span style={{ fontSize: "9px", color: "#334155" }}>
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
