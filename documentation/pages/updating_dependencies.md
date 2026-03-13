# Updating Dependencies

OpsDeck pins all Python dependencies to exact versions (`==`) in `requirements.txt` and `requirements-dev.txt` to ensure reproducible builds and accurate Trivy vulnerability scanning.

## Quick Start

Run the update script from the project root:

```bash
./update-deps.sh
```

This will unpin all versions, install the latest, re-freeze, show the diff, and run tests. If everything passes, commit as suggested.

You can pass extra arguments to pytest:

```bash
./update-deps.sh -x -v          # stop on first failure, verbose
./update-deps.sh -k test_auth   # only run auth tests
```

## What the Script Does

1. **Unpin** — strips `==X.Y.Z` from both requirements files
2. **Upgrade** — `pip install --upgrade` resolves latest compatible versions
3. **Freeze** — writes `requirements.locked.txt` and updates both requirements files with exact versions
4. **Diff** — shows what changed
5. **Test** — runs pytest against the database

## Updating a Single Package

```bash
venv/bin/pip install --upgrade <package-name>
venv/bin/pip show <package-name> | grep Version
# Edit requirements.txt with the new version
```

## Trivy Scanning

After updating, rebuild the Docker image and scan:

```bash
docker compose build web
trivy image opsdeck-web:latest
```
