# `.vscode_cache`

This directory exists so the devcontainer can bind-mount it to `/home/vscode/.vscode-server`.

Purpose:
- Persist VS Code Server extensions, cached binaries, and related local state between devcontainer rebuilds.
- Reduce repeated setup work when the container is recreated.
- Keep that state inside this repository checkout rather than in a host-global location.

How it is intended to be used:
- The devcontainer mount will point this directory at `/home/vscode/.vscode-server`.
- After the container starts, VS Code Server will populate this directory with its runtime files.
- This file stays in git so the directory exists after a fresh checkout and the bind mount has a valid source path.

Git behavior:
- Real VS Code Server state in this directory should remain untracked.
- `.gitignore` is configured to ignore everything here except this `readme.md`.

Notes:
- This directory may contain large cached files and extension data once populated.
- Do not manually edit files created here by VS Code Server unless debugging a specific issue.
