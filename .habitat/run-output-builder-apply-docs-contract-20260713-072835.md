# Habitat builder — apply-docs-contract

_run_id builder-apply-docs-contract-20260713-072835 · verdict ok · 2026-07-13T07:31:05Z_

---

Done. The `apply-docs-contract` change is implemented and committed on `habitat/builder/apply-docs-contract`.

## Wat is gedaan

**Docs gemigreerd naar het handbook-contract** (via `git mv`, historie behouden):
- `docs/cli.md` → `docs/reference/cli.md`
- `docs/mcp.md` → `docs/reference/mcp.md`
- `docs/release.md` → `docs/how-to/release.md`

**Stubs** achtergelaten op de oude paden (`docs/cli.md`, `docs/mcp.md`, `docs/release.md`) met `status: deprecated` en een verwijzing naar de nieuwe locatie — voor mogelijke externe links.

**`docs/index.md`** nieuw aangemaakt: één alinea wat het project is, link naar de `README`, en links naar de aanwezige secties (reference, how-to).

**Front matter** (YAML) op elke pagina: `status` + `last_reviewed`, **geen `owner`**. Gemigreerde pagina's zonder inhoudelijke review = `status: draft`, `last_reviewed: 2026-07-13` (migratiedatum).

**Lege mappen weggelaten**: geen `explanation/` (nog geen ADR's).

**`.mcp.json`** stond al in de root uit de seed en klopt met de template (handbook-URL = placeholder `TODO-change-3`) — ongewijzigd gelaten.

## Zelfcheck tegen het contract ✓
- Alleen `reference/`, `how-to/` en `docs/index.md` + de expliciet gesanctioneerde stubs dragen markdown.
- Elke pagina (7 stuks) heeft geldige front matter; nergens een `owner`-veld.
- Eén taal: Engels.
- Licentie MIT ongewijzigd; README ongewijzigd (blijft de bron, `index.md` verwijst ernaar).

## Wat ik NIET gedaan heb (rol-grenzen)
- **Taak 4.1 (PR + merge)**: niet uitgevoerd. Volgens de builder-rol ("never merge; merges belong to Mark") en taak 1.1 ("de habitat-harness beheert branches en pusht") is dit voor de harness/Mark. De commit-titel is al `docs: apply handbook docs contract` zodat die als PR-titel bruikbaar is.
- Geen wijzigingen aan `CLAUDE.md`, `.claude/agents/` of CI.

### Voorgestelde PR-body (per contractpunt afgevinkt)
- [x] `docs/` volgens contract-layout (index + reference/ + how-to/; lege mappen weggelaten)
- [x] Front matter op elke pagina (`status` + `last_reviewed`, geen `owner`)
- [x] Gemigreerd-zonder-review → `status: draft`, `last_reviewed: 2026-07-13`
- [x] Bestaande docs gemigreerd; stubs achtergelaten op oude paden
- [x] `docs/index.md` verwijst naar README (vervangt niet)
- [x] Eén taal: Engels
- [x] `.mcp.json` met placeholder `TODO-change-3`
- [x] Licentie MIT ongewijzigd (bewuste afwijking)

STOP — Mark merget.
