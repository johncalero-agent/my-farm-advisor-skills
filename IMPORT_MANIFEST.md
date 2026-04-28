# Import Manifest

This manifest tracks planned and completed imports for `my-farm-advisor-skills`. Each entry must retain the full provenance field set even before import execution.

## my-farm-advisor

- source_repo: https://github.com/borealBytes/my-farm-advisor.git
- source_local_path: N/A
- source_ref: main
- source_commit: 4a82ab779e8374035ca5e15f1cb1c0571395dc3d
- source_status: clean remote ref
- source_path: .
- destination_path: my-farm-advisor/
- import_date: 2026-04-28 (planned)
- exclusions: `.git/`, large/generated assets not required for skill packaging, any repo-local CI or deployment files that do not contribute to the imported skill set
- local_modifications: None yet; import not executed
- update_procedure: Run `git ls-remote https://github.com/borealBytes/my-farm-advisor.git refs/heads/main`, confirm the SHA, copy the approved source subset from repo root into `my-farm-advisor/`, then document any repo-specific edits in the final provenance record.

## my-farm-breeding-trial-management

- source_repo: TBD - backfill the authoritative upstream repo URL before import
- source_local_path: /media/clay/Data/dev/scientific-agent-skills-worktrees/scientific-agent-skills-breeding-trial-management
- source_ref: feat/breeding-trial-management
- source_commit: f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1
- source_status: untracked worktree: scientific-skills/breeding-trial-management/
- source_path: scientific-skills/breeding-trial-management/
- destination_path: my-farm-breeding-trial-management/
- import_date: 2026-04-28 (planned)
- exclusions: remote backfill metadata not yet captured; `.git/`; any unrelated scientific skills outside `scientific-skills/breeding-trial-management/`
- local_modifications: None yet; import not executed. Remote provenance backfill still required before first refresh.
- update_procedure: Before import, record the authoritative upstream repo URL plus resolved branch/tag SHA, then rerun `git branch --show-current`, `git rev-parse HEAD`, and `git status --short` in the local worktree, copy only `scientific-skills/breeding-trial-management/`, and convert this planned entry into a completed provenance record.

## my-farm-qtl-analysis

- source_repo: TBD - backfill the authoritative upstream repo URL before import
- source_local_path: /media/clay/Data/dev/scientific-agent-skills-worktrees/scientific-agent-skills-qtl-analysis
- source_ref: feat/qtl-analysis
- source_commit: f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1
- source_status: untracked worktree: scientific-skills/qtl-analysis/
- source_path: scientific-skills/qtl-analysis/
- destination_path: my-farm-qtl-analysis/
- import_date: 2026-04-28 (planned)
- exclusions: remote backfill metadata not yet captured; `.git/`; any unrelated scientific skills outside `scientific-skills/qtl-analysis/`
- local_modifications: None yet; import not executed. Remote provenance backfill still required before first refresh.
- update_procedure: Before import, record the authoritative upstream repo URL plus resolved branch/tag SHA, then rerun `git branch --show-current`, `git rev-parse HEAD`, and `git status --short` in the local worktree, copy only `scientific-skills/qtl-analysis/`, and convert this planned entry into a completed provenance record.
