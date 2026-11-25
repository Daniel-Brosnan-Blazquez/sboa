# Publishing SBOA

SBOA's distribution name is `sboa`. Package metadata and the release version
live in `pyproject.toml`. Follow these steps to build, install, and publish a
release on PyPI.

## Validate a release locally

Use a virtual environment with Python 3.9 or newer, such as the environment
inside the development container. From the repository root:

```bash
python -m pip install build twine
python -m build
python -m twine check --strict dist/*
python tools/check_distribution.py dist --tag v1.0.7
```

Use an empty `dist` directory. The tag must match `v` followed by the project
version. The source distribution and wheel include SBOA's runtime resources,
scripts, MIT license and authors. Tests remain in the checkout under `src/tests`
and are excluded from both artifacts.

Install an SBOA artifact in a clean environment.
From outside the checkout, run the installed-resource checker using its absolute
path:

```bash
python -m pip install /path/to/sboa/dist/sboa-1.0.7-py3-none-any.whl
python -m pip check
cd /tmp
python /path/to/sboa/tools/check_installed_resources.py
```

The checker verifies imports, resources, commands and the initializer's bundled
SQL model without executing database commands. The `sboa-publish.yml` workflow
builds and checks artifacts, installs both the wheel and source distribution,
and runs these checks on Python 3.9 and 3.11. Database integration tests run in
the separate `sboa-testing.yml` workflow.

The build matrix uses `ubuntu-24.04` because Python 3.9 builds are unavailable
for Ubuntu 26.04. Keep the runner pinned while Python 3.9 remains in the matrix.

## Publish a release

1. Update `[project].version` in `pyproject.toml` for subsequent releases. Each
   PyPI release needs a new version. Read the installed version with
   `importlib.metadata.version("sboa")`.
2. Commit and push the release changes. Confirm the packaging and integration
   workflows pass.
3. Create and publish a GitHub release whose tag is exactly `v` followed by the
   package version, for example `v0.1.0`, targeting the validated commit.
4. The `sboa-publish.yml` workflow checks the tag against the package version,
   builds the wheel and source distribution, validates their metadata, and
   tests their installations. Its final job uploads those same artifacts to
   PyPI through the `pypi` environment.
5. Verify the release at [SBOA on PyPI](https://pypi.org/project/sboa/) and install
   it in a fresh environment with `python3 -m pip install sboa==0.1.0`.

Pushes, pull requests, and manual workflow runs only build and validate; a
published GitHub release triggers the upload. GitHub prereleases also upload,
so use a PEP 440 prerelease version such as `0.2.0rc1` and tag `v0.2.0rc1` when
publishing a release candidate.

## Manual upload

To upload directly to PyPI, complete the local validation above and configure
your PyPI API token locally, then run:

```bash
python3 -m twine upload dist/*
```
