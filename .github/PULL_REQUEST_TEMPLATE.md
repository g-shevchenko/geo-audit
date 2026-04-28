<!--
Thanks for the PR. Read CONTRIBUTING.md before opening.
Remove sections that don't apply.
-->

## Summary

One paragraph: what changed, why.

Linked issue: # 

## Type of change

- [ ] Bug fix (no API change)
- [ ] New module (one PR per module)
- [ ] Documentation
- [ ] Refactor (no behavior change)
- [ ] Methodology change (requires RFC discussion in linked issue)
- [ ] CI / repo hygiene

## Pre-flight checklist

Tick every box. PRs without these will be returned for completion.

- [ ] **Issue opened and discussed** before writing code
- [ ] `bash scripts/agent-preinstall-check.sh` exits 0
- [ ] `bash scripts/public-release-audit.sh` exits 0
- [ ] **No new external dependencies** (or justified in PR description)
- [ ] **Tests added** for behavior changes
- [ ] **Docs updated** if user-visible behavior changed
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Commit signed (`git commit -s`, DCO)
- [ ] No secrets or internal infra references

## Test plan

How a reviewer can verify this:

```bash
# Step-by-step commands a reviewer can copy-paste
```

## Methodology / scoring impact

- [ ] No score formulas changed
- [ ] Score formula changed (specify which module, why; methodology version
      bumped in `docs/methodology.md`)

## Notes

Anything else the reviewer needs to know.
