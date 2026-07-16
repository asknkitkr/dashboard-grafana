#!/usr/bin/env python3
"""generate_csv_v3.py – A polished, user‑friendly CSV generator for ORAN.

Features
--------
- Command‑line interface with ``--help`` (argparse).
- Configurable input file (default: ``config_v3.properties``).
- Generates CSV files for CU‑CP, CU‑UP, DU, ORU and NRCell.
- Supports IPv4/IPv6 selection:
  * CU‑UP uses the address type defined by ``IPAddrClassType`` (ipv4 or ipv6).
  * All other components always use the IPv6 address.
- Detailed logging (console + rotating file ``generate_csv.log``).
- Optional ``--dry-run`` to preview data without writing files.
- Optional ``--json`` to also emit JSON equivalents.
- Unit‑test scaffolding provided in ``tests/test_generate_csv.py``.
- Fully type‑annotated and extensively documented.
"""

import argparse
import csv
import json
import logging
import os
import math
import random
import string
import sys
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOG_FILE = "generate_csv.log"
LOGGER = logging.getLogger("generate_csv")
LOGGER.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
LOGGER.addHandler(ch)
# File handler
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(formatter)
LOGGER.addHandler(fh)

# ---------------------------------------------------------------------------
# Configuration handling
# ---------------------------------------------------------------------------
class Config:
    """Load and validate configuration from a .properties file.

    Expected keys in the ``DEFAULT`` section:
    - ``StartingGNodeBId`` (int)
    - ``NumberOfNRCells`` (int)
    - ``GCProfile`` (str)
    - ``IPAddrClassType`` ("ipv4" or "ipv6")
    - ``IPv4Address`` (str) – used when class is ipv4
    - ``IPv6Address`` (str) – used for all other components
    - ``NRCellsPerORU`` (int) - 1 to 3
    """

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        # defaults
        self.start_gnb_id: int = 11001
        self.total_nrcells: int = 54
        self.gc_profile: str = "77.1.1"
        self.ip_addr_class: str = "ipv4"
        self.ipv4_address: str = "10.10.10.10"
        self.ipv6_address: str = "fd10:298c:8df3:398:c3:0:1:75d0"
        self.nrcells_per_oru: int = 1  # default 1 NRCell per ORU
        self.load()

    def load(self) -> None:
        if not self.filepath.is_file():
            LOGGER.warning("Config file %s not found – using defaults.", self.filepath)
            return
        import configparser
        parser = configparser.ConfigParser()
        parser.read(self.filepath)
        defaults = parser["DEFAULT"] if "DEFAULT" in parser else {}
        self.start_gnb_id = int(defaults.get("StartingGNodeBId", self.start_gnb_id))
        self.total_nrcells = int(defaults.get("NumberOfNRCells", self.total_nrcells))
        self.gc_profile = defaults.get("GCProfile", self.gc_profile)
        self.ip_addr_class = defaults.get("IPAddrClassType", self.ip_addr_class).lower()
        if self.ip_addr_class not in {"ipv4", "ipv6"}:
            LOGGER.error("Invalid IPAddrClassType '%s' – falling back to 'ipv4'", self.ip_addr_class)
            self.ip_addr_class = "ipv4"
        self.ipv4_address = defaults.get("IPv4Address", self.ipv4_address)
        self.ipv6_address = defaults.get("IPv6Address", self.ipv6_address)
        # New parameter: NRCellsPerORU (1-3)
        try:
            nrcells = int(defaults.get("NRCellsPerORU", self.nrcells_per_oru))
        except ValueError:
            nrcells = self.nrcells_per_oru
        if nrcells < 1:
            LOGGER.warning("NRCellsPerORU %d is less than 1 – setting to 1", nrcells)
            nrcells = 1
        elif nrcells > 3:
            LOGGER.warning("NRCellsPerORU %d exceeds max 3 – setting to 3", nrcells)
            nrcells = 3
        self.nrcells_per_oru = nrcells
        LOGGER.info("Configuration loaded from %s", self.filepath)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def get_ip(component: str, cfg: Config) -> str:
    """Return the IP address appropriate for *component*.

    ``component`` can be ``cuup`` (uses the configured class) or any other
    component which always receives the IPv6 address.
    """
    if cfg.ip_addr_class == "ipv4":
        return cfg.ipv4_address
    return cfg.ipv6_address

