# `.codex_cache`

This directory exists so the devcontainer can bind-mount it to `/home/vscode/.codex`.

Purpose:
- Persist Codex login/auth state between devcontainer rebuilds.
- Persist Codex local history, session context, and related state between rebuilds.
- Keep that state inside this repository checkout rather than in a host-global location.

How it is intended to be used:
- The devcontainer mount will point this directory at `/home/vscode/.codex`.
- After the container starts, Codex will populate this directory with its runtime files.
- This file stays in git so the directory exists after a fresh checkout and the bind mount has a valid source path.

Git behavior:
- Real Codex state in this directory should remain untracked.
- `.gitignore` is configured to ignore everything here except this `readme.md`.

Notes:
- This directory may contain sensitive local auth/session material once populated.
- Do not manually edit files created here by Codex unless debugging a specific issue.
