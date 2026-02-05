# Feature Roadmap: New Business Locator

**Date**: 2026-02-04
**Status**: Draft
**Scope**: Focused roadmap of 8-10 high-impact features

---

## Overview

This roadmap addresses the most pressing improvements for daily sales workflow:
- Better lead capture from multi-business sources
- Search and filtering for quick lookups and exploration
- Lead editing and data quality tools
- Duplicate detection and resolution

---

## Feature 1: Split Multi-Business URLs into Individual Leads

**Problem**: When a license table or news article contains multiple businesses, the parser may create a single lead or miss some entirely. Users cannot track each business independently.

**Solution**:
- Add `source_batch_id` column to leads table (UUID generated per extraction)
- Modify parsers to yield multiple `BusinessRecord` objects from a single `RawExtract`
- Each lead gets its own fingerprint but shares the batch ID
- UI shows "Extracted with N other leads" link on lead detail panel
- Batch view shows all leads from same extraction for context

**Database Changes**:
```sql
ALTER TABLE leads ADD COLUMN source_batch_id TEXT;
CREATE INDEX idx_leads_source_batch_id ON leads(source_batch_id);
```

**Impact**: More complete lead capture, better traceability for debugging extraction issues.

**Effort**: Medium

---

## Feature 2: Full-Text Search on Business Names

**Problem**: No way to quickly check if a business already exists or find leads by name.

**Solution**:
- Add search box to leads table header
- SQLite FTS5 virtual table for full-text search on `business_name`, `city`, `address`
- Search-as-you-type with debouncing (300ms)
- Highlight matching terms in results

**Database Changes**:
```sql
CREATE VIRTUAL TABLE leads_fts USING fts5(
  business_name,
  city,
  address,
  content='leads',
  content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER leads_ai AFTER INSERT ON leads BEGIN
  INSERT INTO leads_fts(rowid, business_name, city, address)
  VALUES (new.id, new.business_name, new.city, new.address);
END;
```

**API Changes**:
- `GET /api/leads?q=joes+pizza` - search parameter

**Impact**: Instant lookups, prevents duplicate outreach, faster workflow.

**Effort**: Medium

---

## Feature 3: Clickable Charts with Filter Integration

**Problem**: Dashboard charts are view-only. Users see "15 leads in Davidson County" but can't click to view them.

**Solution**:
- Make pie/bar chart segments clickable
- Clicking navigates to leads page with filter applied
- URL reflects filter state: `/leads?county=Davidson&stage=New`
- "Clear filters" button to reset

**Implementation**:
- Add `onClick` handlers to chart components
- Use Next.js router to update URL params
- Leads page reads filters from URL on mount

**Impact**: Seamless exploration from high-level stats to individual leads.

**Effort**: Low

---

## Feature 4: Saved Filter Presets

**Problem**: Users repeatedly apply the same filter combinations (e.g., "New leads in Davidson with score > 50").

**Solution**:
- "Save current filters" button on leads page
- Preset name input (e.g., "Hot Davidson Leads")
- Dropdown to load saved presets
- Store in localStorage initially (no backend needed)
- Optional: sync to backend for cross-device access

**Implementation**:
- React context for filter state
- localStorage persistence with JSON serialization
- Preset selector component in filter bar

**Impact**: Faster daily workflow, consistent filtering across sessions.

**Effort**: Low

---

## Feature 5: Lead Field Editing

**Problem**: Extracted data often has errors (mangled names, wrong city/county, bad addresses) with no way to correct them.

**Solution**:
- Edit mode toggle on lead detail panel
- Editable fields: `business_name`, `address`, `city`, `county`, `zip_code`, `business_type`
- Read-only fields: `fingerprint`, `source_url`, `created_at`, `pos_score` (auto-calculated)
- Save button with optimistic UI update
- Audit trail: track `updated_at` and optionally `updated_by`

**API Changes**:
- `PATCH /api/leads/{id}` - accept field updates beyond just stage/notes

**Validation**:
- County must be in known list (from sources.yaml)
- Business type must be valid enum
- City/zip format validation

**Impact**: Clean data leads to better sales outcomes and reporting accuracy.

**Effort**: Medium

---

## Feature 6: System-Suggested Duplicate Detection

**Problem**: Same business appears multiple times with slight name variations (e.g., "Joe's Coffee" vs "Joes Coffee Co").

**Solution**:
- Background job computes similarity scores between leads
- Algorithm: Levenshtein distance on normalized names + same city = likely duplicate
- Dashboard widget: "5 potential duplicates to review"
- Review UI shows side-by-side comparison
- Actions: "Merge", "Not a duplicate" (dismisses suggestion)

**Similarity Calculation**:
```python
def similarity_score(lead_a, lead_b):
    name_sim = 1 - (levenshtein(normalize(a.name), normalize(b.name)) / max_len)
    city_match = 1.0 if a.city == b.city else 0.0
    return (name_sim * 0.7) + (city_match * 0.3)
```

