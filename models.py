"""Data models for the weekly dinner planning agent."""
from enum import Enum
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field


class DayOfWeek(str, Enum):
    """Days of the week for meal planning."""
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


# Canonical meal type tags for dietary preferences (config and display).
# The LLM may return these or similar strings; we normalize for display.
MEAL_TYPE_LABELS = {
    "high_protein": "High Protein",
    "high_protein_low_carb": "High Protein / Low Carb",
    "gluten_free": "Gluten Free",
    "vegetarian": "Vegetarian",
    "vegan": "Vegan",
    "kid_friendly": "Kid Friendly",
    "low_carb": "Low Carb",
    "dairy_free": "Dairy Free",
    "nut_free": "Nut Free",
    "balanced": "Balanced",
}


class MacroProfile(str, Enum):
    """Legacy macro profile; used when meal_type maps to these."""
    HIGH_PROTEIN_LOW_CARB = "high_protein_low_carb"
    KID_FRIENDLY_BALANCED = "kid_friendly_balanced"
    BALANCED = "balanced"


class Ingredient(BaseModel):
    """Represents a single ingredient with quantity and unit."""
    name: str = Field(..., description="Name of the ingredient")
    quantity: float = Field(..., description="Quantity needed")
    unit: str = Field(..., description="Unit of measurement (e.g., 'cups', 'lbs', 'oz', 'pieces')")
    category: Optional[str] = Field(None, description="Category for grocery organization (e.g., 'produce', 'meat', 'pantry')")


class RecipeStep(BaseModel):
    """A single step in a recipe."""
    order: int = Field(..., description="Step number (1-indexed)")
    instruction: str = Field(..., description="Instruction text for this step")


class Recipe(BaseModel):
    """Complete recipe with ingredients, steps, and metadata."""
    title: str = Field(..., description="Name of the recipe")
    description: str = Field(..., description="Brief description of the meal")
    servings: int = Field(..., description="Number of servings this recipe makes")
    macro_profile: MacroProfile = Field(..., description="Legacy macro profile type")
    meal_type: str = Field(default="balanced", description="Dietary/meal type tag, e.g. high_protein, vegetarian, kid_friendly")
    prep_time_min: int = Field(..., description="Preparation time in minutes")
    cook_time_min: int = Field(..., description="Active cooking time in minutes")
    ingredients: list[Ingredient] = Field(..., description="List of ingredients needed")
    steps: list[RecipeStep] = Field(..., description="Step-by-step cooking instructions")

    @property
    def total_time_min(self) -> int:
        """Total time including prep and cooking."""
        return self.prep_time_min + self.cook_time_min


class PlannedMeal(BaseModel):
    """A meal planned for a specific day."""
    day: DayOfWeek = Field(..., description="Day of the week")
    audience: str = Field(..., description="Target audience: 'adult' or 'kids'")
    meal_type: str = Field(default="balanced", description="Dietary/meal type tag for this meal")
    recipe: Recipe = Field(..., description="The recipe for this meal")


class WeeklyPlan(BaseModel):
    """Complete weekly meal plan for all seven days."""
    meals: list[PlannedMeal] = Field(..., description="List of planned meals")
    week_of: date = Field(default_factory=lambda: date.today(), description="Date representing the week this plan is for")
    
    def get_meal_for_day(self, day: DayOfWeek) -> Optional[PlannedMeal]:
        """Get the meal planned for a specific day."""
        for meal in self.meals:
            if meal.day == day:
                return meal
        return None


def get_all_days_order() -> list[DayOfWeek]:
    """Return all days Monday through Sunday in order."""
    return [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
        DayOfWeek.SATURDAY,
        DayOfWeek.SUNDAY,
    ]


def get_meal_type_label(meal_type: str) -> str:
    """Return human-readable label for a meal_type tag."""
    key = (meal_type or "balanced").lower().strip().replace(" ", "_")
    return MEAL_TYPE_LABELS.get(key, meal_type.replace("_", " ").title())
