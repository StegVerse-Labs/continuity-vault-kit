# Continuity Vault Kit

A portable, open-format, decades-durable personal knowledge vault template + tooling.

KnowledgeVault is a personal continuity system designed to:

- Preserve knowledge across decades  
- Avoid lock-in to any single app or platform  
- Stay AI-compatible while remaining human-readable  
- Support structured retrieval in the future  

---

## 🚀 Start Here

This repository is a **starter framework**.

👉 See **GETTING_STARTED.md** for instructions on creating and using your own private KnowledgeVault.

It contains **structure, templates, and policies only**.

⚠️ **No personal data should be stored in this repository.**

---

## 🛟 Need Help Setting Up Your KnowledgeVault?

If you'd like assistance with:

- Initial KnowledgeVault setup  
- Migrating existing notes or documents  
- Structuring a long-term archival system  
- Safe AI integration with your vault  

Please **open a GitHub Issue** in this repository and describe:

1. What you're trying to accomplish  
2. What tools or platforms you're currently using  
3. Any constraints (device-only, privacy level, storage limits, etc.)

We’ll respond with guidance, templates, or next steps.

---

## 🧱 Format Status

**Current Format Version:** 0.1.0  

This version defines the baseline folder structure and preservation policy for the KnowledgeVault system.

---

## 📦 What You Get

- A ready-to-use folder template at `vault_template/KnowledgeVault/`  
- Index scaffolding for humans + AI  
- A build tool that creates a distributable ZIP + SHA256 checksum + manifest  

---

## 🧠 Core Principles

- Open formats (Markdown, PDF, CSV, JSON)  
- Vendor neutral (works on any cloud or offline)  
- Designed for redundancy (3-2-1 backup compatible)  
- AI-friendly indexing and policy boundaries  

---

## ⚡ Quick Start (Local)

### 1️⃣ Build a distributable package
```bash
python3 tools/build_release.py

## 2️⃣ Initialize vault to chosen dir
1. python3 tools/init_vault.py /path/to/target

## 3️⃣ Verify release bundle
1. python3 tools/verify_release.py dist/ContinuityVault_v0.1.0.zip
