# v0.1.0 Release Playbook

Step-by-step shipping checklist. Each step has a concrete command; run from the repo root unless stated otherwise.

## Pre-flight (before tagging)

- [ ] All tests pass: `python -m pytest` (expect 92 passed as of 2026-04-21).
- [ ] Validation harness clean: `python -m src.validation` → `validation: clean`.
- [ ] Sentinel scan clean: `python -m sentinel scan --repo .` → `BLOCK=0`.
- [ ] Full-corpus analysis artifacts present (or provisional non-reproducible-subset only):
  - `outputs/full_method_results.parquet` or `outputs/nr_method_results.parquet`
  - `outputs/flips.parquet` or `outputs/nr_flips.parquet`
  - `outputs/flip_rates_current.json`
  - `docs/index.html` or `docs/non_reproducible_index.html`
- [ ] Regression snapshot pinned: `tests/snapshots/flip_rates_v0.1.0.json` contains the full-corpus headline rates.
- [ ] `CHANGELOG.md` [0.1.0] section filled with final dated entry.
- [ ] `paper/manuscript.md` — numerical placeholders (XX.X%) replaced with real Phase 9 figures.

## Merge feature branch to master

```bash
git checkout master
git merge --no-ff feat/v0.1-implementation \
    -m "Merge v0.1.0 implementation — analytical pipeline + non-reproducible-subset seed results"
```

## Tag

```bash
git tag -a v0.1.0 -m "v0.1.0 — initial demonstrator release

Analytical pipeline + 92 tests + stratified flip-rate analysis on the
non-reproducible subset (n=680 MAs). Full-corpus run pending.

Seed result: DL -> REML+HKSJ+PI changes the significance judgement
in 15.7% of non-reproducible MAs. Paper in preparation for Research
Synthesis Methods."
```

Do NOT `--force` anything; use a new tag if v0.1.0 ever needs revision (`v0.1.1`).

## Create GitHub repo + push

```bash
# Auth (once, if not already)
gh auth status
# If needed: gh auth login

# Create public repo + push
gh repo create mahmood726-cyber/cochrane-modern-re \
    --public \
    --description "Modern random-effects methods vs RevMan defaults across Cochrane pairwise meta-analyses" \
    --source=. \
    --remote=origin \
    --push

# Push the tag
git push origin v0.1.0
```

This triggers `.github/workflows/validate.yml` for the release. Wait for it to go green before continuing (it runs the non-corpus test subset + uploads artifacts).

## Enable GitHub Pages

```bash
gh api repos/mahmood726-cyber/cochrane-modern-re/pages \
    -X POST \
    -f 'source[branch]=master' \
    -f 'source[path]=/docs'
```

Verify at `https://mahmood726-cyber.github.io/cochrane-modern-re/` (may take 1-2 minutes).

## Mint Zenodo DOI

1. Log in at https://zenodo.org.
2. Go to **GitHub** settings → enable the `cochrane-modern-re` repo toggle.
3. Return to the GitHub repo → Releases → Draft a new release → pick tag `v0.1.0` → publish.
4. Zenodo indexes automatically within ~2 minutes and assigns a DOI (e.g. `10.5281/zenodo.NNNNNNN`).
5. Update `paper/references.bib` @software entry:

```bibtex
@software{cochrane_modern_re_v0_1_0,
  author       = {Ahmad, Mahmood},
  title        = {cochrane-modern-re v0.1.0},
  year         = {2026},
  doi          = {10.5281/zenodo.NNNNNNN},
  url          = {https://github.com/mahmood726-cyber/cochrane-modern-re}
}
```

Commit the updated bib and push. Use the same DOI in the paper abstract/body where it currently says "TBC".

## Record in portfolio

- `C:\ProjectIndex\INDEX.md` — add/promote `cochrane-modern-re` under the Submission-ready section.
- `C:\E156\rewrite-workbook.txt` — optional E156 micro-companion paper (TBD; this is a full RSM paper, not an E156, but an E156 version could accompany).
- Memory file: update or add `cochrane-modern-re.md` in `~/.claude/projects/C--Users-user/memory/` with the v0.1.0 Zenodo DOI, repo URL, and tier-1 rate.

## Submission to Research Synthesis Methods

Separate from the software release. Rough steps:
1. Fill manuscript placeholders with the full-corpus numbers.
2. Generate figures (Tier-1 rate × k-stratum stacked bar; dashboard screenshot).
3. External methodologist review (ideally one Cochrane CSG-adjacent reviewer).
4. RSM submission portal: https://onlinelibrary.wiley.com/journal/17592887.
5. Manuscript structure must match RSM guidelines (~5–7k words, 3–5 figures, supplement allowed).

## Rollback (only if something goes wrong)

- Wrong tag: `git tag -d v0.1.0 && git push --delete origin v0.1.0`. Issue `v0.1.1` afterwards, never reuse `v0.1.0`.
- Accidentally committed secrets / paths_local.py: rotate first, then `git filter-repo` carefully (destructive — confirm with user before running).
- Pages deployment failure: check the workflow log; rebuild locally with `python analysis/04_build_dashboard.py --out docs/index.html`.
