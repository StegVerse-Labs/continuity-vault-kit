# 📱 iOS Guide — Updating Your KnowledgeVault Safely

This guide explains how to update your **private KnowledgeVault** using a new Continuity Vault Kit release **without risking your personal files**.

⚠️ Important:
The **GitHub repository and release ZIP are starter kits only**.  
Your real notes, documents, and records should live in a **separate private vault folder** on your device or cloud storage.

---

## 🧱 First: Understand the Difference

| Kit Release | Your Personal Vault |
|------------|---------------------|
| Public framework | Private data |
| Templates & structure | Your notes, PDFs, media |
| Safe to replace | Must be preserved |
| Versioned (0.1.0 → 0.1.1…) | Continuous over decades |

**Never unzip a new release directly over your personal vault.**

---

## 📥 Step 1 — Download the New Release

1. Open the repository **Releases** page
2. Download the latest **ZIP** asset
3. Save it to **Files → iCloud Drive → Downloads** (or similar temporary folder)

---

## 📦 Step 2 — Unzip the Release

Tap the ZIP file in the Files app.  
iOS will create a new folder like:

```
  KnowledgeVault_v0.1.1/
```

This is just the **new kit version**, not your vault.

---

## 🔍 Step 3 — Compare With Your Private Vault

Your real vault might live at:

```
iCloud Drive/
└── KnowledgeVault/
```

Open **both folders side-by-side** (Split View helps).

You are looking for:

### ✅ Things you SHOULD copy into your vault

| If the release contains… | Put it here in your vault |
|--------------------------|----------------------------|
| New files in `_Templates/` | `KnowledgeVault/_Templates/` |
| New files in `_Policy/` | `KnowledgeVault/_Policy/` |
| New files in `_Index/` | `KnowledgeVault/_Index/` |
| Improvements to `_AI/README.md` etc. | Optional but helpful |

### 🚫 Things you should NOT replace

Never overwrite these folders in your vault:

- `01_Notes`
- `02_Research`
- `03_Records`
- `04_Media`
- `05_Projects`
- `06_Archive`

These contain your **actual life data**.

---

## 🧠 Rule of Thumb

**Copy structure, never replace content.**

If a folder contains your personal files, leave it alone.

---

## 🗑 Step 4 — Delete the Temporary Kit Folder

Once you’ve copied any new templates or policies:

1. Go back to the unzipped release folder
2. Delete it

You don’t need to keep old kit versions on your device.

---

## 🔒 Safety Reminder

The public repository is a **framework**, not a storage location.

Never upload personal vault content back to GitHub unless the repo is private and you fully understand the risks.

---

## 🧭 Why This Matters

Your KnowledgeVault is designed to last **decades**.  
The kit will evolve, but your vault should remain stable.

This process ensures:
- Your data is never accidentally overwritten
- You benefit from structural improvements
- You stay platform-independent

---

Future versions may include an automated update helper.  
For now, manual updates are the safest approach.
