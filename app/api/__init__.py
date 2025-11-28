"""
API Endpoints Module
Contains simulation and receipt scanning endpoints.
"""

from app.api.simulation_endpoints import router as simulation_router
from app.api.receipt_endpoints import router as receipt_router

__all__ = ['simulation_router', 'receipt_router']
