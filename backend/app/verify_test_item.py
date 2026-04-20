from . import models
from .database import SessionLocal


def verify_test_item():
    db = SessionLocal()
    try:
        # Try to find the item
        item = (
            db.query(models.Item).filter(models.Item.barcode == "9780262529846").first()
        )

        if item:
            print("Found item:")
            print(f"ID: {item.id}")
            print(f"Name: {item.name}")
            print(f"Barcode: {item.barcode}")
            print(f"Owner ID: {item.owner_id}")
        else:
            print("No item found with barcode 9780262529846")

    finally:
        db.close()


if __name__ == "__main__":
    verify_test_item()
