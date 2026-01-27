# Continuity Vault Kit

A portable, open-format, decades-durable personal knowledge vault template + tooling.

## What you get
- A ready-to-use folder template at `vault_template/KnowledgeVault/`
- Index scaffolding for humans + AI
- A build tool that creates a distributable ZIP + SHA256 checksum + manifest

## Core principles
- Open formats (Markdown, PDF, CSV, JSON)
- Vendor neutral (works on any cloud or offline)
- Designed for redundancy (3-2-1 backup compatible)
- AI-friendly indexing and policy boundaries

## Quick start (local)
1. Build a distributable package:
   ```bash
   python3 tools/build_release.py

## Initialize vault to chosen dir
1. python3 tools/init_vault.py /path/to/target

## Verify release bundle
1. python3 tools/verify_release.py dist/ContinuityVault_v0.1.0.zip