def export_csv(data: List[Dict[str, Any]], columns: List[str], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
    LOGGER.info("Wrote %d rows to %s", len(data), out_path)

def export_json(data: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(data, f, indent=2)
    LOGGER.info("Wrote JSON to %s", out_path)

# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------
class ORANCSVGenerator:
    """Generate CSV (and optional JSON) data for ORAN components.
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.mcc = "001"
        self.mnc = "01"
        # Separate GC profile suffixes
        self.gc_profile_default = f"{cfg.gc_profile}@default"
        self.gc_profile_ipv4 = f"{cfg.gc_profile}@default_ipv4"

        # Column definitions – kept identical to previous versions for compatibility
        self.cucp_columns = [
            "cluster",
            "gNBId",
            "gNBCUName",
            "perfIpAddress",
            "notifIpAddress",
            "certIpAddress",
            "confdIpAddress",
            "confdProxyIpAddress",
            "e1cIpAddress",
            "f1cIpAddress",
            "xncIpAddress",
            "ngcIpAddress",
            "xncRelation",
            "mcc",
            "mnc",
            "gcProfile",
            "description",
        ]
        self.cuup_columns = [
            "cluster",
            "gNBId",
            "gNBCUUPId",
            "gNBCUUPName",
            "perfIpAddress",
            "notifIpAddress",
            "certIpAddress",
            "confdIpAddress",
            "confdProxyIpAddress",
            "e1cIpAddress",
            "f1uIpAddress",
            "s1uIpAddress",
            "mcc",
            "mnc",
            "gcProfile",
            "description",
            "f1uGatewayAddress",
            "nguIpAddress",
            "nguGatewayAddress",
            "sliceProfile",
        ]
        self.du_columns = [
            "cluster",
            "gNBId",
            "gNBCUUPIds",
            "gNBDUId",
            "gNBDUName",
            "ruIpAddress",
            "perfIpAddress",
            "notifIpAddress",
            "certIpAddress",
            "confdIpAddress",
            "confdProxyIpAddress",
            "f1cIpAddress",
            "f1uIpAddress",
            "mcc",
            "mnc",
            "gcProfile",
            "rRMPolicyDedicatedRatio",
            "rRMPolicyMaxRatio",
            "rRMPolicyMinRatio",
            "description",
        ]
        self.oru_columns = [
            "gNBId",
            "gNBDUId",
            "ruId",
            "radioSerialNumber",
            "siteId",
            "siteLatitude",
            "siteLongitude",
            "type",
            "manufacturer",
            "cuPlaneInterface",
            "cuPlaneVlanId",
            "enableAisg",
            "version",
            "gcProfile",
            "baseInterfaceName",
            "radioCUPlaneVlanId",
            "description",
        ]
        self.nrcell_columns = [
            "radioSerialNumber",
            "cellLocalId",
            "nrCellName",
            "retAntennas",
            "sectorId",
            "sectorCarrierId",
            "band",
            "carrierId",
            "tx",
            "rx",
            "bandwidth",
            "mcc",
            "mnc",
            "nRPCI",
            "nRTAC",
            "rootSequenceIndex",
            "txDirection",
            "configuredMaxTxPower",
            "arfcnDL",
            "arfcnUL",
            "bSChannelBwDL",
            "bSChannelBwUL",
            "ssbFrequency",
            "ssbSubCarrierOffset",
            "controlResSetZero",
            "offsetToPointA",
            "cellReserveState",
            "ssbTransBitmap",
            "description",
        ]
        # Accumulators
        self.cucp_data: List[Dict[str, Any]] = []
        self.cuup_data: List[Dict[str, Any]] = []
        self.du_data: List[Dict[str, Any]] = []
        self.oru_data: List[Dict[str, Any]] = []
        self.nrcell_data: List[Dict[str, Any]] = []

    def generate_all(self) -> None:
        """Generate data for every component based on the current configuration."""
        cells_remaining = self.cfg.total_nrcells
        cur_gnb = self.cfg.start_gnb_id
        while cells_remaining > 0:
            cells_this = min(54, cells_remaining)
            cluster = f"scale-test-{cur_gnb}"
            self._gen_cucp(cur_gnb, cluster)
            self._gen_cuup(cur_gnb, cluster)
            self._gen_du(cur_gnb, cluster, cells_this)
            self._gen_oru_nrcell(cur_gnb, cells_this)
            cells_remaining -= cells_this
            cur_gnb += 1
        LOGGER.info(
            "Generation finished – %d CUCP, %d CUUP, %d DU, %d ORU, %d NRCell rows",
            len(self.cucp_data),
            len(self.cuup_data),
            len(self.du_data),
            len(self.oru_data),
            len(self.nrcell_data),
        )

    # ---------------------------------------------------------------------
    # Component generators
    # ---------------------------------------------------------------------
    def _gen_cucp(self, gnb_id: int, cluster: str) -> None:
        ip = get_ip("cucp", self.cfg)
        self.cucp_data.append({
            "cluster": cluster,
            "gNBId": gnb_id,
            "gNBCUName": f"CUCP_{gnb_id}",
            "perfIpAddress": ip,
            "notifIpAddress": ip,
            "certIpAddress": ip,
            "confdIpAddress": ip,
            "confdProxyIpAddress": ip,
            "e1cIpAddress": ip,
            "f1cIpAddress": ip,
            "xncIpAddress": ip,
            "ngcIpAddress": ip,
            "xncRelation": "",
            "mcc": self.mcc,
            "mnc": self.mnc,
            "gcProfile": self.gc_profile_default,
            "description": f"CUCP for gNB {gnb_id}",
        })

    def _gen_cuup(self, gnb_id: int, cluster: str) -> None:
        ip = get_ip("cuup", self.cfg)
        self.cuup_data.append({
            "cluster": cluster,
            "gNBId": gnb_id,
            "gNBCUUPId": 1,
            "gNBCUUPName": f"CUUP_{gnb_id}",
            "perfIpAddress": ip,
            "notifIpAddress": ip,
            "certIpAddress": ip,
            "confdIpAddress": ip,
            "confdProxyIpAddress": ip,
            "e1cIpAddress": ip,
            "f1uIpAddress": ip,
            "s1uIpAddress": ip,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "gcProfile": self.gc_profile_ipv4 if self.cfg.ip_addr_class == "ipv4" else self.gc_profile_default,
            "description": f"CUUP for gNB {gnb_id}",
            "f1uGatewayAddress": get_ip("cucp", self.cfg),
            "nguIpAddress": get_ip("cucp", self.cfg),
            "nguGatewayAddress": get_ip("cucp", self.cfg),
            "sliceProfile": "nsp1",
        })

    def _gen_du(self, gnb_id: int, cluster: str, cells: int) -> None:
        num_dus = (cells + 2) // 3  # ceiling division
        for du_id in range(1, num_dus + 1):
            self.du_data.append({
                "cluster": cluster,
                "gNBId": gnb_id,
                "gNBCUUPIds": 1,
                "gNBDUId": du_id,
                "gNBDUName": f"DU_{gnb_id + du_id - 1}",
                "ruIpAddress": get_ip("cucp", self.cfg),
                "perfIpAddress": get_ip("cucp", self.cfg),
                "notifIpAddress": get_ip("cucp", self.cfg),
                "certIpAddress": get_ip("cucp", self.cfg),
                "confdIpAddress": get_ip("cucp", self.cfg),
                "confdProxyIpAddress": get_ip("cucp", self.cfg),
                "f1cIpAddress": get_ip("cucp", self.cfg),
                "f1uIpAddress": get_ip("cucp", self.cfg),
                "mcc": self.mcc,
                "mnc": self.mnc,
                "gcProfile": self.gc_profile_default,
                "rRMPolicyDedicatedRatio": 0,
                "rRMPolicyMaxRatio": 100,
                "rRMPolicyMinRatio": 0,
                "description": f"DU {du_id} for gNB {gnb_id}",
            })

    def _gen_oru_nrcell(self, gnb_id: int, cells: int) -> None:
        """Generate ORU entries and associated NRCell entries.

        Each ORU will have ``self.cfg.nrcells_per_oru`` NRCell rows (1‑3).
        """
        nrcells_per_oru = self.cfg.nrcells_per_oru
        cell_id = 1
        oru_index = 1
        while cell_id <= cells:
            # Determine DU for the first cell of this ORU
            du_id = (cell_id + 2) // 3
            # ORU entry (one per ORU)
            serial_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            radio_sn = f"RU{gnb_id}{oru_index:04d}{serial_suffix}"
            sector_id = (cell_id - 1) % 2
            lat = f"{random.uniform(-90.0, 90.0):.5f}"
            lon = f"{random.uniform(-180.0, 180.0):.5f}"
            self.oru_data.append({
                "gNBId": gnb_id,
                "gNBDUId": du_id,
                "ruId": oru_index,
                "radioSerialNumber": radio_sn,
                "siteId": f"gnb-{gnb_id}-site-{sector_id}",
                "siteLatitude": lat,
                "siteLongitude": lon,
                "type": "ORAN",
                "manufacturer": "Prose",
                "cuPlaneInterface": "plane1",
                "cuPlaneVlanId": 60,
                "enableAisg": "false",
                "version": "",
                "gcProfile": self.gc_profile_default,
                "baseInterfaceName": "eth0",
                "radioCUPlaneVlanId": 1,
                "description": f"ORU {oru_index} for gNB {gnb_id}",
            })
            # Generate up to nrcells_per_oru NRCell rows for this ORU
            for _ in range(nrcells_per_oru):
                if cell_id > cells:
                    break
                # NRCell entry
                self.nrcell_data.append({
                    "radioSerialNumber": radio_sn,
                    "cellLocalId": cell_id,
                    "nrCellName": f"Cell-{gnb_id}-{cell_id}",
                    "retAntennas": "",
                    "sectorId": sector_id,
                    "sectorCarrierId": 0,
                    "band": "n78",
                    "carrierId": 0,
                    "tx": 4,
                    "rx": 4,
                    "bandwidth": 100,
                    "mcc": self.mcc,
                    "mnc": self.mnc,
                    "nRPCI": 123,
                    "nRTAC": 6136,
                    "rootSequenceIndex": 60,
                    "txDirection": "DL_AND_UL",
                    "configuredMaxTxPower": 39811,
                    "arfcnDL": 653390,
                    "arfcnUL": 653390,
                    "bSChannelBwDL": 100,
                    "bSChannelBwUL": 100,
                    "ssbFrequency": 656640,
                    "ssbSubCarrierOffset": 6,
                    "controlResSetZero": 7,
                    "offsetToPointA": 100,
                    "cellReserveState": "PLMN_ID_INFO_NOT_RESERVED",
                    "ssbTransBitmap": 1,
                    "description": f"NRCell {cell_id} for gNB {gnb_id}",
                })
                cell_id += 1
            oru_index += 1

# ---------------------------------------------------------------------------
# CLI utilities
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ORAN CSV/JSON files with optional dry‑run mode.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config_v3.properties",
        help="Path to the configuration .properties file (default: config_v3.properties).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "output",
        help="Directory where CSV/JSON files will be written (default: ./output in script folder).",
    )
    parser.add_argument(
        "--folder-naming",
        choices=["gnobeb-nrcell", "none"],
        default="gnobeb-nrcell",
        help="Create per‑gNodeB folders named gnobeb-<gNodeB_id>-nrcell-<nrcell_count>. Use 'none' for flat layout.",
    )
    parser.add_argument("--json", action="store_true", help="Write JSON equivalents alongside CSV files.")
    parser.add_argument("--dry-run", action="store_true", help="Show a summary without writing files.")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    LOGGER.setLevel(getattr(logging, args.log_level))
    cfg = Config(args.config)
    gen = ORANCSVGenerator(cfg)
    gen.generate_all()

    if args.dry_run:
        LOGGER.info("Dry‑run summary:")
        LOGGER.info("CUCP rows: %d", len(gen.cucp_data))
        LOGGER.info("CUUP rows: %d", len(gen.cuup_data))
        LOGGER.info("DU rows: %d", len(gen.du_data))
        LOGGER.info("ORU rows: %d", len(gen.oru_data))
        LOGGER.info("NRCell rows: %d", len(gen.nrcell_data))
        return

    out_dir: Path = args.output_dir
    export_csv(gen.cucp_data, gen.cucp_columns, out_dir / "cucp.csv")
    export_csv(gen.cuup_data, gen.cuup_columns, out_dir / "cuup.csv")
    export_csv(gen.du_data, gen.du_columns, out_dir / "du.csv")
    export_csv(gen.oru_data, gen.oru_columns, out_dir / "oru.csv")
    export_csv(gen.nrcell_data, gen.nrcell_columns, out_dir / "nrcell.csv")

    if args.json:
        export_json(gen.cucp_data, out_dir / "cucp.json")
        export_json(gen.cuup_data, out_dir / "cuup.json")
        export_json(gen.du_data, out_dir / "du.json")
        export_json(gen.oru_data, out_dir / "oru.json")
        export_json(gen.nrcell_data, out_dir / "nrcell.json")

    LOGGER.info("All files generated in %s", out_dir)

if __name__ == "__main__":
    main()
