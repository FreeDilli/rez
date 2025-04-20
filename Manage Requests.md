# 🚀 RezScan Git Collaboration Setup

This document outlines the branching strategy and daily workflow for contributing to the RezScan project.

## 📁 Branch Structure

- `main`: Production-ready code only.
- `dev`: Active development branch.
- `KShaw/feature-name`: KShaw's working branches.
- `Dilli/feature-name`: Dilli's working branches.

## 🔧 Step 1: Create and Push Shared `dev` Branch

Only run this if `dev` does not exist yet:

```bash
git checkout main
git pull origin main
git checkout -b dev
git push -u origin dev
```

## 👤 Step 2: Create Feature Branch

### For KShaw:
```bash
git checkout dev
git pull origin dev
git checkout -b KShaw/location-manager
git push -u origin KShaw/location-manager
```

### For Dilli:
```bash
git checkout dev
git pull origin dev
git checkout -b Dilli/import-enhancements
git push -u origin Dilli/import-enhancements
```

## 🔁 Step 3: Daily Workflow

Make changes, then:

```bash
git add .
git commit -m "Short clear message"
git push
```

Stay in sync:

```bash
git pull origin dev
```

## ✅ Step 4: Merge Process

1. Open Pull Request: `your-feature-branch` → `dev`
2. Get it reviewed and approved
3. Merge into `dev`
4. Once dev is stable and tested, open PR from `dev` → `main`

---
*Last updated: April 20, 2025*
