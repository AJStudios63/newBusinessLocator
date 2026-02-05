# Multi-Business Article Parser Enhancement

**Date:** 2026-02-04
**Status:** Approved

## Problem

News articles like "New businesses coming to Williamson County in 2026" list multiple businesses (Potbelly, Velvet Taco, etc.), but the pipeline creates a single lead using the article title as the business name. Individual businesses should be extracted as separate leads.

## Solution

Enhance `parse_news_article()` in `utils/parsers.py` to extract business names from multiple article formats, not just `## ` headings.

## Extraction Strategies (Priority Order)

Only the first successful strategy that yields results is used to prevent double-counting.

### 1. `## Heading` Sections (Current)
```markdown
## Potbelly Sandwich Shop
*123 Main Street, Franklin*
Opening March 2026...
```
Each `## Business Name` becomes a lead. Most reliable format.

### 2. Bold Names
```markdown
**Potbelly** or __Velvet Taco__
```
Extract text between bold markers. Filter out generic words ("New", "Opening", "Location").

### 3. List Items
```markdown
- Potbelly Sandwich Shop - opening March 2026
* Velvet Taco (coming to Franklin)
1. Crumbl Cookies
2. Jersey Mike's Subs
```
Extract first phrase before delimiters (` - `, ` – `, `(`, `,`).

### 4. Sentence Patterns (Fallback)
```
"Potbelly is opening a new location..."
"Velvet Taco will open at..."
"A new Crumbl Cookies is coming to Franklin"
```
Match patterns and extract subject as business name. Least reliable.

## Filtering

- Skip entries < 3 characters
- Skip entries matching `is_article_title()` patterns
- Skip purely numeric entries
- Apply existing chain filter to all extracted businesses

## Address Association

**Bold names / List items:**
- Look for address patterns in same line or next 2 lines
- Address indicators: street numbers, city names, "located at"

**Sentence patterns:**
- Extract location from sentence: "opening at 123 Main St", "coming to Franklin"

**Fallback:**
- Scan full article for city mentions, assign first match
- County inherited from search query

Leads without street addresses score lower on address completeness but still enter pipeline.

## Configuration Changes

### sources.yaml - Add extractable domains
```yaml
extractable_domains:
  - wilcosun.com
  - tennessean.com
  - nashvillepost.com
  - bizjournals.com
  - newschannel5.com
```

### chains.yaml - Add common chains
```yaml
- Potbelly
- Velvet Taco
- "Nothing Bundt Cakes"
- "Raising Cane's"
```

## Files to Modify

1. `utils/parsers.py` - Enhance `parse_news_article()` with new extraction strategies
2. `config/sources.yaml` - Add news domains to `extractable_domains`
3. `config/chains.yaml` - Add common chains
4. `tests/test_transform.py` - Add tests for new parser logic

## Testing

- Unit tests for each extraction strategy
- Test deduplication across strategies
- Test address association logic
- Integration test with sample article content
