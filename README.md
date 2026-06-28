# EDF-L1 — Education Download Framework, Level 1

Automated PDF acquisition and management for educational textbooks (GSEB, NCERT).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp config/config.yaml.example config.yaml

# Run bootstrap check
python main.py
```

## Project Structure

```
├── main.py                  # CLI entry point
├── config.yaml              # Runtime configuration
├── config/
│   └── config.yaml.example  # Example configuration
├── src/
│   └── edf/
│       ├── adapters/        # Source adapters (GSEB, NCERT)
│       ├── core/            # Config, pipeline orchestrator
│       ├── logging/         # Structured logging
│       ├── manifests/       # Manifest generation
│       ├── models/          # Data models and interfaces
│       ├── storage/         # Filesystem storage manager
│       └── utils/           # Hashing, PDF validation, HTTP
├── tests/
│   ├── unit/
│   └── integration/
└── scripts/
```

## Configuration

Copy `config/config.yaml.example` to `config.yaml` and edit:

- `general.content_root` — Path to CONTENT directory
- `gseb.textbooks` — GSEB textbook URL list
- `ncert.textbooks` — NCERT textbook codes (verified against master-list)

## CLI Usage

```bash
python main.py                  # Run full pipeline
python main.py --dry-run        # Simulate without downloading
python main.py --board GSEB     # Run for single board
python main.py --verify-only    # Re-validate existing files
```

## Implementation Phases

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | ✅ Complete | Project skeleton, models, logging, CLI bootstrap |
| 2 | ⬜ Pending | GSEB placeholder adapter, NCERT pre-flight |
| 3 | ⬜ Pending | Download manager, validation pipeline |
| 4 | ⬜ Pending | Integration, CONTENT scanning, manifest merge |
| 5 | ⬜ Pending | Hardening, documentation, CLI flags |

## License

MIT
