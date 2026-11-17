# Publishing SBOA

The root `pyproject.toml` owns the version, dependencies and package metadata.
Use Linux with Python 3.9–3.11 to build from the repository root:

```bash
python -m pip install build twine
python -m build
python -m twine check --strict dist/*
python tools/check_distribution.py dist --tag v1.0.7
```

Use an empty `dist` directory. The tag must match `v` followed by the project
version. The source distribution and wheel include SBOA's runtime resources,
scripts, MIT license and authors. Tests remain in the checkout under `src/tests`
and are excluded from both artifacts, following the other BOA components.

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

## Release workflow

Configure PyPI Trusted Publishing for the `sboa` project with repository owner
`danielbrosnan`, repository `sboa`, workflow `sboa-publish.yml`, and environment
`pypi`. Create the corresponding GitHub environment before releasing. If the
repository is hosted under another owner, use that owner in the publisher setup.

Update the project version, commit the release changes, and wait for packaging
and integration checks to pass. Publish a GitHub release with the matching
`v<version>` tag, for example `v1.0.7`. The release workflow verifies the tag and
uploads the checked Python 3.11 artifacts using the PyPI environment's identity.
Pushes and pull requests only validate artifacts. Previously uploaded PyPI
versions cannot be replaced; fixes require a new version and release.
