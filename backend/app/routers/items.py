from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Any, List
from .. import models, schemas, security, database
import uuid

router = APIRouter(tags=["items"])

@router.post("/items/", response_model=schemas.Item)
def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    db_item = models.Item(**item.model_dump(), owner_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/items/", response_model=schemas.ItemList)
def list_items(
    search_filter: schemas.SearchFilter = Depends(),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    query = db.query(models.Item).filter(models.Item.owner_id == current_user.id)
    
    # Apply filters
    if search_filter.query:
        search = f"%{search_filter.query}%"
        query = query.filter(
            or_(
                models.Item.name.ilike(search),
                models.Item.category.ilike(search),
                models.Item.location.ilike(search),
                models.Item.brand.ilike(search),
                models.Item.notes.ilike(search)
            )
        )
    
    if search_filter.category:
        query = query.filter(models.Item.category == search_filter.category)
    
    if search_filter.location:
        query = query.filter(models.Item.location == search_filter.location)
    
    if search_filter.min_value is not None:
        query = query.filter(models.Item.current_value >= search_filter.min_value)
    
    if search_filter.max_value is not None:
        query = query.filter(models.Item.current_value <= search_filter.max_value)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if search_filter.sort_by:
        if hasattr(models.Item, search_filter.sort_by):
            order_by = getattr(models.Item, search_filter.sort_by)
            if search_filter.sort_desc:
                order_by = order_by.desc()
            query = query.order_by(order_by)
    
    # Apply pagination
    query = query.offset((search_filter.page - 1) * search_filter.page_size)
    query = query.limit(search_filter.page_size)
    
    items = query.all()
    return {
        "items": items,
        "total": total,
        "page": search_filter.page,
        "page_size": search_filter.page_size
    }

@router.get("/items/{item_id}", response_model=schemas.Item)
def get_item(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    item = db.query(models.Item).filter(
        and_(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/items/{item_id}", response_model=schemas.Item)
def update_item(
    item_id: uuid.UUID,
    item_update: schemas.ItemUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    db_item = db.query(models.Item).filter(
        and_(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}")
def delete_item(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    db_item = db.query(models.Item).filter(
        and_(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return {"status": "success"}

@router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    categories = db.query(models.Item.category).filter(
        models.Item.owner_id == current_user.id
    ).distinct().all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/items/barcode/{barcode}", response_model=schemas.Item)
def lookup_by_barcode(
    barcode: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    item = db.query(models.Item).filter(
        and_(
            models.Item.barcode == barcode,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="No item found with this barcode")
    return item

@router.get("/items/barcode/{barcode}", response_model=schemas.Item)
def lookup_by_barcode(
    barcode: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    item = db.query(models.Item).filter(
        and_(
            models.Item.barcode == barcode,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="No item found with this barcode")
    return item

@router.get("/locations", response_model=List[str])
def get_locations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    locations = db.query(models.Item.location).filter(
        models.Item.owner_id == current_user.id
    ).distinct().all()
    return [loc[0] for loc in locations if loc[0]]
