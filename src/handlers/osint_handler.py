import os
import yaml
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import json
from scapy.all import *
from scapy.layers.inet import TCP, UDP, IP
from scapy.layers.http import HTTP
from scapy.layers.dns import DNS
from flask import jsonify

# Load OSINT configuration
def load_config():
    config_path = Path(__file__).parent / 'config' / 'osint_config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()
osint_config = config.get('osint', {})

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=osint_config.get('protocol_interception', {}).get('logging', {}).get('format', '%(asctime)s - %(levelname)s - %(message)s'),
    filename=osint_config.get('protocol_interception', {}).get('logging', {}).get('file', 'osint.log')
)
logger = logging.getLogger('OSINT')

class OSINTHandler:
    def __init__(self, db, encryption_key):
        self.capture_dir = Path(__file__).parent / 'captures'
        self.capture_dir.mkdir(exist_ok=True)
        self.current_capture = None
        self.capture_process = None
        self.db = db
        self.encryption_key = encryption_key

    def start_capture(self, interface=None, filter=None):
        """Start packet capture using tcpdump"""
        if self.capture_process:
            return jsonify({'error': 'Capture already in progress'})

        interface = interface or osint_config['wireshark']['capture']['interface']
        filter = filter or osint_config['wireshark']['capture']['capture_filter']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        capture_file = self.capture_dir / f'capture_{timestamp}.pcap'

        cmd = [
            'tcpdump',
            '-i', interface,
            '-w', str(capture_file),
            '-s', str(osint_config['wireshark']['capture']['buffer_size'])
        ]

        if filter:
            cmd.extend(['-f', filter])

        try:
            self.capture_process = subprocess.Popen(cmd)
            self.current_capture = capture_file
            logger.info(f'Started capture on {interface} with filter: {filter}')
            return jsonify({
                'status': 'success',
                'capture_file': str(capture_file),
                'interface': interface,
                'filter': filter
            })
        except Exception as e:
            logger.error(f'Failed to start capture: {str(e)}')
            return jsonify({'error': str(e)}), 500

    def stop_capture(self):
        """Stop current packet capture"""
        if not self.capture_process:
            return jsonify({'error': 'No capture in progress'})

        try:
            self.capture_process.terminate()
            self.capture_process.wait()
            self.capture_process = None
            logger.info('Capture stopped successfully')
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f'Failed to stop capture: {str(e)}')
            return jsonify({'error': str(e)}), 500

    def analyze_capture(self, capture_file=None):
        """Analyze a capture file using Scapy"""
        if not capture_file:
            capture_file = self.current_capture
        if not capture_file or not os.path.exists(capture_file):
            return jsonify({'error': 'No capture file available'})

        try:
            packets = rdpcap(str(capture_file))
            analysis = {
                'total_packets': len(packets),
                'protocols': {},
                'connections': {},
                'dns_requests': [],
                'http_requests': [],
                'tls_handshakes': []
            }

            for packet in packets:
                if packet.haslayer(IP):
                    ip_layer = packet[IP]
                    src_ip = ip_layer.src
                    dst_ip = ip_layer.dst

                    if packet.haslayer(TCP):
                        tcp_layer = packet[TCP]
                        src_port = tcp_layer.sport
                        dst_port = tcp_layer.dport
                        
                        # Track connections
                        conn_key = f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}"
                        if conn_key not in analysis['connections']:
                            analysis['connections'][conn_key] = {
                                'src': src_ip,
                                'src_port': src_port,
                                'dst': dst_ip,
                                'dst_port': dst_port,
                                'count': 0
                            }
                        analysis['connections'][conn_key]['count'] += 1

                        # Analyze HTTP
                        if packet.haslayer(HTTP):
                            analysis['http_requests'].append({
                                'timestamp': str(packet.time),
                                'src': src_ip,
                                'dst': dst_ip,
                                'method': packet[HTTP].Method.decode(),
                                'path': packet[HTTP].Path.decode()
                            })

                        # Analyze TLS
                        if packet.haslayer(TLS):
                            analysis['tls_handshakes'].append({
                                'timestamp': str(packet.time),
                                'src': src_ip,
                                'dst': dst_ip,
                                'handshake_type': 'TLS'
                            })

                    if packet.haslayer(UDP):
                        udp_layer = packet[UDP]
                        src_port = udp_layer.sport
                        dst_port = udp_layer.dport

                        # Analyze DNS
                        if packet.haslayer(DNS):
                            analysis['dns_requests'].append({
                                'timestamp': str(packet.time),
                                'src': src_ip,
                                'dst': dst_ip,
                                'query': packet[DNS].qd.qname.decode()
                            })

            # Clean up old captures
            self.cleanup_captures()

            return jsonify(analysis)

        except Exception as e:
            logger.error(f'Failed to analyze capture: {str(e)}')
            return jsonify({'error': str(e)}), 500

    def cleanup_captures(self):
        """Clean up old capture files"""
        retention_days = osint_config['wireshark']['storage']['retention_days']
        max_size_mb = osint_config['wireshark']['storage']['max_size_mb']

        current_size = sum(f.stat().st_size for f in self.capture_dir.glob('*.pcap') if f.is_file())
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # Delete old files
        for file in self.capture_dir.glob('*.pcap'):
            if file.stat().st_mtime < cutoff_date.timestamp():
                file.unlink()

        # Delete files if total size exceeds limit
        if current_size > max_size_mb * 1024 * 1024:
            files = sorted(self.capture_dir.glob('*.pcap'), key=lambda x: x.stat().st_mtime)
            while current_size > max_size_mb * 1024 * 1024 and files:
                oldest_file = files.pop(0)
                oldest_file.unlink()
                current_size -= oldest_file.stat().st_size

    def get_capture_files(self):
        """Get list of available capture files"""
        files = []
        for file in self.capture_dir.glob('*.pcap'):
            files.append({
                'name': file.name,
                'size': file.stat().st_size,
                'created': datetime.fromtimestamp(file.stat().st_ctime).isoformat(),
                'path': str(file)
            })
        return jsonify(files)


