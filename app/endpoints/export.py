# in routers/router2.py
from fastapi import APIRouter

from app.db_api import database

router = APIRouter()

"""
@router.get("/endpoint2", response_model=List[schemas.SomeSchema])
def read_something(db: dependencies.Session = Depends(dependencies.get_db)):
    # Your endpoint logic here
    return []
"""
