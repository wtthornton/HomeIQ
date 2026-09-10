"""automation-domain test suite (TAP-7275).

This file is load-bearing, not decorative. The suite imports its subject as
``src.<slice>....``; under pytest's default ``prepend`` import mode the
directory put on ``sys.path`` is the first parent of a test module that has no
``__init__.py``. Each folded service used to carry ``tests/__init__.py``, so
that walk stopped at the service root and ``src`` was importable. The fold
re-homed those files as ``tests/agent/``, ``tests/authoring/`` and
``tests/proactive/`` without a package marker at ``tests/``, so the walk
stopped one level early at ``tests/`` and all 62 modules failed collection with
``ModuleNotFoundError: No module named 'src'``.
"""
