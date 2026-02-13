"""Grocery list aggregation logic."""
from collections import defaultdict
from typing import Optional
from models import WeeklyPlan, Ingredient
from config import Config


def normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient name for comparison (lowercase, strip whitespace)."""
    return name.lower().strip()


def normalize_unit(unit: str) -> str:
    """Normalize unit for comparison."""
    unit_lower = unit.lower().strip()
    # Handle common unit variations
    unit_mappings = {
        "cup": "cups",
        "c": "cups",
        "pound": "lbs",
        "lb": "lbs",
        "pounds": "lbs",
        "ounce": "oz",
        "ounces": "oz",
        "piece": "pieces",
        "item": "pieces",
        "whole": "pieces",
    }
    return unit_mappings.get(unit_lower, unit_lower)


def can_combine_ingredients(ing1: Ingredient, ing2: Ingredient) -> bool:
    """Check if two ingredients can be combined (same name and compatible units)."""
    name1 = normalize_ingredient_name(ing1.name)
    name2 = normalize_ingredient_name(ing2.name)
    
    if name1 != name2:
        return False
    
    unit1 = normalize_unit(ing1.unit)
    unit2 = normalize_unit(ing2.unit)
    
    # Same unit = can combine
    if unit1 == unit2:
        return True
    
    # Check for compatible units (simple cases)
    compatible_units = {
        ("cups", "cup"),
        ("lbs", "lb", "pound", "pounds"),
        ("oz", "ounce", "ounces"),
        ("pieces", "piece", "whole", "item"),
        ("tbsp", "tablespoon", "tablespoons"),
        ("tsp", "teaspoon", "teaspoons"),
    }
    
    for unit_group in compatible_units:
        if unit1 in unit_group and unit2 in unit_group:
            return True
    
    return False


def generate_grocery_list(plan: WeeklyPlan, config: type[Config]) -> list[Ingredient]:
    """
    Generate an aggregated grocery list from the weekly meal plan.
    
    Args:
        plan: Weekly meal plan
        config: Configuration class
        
    Returns:
        List of aggregated ingredients, sorted by category and name
    """
    # Dictionary keyed by (normalized_name, normalized_unit) -> aggregated ingredient
    aggregated: dict[tuple[str, str], Ingredient] = {}
    
    for meal in plan.meals:
        for ingredient in meal.recipe.ingredients:
            # Try to find existing ingredient to combine with
            combined = False
            for key, existing_ing in aggregated.items():
                if can_combine_ingredients(ingredient, existing_ing):
                    # Combine quantities
                    existing_ing.quantity += ingredient.quantity
                    combined = True
                    break
            
            if not combined:
                # Create new entry
                norm_name = normalize_ingredient_name(ingredient.name)
                norm_unit = normalize_unit(ingredient.unit)
                key = (norm_name, norm_unit)
                
                # Use the first occurrence's category if available
                aggregated[key] = Ingredient(
                    name=ingredient.name,  # Keep original capitalization from first occurrence
                    quantity=ingredient.quantity,
                    unit=ingredient.unit,  # Keep original unit format
                    category=ingredient.category
                )
    
    # Convert to list and sort
    grocery_list = list(aggregated.values())
    
    # Sort by category (None/empty category goes last), then by name
    def sort_key(ing: Ingredient) -> tuple[str, str]:
        category = ing.category or "zzz_uncategorized"
        return (category.lower(), normalize_ingredient_name(ing.name))
    
    grocery_list.sort(key=sort_key)
    
    return grocery_list


def format_grocery_list_for_display(grocery_list: list[Ingredient]) -> str:
    """
    Format grocery list as a readable string, grouped by category.
    
    Args:
        grocery_list: List of ingredients
        
    Returns:
        Formatted string
    """
    # Group by category
    by_category: dict[Optional[str], list[Ingredient]] = defaultdict(list)
    for ing in grocery_list:
        by_category[ing.category].append(ing)
    
    lines = []
    current_category = None
    
    # Sort categories (None/empty last)
    sorted_categories = sorted(
        [cat for cat in by_category.keys() if cat],
        key=str.lower
    )
    if None in by_category:
        sorted_categories.append(None)
    
    for category in sorted_categories:
        if category != current_category:
            if category:
                lines.append(f"\n{category.upper()}:")
            else:
                lines.append("\nOTHER:")
            current_category = category
        
        for ing in sorted(by_category[category], key=lambda x: normalize_ingredient_name(x.name)):
            # Format quantity nicely
            if ing.quantity == int(ing.quantity):
                qty_str = str(int(ing.quantity))
            else:
                qty_str = str(ing.quantity)
            
            lines.append(f"  • {qty_str} {ing.unit} {ing.name}")
    
    return "\n".join(lines)
