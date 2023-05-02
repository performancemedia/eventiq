import os

from eventiq.config.factory import create_app

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

service = create_app(CONFIG_FILE, section="DEV")
