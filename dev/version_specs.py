"""Python Script that copies jsonschema specs from specs/ to docs/spec grouped by version"""

import os
import shutil
import re
import argparse
import difflib
import json

def extract_version_from_id(id_url):
  # Extract the version from the $id URL
  match = re.search(r'/(\d+-\d+-\d+)/', id_url)
  if match:
    return match.group(1)
  return None

def extract_version_from_schema(schema_data):
  # Extract the version from the $id field in the schema
  schema = json.loads(schema_data)
  if "$id" in schema:
    return extract_version_from_id(schema["$id"])
  return None

def compare_content(src_content, dest_content):
  # Create a unified diff between source and destination content
  diff = difflib.unified_diff(src_content.splitlines(), dest_content.splitlines(), lineterm='')
  return '\n'.join(diff)

def copy_specs_by_version(src_dir, dest_dir, allow_overwrite=False, ignore_missing=False):
  # Create the destination directory if it doesn't exist
  if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

  errors = []

  # Iterate through the files in the source directory
  for filename in os.listdir(src_dir):
    if filename.endswith('.json'):
      src_path = os.path.join(src_dir, filename)

      with open(src_path, 'r') as file:
        data = file.read()
        # Extract version from $id
        version = extract_version_from_schema(data)

        if not version:
          errors.append(f"Version missing in {src_path}")
        else:
          version_dir = os.path.join(dest_dir, version)
          if not os.path.exists(version_dir):
            os.makedirs(version_dir)

          dest_path = os.path.join(version_dir, filename)

          if not os.path.exists(dest_path) and not ignore_missing:
            errors.append(f"Destination file {dest_path} does not exist.")

          elif os.path.exists(dest_path) and not allow_overwrite:
            with open(dest_path, 'r') as dest_file:
              dest_data = dest_file.read()
              if dest_data != data:
                diff = compare_content(data, dest_data)
                errors.append(
                  f"Content mismatch between {src_path} and {dest_path}:\n"
                  "  === Diff ===\n"
                  f"{diff}"
                )
          else:
            shutil.copy(src_path, dest_path)
            print(f"Copied {filename} to {dest_path}")

  if errors:
    raise ValueError("\n\n".join(errors))

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Copy JSON schema specs by version.")
  parser.add_argument("--allow-overwrite", action="store_true",
                      help="Allow overwriting destination files if content differs.")
  parser.add_argument("--ignore-missing", action="store_true",
                      help="Ignore missing destination files.")
  args = parser.parse_args()

  src_directory = "spec"
  dest_directory = "docs/spec"
  allow_overwrite = args.allow_overwrite
  ignore_missing = args.ignore_missing

  copy_specs_by_version(src_directory, dest_directory, allow_overwrite, ignore_missing)
