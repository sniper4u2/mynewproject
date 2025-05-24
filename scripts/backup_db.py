import os
import subprocess
from datetime import datetime
import shutil

def backup_database():
    """Backup all databases"""
    backup_dir = os.path.join('backups', datetime.now().strftime('%Y%m%d_%H%M%S'))
    os.makedirs(backup_dir, exist_ok=True)

    print("\n=== Starting Database Backup ===\n")

    # MongoDB backup
    print("Backing up MongoDB...")
    subprocess.run(['mongodump', '--out', os.path.join(backup_dir, 'mongodb')], check=True)

    # InfluxDB backup
    print("Backing up InfluxDB...")
    subprocess.run(['influxd', 'backup', os.path.join(backup_dir, 'influxdb')], check=True)

    # Elasticsearch backup
    print("Backing up Elasticsearch...")
    subprocess.run(['elasticsearch-backup', os.path.join(backup_dir, 'elasticsearch')], check=True)

    # Redis backup
    print("Backing up Redis...")
    subprocess.run(['redis-cli', 'save'], check=True)
    shutil.copy('/var/lib/redis/dump.rdb', os.path.join(backup_dir, 'redis/dump.rdb'))

    print(f"\nAll databases backed up successfully to: {backup_dir}")

if __name__ == "__main__":
    backup_database()
