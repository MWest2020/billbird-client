---
status: draft
last_reviewed: 2026-07-13
---

# Release process

Releases are driven by version tags. Pushing `v0.1.0` (or any `v*.*.*`) triggers `.github/workflows/release.yml`, which builds an sdist + wheel and publishes them to PyPI through trusted publishing — no API token in GitHub secrets.

## One-time PyPI setup (project owner)

Until the project exists on PyPI, the workflow has nothing to publish *to*. The first release needs a manual step:

1. **Create a PyPI account** (or log in to your existing one): https://pypi.org/account/register/
2. **Reserve the project name.** Easiest path: build locally and upload once with an API token:
   ```bash
   uv build
   uv publish --token <YOUR_PYPI_API_TOKEN>
   ```
   Or: go to https://pypi.org/manage/account/publishing/ and add a *pending* trusted publisher for `billbird-client`. The first publish from this repo then creates the project.
3. **Wire trusted publishing** at https://pypi.org/manage/project/billbird-client/settings/publishing/:
   - Owner: `MWest2020`
   - Repository: `billbird-client`
   - Workflow filename: `release.yml`
   - Environment: `pypi`
4. **Create the `pypi` GitHub environment** in this repo's settings → Environments → New → name it `pypi`. Optionally add a required-reviewer (your own login) so a human approves each publish.

After step 4, every subsequent `git tag vX.Y.Z && git push origin vX.Y.Z` releases automatically.

## Cutting a release

```bash
# bump version in pyproject.toml first, then:
git tag v0.1.0
git push origin v0.1.0
```

The workflow:

1. Verifies that the git tag (`v0.1.0`) matches `pyproject.toml`'s `version` field (`0.1.0`). Mismatch → fail loud.
2. Runs `uv build` to produce `dist/billbird_client-*.whl` and `dist/billbird_client-*.tar.gz`.
3. Uploads both artifacts to PyPI via `pypa/gh-action-pypi-publish` using OIDC.

## CI

Every push to `main` and every PR runs `.github/workflows/ci.yml`:

- `uv sync --frozen` — lockfile must be honoured.
- `uv run ruff check .` — lint.
- `uv run pytest -q` — full test suite.

Both checks must pass before a release tag is meaningful.
