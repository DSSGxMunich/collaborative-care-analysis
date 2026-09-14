"""The approved list of cluster modules to build.

Kept in its own module, apart from the harness, for two reasons:

* **Adding a cluster touches one line here and nothing else.** ``build.py``,
  ``drops.py`` and ``unclustered.py`` all read the list from here, so a branch
  adding a cluster no longer edits the harness and cannot collide with another
  cluster branch anywhere except this list.
* **It breaks a dependency cycle.** ``drops`` and ``unclustered`` need to know
  which clusters exist; when that list lived in ``build``, which imports the
  cluster modules, they had to import ``build`` and ``build`` had to defer its
  own import of ``unclustered`` to function scope. Both now depend on this
  module, which depends on neither.

The list stays explicit rather than globbing the package: a cluster is built
only once its design has been approved at the Step 3 checkpoint in
PROMPT_column_harmonization.md. Auto-discovery would pull a half-finished
module into the build the moment it was saved.
"""

import importlib
from types import ModuleType

PACKAGE = "collaborative_care_analysis.harmonization_column_clusters"

# Approved clusters, one per line and alphabetical so appends merge cleanly.
IMPLEMENTED_CLUSTERS = [
    "sex",
]

# The contract every cluster module satisfies. Checked on load so a module that
# is listed before it is finished fails loudly here, naming what it lacks,
# rather than with an AttributeError from somewhere inside the build.
REQUIRED_ATTRIBUTES = (
    "CLUSTER_KEY",
    "HARMONIZED_COLS",
    "harmonize",
    "COLUMN_PROVENANCE",
    "CONSUMPTION",
)


def cluster_modules() -> list[ModuleType]:
    """Import and return every approved cluster module, in list order."""
    modules = []
    for name in IMPLEMENTED_CLUSTERS:
        module = importlib.import_module(f"{PACKAGE}.{name}")
        if missing := [attr for attr in REQUIRED_ATTRIBUTES if not hasattr(module, attr)]:
            raise AttributeError(
                f"Cluster module {name!r} is listed in IMPLEMENTED_CLUSTERS but does not "
                f"define {missing}; every cluster must provide {list(REQUIRED_ATTRIBUTES)}."
            )
        modules.append(module)
    return modules
