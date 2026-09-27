# Pull Request Checklist

Use this before opening a PR for any backend or model-related change.

## Required checks

- [ ] No `.joblib`, `.bin`, `.pkl`, `.pth`, or generated FAISS files are committed to Git.
- [ ] The release bundle is versioned and uploaded to GitHub Releases (or the approved artifact host).
- [ ] `python scripts/download_model_artifacts.py` works for a clean local clone.
- [ ] The backend fails fast with a clear message if model artifacts are missing.
- [ ] The `.env.example` file is complete and does not contain secrets.
- [ ] Local DB setup instructions are documented for new contributors.
- [ ] The backend runs with the team’s standard dev environment and no hidden manual steps.
- [ ] The model bundle version is compatible with the code in this PR.
- [ ] Tests pass for the changed behavior and the related regression suite.

## Model artifact policy

- Treat all ML binaries as release artifacts, not source code.
- Keep model data out of Git history.
- Document which release bundle is required for each backend version.
- Ensure every developer downloads the same version before testing.

## Suggested PR title format

- feat: add model artifact bootstrap for local dev
- fix: skip Alembic migration during reload startup
- chore: document binary release workflow for ML assets
