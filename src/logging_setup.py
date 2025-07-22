import burr
import logging

# Initialize Burr tracing
burr.init(service_name="pdf-profile-app")

# Set up Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)

# Function to get the app logger

def get_logger(name="pdf-profile-app"):
    return logging.getLogger(name) 