"""Unit tests for grocery list aggregation."""
from models import WeeklyPlan, PlannedMeal, Recipe, RecipeStep, Ingredient, DayOfWeek, MacroProfile
from datetime import date
from grocery_list import generate_grocery_list, can_combine_ingredients, normalize_ingredient_name, normalize_unit
from config import Config


def test_normalize_ingredient_name():
    """Test ingredient name normalization."""
    assert normalize_ingredient_name("  Chicken Breast  ") == "chicken breast"
    assert normalize_ingredient_name("Tomatoes") == "tomatoes"
    assert normalize_ingredient_name("Olive Oil") == "olive oil"


def test_normalize_unit():
    """Test unit normalization."""
    assert normalize_unit("cup") == "cups"
    assert normalize_unit("C") == "cups"
    assert normalize_unit("lb") == "lbs"
    assert normalize_unit("pound") == "lbs"
    assert normalize_unit("oz") == "oz"
    assert normalize_unit("piece") == "pieces"


def test_can_combine_ingredients():
    """Test ingredient combination logic."""
    ing1 = Ingredient(name="chicken", quantity=1.0, unit="lb", category="meat")
    ing2 = Ingredient(name="Chicken", quantity=0.5, unit="lbs", category="meat")
    assert can_combine_ingredients(ing1, ing2) == True
    
    ing3 = Ingredient(name="tomatoes", quantity=2.0, unit="cups", category="produce")
    ing4 = Ingredient(name="chicken", quantity=1.0, unit="lb", category="meat")
    assert can_combine_ingredients(ing3, ing4) == False
    
    ing5 = Ingredient(name="onion", quantity=1.0, unit="piece", category="produce")
    ing6 = Ingredient(name="onion", quantity=2.0, unit="pieces", category="produce")
    assert can_combine_ingredients(ing5, ing6) == True


def test_generate_grocery_list():
    """Test grocery list generation with ingredient aggregation."""
    # Create a simple meal plan
    recipe1 = Recipe(
        title="Test Meal 1",
        description="Test",
        servings=2,
        macro_profile=MacroProfile.HIGH_PROTEIN_LOW_CARB,
        prep_time_min=10,
        cook_time_min=30,
        ingredients=[
            Ingredient(name="chicken breast", quantity=1.0, unit="lb", category="meat"),
            Ingredient(name="broccoli", quantity=2.0, unit="cups", category="produce"),
        ],
        steps=[RecipeStep(order=1, instruction="Cook")]
    )
    
    recipe2 = Recipe(
        title="Test Meal 2",
        description="Test",
        servings=2,
        macro_profile=MacroProfile.HIGH_PROTEIN_LOW_CARB,
        prep_time_min=10,
        cook_time_min=30,
        ingredients=[
            Ingredient(name="Chicken Breast", quantity=0.5, unit="lbs", category="meat"),  # Should combine with recipe1
            Ingredient(name="carrots", quantity=1.0, unit="cup", category="produce"),
        ],
        steps=[RecipeStep(order=1, instruction="Cook")]
    )
    
    plan = WeeklyPlan(
        meals=[
            PlannedMeal(day=DayOfWeek.MONDAY, audience="adult", recipe=recipe1),
            PlannedMeal(day=DayOfWeek.TUESDAY, audience="adult", recipe=recipe2),
        ],
        week_of=date.today()
    )
    
    grocery_list = generate_grocery_list(plan, Config)
    
    # Should have 3 unique ingredients (chicken combined, broccoli, carrots)
    assert len(grocery_list) == 3
    
    # Find chicken - should have combined quantity
    chicken = next((ing for ing in grocery_list if "chicken" in ing.name.lower()), None)
    assert chicken is not None
    assert chicken.quantity == 1.5  # 1.0 + 0.5
    
    # Check broccoli and carrots are present
    broccoli = next((ing for ing in grocery_list if "broccoli" in ing.name.lower()), None)
    carrots = next((ing for ing in grocery_list if "carrots" in ing.name.lower()), None)
    assert broccoli is not None
    assert carrots is not None


def test_grocery_list_sorting():
    """Test that grocery list is sorted by category and name."""
    recipe = Recipe(
        title="Test",
        description="Test",
        servings=2,
        macro_profile=MacroProfile.HIGH_PROTEIN_LOW_CARB,
        prep_time_min=10,
        cook_time_min=30,
        ingredients=[
            Ingredient(name="zucchini", quantity=1.0, unit="cup", category="produce"),
            Ingredient(name="chicken", quantity=1.0, unit="lb", category="meat"),
            Ingredient(name="apples", quantity=2.0, unit="pieces", category="produce"),
        ],
        steps=[RecipeStep(order=1, instruction="Cook")]
    )
    
    plan = WeeklyPlan(
        meals=[PlannedMeal(day=DayOfWeek.MONDAY, audience="adult", recipe=recipe)],
        week_of=date.today()
    )
    
    grocery_list = generate_grocery_list(plan, Config)
    
    # Should be sorted: meat first (chicken), then produce (apples, zucchini alphabetically)
    assert len(grocery_list) == 3
    assert "chicken" in grocery_list[0].name.lower()
    assert "apples" in grocery_list[1].name.lower()
    assert "zucchini" in grocery_list[2].name.lower()


if __name__ == "__main__":
    test_normalize_ingredient_name()
    print("✓ test_normalize_ingredient_name passed")
    
    test_normalize_unit()
    print("✓ test_normalize_unit passed")
    
    test_can_combine_ingredients()
    print("✓ test_can_combine_ingredients passed")
    
    test_generate_grocery_list()
    print("✓ test_generate_grocery_list passed")
    
    test_grocery_list_sorting()
    print("✓ test_grocery_list_sorting passed")
    
    print("\nAll tests passed!")
