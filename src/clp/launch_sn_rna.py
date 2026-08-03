#!/usr/bin/env python3
"""Launch the single-nucleus RNA-seq (snRNA) workflow cascade for a library in Seqera cloud.
"""
import argparse
import re
import sys
import getpass
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from google.cloud import storage

from manifest.util.manifest_util import YamlManifestUtil

GCS_PATH_RE = re.compile(r"^gs://(?P<bucket>[^/]+)/(?P<blob>.+)$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Stand-ins for the manifest keys used to project libraryDefaults onto libraries.
# YamlManifestUtil.apply_defaults() only needs a `.name` attribute, so these avoid a
# dependency on manifest.util.manifest_keys, which cannot currently be imported (its
# import of manifest.property_keys fails: SampleType/WorkflowKind/CallSTAMPsMethod are
# referenced there but not yet defined in manifest.enums).
_LIBRARIES_KEY = argparse.Namespace(name="libraries")
_LIBRARY_DEFAULTS_KEY = argparse.Namespace(name="libraryDefaults")
_VERSION_10X_KEY = "version10X"



class LaunchSnRnaError(Exception):
    """A user-facing problem with the launch arguments, manifest, or cloud metadata."""


@dataclass
class SnRnaLaunchContext:
    manifest_path: Path
    manifest: Dict[str, Any]
    project: str
    project_resources: Optional[Dict[str, Any]]
    tenx_metadata: Optional[Dict[str, Any]]
    email: Optional[str]
    output_dir: Optional[str]

    def describe(self) -> str:
        lines = [
            "Launching snRNA workflow",
            f"  manifest: {self.manifest_path}",
            f"  project: {self.project}",
        ]
        if self.project_resources is not None:
            resource_keys = ", ".join(sorted(self.project_resources)) or "(empty)"
            lines.append(f"  project resources: {resource_keys}")
        else:
            lines.append("  project resources: not resolved (--project-metadata not given)")
        if self.tenx_metadata is not None:
            lines.append(f"  10X metadata: {len(self.tenx_metadata)} chemistry version(s) loaded")
        else:
            lines.append("  10X metadata: not loaded (--tenx-metadata not given)")
        lines.append(f"  user: {self.email or 'not specified'}")
        lines.append(f"  output directory: {self.output_dir or 'not specified'}")
        return "\n".join(lines)


def _gcs_path_type(value: str) -> str:
    if not GCS_PATH_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a gs:// path: '{value}'")
    return value


def _email_type(value: str) -> str:
    if not EMAIL_RE.match(value):
        raise argparse.ArgumentTypeError(f"not a valid email address: '{value}'")
    return value


def _manifest_path_type(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"manifest file not found: '{path}'")
    return path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__)
    parser.add_argument(
        "manifest", type=_manifest_path_type, nargs="+",
        help="Local yaml manifest file describing the libraries to process.  If more than one manifest file "
             "is provided, they will be combined with earlier manifest files taking precedence if key collisions.")
    parser.add_argument(
        "--project",
        help="Project name, used to look up project resources in the project metadata file.")
    parser.add_argument(
        "--project-metadata", type=_gcs_path_type, metavar="GCS_PATH",
        default="gs://mccarroll_scrnaseq_standard/metadata/project/project_metadata.yaml",
        help="gs:// path to a yaml file containing project resources, keyed by project name. Default: %(default)s)")
    parser.add_argument(
        "--tenx-metadata", type=_gcs_path_type, metavar="GCS_PATH",
        default='gs://mccarroll_scrnaseq_standard/metadata/10X/10X_version_metadata.yaml',
        help="gs:// path to a yaml file containing 10X chemistry version metadata. Default: %(default)s)")
    parser.add_argument(
        "--email", type=_email_type, metavar="EMAIL",
        default=f"{getpass.getuser()}@broadinstitute.org",
        help="Email address of the user launching this workflow. Default: %(default)s)")
    parser.add_argument(
        "--output-dir", type=_gcs_path_type, metavar="GCS_PATH",
        help="gs:// path under which workflow outputs will be written. Default: determined based on project and library")
    return parser.parse_args(argv)


def _split_gcs_path(gcs_path: str) -> (str, str):
    match = GCS_PATH_RE.match(gcs_path)
    if not match:
        raise LaunchSnRnaError(f"not a gs:// path: '{gcs_path}'")
    return match.group("bucket"), match.group("blob")


