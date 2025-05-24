import logging
import asyncio
import yaml
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.yate.yate_integration import YateBTSIntegration, YateBTSConfig
from src.kamailio.ss7_module import KamailioSS7Module
from src.databases.mcc_mnc.mcc_mnc_database import MccMncDatabase

# Add the source directory to Python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pymongo import MongoClient
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('GSM_SS7_Init')

async def initialize_system():
    try:
        # Load configuration
        with open('config/gsm_ss7_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        # Initialize database
        db_client = MongoClient(config['database']['uri'])
        db = db_client[config['database']['name']]
        
        # Initialize YateBTS
        yate_config = config['yate']
        yate = YateBTSIntegration(YateBTSConfig(
            host=yate_config['host'],
            port=yate_config['port'],
            username=yate_config['username'],
            password=yate_config['password'],
            max_connections=yate_config['max_connections'],
            timeout=yate_config['timeout'],
            retry_delay=yate_config['retry_delay'],
            max_retries=yate_config['max_retries']
        ))
        
        # Initialize Kamailio SS7
        kamailio = KamailioSS7Module(config['kamailio'])
        
        # Initialize MCC-MNC database
        mcc_mnc_db = MccMncDatabase(db)
        
        # Start monitoring
        monitoring_tasks = []
        
        # Start YateBTS monitoring
        monitoring_tasks.append(
            asyncio.create_task(yate.start_monitoring('default'))
        )
        
        # Start SS7 protocol monitoring
        for protocol, config in config['ss7']['protocols'].items():
            if config.get('enabled', True):
                monitoring_tasks.append(
                    asyncio.create_task(kamailio.start_monitoring(protocol))
                )
        
        # Start MCC-MNC database refresh
        monitoring_tasks.append(
            asyncio.create_task(mcc_mnc_db.refresh_database())
        )
        
        # Wait for all monitoring tasks
        await asyncio.gather(*monitoring_tasks)
        
        logger.info("GSM/SS7 system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize GSM/SS7 system: {str(e)}")
        raise

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/gsm_ss7_init.log'),
            logging.StreamHandler()
        ]
    )
    
    # Run initialization
    asyncio.run(initialize_system())
