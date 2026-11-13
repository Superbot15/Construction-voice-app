# Roadmap

Civil AI is pre-release. Priorities, roughly in order:

## 1. Offline-first local LLM support
Jobsite trailers often have poor or no cellular service. Rule-based parsing already runs fully offline. Next:
- An optional extraction backend that runs a local model (llama.cpp / Ollama) to handle layouts the regex parsers miss.
- Local embeddings plus SQLite for "ask the spec" search without a network connection.
- A hard guarantee that no document text leaves the machine unless a cloud backend is configured explicitly.

## 2. Parser test coverage for product data sheets
- A corpus of anonymized, permissively licensed data sheets (concrete, rebar, geotextiles, pipe, asphalt, coatings).
- Table-layout extraction for multi-column PDS tables.
- Golden-file tests for every supported layout, with coverage tracked in CI.

## 3. Enterprise deployment documentation
- Installing on locked-down Windows workstations and air-gapped networks.
- Running as a shared service (container image, reverse proxy, SSO).
- Data retention, backup and security guidance for IT teams.

## Later
- Submittal register tracking: due dates, resubmittal cycles and review aging.
- Export to CSV and Excel for project controls.
- Comparing a submittal package against its spec section in one step.
