import importlib
import pkgutil
from inspect import isfunction
from typing import Iterable


def import_submodules(module_name: str, recursive: bool = True, has_attr_filter: str = None):
    if isinstance(module_name, str):
        module_name = importlib.import_module(module_name)

    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(module_name.__path__, module_name.__name__ + "."):
        try:
            module = importlib.import_module(name)
        except ImportError as e:
            raise ImportError(
                f"Failed to import submodule '{name}' while discovering submodules of '{module_name.__name__}': {e}"
            ) from e

        if isinstance(has_attr_filter, str) and hasattr(module, has_attr_filter) or has_attr_filter is None:
            results[name] = module

        if recursive and is_pkg:
            results.update(import_submodules(name, recursive, has_attr_filter))

    return results


def get_functions_by_prefix_from_modules(
    module_names: Iterable[str], func_name_prefix: str, trim_func_name_prefix: bool = True
):
    func_name_prefix = func_name_prefix.rstrip("_") + "_"
    modules = {
        mod_name: mod for module_name in module_names for mod_name, mod in import_submodules(module_name).items()
    }

    functions_map = {
        func_name[len(func_name_prefix) :] if trim_func_name_prefix else func_name: func
        for module in modules.values()
        for func_name, func in module.__dict__.items()
        if isfunction(func) and func_name.startswith(func_name_prefix)
    }

    return functions_map
