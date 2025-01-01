"""
eBay category mapping system for WHIS items.
Maps internal WHIS categories to eBay category IDs.
"""

from typing import Dict, Optional, List

# Common eBay categories with their IDs
# Reference: https://pages.ebay.com/sellerinformation/news/categorychanges.html
EBAY_CATEGORIES: Dict[str, Dict[str, str]] = {
    # Electronics
    "electronics": {
        "id": "293",
        "subcategories": {
            "computers": "58058",
            "phones": "15032",
            "cameras": "625",
            "tv_video": "32852",
            "audio": "293",
        }
    },
    # Home & Garden
    "home": {
        "id": "11700",
        "subcategories": {
            "furniture": "3197",
            "appliances": "20710",
            "kitchen": "20625",
            "garden": "159912",
        }
    },
    # Sporting Goods
    "sports": {
        "id": "888",
        "subcategories": {
            "exercise": "15273",
            "outdoor": "159043",
            "team_sports": "159049",
        }
    },
    # Collectibles
    "collectibles": {
        "id": "1",
        "subcategories": {
            "antiques": "20081",
            "art": "550",
            "coins": "11116",
            "stamps": "260",
        }
    },
    # Tools
    "tools": {
        "id": "631",
        "subcategories": {
            "power_tools": "632",
            "hand_tools": "3244",
            "garden_tools": "181033",
        }
    },
}

# Default fallback category for unknown items
DEFAULT_CATEGORY = {
    "id": "11450",  # Everything Else
    "name": "Other Items"
}

def get_category_id(whis_category: str, subcategory: Optional[str] = None) -> str:
    """
    Map WHIS category to eBay category ID.
    
    Args:
        whis_category: Category from WHIS item
        subcategory: Optional subcategory for more specific mapping
    
    Returns:
        eBay category ID as string
    """
    # Normalize category name
    category_key = whis_category.lower().replace(" ", "_")
    
    if category_key in EBAY_CATEGORIES:
        if subcategory:
            # Try to find matching subcategory
            subcat_key = subcategory.lower().replace(" ", "_")
            if subcat_key in EBAY_CATEGORIES[category_key]["subcategories"]:
                return EBAY_CATEGORIES[category_key]["subcategories"][subcat_key]
        # Return main category if no subcategory match
        return EBAY_CATEGORIES[category_key]["id"]
    
    # Return default category if no match found
    return DEFAULT_CATEGORY["id"]

def get_all_categories() -> List[Dict[str, any]]:
    """
    Get all available eBay categories and subcategories.
    
    Returns:
        List of category dictionaries with IDs and subcategories
    """
    categories = []
    for main_cat, details in EBAY_CATEGORIES.items():
        category = {
            "name": main_cat.replace("_", " ").title(),
            "id": details["id"],
            "subcategories": [
                {
                    "name": sub_name.replace("_", " ").title(),
                    "id": sub_id
                }
                for sub_name, sub_id in details["subcategories"].items()
            ]
        }
        categories.append(category)
    return categories

def suggest_category(item_name: str, description: Optional[str] = None) -> str:
    """
    Suggest an eBay category based on item name and description.
    Basic implementation - can be enhanced with ML/AI in the future.
    
    Args:
        item_name: Name of the item
        description: Optional item description
    
    Returns:
        Suggested eBay category ID
    """
    # Normalize text for matching
    text = (item_name + " " + (description or "")).lower()
    
    # Simple keyword matching - can be enhanced with better algorithms
    keywords = {
        "electronics": ["phone", "computer", "laptop", "camera", "tv", "television", "audio"],
        "home": ["furniture", "appliance", "kitchen", "garden", "home"],
        "sports": ["exercise", "fitness", "sports", "outdoor"],
        "collectibles": ["antique", "art", "coin", "stamp", "collection"],
        "tools": ["tool", "drill", "saw", "hammer", "garden tools"],
    }
    
    # Find matching category based on keywords
    for category, words in keywords.items():
        if any(word in text for word in words):
            return EBAY_CATEGORIES[category]["id"]
    
    return DEFAULT_CATEGORY["id"]