def load_gcs_yaml(gcs_path: str, storage_client: storage.Client) -> Dict[str, Any]:
    """Download a yaml file from Google Cloud Storage and parse it into a dict."""
    bucket_name, blob_name = _split_gcs_path(gcs_path)
    blob = storage_client.bucket(bucket_name).blob(blob_name)
    if not blob.exists():
        raise LaunchSnRnaError(f"gs:// object not found: '{gcs_path}'")
    loaded = yaml.safe_load(blob.download_as_text())
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise LaunchSnRnaError(
            f"expected a yaml mapping at '{gcs_path}', found {type(loaded).__name__}")
    return loaded


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    with open(manifest_path) as fh:
        loaded = yaml.safe_load(fh)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise LaunchSnRnaError(
            f"expected a yaml mapping in manifest '{manifest_path}', found {type(loaded).__name__}")
    return loaded


_COMBINE_DEFAULTS_KEY = argparse.Namespace(name="defaults")
_COMBINE_TARGET_KEY = argparse.Namespace(name="target")


def load_and_combine_manifests(manifest_paths: List[Path]) -> Dict[str, Any]:
    """Load each yaml manifest in order and merge them into one, with the earlier manifest taking precedence
    in the event of collisions."""
    combined: Dict[str, Any] = load_manifest(manifest_paths[0])
    for manifest_path in manifest_paths[1:]:
        manifest = load_manifest(manifest_path)
        combined = YamlManifestUtil.project_defaults(combined, manifest)
    return combined


def resolve_project_resources(project_metadata: Dict[str, Any], project: str) -> Dict[str, Any]:
    if project not in project_metadata:
        raise LaunchSnRnaError(f"project '{project}' not found in project metadata")
    resources = project_metadata[project]
    if not isinstance(resources, dict):
        raise LaunchSnRnaError(
            f"expected a yaml mapping for project '{project}', found {type(resources).__name__}")
    return resources


def get_tenx_metadata(tenx_version: str, tenx_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """find 10X version in tenx_metadata dictionary, and return that sub-dictionary."""
    if tenx_version not in tenx_metadata:
        raise LaunchSnRnaError(
            f"10X chemistry version(s) not found in 10X metadata: {tenx_version}")
    return tenx_metadata[tenx_version]

def load_project_metadata(gcs_path: str, storage_client: storage.Client) -> Dict[str, Any]:
    project_metadata = load_gcs_yaml(gcs_path, storage_client)
    lstProjects = project_metadata['projects']
    # Convert the list of projects into a dictionary in which the key is the value of the 'name' element of each sub-dictionary
    dctProjects = {dctProject['name']: dctProject for dctProject in lstProjects}

    return dctProjects

def load_tenx_metadata(gcs_path: str, storage_client: storage.Client) -> Dict[str, Any]:
    tenx_metadata = load_gcs_yaml(gcs_path, storage_client)
    # Convert the list of tenx metadata into a dictionary in which the key is the value of the 'version10X' element of each sub-dictionary
    dctTenxMetadata = {dctTenx['version10X']: dctTenx for dctTenx in tenx_metadata['versions']}
    return dctTenxMetadata

def build_launch_context(args: argparse.Namespace,
                         storage_client: Optional[storage.Client] = None) -> SnRnaLaunchContext:
    manifest = load_and_combine_manifests(args.manifest)

    storage_client = storage_client or storage.Client()
    project_metadata = load_project_metadata(args.project_metadata, storage_client)
    project_resources = resolve_project_resources(project_metadata, args.project)
    tenx_metadata = load_tenx_metadata(args.tenx_metadata, storage_client)
    manifest.update(get_tenx_metadata(manifest['version10X'], tenx_metadata))

    return SnRnaLaunchContext(
        manifest_path=args.manifest,
        manifest=manifest,
        project=args.project,
        project_resources=project_resources,
        tenx_metadata=tenx_metadata,
        email=args.email,
        output_dir=args.output_dir)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        context = build_launch_context(args)
    except LaunchSnRnaError as e:
        print(f"launchSnRna: {e}", file=sys.stderr)
        return 1
    print(context.describe())
    return 0


if __name__ == "__main__":
    sys.exit(main())
