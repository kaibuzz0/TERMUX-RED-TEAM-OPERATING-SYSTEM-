# Repo Factory Toolset

Reusable bootstrap kit for new AI-assisted GitHub repositories. Imported from `kaibuzz0/cipher-solving-suite`.

## Purpose

Install a compact operating foundation into a new repository so humans and AI agents can immediately understand project intent, current state, research, work ownership, handoffs, integration requirements, and exact CI failures.

## Export

```bash
python blueprints/toolsets/repo-factory/export_toolset.py /path/to/new-repo --project-name "My Project"
```

Preview only:

```bash
python blueprints/toolsets/repo-factory/export_toolset.py /path/to/new-repo --project-name "My Project" --dry-run
```

Existing files are not overwritten unless `--force` is supplied.

## Release scope

Repository-development tool only. It lives under `blueprints/`, which Hive excludes from release manifests.
