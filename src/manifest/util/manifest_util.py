from pathlib import Path
from typing import Any, Dict, List, Optional

from manifest.util.exception import YamlException


class YamlManifestUtil:

    @staticmethod
    def apply_defaults(manifest: Dict[str, Any], defaults_key: Any, targets_key: Any) -> List[Any]:
        """For multi-library workflows, apply default values to any libraries that don't have those values set.

        :param manifest: yaml map containing defaults and libraries definitions
        :param defaults_key: key into manifest to submap containing default values
        :param targets_key: key into manifest to list of submaps onto which defaults will be applied if necessary
        :return: Copy of manifest[targets_key] submap with defaults applied, or the original manifest[targets_key]
            if there were no defaults to be applied.
        """
        defaults = manifest.get(defaults_key.name)
        raw_targets_value = manifest.get(targets_key.name)
        if raw_targets_value is None:
            raw_targets = []
        elif isinstance(raw_targets_value, dict):
            raw_targets = [raw_targets_value]
        elif isinstance(raw_targets_value, list):
            raw_targets = raw_targets_value
        else:
            raise RuntimeError(f"Weird value for '{targets_key.name}' in manifest")
        if defaults is None:
            return raw_targets
        return [YamlManifestUtil.project_defaults(t, defaults) for t in raw_targets]

    @staticmethod
    def _is_any_val_or_null(v: Any) -> bool:
        return v is None or not (isinstance(v, dict) or isinstance(v, list))

    @staticmethod
    def project_defaults(target: Any, defaults: Dict[str, Any]) -> Any:
        """Apply default values for any attributes not set. If target is a primitive, it is returned unchanged.
        If target is a dict, any values in defaults that are not present in target are added. If a value in
        target and defaults are both dicts, project_defaults is recursed. If target is a list, project_defaults
        is called for every list element.

        :return: target with appropriate defaults applied
        """
        if YamlManifestUtil._is_any_val_or_null(target):
            return target
        if isinstance(target, list):
            return [YamlManifestUtil.project_defaults(t, defaults) for t in target]
        if not isinstance(target, dict):
            raise RuntimeError(f"Unexpected target type {type(target)}")
        result = dict(target)
        for k, v in defaults.items():
            if k not in result:
                # If target does not contain key, simply copy from defaults
                result[k] = v
            elif isinstance(v, dict):
                # If target contains key, only attempt to project defaults[key] if it is a dict
                if isinstance(result[k], list):
                    result[k] = [
                        YamlManifestUtil.project_defaults(sub, v) if isinstance(sub, dict) else sub
                        for sub in result[k]
                    ]
                elif isinstance(result[k], dict):
                    result[k] = YamlManifestUtil.project_defaults(result[k], v)
        return result

    @staticmethod
    def get_required_value(manifest: Dict[str, Any], key: Any, file: Optional[Path] = None) -> Any:
        if key.name not in manifest:
            suffix = f" in {file.resolve()}" if file is not None else ""
            raise YamlException(f"yaml element {key.name} not found{suffix}")
        return manifest[key.name]
