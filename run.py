"""
Copernicus Marine ETL Pipeline
Downloads oceanographic datasets from the Copernicus Marine Data Store.
"""

import os
import logging
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import copernicusmarine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "test-data"
ENV_FILE = BASE_DIR / ".env"

# Area of interest
MIN_LONGITUDE = 79.970
MAX_LONGITUDE = 80.021
MIN_LATITUDE = 6.3461
MAX_LATITUDE = 6.4196

# Date range
START_DATETIME = "2010-01-01T00:00:00"
END_DATETIME = f"{date.today().isoformat()}T00:00:00"

# Datasets to download.
# Duplicate dataset_id entries have been merged by taking the union of their
# variable lists so each dataset is only downloaded once.
DATASETS = [
    {
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1M-m",
        "variables": ["uo", "vo", "thetao"],
        "output_filename": "cmems_mod_glo_phy_my_0.083deg_P1M-m.nc",
    },
    {
        "dataset_id": "cmems_mod_glo_wav_my_0.2deg_PT3H-i",
        "variables": ["VHM0", "VTM02", "VTPK"],
        "output_filename": "cmems_mod_glo_wav_my_0.2deg_PT3H-i.nc",
    },
    {
        "dataset_id": "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H",
        "variables": ["eastward_wind", "northward_wind"],
        "output_filename": "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H.nc",
    },
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_credentials() -> tuple[str, str]:
    """Load Copernicus Marine credentials.

    Reads from a .env file when present (local dev) or from environment
    variables injected at runtime (Docker / Jenkins / CI).
    """
    load_dotenv(ENV_FILE)  # silently no-ops if .env is absent (e.g. in Docker)
    username = os.getenv("COPERNICUSMARINE_USERNAME")
    password = os.getenv("COPERNICUSMARINE_PASSWORD")
    if not username or not password:
        raise EnvironmentError(
            "Credentials not found. Set COPERNICUSMARINE_USERNAME and "
            "COPERNICUSMARINE_PASSWORD as environment variables (Docker / CI) "
            f"or in the {ENV_FILE} file (local dev)."
        )
    return username, password


def clear_output_directory(directory: Path) -> None:
    """Remove all files inside the output directory."""
    directory.mkdir(parents=True, exist_ok=True)
    files = list(directory.glob("*"))
    if not files:
        logger.info("Output directory is already empty: %s", directory)
        return
    for file_path in files:
        if file_path.is_file():
            try:
                file_path.unlink()
                logger.info("Deleted: %s", file_path.name)
            except OSError as exc:
                logger.warning("Could not delete %s: %s", file_path.name, exc)
    logger.info("Cleared %d file(s) from %s", len(files), directory)


def download_dataset(dataset: dict, username: str, password: str) -> bool:
    """
    Download a single dataset using copernicusmarine.subset().

    Returns True on success, False on failure.
    Raises SystemExit for unrecoverable credential errors.
    """
    dataset_id = dataset["dataset_id"]
    variables = dataset["variables"]
    output_filename = dataset["output_filename"]

    logger.info(
        "Downloading dataset: %s | variables: %s",
        dataset_id,
        variables,
    )

    try:
        copernicusmarine.subset(
            dataset_id=dataset_id,
            variables=variables,
            minimum_longitude=MIN_LONGITUDE,
            maximum_longitude=MAX_LONGITUDE,
            minimum_latitude=MIN_LATITUDE,
            maximum_latitude=MAX_LATITUDE,
            start_datetime=START_DATETIME,
            end_datetime=END_DATETIME,
            output_directory=str(OUTPUT_DIR),
            output_filename=output_filename,
            username=username,
            password=password,
            overwrite=True,
        )
        dest = OUTPUT_DIR / output_filename
        if dest.exists():
            size_mb = dest.stat().st_size / (1024 ** 2)
            logger.info("Saved: %s (%.2f MB)", dest.name, size_mb)
        else:
            logger.warning(
                "Download reported success but file not found: %s", dest
            )
        return True

    except (
        copernicusmarine.InvalidUsernameOrPassword,
        copernicusmarine.CredentialsCannotBeNone,
        copernicusmarine.CouldNotConnectToAuthenticationSystem,
    ) as exc:
        # Credential / auth failures are fatal — stop the whole pipeline
        logger.error("Authentication error: %s", exc)
        raise SystemExit(1) from exc

    except copernicusmarine.DatasetNotFound as exc:
        logger.error("Dataset not found '%s': %s", dataset_id, exc)

    except copernicusmarine.VariableDoesNotExistInTheDataset as exc:
        logger.error(
            "Variable not found in dataset '%s': %s", dataset_id, exc
        )

    except copernicusmarine.CoordinatesOutOfDatasetBounds as exc:
        logger.error(
            "Coordinates out of bounds for dataset '%s': %s", dataset_id, exc
        )

    except copernicusmarine.ServiceNotAvailable as exc:
        logger.error(
            "Service not available for dataset '%s': %s", dataset_id, exc
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Unexpected error while downloading '%s': %s",
            dataset_id,
            exc,
            exc_info=True,
        )

    return False


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Copernicus Marine ETL Pipeline")
    logger.info("Date range : %s → %s", START_DATETIME, END_DATETIME)
    logger.info(
        "Bounding box: lon [%.3f, %.3f]  lat [%.4f, %.4f]",
        MIN_LONGITUDE, MAX_LONGITUDE, MIN_LATITUDE, MAX_LATITUDE,
    )
    logger.info("=" * 60)

    # 1. Load credentials
    try:
        username, password = load_credentials()
        logger.info("Credentials loaded from .env")
    except EnvironmentError as exc:
        logger.error(exc)
        sys.exit(1)

    # 2. Clear output directory
    logger.info("Clearing output directory: %s", OUTPUT_DIR)
    clear_output_directory(OUTPUT_DIR)

    # 3. Download each dataset
    results = {}
    for dataset in DATASETS:
        success = download_dataset(dataset, username, password)
        results[dataset["dataset_id"]] = "OK" if success else "FAILED"

    # 4. Summary
    logger.info("=" * 60)
    logger.info("Download summary:")
    all_ok = True
    for dataset_id, status in results.items():
        logger.info("  %-55s %s", dataset_id, status)
        if status != "OK":
            all_ok = False
    logger.info("=" * 60)

    if not all_ok:
        logger.warning("One or more downloads failed. Check logs above.")
        sys.exit(1)

    logger.info("All downloads completed successfully.")


if __name__ == "__main__":
    main()
