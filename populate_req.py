import importlib.metadata
import requests
import logging
from packaging.requirements import Requirement
from packaging.version import Version

logging.basicConfig(level=logging.INFO)

def get_installed_version(package_name):
    """
    Get the installed version of a package.

    Parameters:
        package_name (str): The name of the package.

    Returns:
        str or None: The installed version if installed, else None.
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        logging.debug(f"Package '{package_name}' is not installed.")
        return None
    except Exception as e:
        logging.error(f"Error getting installed version for '{package_name}': {e}")
        return None

def get_latest_version_from_pypi(package_name):
    """
    Get the latest version of a package from PyPI.

    Parameters:
        package_name (str): The name of the package.

    Returns:
        str or None: The latest version if found, else None.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            latest_version = data['info']['version']
            return latest_version
        else:
            logging.warning(f"Failed to get latest version for '{package_name}' from PyPI. Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching latest version from PyPI for '{package_name}': {e}")
        return None

def update_requirements_file(requirements_file):
    """
    Update the requirements.txt file by adding versions to packages without specified versions.

    Parameters:
        requirements_file (str): Path to the requirements.txt file.

    Returns:
        None
    """
    updated_lines = []

    try:
        with open(requirements_file, "r") as file:
            for line in file:
                package_line = line.rstrip('\n')

                # Ignore comments or empty lines
                if not package_line.strip() or package_line.strip().startswith("#"):
                    updated_lines.append(package_line)
                    continue

                try:
                    req = Requirement(package_line)
                except Exception as e:
                    logging.warning(f"Could not parse the line: '{package_line}'. Error: {e}")
                    updated_lines.append(package_line)
                    continue

                package_name = req.name
                extras = req.extras  # Set of extras
                specifier = req.specifier  # SpecifierSet
                markers = req.marker
                url = req.url  # For VCS or URL requirements

                # Skip if it's a URL or VCS requirement
                if url:
                    updated_lines.append(package_line)
                    continue

                # Remove extras from package name when looking up versions
                package_name_for_lookup = package_name

                installed_version = get_installed_version(package_name_for_lookup)

                operator = None
                version = None

                if installed_version:
                    if not specifier:
                        operator = '=='
                        version = installed_version
                    else:
                        # Version is specified, keep original line
                        updated_lines.append(package_line)
                        continue
                else:
                    if not specifier:
                        # No version specified and package not installed
                        latest_version = get_latest_version_from_pypi(package_name_for_lookup)
                        if latest_version:
                            operator = '=='
                            version = latest_version
                        else:
                            logging.warning(f"Could not find '{package_name_for_lookup}' on PyPI.")
                            updated_lines.append(package_line)
                            continue
                    else:
                        # Package not installed, but version is specified
                        updated_lines.append(package_line)
                        continue

                # Reconstruct the requirement line
                updated_req_str = package_name
                if extras:
                    extras_str = '[' + ','.join(extras) + ']'
                    updated_req_str += extras_str
                if operator and version:
                    updated_req_str += f"{operator}{version}"
                if markers:
                    updated_req_str += f"; {markers}"
                updated_lines.append(updated_req_str)
    except Exception as e:
        logging.error(f"Error processing requirements file: {e}")
        return

    # Write the updated content back to requirements.txt
    try:
        with open(requirements_file, "w") as file:
            file.write("\n".join(updated_lines) + "\n")
    except Exception as e:
        logging.error(f"Error writing to requirements file: {e}")

if __name__ == "__main__":
    requirements_file = "requirements.txt"
    update_requirements_file(requirements_file)
