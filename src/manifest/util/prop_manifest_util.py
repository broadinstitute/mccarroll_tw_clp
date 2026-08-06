"""Tools for handling yaml manifests, which are inputs to Launch* commands, and yaml properties files, which
are produced by workflows to summarize analyses."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from util.relative_path_util import RelativePathUtil


class YamlPropManifestUtil:
    YAML_EXTENSION = "yaml"

    @staticmethod
    def downstream_properties_helper(yaml_schema_element: Any, downstream_yaml_as_string: Optional[str]):
        """For converting yaml for downstream workflows that are stored as Optional[str], like alignment, cbrb."""
        if downstream_yaml_as_string is None:
            return None
        return yaml_schema_element.name, yaml.safe_load(downstream_yaml_as_string)

    @staticmethod
    def load(yaml_file: Path) -> Dict[str, Any]:
        """Load a yaml file and give it the right type."""
        with open(yaml_file) as fh:
            loaded = yaml.safe_load(fh)
        return loaded if loaded is not None else {}

    @staticmethod
    def parse(yaml_string: str) -> Dict[str, Any]:
        """Convert a string into a yaml dictionary. Note that this won't work if the top level is a list."""
        return yaml.safe_load(yaml_string)

    @staticmethod
    def absolutize_path_in_yaml(yaml_map: Dict[str, Any], element_name: Any, yaml_path: Path) -> Path:
        """Convert a path stored in a yaml file that is relative to the location of the yaml file to an
        absolute path.

        :param yaml_map: loaded yaml
        :param element_name: name of the path in yaml_map
        :param yaml_path: path to yaml file
        :return: Value of element_name, converted from relative to directory containing yaml_path to absolute
        """
        maybe_relative_path = Path(str(yaml_map[element_name.name]))
        return RelativePathUtil.maybe_absolutize(maybe_relative_path, yaml_path.parent, strict=False)

    @staticmethod
    def descend(yaml_obj: Any, path: Sequence[Any]) -> List[Any]:
        """Descend into a map following a path of map keys, and return a list of elements found, or
        [] if some part of that path does not exist."""
        if isinstance(yaml_obj, dict):
            if not path:
                return [yaml_obj]
            head = path[0]
            head_name = head.name if hasattr(head, "name") else head
            if head_name in yaml_obj:
                return YamlPropManifestUtil.descend(yaml_obj[head_name], path[1:])
            return []
        if isinstance(yaml_obj, list):
            result: List[Any] = []
            for item in yaml_obj:
                result.extend(YamlPropManifestUtil.descend(item, path))
            return result
        if not path:
            return [yaml_obj]
        return []



    @staticmethod
    def dump_compact(d: Any) -> str:
        """Format a yaml map as a compact string for transmitting as a workflow property."""
        return yaml.dump(d, default_flow_style=True).strip()

    @staticmethod
    def dump_readable(d: Any) -> str:
        """Format a yaml map for writing to a properties.yaml or manifest.yaml, in most readable style."""
        return yaml.dump(d, default_flow_style=False)

    @staticmethod
    def dump_readable_lines(d: Any) -> List[str]:
        """Like dump_readable, but splits into lines so that StepProperty length limit isn't exceeded."""
        return YamlPropManifestUtil.dump_readable(d).split("\n")

    @staticmethod
    def force_list(v: Any) -> List[Any]:
        """Some values in a yaml map can be a list, but a yaml parser won't return a list if there is 1 or 0
        elements. This makes writing code to handle the element more complicated, so this method makes a yaml
        value always look like a list.

        :param v: a value from a yaml map
        :return: if v is a list, v itself. If v is None, []. Otherwise [v].
        """
        if isinstance(v, list):
            return v
        if v is None:
            return []
        return [v]

    @staticmethod
    def get_double(v: Any) -> float:
        """Allow an int or float to be treated as a double."""
        if not isinstance(v, bool) and isinstance(v, (int, float)):
            return float(v)
        raise ValueError(f"Could not cast {v} (class {type(v)}) to double")
