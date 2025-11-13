"""In-memory storage for workflows and workers"""
from typing import Dict
from shared.schemas import Workflow, Worker

# In-memory storage (replace with database in production)
workflows: Dict[str, Workflow] = {}
workers: Dict[str, Worker] = {}
