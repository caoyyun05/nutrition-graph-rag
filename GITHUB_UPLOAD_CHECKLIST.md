# GitHub Upload Checklist

Date: 2026-05-27

This repository is prepared as a runtime and reproducibility package. It intentionally excludes manuscript submission files.

## Upload Scope

Files intended for GitHub:

- `src_v3/`
- `data_usda_55/`
- `data_v2/` except `data_v2/dataset/`
- `results_usda_55/`
- `results_v2/`
- `README.md`
- `STREAMLIT_V3_DASHBOARD_GUIDE.md`
- `MULTI_LLM_AUDIT_PLAN_USDA.md`
- `PAPER_EXPERIMENT_RESTRUCTURE_NOTE.md`
- `requirements.txt`
- `requirements-api.txt`
- `.env.example`
- `.gitignore`

## Excluded From GitHub

The following are intentionally retained locally but excluded from GitHub:

- `.env`
- `paper_submission/`
- `paper_submission_final/`
- `data_v2/dataset/`
- Python cache directories such as `__pycache__/`
- Word temporary files such as `~$*.docx`
- manuscript backup files
- local paper-formatting and figure-generation helper scripts

## Pre-Upload Checks Already Performed

- `.env` is ignored by `.gitignore`.
- `paper_submission/` and `paper_submission_final/` are ignored.
- Raw USDA download folder `data_v2/dataset/` is ignored.
- Python cache directories were removed.
- No files larger than 10 MB were found in the upload set.
- Saved multi-LLM result files are small enough for GitHub.
- Sensitive-key pattern scan did not find real API keys outside `.env`.

## Commands For Final Upload

Run from the repository root:

```powershell
cd D:\claude\study\paper\nutrition-graph-rag-github-ready
git status --short --ignored
git check-ignore -v .env paper_submission paper_submission_final data_v2\dataset
git add .
git status
git commit -m "Initial reproducibility package"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Before `git commit`, inspect `git status` carefully. The staged list should not include `.env`, `paper_submission/`, or `paper_submission_final/`.

If the remote already exists, use:

```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

