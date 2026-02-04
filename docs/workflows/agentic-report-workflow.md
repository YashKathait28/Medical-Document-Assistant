---
description: Agentic workflow for report generation
---

1. Ingest documents (upload or Drive) and store raw files in `data/uploads`.
2. Parse each file into text + tables.
3. Chunk the text, embed chunks, and store in ChromaDB.
4. When a report is requested, call the `collect_section_data` tool for each section title.
5. The tool retrieves top chunks + tables for that section and returns them verbatim.
6. Insert extracted content into the report sections in order.
7. If `include_summary` is true, summarize the collected text and append a Summary section.
8. Export the final report to PDF in `data/reports` and return a download URL.
