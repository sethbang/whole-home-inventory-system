from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Any, List, Optional
from .. import models, schemas, security, database
import uuid

router = APIRouter(tags=["items"])

@router.post("/items/", response_model=schemas.Item)
def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    db_item = models.Item(**item.model_dump(), owner_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/items", response_model=schemas.ItemList)
def list_items(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_value: Optional[float] = Query(None),
    max_value: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_desc: Optional[bool] = Query(False),
    page: Optional[int] = Query(1),
    page_size: Optional[int] = Query(20),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    # Convert empty strings to None
    query = None if query == "" else query
    category = None if category == "" else category
    location = None if location == "" else location
    sort_by = None if sort_by == "" else sort_by

    # Create search filter from query params
    try:
        search_filter = schemas.SearchFilter(
            query=query,
            category=category,
            location=location,
            min_value=min_value,
            max_value=max_value,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        print(f"Error creating SearchFilter: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search parameters: {str(e)}"
        )
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
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

@router.get("/items/barcode/{barcode}", response_model=schemas.Item, responses={404: {"model": schemas.Error}})
async def lookup_by_barcode(
    barcode: str,
    db: Session = Depends(database.get_db),
    current_user: Optional[models.User] = Depends(security.get_current_active_user_or_none)
) -> Any:
    query = db.query(models.Item).filter(models.Item.barcode == barcode)
    if current_user:
        query = query.filter(models.Item.owner_id == current_user.id)
    item = query.first()
    if not item:
        raise HTTPException(
            status_code=404,
            detail="No item found with this barcode"
        )
    return item

@router.get("/items/{item_id}", response_model=schemas.Item)
def get_item(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
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
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
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
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
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
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    categories = db.query(models.Item.category).filter(
        models.Item.owner_id == current_user.id
    ).distinct().all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/locations", response_model=List[str])
def get_locations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user_or_none)
) -> Any:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    locations = db.query(models.Item.location).filter(
        models.Item.owner_id == current_user.id
    ).distinct().all()
    return [loc[0] for loc in locations if loc[0]]
