# KnowledgeVault — Continuity Vault Kit

A portable, open-format, decades-durable framework for preserving personal knowledge and life records.

KnowledgeVault is designed to help individuals:

- Preserve important information across decades  
- Avoid lock-in to any single app or platform  
- Keep data AI-compatible while remaining human-readable  
- Maintain structure that future tools (and future-you) can understand  

This is **not an app**.  
It is a **framework and structure** for building your own long-term personal knowledge archive.

---

## 🚀 Start Here

This repository is a **starter kit**.

👉 See **GETTING_STARTED.md** to create and use your own **private KnowledgeVault**.

It contains **structure, templates, and policies only**.

⚠️ **No personal data should ever be stored in this repository.**

---

## 🛟 Need Help Setting Up?

If you'd like help with:

- Initial KnowledgeVault setup  
- Migrating existing notes or documents  
- Designing a long-term archival system  
- Safe AI integration with your vault  

Please **open a GitHub Issue** and include:

1. What you're trying to accomplish  
2. What tools or platforms you're currently using  
3. Any constraints (device-only, privacy level, storage limits, etc.)

This project evolves through real-world use and feedback.

---

## 🧱 Format Status

**Current Format Version:** 0.1.0  

This version defines the baseline folder structure and preservation policies for the KnowledgeVault system. The structure will evolve carefully over time with backward compatibility in mind.

---

## 📦 What You Get

- A ready-to-use folder template at `vault_template/KnowledgeVault/`  
- Index scaffolding for humans + AI  
- Tooling to generate distributable, verifiable release packages  

---

## 🧠 Core Principles

- Open formats (Markdown, PDF, CSV, JSON)  
- Vendor neutral (works with any cloud or offline storage)  
- Designed for redundancy (3-2-1 backup compatible)  
- AI-friendly structure with clear privacy boundaries  
- Calm, durable organization rather than constant reorganization  

---

## ⚡ Quick Start (Local Use)

### 1️⃣ Build a distributable package
```bash
python3 tools/build_release.py
```

### 2️⃣ Initialize a vault in a chosen location
```bash
python3 tools/init_vault.py /path/to/target
```

### 3️⃣ Verify a release bundle
```bash
python3 tools/verify_release.py dist/ContinuityVault_v0.1.0.zip
```
