from pathlib import Path
from typing import Any, Mapping, Sequence

from jinja2 import FileSystemLoader

from resume_generator.data.accessor import DBAccessor
from resume_generator.import_functions import get_functions_by_prefix_from_modules
from resume_generator.templates.environment import TypedVariableEnvironment


def new_template_environment(
    templates_dir: Path,
    filters_modules: str | Sequence[str] = None,
    filters_func_prefix: str = "jinja_filter",
    tests_modules: str | Sequence[str] = None,
    tests_func_prefix: str = "jinja_test",
    trim_func_prefix: bool = True,
    db_accessor: DBAccessor = None,
    globals_mapping: Mapping[str, Any] = None,
    **jinja2_env_kwargs,
) -> TypedVariableEnvironment:
    """Build a `TypedVariableEnvironment` wired up with filters, tests, and globals.

    Discovers Jinja2 filter/test functions by name prefix from
    `resume_generator.templates.filters`/`resume_generator.templates.tests` plus any
    additional modules given, and registers them on the returned
    environment. A `DBAccessor` (or plain mapping) can be supplied as the
    environment's globals so templates can query the database directly.

    Args:
        templates_dir: The directory to load templates from.
        filters_modules: Additional dotted module path(s) to search for
            filter functions.
        filters_func_prefix: The function name prefix that marks a function
            as a Jinja2 filter.
        tests_modules: Additional dotted module path(s) to search for test
            functions.
        tests_func_prefix: The function name prefix that marks a function as
            a Jinja2 test.
        trim_func_prefix: Whether to strip the prefix from the registered
            filter/test name.
        db_accessor: A `DBAccessor` (or mapping) to use as the environment's
            globals, enabling database access from templates.
        globals_mapping: Additional global variables to merge into the
            environment's globals.
        **jinja2_env_kwargs: Additional keyword arguments passed through to
            `TypedVariableEnvironment`/`jinja2.Environment`.
            See [Jinja2.Environment docs](https://jinja.palletsprojects.com/en/stable/api/#jinja2.Environment)

    Returns:
        A configured `TypedVariableEnvironment`.
    """
    filter_module_names = ["resume_generator.templates.filters"]
    if isinstance(filters_modules, str):
        filter_module_names.append(filters_modules)
    elif isinstance(filters_modules, Sequence):
        filter_module_names = [*filters_modules, *filter_module_names]
    filters_dict = get_functions_by_prefix_from_modules(filter_module_names, filters_func_prefix, trim_func_prefix)

    tests_module_names = ["resume_generator.templates.tests"]
    if isinstance(tests_modules, str):
        tests_module_names.append(tests_modules)
    elif isinstance(tests_modules, Sequence):
        tests_module_names = [*tests_modules, *tests_module_names]
    tests_dict = get_functions_by_prefix_from_modules(tests_module_names, tests_func_prefix, trim_func_prefix)

    environment_loader = FileSystemLoader(searchpath=templates_dir)
    environment = TypedVariableEnvironment(loader=environment_loader, **jinja2_env_kwargs)
    environment.globals = db_accessor if db_accessor else {}

    if globals_mapping:
        environment.globals.update(globals_mapping)
    environment.filters.update(filters_dict)
    environment.tests.update(tests_dict)

    return environment
