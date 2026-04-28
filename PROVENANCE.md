# Import Provenance Template

Every imported skill or source snapshot in this repository must ship with a provenance record that is committed alongside the import.

## Required record for every import

Use the template below for each import. Keep every field present. If a field does not apply, write `N/A` and explain why.

```md
## <import-name>
- source_repo: <git URL or N/A when local-only>
- source_local_path: <absolute local path or N/A when remote-only>
- source_ref: <branch or tag used for the import>
- source_commit: <resolved 40-character SHA or N/A when there is no clean commit snapshot>
- source_status: <clean remote ref | clean worktree | modified worktree | untracked worktree | detached HEAD | N/A>
- source_path: <path within the source repo/worktree>
- destination_path: <path within this repository>
- import_date: <YYYY-MM-DD>
- exclusions: <files, directories, assets, or behaviors intentionally not imported>
- local_modifications: <changes made after copy/import relative to the recorded source>
- update_procedure: <exact steps to refresh from upstream>
```

## Source-ref verification policy

1. Resolve every remote branch or tag to a commit SHA before copying files. Never record only a branch name.
2. For authenticated Omni/Wrighter imports, run this precheck before import or refresh:

   ```bash
   git ls-remote git@github.com:borealBytes/omni.git refs/heads/feature/wrighter-delivery
   ```

   Record the returned SHA as `source_commit` and keep `source_ref: feature/wrighter-delivery`.
3. For public remotes, record the exact ref plus the resolved SHA from `git ls-remote <repo> refs/heads/<branch>` or `refs/tags/<tag>`.
4. For local worktrees, capture all of the following before import:

   ```bash
   git branch --show-current
   git rev-parse HEAD
   git status --short
   ```

   Record the branch/tag in `source_ref`, the HEAD SHA in `source_commit`, and the worktree state in `source_status`.
5. If the imported content comes from uncommitted local worktree files, explicitly say so in `source_status` (for example `untracked worktree: scientific-skills/breeding-trial-management/`).
6. Update or refresh work must repeat the same verification step and replace the recorded SHA/status before files are copied.

## Update checklist

1. Re-run the source-ref verification step.
2. Compare current upstream/local content against the last recorded `source_commit` or `source_status`.
3. Re-copy only the intended `source_path` into `destination_path`.
4. Re-apply any `local_modifications` intentionally kept in this repo.
5. Update the provenance record, manifest entry, and related QA evidence in the same commit.
