# Map View Feature — Design Spec

## Problem

Salespeople using the newBusinessLocator app can see leads in tables, kanban boards, and charts — but have no spatial awareness of where businesses are located. They can't answer "what leads are near me?" or "which areas have the most opportunity?" without mentally mapping city names to geography.

## Solution

A dedicated `/map` page showing all geocoded leads as interactive pins on a Leaflet/OpenStreetMap map, centered on the Nashville/Middle Tennessee service area. Pins are color-coded by stage, clustered when zoomed out, and clickable to open the existing lead detail panel.

## Scope

### In scope
- Add `latitude`/`longitude` columns to leads table
- Geocoding utility using free OpenStreetMap Nominatim API (1 req/sec rate limit)
- Geocoding integrated into ETL transform phase
- CLI command to backfill existing leads: `python -m cli.main geocode`
- Dedicated `/api/map` endpoint (lightweight payload, no pagination)
- `/map` page with full-screen Leaflet map, marker clustering, color-coded pins
- Floating glassmorphism filter bar (stage, county, score, business type)
- Click pin → reuse existing `LeadDetailPanel` slide-out
- Hover tooltip showing business name + score

### Out of scope
- Route planning / directions
- Heat map layer (can add later)
- Persistent geocode cache table (in-memory cache within batch is sufficient)
- Real-time location tracking
- Dashboard mini-map (could add later if desired)

## Architecture

### Data Flow
```
ETL extract → transform (classify, filter, score, infer county)
    → geocode_batch() [NEW — after filtering, before dedup]
    → deduplicate → load (INSERT with lat/lng)
```

### Database Changes
- `leads` table: add `latitude REAL`, `longitude REAL`
- Migration via existing `_migrate_add_column()` pattern
- Partial index: `idx_leads_geocoded ON leads(latitude, longitude) WHERE latitude IS NOT NULL`

### Geocoding (`utils/geocoder.py`)
- Nominatim API: `https://nominatim.openstreetmap.org/search`
- Rate limit: 1.1s between requests (enforced via monotonic clock)
- Query construction priority: full address → address+city → city+state → skip
- In-memory cache within batch to avoid duplicate geocoding
- Never crashes pipeline — returns (None, None) on failure
- Custom User-Agent header required by Nominatim TOS

### API Endpoint (`GET /api/map`)
- Returns only geocoded leads (lat IS NOT NULL)
- Lightweight fields: id, business_name, business_type, city, county, pos_score, stage, latitude, longitude
- No pagination — returns all matching (hard cap 2000)
- Filters: stage, county, minScore, maxScore, businessType
- Response: `{ leads: [...], total_geocoded: N, total_without_coords: N }`

### Frontend Components
- **`frontend/app/map/page.tsx`** — page with React Query, dynamic Leaflet import (SSR disabled)
- **`frontend/components/lead-map.tsx`** — MapContainer centered on Nashville [36.1627, -86.7816] zoom 9, MarkerClusterGroup, custom divIcon pins
- **`frontend/components/map-filters.tsx`** — floating glass overlay with filter controls
- **Dependencies:** react-leaflet, leaflet, @types/leaflet, react-leaflet-cluster

### Pin Colors by Stage
| Stage | Color |
|-------|-------|
| New | Blue (hsl 226) |
| Qualified | Purple (hsl 262) |
| Contacted | Teal (hsl 173) |
| Follow-up | Amber (hsl 43) |
| Closed-Won | Green (hsl 152) |
| Closed-Lost | Gray |

## Key Decisions

1. **Geocode in transform, not load** — minimizes API calls (only geocode filtered leads), coordinates available during dry runs
2. **Dedicated /api/map endpoint** — 3-4x smaller payload than reusing /api/leads, no pagination needed for map
3. **Leaflet + OSM** — completely free, no API keys, adequate for pin+cluster territory view
4. **City-center fallback** — leads with only city (no street address) geocode to city center; clustering handles the imprecision
5. **No persistent cache** — in-memory batch cache sufficient for initial implementation; can add geocode_cache table later if needed
