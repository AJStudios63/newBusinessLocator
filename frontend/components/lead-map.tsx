"use client";

import { MapContainer, TileLayer, Marker, Tooltip } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MapLead, Stage } from "@/lib/types";

interface LeadMapProps {
  leads: MapLead[];
  onLeadClick: (leadId: number) => void;
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

function createClusterIcon(cluster: any): L.DivIcon {
  const count = cluster.getChildCount();
  return L.divIcon({
    html: `<div style="
      width: 40px;
      height: 40px;
      background: rgba(99, 102, 241, 0.15);
      backdrop-filter: blur(8px);
      border: 1.5px solid rgba(139, 92, 246, 0.3);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 600;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    ">${count}</div>`,
    className: "",
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
}

export default function LeadMap({ leads, onLeadClick }: LeadMapProps) {
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
      <MarkerClusterGroup
        chunkedLoading
        iconCreateFunction={createClusterIcon}
      >
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
      </MarkerClusterGroup>
    </MapContainer>
  );
}
