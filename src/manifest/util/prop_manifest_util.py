"""Tools for handling yaml manifests, which are inputs to Launch* commands, and yaml properties files, which
are produced by workflows to summarize analyses."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from util.relative_path_util import RelativePathUtil


@dataclass(frozen=True)
class YamlPathAndMap:
    """A loaded yaml map, and the file it came from."""
    path: Path
    map: Dict[str, Any]


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
    def create_downstream_manifest(downstream_yaml: Optional[str], next_workflow_key: Any,
                                   downstreams_to_remove: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        """Create manifest content for the next workflow to be launched.

        :param downstream_yaml: contents of 'downstream' element for current workflow
        :param next_workflow_key: yaml subkey in downstream map for next workflow to be launched.
        :param downstreams_to_remove: For workflows that launch multiple downstream workflows, like standard
            analysis launches both scPred and MMC, remove the downstream yaml for the workflow that is not
            being launched, because it will be an invalid manifest.
        :return: None if next workflow is explicitly disabled (null in that slot of downstream).
            {} if downstream_yaml is empty, which does not necessarily preclude launching downstream workflow.
            A map in which the submap for the next workflow has been promoted to top level, and the remainder
            of downstream elements are in a downstream submap.
        """
        from manifest.util.property_keys import ScRnaDownstreamPropertyKey

        if downstream_yaml is None:
            return {}
        remove_names = {e.name for e in downstreams_to_remove}
        downstream_map = {k: v for k, v in yaml.safe_load(downstream_yaml).items() if k not in remove_names}
        next_name = next_workflow_key.name
        if next_name not in downstream_map:
            return {ScRnaDownstreamPropertyKey.downstream.name: downstream_map}
        if downstream_map[next_name] is None:
            return None
        downstream_remainder = {k: v for k, v in downstream_map.items() if k != next_name}
        next_workflow_map = dict(downstream_map[next_name])
        if not downstream_remainder:
            return next_workflow_map
        next_workflow_map[ScRnaDownstreamPropertyKey.downstream.name] = downstream_remainder
        return next_workflow_map

    @staticmethod
    def get_upstream_properties_path(yaml_path_and_map: YamlPathAndMap,
                                     upstream_properties_key: Optional[Any] = None) -> Path:
        """Get a non-optional path from a yaml map that may be relative to the map, and absolutize it.

        :param yaml_path_and_map: The map containing the path to be fetched, and the file it was loaded from
        :param upstream_properties_key: the key containing the path to be fetched.
        :return: value of upstream_properties_key, absolutized if necessary.
        """
        from manifest.util.property_keys import YamlPropertyKey

        if upstream_properties_key is None:
            upstream_properties_key = YamlPropertyKey.upstream_properties
        return YamlPropManifestUtil.absolutize_path_in_yaml(
            yaml_path_and_map.map, upstream_properties_key, yaml_path_and_map.path)

    @staticmethod
    def load_upstream_properties(yaml_path_and_map: YamlPathAndMap,
                                 upstream_properties_key: Optional[Any] = None) -> YamlPathAndMap:
        """Load a (non-optional) yaml map that is referred to by a value in another yaml map, possibly relative
        to the original map.

        :param yaml_path_and_map: map containing path to another map
        :param upstream_properties_key: key to path of referred-to map
        :return: path to upstream map, and the referred-to map, loaded
        """
        upstream_path = YamlPropManifestUtil.get_upstream_properties_path(yaml_path_and_map, upstream_properties_key)
        return YamlPathAndMap(upstream_path, YamlPropManifestUtil.load(upstream_path))

    @staticmethod
    def load_multiple_upstream_properties(yaml_path_and_map: YamlPathAndMap,
                                          num_upstream_or_keys) -> List[YamlPathAndMap]:
        """Follow the upstreamProperties key multiple times (if given a count), or follow a specific chain of
        keys, to load multiple upstream maps.

        :param yaml_path_and_map: head of the upstreamProperties chain
        :param num_upstream_or_keys: either an int count of steps upstream to fetch (all via the default
            upstream_properties key), or a sequence of keys to upstream maps, with immediate predecessor key
            first.
        :return: list of upstream YamlPathAndMap, with head of list being the immediate predecessor of
            yaml_path_and_map
        """
        from manifest.util.property_keys import YamlPropertyKey

        if isinstance(num_upstream_or_keys, int):
            upstream_keys = [YamlPropertyKey.upstream_properties] * num_upstream_or_keys
        else:
            upstream_keys = list(num_upstream_or_keys)
        if not upstream_keys:
            return []
        upstream_yaml = YamlPropManifestUtil.load_upstream_properties(yaml_path_and_map, upstream_keys[0])
        return [upstream_yaml] + YamlPropManifestUtil.load_multiple_upstream_properties(
            upstream_yaml, upstream_keys[1:])

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
