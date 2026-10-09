from fastapi import APIRouter
from sqlalchemy import text
from database.sql_conn import get_engine
from database.extract_metrics import get_metrics

router= APIRouter()

@router.get("/metrics")
def metrics():
     return get_metrics()