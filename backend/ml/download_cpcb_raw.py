"""
CPCB Raw Dataset Downloader & Verifier
Downloads official Uttar Pradesh surface water quality packages from NWDP / NWIC
and verifies their SHA-256 checksums for complete environment-independent reproducibility.
"""

import os
import hashlib
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EXPECTED_MANIFEST = {
    'physical_up_1961_2020.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/c547abaa-fbdc-4f46-b152-dc023be0c75c/resource/3aac0149-d815-42a6-975a-2e5c757256f6/download/swq_manual_physical_parameters_cpcb_up_1961_2020.csv',
        'sha256': 'b14dc5e3d59a7d307519e164d820a13ccf263f72dc7b919de652f0cf5f66c291',
        'size': 570765
    },
    'physical_up_2021_2025.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/c547abaa-fbdc-4f46-b152-dc023be0c75c/resource/caf05460-e4bc-498d-85f3-2ed21a595e89/download/swq_physical_parameter_manual_cpcb_up_2021_2025.csv',
        'sha256': '9ed3e9a7c8f30e957d5fa7024692646de6b0b1de4552828074b00f838746f66a',
        'size': 63519
    },
    'chemical_up_1961_2020.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/d54d7702-d21f-408f-8dc0-2665bde47201/resource/75c260b7-ab36-4cda-a21b-f6fe22387eb6/download/swq_manual_chemical_parameters_cpcb_up_1961_2020.csv',
        'sha256': 'ad3a143b7b6eccadc8e3381d46f971f458c3aea15ff71bef4e492656f38380df',
        'size': 901047
    },
    'chemical_up_2021_2025.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/d54d7702-d21f-408f-8dc0-2665bde47201/resource/fb147bf0-f952-4153-84ad-ef5cb39f6517/download/swq_chemical_parameter_manual_cpcb_up_2021_2025.csv',
        'sha256': 'f8e2c82a1fad3928271ac9e384f9f99027c12d6b69b1fc3029ce5e07268efd72',
        'size': 352325
    },
    'biological_up_1961_2020.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/e97bcc1b-895e-4eb9-a826-09d52f7b5ca0/resource/4b7b29f0-be59-499a-986a-58635449a08c/download/swq_manual_biological_parameters_cpcb_up_1961_2020.csv',
        'sha256': '2ea5f193d6b7a466d57d299f84207811cba05348c44c05c0d8a2896319a4fb56',
        'size': 557862
    },
    'biological_up_2021_2025.csv': {
        'url': 'https://nwdp.nwic.gov.in/dataset/e97bcc1b-895e-4eb9-a826-09d52f7b5ca0/resource/31003ead-35e6-488d-84c9-8536a3dd7ab9/download/swq_biological_parameter_manual_cpcb_up_2021_2025.csv',
        'sha256': '02b0a00ca59c5b55f06b790b1c526dd0f0ae0d2c3fb70d43135c133eb220613a',
        'size': 218320
    }
}


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ensure_cpcb_raw_datasets(target_dir=None):
    """
    Downloads and verifies all raw CPCB CSV datasets.
    Returns dict mapping filename to absolute path.
    """
    if target_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_dir = os.path.join(base_dir, 'data', 'raw', 'cpcb')
    
    os.makedirs(target_dir, exist_ok=True)
    paths = {}
    
    for filename, meta in EXPECTED_MANIFEST.items():
        dest = os.path.join(target_dir, filename)
        paths[filename] = dest
        
        need_download = True
        if os.path.exists(dest):
            actual_hash = compute_sha256(dest)
            if actual_hash == meta['sha256']:
                need_download = False
            else:
                print(f"[WARN] Hash mismatch for {filename}, re-downloading...")
        
        if need_download:
            print(f"[INFO] Downloading {filename} from NWDP...")
            resp = requests.get(meta['url'], verify=False, timeout=90)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to download {filename}: HTTP {resp.status_code}")
            with open(dest, 'wb') as f:
                f.write(resp.content)
            
            actual_hash = compute_sha256(dest)
            if actual_hash != meta['sha256']:
                raise ValueError(f"Checksum mismatch for {filename}! Expected {meta['sha256']}, got {actual_hash}")
            print(f"[OK] Downloaded and verified {filename} ({len(resp.content)} bytes)")
        else:
            print(f"[OK] Verified existing {filename}")
            
    return paths


if __name__ == '__main__':
    ensure_cpcb_raw_datasets()
