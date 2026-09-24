import builtins
import logging
import re
from difflib import get_close_matches
from typing import Any, MutableMapping, Optional, Type, Union

from click import Choice
from jinja2 import FileSystemLoader, TemplateSyntaxError
from jinja2.environment import Environment, Template
from jinja2.meta import find_undeclared_variables
from jinja2.runtime import StrictUndefined

logger = logging.getLogger(__name__)


class TypedVariableEnvironment(Environment):
    """A `jinja2.Environment` that pre-processes templates to support typed variables.

    Allows template authors to specify variable types using PEP 484
    annotation syntax. Typed variables can be useful when prompting users for
    the value of undefined variables.

    Variables won't appear in `undeclared_variables` until the template is
    read via `get_template()`. Resist the urge to call `get_template()` and
    `Template.render()` back-to-back in the same loop; instead:

    1. Iterate through `list_templates()`, calling `get_template()` on each
       item and storing the resulting `Template` in a list.
    2. Use the keys/values of `undeclared_variables` to prompt the user for
       missing values.
    3. Update `globals` with the user's inputs.
    4. Validate the values in `globals` against the types recorded in
       `type_registry`.
    5. Finally, render the list of `Template` objects.

    Attributes:
        type_registry: Maps every variable name found while pre-processing a
            template to its declared (or inferred) type. Populated during
            `preprocess()`; a variable with no explicit type annotation
            defaults to `str`.
        undeclared_variables: The subset of `type_registry` whose variables
            have no defined value yet, populated by `update_undeclared_variables()`.
    """

    loader: FileSystemLoader

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, undefined=StrictUndefined)
        """
        StrictUndefined is required as jinja2.meta.find_undeclared_variables will not detect any
        undeclared variables when the default of jinja2.runtime.Undefined is used.
        """

        self.type_registry: dict[str, type | object] = {}
        """
        Used to assign types to keys in self.undeclared_variables.
        Is populated during pre-process, marking a variable as the found type. Type defaults to str if none is found.
        Should contain every variable.
        """

        self.undeclared_variables: dict[str, type] = {}
        """
        The keys/values from self.type_registry who have no defined value.
        """

    def preprocess(self, source, name=None, filename=None):
        """
        - Extracts the PEP 484 type from the template variable tag, if it exists.
        - The variable name and type are stored in a dict 'Environment.type_registry'.
        - If no type annotation is found, the variable will be mapped to type 'str'.
        - The type annotation (: $type_name) is removed from the template source before handing it back
          to the parent class jinja2.environment.Environment's 'preprocess' method.
        """

        # In case it's not '{{' and '}}', we need to escape them because they probably still contain braces
        start_string = "".join(["\\" + char for char in self.variable_start_string])
        end_string = "".join(["\\" + char for char in self.variable_end_string])
        var_pattern = r"(\w+)"
        type_pattern = r"(\w+)"
        type_args_pattern = r"([\(\[]\[.+\][\)\]])"
        match_pattern = (
            start_string
            + r"\s*"
            + var_pattern
            + r"\s*:\s*"
            + type_pattern
            + r"\s*(?:"
            + type_args_pattern
            + r")?\s*"
            + end_string
        )

        for match in re.finditer(match_pattern, source):
            var_name, var_type_str, var_type_args = match.groups()
            var_type_str = var_type_str if var_name is not None else "str"

            if "Choice" == var_type_str.strip():
                choice_args = var_type_args.lstrip("(").rstrip(")")
                self.type_registry[var_name] = Choice(eval(choice_args))

                continue

            var_type = getattr(builtins, var_type_str) if hasattr(builtins, var_type_str) else str
            self.type_registry[var_name] = var_type

        clean_source = re.sub(
            match_pattern,
            rf"{self.variable_start_string} \1 {self.variable_end_string}",
            source,
        )

        return super().preprocess(clean_source, name, filename)

    def _closest_global_match(self, name: str) -> str | None:
        """Return the known global name `name` most likely mistypes, or None if it isn't close to any."""
        matches = get_close_matches(name, list(self.globals.keys()), n=1, cutoff=0.7)
        return matches[0] if matches else None

    def update_undeclared_variables(self, source: str, template_name: str = None):
        ast = self.parse(source)
        undeclared_variables = list(find_undeclared_variables(ast))
        for var_name in undeclared_variables:
            closest_match = self._closest_global_match(var_name)
            if closest_match is not None:
                location = f" in '{template_name}'" if template_name else ""
                raise NameError(
                    f"Template{location} references undefined variable '{var_name}', which is too close to "
                    f"known global '{closest_match}' to treat as a real input - did you mean '{closest_match}'?"
                )

        if undeclared_variables:
            input_variables = {var_name: self.type_registry.get(var_name, str) for var_name in undeclared_variables}
            self.undeclared_variables.update(input_variables)

    def get_template(
        self,
        name: Union[str, "Template"],
        parent: Optional[str] = None,
        _globals: Optional[MutableMapping[str, Any]] = None,
    ) -> "Template":
        """
        Based on jinja2.Environment's original get_template method, adding the call to update_undeclared_variables.
        """
        if isinstance(name, Template):
            return name

        if parent is not None:
            name: str = self.join_path(name, parent)

        source, _, _ = self.loader.get_source(self, name)

        try:
            self.update_undeclared_variables(source, template_name=name)
        except TemplateSyntaxError as e:
            logger.error(f"Syntax error at: {name}:{e.lineno}")
            raise e

        template = self._load_template(name, _globals)
        return template

    def from_string(
        self,
        source: Union[str],
        _globals: Optional[MutableMapping[str, Any]] = None,
        template_class: Optional[Type[Template]] = None,
    ) -> "Template":
        """
        Based on jinja2.Environment's original from_string method, adding the call to update_undeclared_variables.
        """
        self.update_undeclared_variables(source)
        gs = self.make_globals(_globals)
        cls = template_class or self.template_class
        return cls.from_code(self, self.compile(source), gs, None)
