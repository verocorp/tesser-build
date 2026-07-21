"""Keep pytest out of ``testdata/``.

The fixture trees are analyzer INPUT, not tests. ``testdata/tb031/*_tree/``
introduced the first fixtures whose filenames match pytest's ``python_files``
pattern, which made a root-level ``pytest ./tessercheck-py`` fail collection on
the duplicate basename — and, worse, import the deliberately non-conformant
``bad_tree`` module and collect its function as a live test.

``testpaths`` in pyproject.toml only applies when pytest's rootdir resolves to
this directory; this conftest is found by walking up from the collected file, so
it holds wherever the run starts.
"""

collect_ignore_glob = ["testdata/*", "testdata/**/*"]
