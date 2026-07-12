import csv
import math
import random
import configparser
import os

class Config:
    def __init__(self, filepath='config.properties'):
        self.config = configparser.ConfigParser()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(base_dir, filepath)
        self.start_gnb_id = 11001
        self.total_nrcells = 54
        self.gc_profile = "default"
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.filepath):
            print(f"Warning: {self.filepath} not found. Using default values.")
            return

        self.config.read(self.filepath)
        if 'DEFAULT' in self.config:
            default_section = self.config['DEFAULT']
            self.start_gnb_id = int(default_section.get('StartingGNodeBId', self.start_gnb_id))
            self.total_nrcells = int(default_section.get('NumberOfNRCells', self.total_nrcells))
            self.gc_profile = default_section.get('GCProfile', self.gc_profile)


class ORANCSVGenerator:
    def __init__(self, config):
        self.config = config
        self.dummy_ip = "10.10.10.10"
        self.mcc = "001"
        self.mnc = "01"
        self.gc_profile_full = f"{self.config.gc_profile}@default"
        
        # Accumulated data
        self.cucp_data = []
        self.cuup_data = []
        self.du_data = []
        self.oru_data = []
        self.nrcell_data = []

        # Columns
        self.cucp_columns = ["cluster", "gNBId", "gNBCUName", "perfIpAddress", "notifIpAddress", "certIpAddress", "confdIpAddress", "confdProxyIpAddress", "e1cIpAddress", "f1cIpAddress", "xncIpAddress", "ngcIpAddress", "xncRelation", "mcc", "mnc", "gcProfile", "description"]
        self.cuup_columns = ["cluster", "gNBId", "gNBCUUPId", "gNBCUUPName", "perfIpAddress", "notifIpAddress", "certIpAddress", "confdIpAddress", "confdProxyIpAddress", "e1cIpAddress", "f1uIpAddress", "s1uIpAddress", "mcc", "mnc", "gcProfile", "description", "f1uGatewayAddress", "nguIpAddress", "nguGatewayAddress", "sliceProfile"]
        self.du_columns = ["cluster", "gNBId", "gNBCUUPIds", "gNBDUId", "gNBDUName", "ruIpAddress", "perfIpAddress", "notifIpAddress", "certIpAddress", "confdIpAddress", "confdProxyIpAddress", "f1cIpAddress", "f1uIpAddress", "mcc", "mnc", "gcProfile", "rRMPolicyDedicatedRatio", "rRMPolicyMaxRatio", "rRMPolicyMinRatio", "description"]
        self.oru_columns = ["gNBId", "gNBDUId", "ruId", "radioSerialNumber", "siteId", "siteLatitude", "siteLongitute", "type", "manufacturer", "cuPlaneInterface", "cuPlaneVlanId", "enableAisg", "version", "gcProfile", "baseInterfaceName", "radioCUPlanVlanId", "description"]
        self.nrcell_columns = ["radioSerialNumber", "cellLocalId", "nrCellName", "retAntennas", "sectorId", "sectorCarrierId", "band", "carrierId", "tx", "rx", "bandwidth", "mcc", "mnc", "nRPCI", "nRTAC", "rootSequenceIndex", "txDirection", "configuredMaxTxPower", "arfcnDL", "arfcnUL", "bSChannelBwDL", "bSChannelBwUL", "ssbFrequency", "ssbCarrierOffset", "controlResSetZero", "offsetToPointA", "cellReserveState", "ssbTransBitmap", "description"]

    def generate_data(self):
        cells_remaining = self.config.total_nrcells
        current_gnb_id = self.config.start_gnb_id
        
        while cells_remaining > 0:
            # A gNodeB can have up to 54 NRCells based on the relation (18 DUs * 3 ORUs)
            cells_for_this_gnb = min(54, cells_remaining)
            cluster_name = f"scale-test-{current_gnb_id}"
            
            self._generate_cucp(current_gnb_id, cluster_name)
            self._generate_cuup(current_gnb_id, cluster_name)
            self._generate_du(current_gnb_id, cluster_name, cells_for_this_gnb)
            self._generate_oru_and_nrcell(current_gnb_id, cells_for_this_gnb)
            
            cells_remaining -= cells_for_this_gnb
            current_gnb_id += 1

    def _generate_cucp(self, gnb_id, cluster_name):
        self.cucp_data.append({
            "cluster": cluster_name,
            "gNBId": gnb_id,
            "gNBCUName": f"CUCP_{gnb_id}",
            "perfIpAddress": self.dummy_ip,
            "notifIpAddress": self.dummy_ip,
            "certIpAddress": self.dummy_ip,
            "confdIpAddress": self.dummy_ip,
            "confdProxyIpAddress": self.dummy_ip,
            "e1cIpAddress": self.dummy_ip,
            "f1cIpAddress": self.dummy_ip,
            "xncIpAddress": self.dummy_ip,
            "ngcIpAddress": self.dummy_ip,
            "xncRelation": "",
            "mcc": self.mcc,
            "mnc": self.mnc,
            "gcProfile": self.gc_profile_full,
            "description": f"CUCP for gNB {gnb_id}"
        })

    def _generate_cuup(self, gnb_id, cluster_name):
        self.cuup_data.append({
            "cluster": cluster_name,
            "gNBId": gnb_id,
            "gNBCUUPId": 1,
            "gNBCUUPName": f"CUUP_{gnb_id}",
            "perfIpAddress": self.dummy_ip,
            "notifIpAddress": self.dummy_ip,
            "certIpAddress": self.dummy_ip,
            "confdIpAddress": self.dummy_ip,
            "confdProxyIpAddress": self.dummy_ip,
            "e1cIpAddress": self.dummy_ip,
            "f1uIpAddress": self.dummy_ip,
            "s1uIpAddress": self.dummy_ip,
            "mcc": self.mcc,
            "mnc": self.mnc,
            "gcProfile": self.gc_profile_full,
            "description": f"CUUP for gNB {gnb_id}",
            "f1uGatewayAddress": self.dummy_ip,
            "nguIpAddress": self.dummy_ip,
            "nguGatewayAddress": self.dummy_ip,
            "sliceProfile": "nsp1"
        })

    def _generate_du(self, gnb_id, cluster_name, cells_for_this_gnb):
        num_dus = math.ceil(cells_for_this_gnb / 3.0)
        for du_id in range(1, num_dus + 1):
            self.du_data.append({
                "cluster": cluster_name,
                "gNBId": gnb_id,
                "gNBCUUPIds": 1,
                "gNBDUId": du_id,
                "gNBDUName": f"DU_{gnb_id}_{du_id}",
                "ruIpAddress": self.dummy_ip,
                "perfIpAddress": self.dummy_ip,
                "notifIpAddress": self.dummy_ip,
                "certIpAddress": self.dummy_ip,
                "confdIpAddress": self.dummy_ip,
                "confdProxyIpAddress": self.dummy_ip,
                "f1cIpAddress": self.dummy_ip,
                "f1uIpAddress": self.dummy_ip,
                "mcc": self.mcc,
                "mnc": self.mnc,
                "gcProfile": self.gc_profile_full,
                "rRMPolicyDedicatedRatio": 0,
                "rRMPolicyMaxRatio": 100,
                "rRMPolicyMinRatio": 0,
                "description": f"DU {du_id} for gNB {gnb_id}"
            })

    def _generate_oru_and_nrcell(self, gnb_id, cells_for_this_gnb):
        for cell_id in range(1, cells_for_this_gnb + 1):
            # 1 DU has 3 ORUs
            du_id_for_cell = math.ceil(cell_id / 3.0)
            oru_id = cell_id
            
            # Realistic radio serial number without symbols
            import string
            serial_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            radio_serial_number = f"RU{gnb_id}{oru_id:04d}{serial_suffix}"
            
            sector_id = (cell_id - 1) % 2
            
            site_lat = f"{random.uniform(-180.0, 180.0):.5f}"
            site_long = f"{random.uniform(-180.0, 180.0):.5f}"
            
            self.oru_data.append({
                "gNBId": gnb_id,
                "gNBDUId": du_id_for_cell,
                "ruId": oru_id,
                "radioSerialNumber": radio_serial_number,
                "siteId": f"gnb-{gnb_id}-site-{sector_id}",
                "siteLatitude": site_lat,
                "siteLongitute": site_long,
                "type": "ORAN",
                "manufacturer": "Prose",
                "cuPlaneInterface": "plane1",
                "cuPlaneVlanId": 60,
                "enableAisg": "false",
                "version": "",
                "gcProfile": self.gc_profile_full,
                "baseInterfaceName": "eth0",
                "radioCUPlanVlanId": 1,
                "description": f"ORU {oru_id} for gNB {gnb_id}"
            })
            
            self.nrcell_data.append({
                "radioSerialNumber": radio_serial_number,
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
                "ssbCarrierOffset": 6,
                "controlResSetZero": 7,
                "offsetToPointA": 100,
                "cellReserveState": "PLMN_ID_INFO_NOT_RESERVED",
                "ssbTransBitmap": 1,
                "description": f"NRCell {cell_id} for gNB {gnb_id}"
            })

    def write_csvs(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        folder_name = f"{self.config.start_gnb_id}_{self.config.total_nrcells}"
        folder_path = os.path.join(base_dir, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        self._write_csv(os.path.join(folder_path, "gNBCUCP.csv"), self.cucp_columns, self.cucp_data)
        self._write_csv(os.path.join(folder_path, "gNBCUUP.csv"), self.cuup_columns, self.cuup_data)
        self._write_csv(os.path.join(folder_path, "gNBDU.csv"), self.du_columns, self.du_data)
        self._write_csv(os.path.join(folder_path, "oru.csv"), self.oru_columns, self.oru_data)
        self._write_csv(os.path.join(folder_path, "nrcell.csv"), self.nrcell_columns, self.nrcell_data)

    def _write_csv(self, filename, columns, data):
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        print(f"Generated {filename} with {len(data)} records.")


def main():
    print("--- ORAN CSV Generator ---")
    config = Config('config.properties')
    print(f"Loaded config: Start gNodeB = {config.start_gnb_id}, NRCells = {config.total_nrcells}, GCProfile = {config.gc_profile}")
    
    generator = ORANCSVGenerator(config)
    generator.generate_data()
    generator.write_csvs()
    print("Finished generating all CSV files.")


if __name__ == "__main__":
    main()
