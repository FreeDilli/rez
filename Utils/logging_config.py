import logging
import os

def setup_logging():
    os.makedirs('./logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('./logs/app.log')
        ]
    )