**Database Changes**:
```sql
CREATE TABLE duplicate_suggestions (
  id INTEGER PRIMARY KEY,
  lead_id_a INTEGER REFERENCES leads(id),
  lead_id_b INTEGER REFERENCES leads(id),
  similarity_score REAL,
  status TEXT DEFAULT 'pending',  -- pending, merged, dismissed
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Impact**: Cleaner lead list, no wasted outreach to same business twice.

**Effort**: High

---

## Feature 7: Manual Lead Merge

**Problem**: When duplicates are found (manually or via suggestions), there's no way to combine them.

**Solution**:
- Select two leads from list or duplicate review UI
- Side-by-side merge dialog shows all fields
- User picks which value to keep for each field (or edits manually)
- "Merge" button combines into single lead
- Losing lead is soft-deleted (marked `merged_into_id`)
- Stage history and notes from both leads are preserved

**Database Changes**:
```sql
ALTER TABLE leads ADD COLUMN merged_into_id INTEGER REFERENCES leads(id);
-- Soft delete: merged leads have merged_into_id set, excluded from normal queries
```

**Merge Logic**:
- Keep higher `pos_score` by default
- Preserve earlier `created_at`
- Concatenate notes with separator
- Keep more complete address

**Impact**: Single source of truth per business, cleaner reporting.

**Effort**: Medium

---

## Feature 8: Bulk Delete and Bulk Actions

**Problem**: Stale or junk leads (not real businesses, out of territory) clutter the list with no efficient way to remove them.

**Solution**:
- Checkbox column in leads table
- "Select all on page" / "Select all matching filters" options
- Bulk action toolbar appears when items selected
- Actions: Delete, Change Stage, Change County
- Confirmation dialog with count: "Delete 12 leads?"
- Soft delete with `deleted_at` timestamp (recoverable)

**API Changes**:
- `DELETE /api/leads/bulk` - accepts array of IDs
- `PATCH /api/leads/bulk` - accepts array of IDs + field updates

**UI Components**:
- Checkbox column with indeterminate state
- Floating action bar at bottom of screen
- Undo toast for accidental deletes (30 second window)

**Impact**: 10x faster cleanup of bad data, maintainable lead list.

**Effort**: Medium

---

## Feature 9: Batch Context View

**Problem**: After Feature 1 splits multi-business URLs, users need to see which leads came from the same extraction.

**Solution**:
- Lead detail shows: "Part of batch with 4 other leads" (clickable)
- Batch view page: `/batch/{source_batch_id}`
- Shows all leads from same extraction in a table
- Displays original source URL and extraction metadata
- Quick actions: "Move all to stage X", "Delete entire batch"

**Use Cases**:
- Debug why some businesses from a license table weren't captured
- Quickly qualify/disqualify all leads from a questionable source
- Understand extraction patterns over time

**Impact**: Better debugging, confidence in data completeness.

**Effort**: Low (once Feature 1 is built)

---

## Feature 10: Filter by Score Range

**Problem**: Current `minScore` filter only sets a floor. Users can't filter for "medium quality leads" (e.g., 30-50 score).

**Solution**:
- Replace single `minScore` input with range slider
- Min and max score inputs (0-100)
- Visual slider component with dual handles
- URL params: `?minScore=30&maxScore=50`

**Use Cases**:
- Focus on "almost qualified" leads that need more research
- Exclude both low-quality and already-contacted high-quality leads
- Segment outreach by lead tier

**Impact**: More nuanced lead prioritization.

**Effort**: Low

---

## Implementation Priority

| Priority | Feature | Effort | Dependencies |
|----------|---------|--------|--------------|
| 1 | Feature 1: Multi-Business Split | Medium | None |
| 2 | Feature 2: Full-Text Search | Medium | None |
| 3 | Feature 5: Lead Field Editing | Medium | None |
| 4 | Feature 8: Bulk Delete/Actions | Medium | None |
| 5 | Feature 3: Clickable Charts | Low | None |
| 6 | Feature 10: Score Range Filter | Low | None |
| 7 | Feature 4: Saved Filter Presets | Low | None |
| 8 | Feature 9: Batch Context View | Low | Feature 1 |
| 9 | Feature 6: Duplicate Detection | High | None |
| 10 | Feature 7: Manual Lead Merge | Medium | Feature 6 (optional) |

---

## Summary

This roadmap focuses on the core workflow improvements:

1. **Better data capture** (Features 1, 9) - Extract every business, track where they came from
2. **Find leads fast** (Features 2, 3, 4, 10) - Search, click-through, saved filters, score ranges
3. **Fix bad data** (Features 5, 7) - Edit fields, merge duplicates
4. **Clean up junk** (Features 6, 8) - Detect duplicates, bulk delete

Estimated total effort: 4-6 weeks for a single developer working full-time, or 2-3 months at part-time pace.
