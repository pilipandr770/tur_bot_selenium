# run.py
import os
from flask import Flask
from app.init import create_app
from app.models import db
from app.scheduler import start_scheduler
from app.utils.logging_utils import setup_logging

# Set up logging
loggers = setup_logging()
logger = loggers['app_logger']

# Create the application
app = create_app()

# Note: db.init_app(app) is already called in create_app(), so we don't need to call it again

start_scheduler(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
