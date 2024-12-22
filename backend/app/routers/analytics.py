from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Dict, List
from datetime import datetime
from .. import models, security, database

router = APIRouter(tags=["analytics"])

@router.get("/analytics/value-by-category")
def get_value_by_category(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> List[Dict[str, Any]]:
    results = db.query(
        models.Item.category,
        func.count(models.Item.id).label('item_count'),
        func.sum(models.Item.current_value).label('total_value')
    ).filter(
        models.Item.owner_id == current_user.id
    ).group_by(
        models.Item.category
    ).all()
    
    return [
        {
            "category": r.category,
            "item_count": r.item_count,
            "total_value": float(r.total_value) if r.total_value else 0
        }
        for r in results
    ]

@router.get("/analytics/value-by-location")
def get_value_by_location(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> List[Dict[str, Any]]:
    results = db.query(
        models.Item.location,
        func.count(models.Item.id).label('item_count'),
        func.sum(models.Item.current_value).label('total_value')
    ).filter(
        models.Item.owner_id == current_user.id
    ).group_by(
        models.Item.location
    ).all()
    
    return [
        {
            "location": r.location,
            "item_count": r.item_count,
            "total_value": float(r.total_value) if r.total_value else 0
        }
        for r in results
    ]

@router.get("/analytics/value-trends")
def get_value_trends(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Dict[str, Any]:
    items = db.query(
        models.Item.purchase_date,
        models.Item.purchase_price,
        models.Item.current_value
    ).filter(
        models.Item.owner_id == current_user.id,
        models.Item.purchase_date.isnot(None)
    ).all()
    
    total_purchase = sum(item.purchase_price or 0 for item in items)
    total_current = sum(item.current_value or 0 for item in items)
    
    return {
        "total_purchase_value": total_purchase,
        "total_current_value": total_current,
        "value_change": total_current - total_purchase,
        "value_change_percentage": ((total_current - total_purchase) / total_purchase * 100) if total_purchase else 0
    }

@router.get("/analytics/warranty-status")
def get_warranty_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Dict[str, Any]:
    from dateutil.relativedelta import relativedelta
    
    now = datetime.utcnow()
    three_months_later = now + relativedelta(months=3)
    
    expiring_soon = db.query(models.Item).filter(
        models.Item.owner_id == current_user.id,
        models.Item.warranty_expiration > now,
        models.Item.warranty_expiration <= three_months_later
    ).all()
    
    expired = db.query(models.Item).filter(
        models.Item.owner_id == current_user.id,
        models.Item.warranty_expiration <= now,
        models.Item.warranty_expiration.isnot(None)
    ).all()
    
    active = db.query(models.Item).filter(
        models.Item.owner_id == current_user.id,
        models.Item.warranty_expiration > three_months_later
    ).all()
    
    return {
        "expiring_soon": [
            {
                "id": str(item.id),
                "name": item.name,
                "expiration_date": item.warranty_expiration
            }
            for item in expiring_soon
        ],
        "expired": [
            {
                "id": str(item.id),
                "name": item.name,
                "expiration_date": item.warranty_expiration
            }
            for item in expired
        ],
        "active": [
            {
                "id": str(item.id),
                "name": item.name,
                "expiration_date": item.warranty_expiration
            }
            for item in active
        ]
    }

@router.get("/analytics/age-analysis")
def get_age_analysis(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Dict[str, Any]:
    now = datetime.utcnow()
    items = db.query(models.Item).filter(
        models.Item.owner_id == current_user.id,
        models.Item.purchase_date.isnot(None)
    ).all()
    
    age_ranges = {
        "0-1 year": [],
        "1-3 years": [],
        "3-5 years": [],
        "5+ years": []
    }
    
    for item in items:
        age = (now - item.purchase_date).days / 365
        if age <= 1:
            age_ranges["0-1 year"].append(item)
        elif age <= 3:
            age_ranges["1-3 years"].append(item)
        elif age <= 5:
            age_ranges["3-5 years"].append(item)
        else:
            age_ranges["5+ years"].append(item)
    
    return {
        range_name: {
            "count": len(items),
            "total_value": sum(item.current_value or 0 for item in items),
            "items": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "purchase_date": item.purchase_date,
                    "current_value": item.current_value
                }
                for item in items
            ]
        }
        for range_name, items in age_ranges.items()
    }