# Releasing

The package is `django-djadmin` on PyPI; the import name is `djadmin`.

> There is an unrelated `djadmin` distribution on PyPI (an old admin theme)
> whose import name is also `djadmin`. Installing both in one environment would
> collide. Ours is only ever installed as `django-djadmin`.

## 1. Prepare

1. Bump the version in `src/djadmin/__init__.py` — `pyproject.toml` reads it
   from there, so there is one source of truth.
2. Add the release to `CHANGELOG.md`.
3. Run the suite and the demo:

   ```bash
   uv run demo/manage.py test shop
   uv run demo/manage.py check --deploy
   ```

## 2. Build and verify

```bash
rm -rf dist
uv build
uv run --with twine twine check dist/*
```

Then prove the artifact stands on its own — install the wheel into a throwaway
environment with no source tree on the path, and render the admin from it:

```bash
uv venv /tmp/djadmin-check/.venv
uv pip install --python /tmp/djadmin-check/.venv/bin/python "dist/django_djadmin-*.whl[mfa]"
```

A wheel that builds is not the same as a wheel that works: templates, static
files and migrations are package *data*, and it is data that silently goes
missing. Check for `djadmin/templates/admin/base.html` and
`djadmin/static/djadmin/css/djadmin.css` inside the wheel before publishing.

## 3. Publish

Test on TestPyPI first — an uploaded version number can never be reused on
PyPI, even after deletion:

```bash
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
uv publish dist/*
```

Authenticate with a PyPI API token (`UV_PUBLISH_TOKEN`, or `--token`). Prefer a
project-scoped token, or configure Trusted Publishing so no token is stored at
all.

## 4. Tag

```bash
git tag -a v0.1.0 -m "djadmin 0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --notes-from-tag
```
