# GitHub Repository Operations Toolset

Repository onboarding and bounded snapshot utilities imported from `kaibuzz0/Git-hub-command-site`.

## Included

- `connectors/export_repo_snapshot.py` — content-bounded, secret-avoiding repository metadata exporter.
- `scripts/onboard_repository.py` — generates a portable connector kit for another repository.

## Usage

Export a bounded snapshot from a repository checkout:

```bash
python blueprints/toolsets/github-repo-ops/connectors/export_repo_snapshot.py \
  --repo-id hive-os \
  --full-name kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-
```

Generate a connector kit:

```bash
python blueprints/toolsets/github-repo-ops/scripts/onboard_repository.py \
  --repo-id example \
  --full-name owner/repo \
  --snapshot-url https://raw.githubusercontent.com/owner/repo/main/.command-site/repo-snapshot.json
```

## Release scope

Repo-development tooling only. It remains under `blueprints/` and is excluded from Hive release manifests.
