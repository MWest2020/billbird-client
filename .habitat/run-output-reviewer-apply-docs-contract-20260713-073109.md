# Habitat reviewer — apply-docs-contract

_run_id reviewer-apply-docs-contract-20260713-073109 · verdict ok · 2026-07-13T07:32:55Z_

---

All checks verified. Here is my review verdict as the **reviewer** agent (read-only; no fixes applied).

---

# Review: `apply-docs-contract` — **PASS** ✅

Judged the diff (`main...HEAD`) against the reviewer checks and the change's proposal/tasks.

## 1. Scope ✅ (with one note)
The docs work matches the change's tasks exactly:
- `docs/cli.md`, `docs/mcp.md` → `reference/`; `docs/release.md` → `how-to/`; stubs left at old paths — as specified in *Repo-specifiek*.
- `docs/index.md` created new from the README (task 2.3).
- Tasks 1.1–3.1 checked; **4.1 (PR/merge) correctly left unchecked** — that belongs to the harness/Mark, not the builder.

**Note (non-blocking):** the diff also carries harness bookkeeping — `.habitat/audit.jsonl`, `.habitat/run-output-*.md`, `.habitat/run-report-*.html`, `run-report.json`. These are habitat-generated artifacts, not builder docs content, so I don't treat them as scope creep. Flagging so Mark can confirm they should ride along in the docs PR (or be stripped before merge).

## 2. Contract ✅
- **Markdown location:** `index.md` + `reference/` + `how-to/` carry the real content; `explanation/` omitted (no ADRs — correct, empty dirs left out). The three top-level stubs (`docs/cli.md`, `docs/mcp.md`, `docs/release.md`) *are* markdown outside the canonical dirs, but they are **explicitly sanctioned** by the proposal ("stubs achterlaten … externe links"), so within contract.
- **Front matter:** all 7 pages have `status` + `last_reviewed`. Migrated-without-review pages (`index.md`, `reference/cli.md`, `reference/mcp.md`, `how-to/release.md`) = `status: draft`; stubs = `status: deprecated`; `last_reviewed: 2026-07-13` (migration date) throughout. ✅
- **No `owner` field** — confirmed; the only `owner` hits are prose ("project owner") and a CLI flag (`owner/name`), not front matter. ✅
- **One language** (English) across `docs/`. ✅
- README kept; `index.md` links to it rather than replacing it. ✅
- Internal links resolve correctly (stubs → new paths; `reference/cli.md` → `mcp.md` sibling; `index.md` → section paths). ✅
- `.mcp.json` present in root with placeholder `TODO-change-3` intact (task 2.4 satisfied; seeded earlier, unchanged this run). ✅

## 3. Cage intact ✅
No changes to `CLAUDE.md`, `.claude/agents/`, or CI config (`.github/`). Confirmed via name-only diff.

## 4. No secrets ✅
All token examples are placeholders (`bb_xxxx…`, `<YOUR_PYPI_API_TOKEN>`); remaining `token` hits are prose. No credentials, keys, or secret-bearing URLs.

---

**Verdict: PASS.** The change is ready for Mark to open the PR (`docs: apply handbook docs contract`) and merge. The only thing worth a glance before merge is whether the `.habitat/*` and `run-report.json` harness artifacts belong in the PR.
