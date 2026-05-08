# GitHub Sync Status

Repository: `DhruvNITDelhi/SolarCast`

Checked on: 2026-05-08

## Current Local Branch

```text
feature/analytics-upgrade
```

## Last Known Synced Commit

```text
f25ca6b Harden backend and improve forecast confidence
```

At the start of this check, local `HEAD` matched the local tracking reference `origin/feature/analytics-upgrade`.

## Authentication Status

The configured remote is:

```text
git@github.com:DhruvNITDelhi/SolarCast.git
```

`git fetch origin` failed because the current machine/session does not have a working SSH key for GitHub:

```text
git@github.com: Permission denied (publickey)
```

GitHub CLI is also not installed:

```text
gh: The term 'gh' is not recognized
```

Because of this, the repository could be prepared locally, but it could not be pushed to GitHub from this session.

## Local Work Prepared For Sync

The tracked repository layout has been updated with the SolarCast patent-track work:

- Hybrid physics + ML residual forecast endpoint
- ML-only forecast endpoint support
- Physics vs Hybrid vs ML comparison response
- Frontend Hybrid mode and comparison panel
- Indian solar dataset training pipeline
- Hybrid residual training pipeline
- Exported lightweight model artifacts
- Documentation describing dataset, training process, hybrid approach, and patent-track next steps

Generated datasets, raw Kaggle/OPSD files, local cache folders, and development-only inspection folders are ignored through `.gitignore`.

## Verification

Latest local verification:

```text
python -m py_compile backend\hybrid_engine.py ml\train_hybrid_residual_model.py ml\hybrid_residual_model.py
python -m pytest tests -q
npm.cmd run build
```

Result:

```text
Backend tests: 8 passed
Frontend build: passed
Python compile check: passed
```

## Push Blocker

To finish syncing with GitHub, one of these needs to be fixed:

1. Add/configure the correct SSH key for `git@github.com:DhruvNITDelhi/SolarCast.git`.
2. Install/authenticate GitHub CLI.
3. Switch remote to HTTPS and authenticate with Git Credential Manager or a GitHub token.

