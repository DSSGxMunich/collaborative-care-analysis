
The documentation is an [MkDocs](http://www.mkdocs.org/) site. The pages are in
`docs/docs/` and the configuration (including navigation) is in
`docs/mkdocs.yml`. It uses only the built-in theme, so it builds and renders
offline.

From the repository root:

    uv sync                                   # installs mkdocs (dev dependency)
    uv run mkdocs serve -f docs/mkdocs.yml    # live preview at http://127.0.0.1:8000
    uv run mkdocs build -f docs/mkdocs.yml    # static site in docs/site/ (git-ignored)

The built `docs/site/index.html` can also be opened directly in a browser.
