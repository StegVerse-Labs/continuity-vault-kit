# Continuity Vault Kit

A portable, open-format, decades-durable personal knowledge vault template + tooling.

KnowledgeVault is a personal continuity system designed to:

- Preserve knowledge across decades
- Avoid lock-in to any single app or platform
- Stay AI-compatible while remaining human-readable
- Support structured retrieval in the future

⚠️ ## 🚀 Start Here

This repository is a **starter framework**.

👉 See **GETTING_STARTED.md** for instructions on creating and using your own private KnowledgeVault.

It contains structure, templates, and policies only.

No personal data should be stored here.

## Format Status

Current Format Version: 0.1.0  

This version defines the baseline folder structure and preservation policy for the KnowledgeVault system.

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
