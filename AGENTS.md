# Public repository identity

This repository is public. Before creating any commit, set and verify these
repository-local values; never inherit a personal name or email from global Git
configuration:

```powershell
git config --local user.name cncagn
git config --local user.email 176000094+cncagn@users.noreply.github.com
git config --local user.useConfigOnly true
```

Check the effective author and committer identity, including environment
overrides, with `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT`.
Both must use the approved alias and GitHub noreply address above.

Before publishing, inspect author/committer metadata and commit-message trailers
in every outgoing commit. Do not publish personal identity from local Git config
or add personal `Co-authored-by` trailers.

When merging through GitHub CLI, explicitly pass
`--author-email 176000094+cncagn@users.noreply.github.com`; local Git config does
not control GitHub's server-created merge author email.

Keep local account configuration, cookies, study history, logs, research
downloads and private backups outside the tracked file set. Do not commit any
file under the ignored local `Autovisor/` install and backup directory.
