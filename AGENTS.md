**This file is the canonical guardrails + pointers for Codex work in this repo. Tread as immutable unless explicitly told otherwise**

## Project overview
- [`docs/design.md`](docs/design.md)
- [`README.md`](README.md) (end-user)

## Implementation roadmap
- [`docs/roadmap.md`](docs/roadmap.md)

## Ongoing tasks
- [`docs/todo.md`](docs/todo.md)
- [`TODO`](TODO)

## Design contracts (immutable)
- [`docs/design.md`](docs/design.md)
- [`README.md`](README.md)

## Context for Codex
- [`docs/decisions.md`](docs/decisions.md)

## Project file structure (in-file)
- [`custom_components/vklass/`](custom_components/vklass/): Home Assistant integration code.
- [`docs/`](docs/): working docs and design contracts.
- [`test/`](test/): tests ans fixtures.
- [`custom_components/skolmat/`](custom_components/skolmat/): Home Assistant reference integration code, should be ignored, never changed, immutable
- Project settings are normally defined in [`.vscode/settings.json`](.vscode/settings.json), but [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) or [`workspace.code-workspace`](workspace.code-workspace) may also be used depending on setting.


## Devcontainer model (in-file)
- [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json)
- Post-create runs `container setup-project` -> [`.devcontainer/setup-project`](.devcontainer/setup-project).
- Bootstraps HA [`.storage`](.storage) from [`.devcontainer/ha_config_bootstrap/.storage`](.devcontainer/ha_config_bootstrap/.storage).
- Ports: 8123 (HA) and 5678 (debugpy).

## Home Assistant system model
- [`/home/vscode/ha_config/`](/home/vscode/ha_config/): Home Assistant configuration dir
- [`/home/vscode/ha_core/`](/home/vscode/ha_core/): Home Assistant Core repository and installation dir
- [`/workspace/vklass`](/workspace/vklass): Repo mount dir
- [`/workspace/vklass/.devcontainer/`](/workspace/vklass/.devcontainer/): devcontainer setup dir. Usefull for understanding system setup and installation procedure

## Generic guardrails (in-file)
- Comply always to Home Assistant best practice and design patterns
- Assume a fail fast approact. Do not safeguard things that will have an obvious immmidiate effect. Eg shown in logs or otherwise crashing visibly.
- Align always before modifying files. Explain approach and get approval before modifying files.
- Do not modify design contracts unless explicitly requested.
- Never refactor code outside of the currently discussed scope.
- Only run code generation related to current file / feature.
- Prefer small, reviewable changes; avoid sweeping reformatting.
- When requirements are unclear, pause and ask one question at a time before coding.
- Keep dev docs in [`docs/`](docs/) aligned with actual behavior;
- Alert me when end user docs, eg [`README.md`](README.md) conflicts with implementation.
- Use UTF-8 when Swedish terms or data require it; do not force ASCII where it harms clarity.
- Log important decisions in [`docs/decisions.md`](docs/decisions.md) without waiting for confirmation.
- Dont overengineer things, keep it simple when possible
- If something is not clear in [`AGENTS.md`](AGENTS.md) and [`docs/design.md`](docs/design.md), ask questions and suggest clarifications.
- For any new implementation, follow the coding design style of existing implementation

# In all converstaions
- Acknowledge once that [`AGENTS.md`](AGENTS.md) and [`docs/design.md`](docs/design.md) and [`/docs/roadmap.md`](/docs/roadmap.md) are read, understood and respected.

# Example code and reference implementations (not used in this project)
- [`docs/vklass_sensor_example.py`](docs/vklass_sensor_example.py): example implementation for vklass user/passw login and fetching
- [`docs/curl_fetch_example.py`](docs/curl_fetch_example.py): working example for curl fetch of the calendar page


## Coding style and formatting

* when generating code, respect any formatting config given to ruff in [`.vscode/settings.json`](.vscode/settings.json)