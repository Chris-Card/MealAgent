"""LLM-based meal planning logic."""
import json
import re
import time
from datetime import date
from typing import Optional
from anthropic import Anthropic
from models import WeeklyPlan, PlannedMeal, Recipe, RecipeStep, Ingredient, DayOfWeek, MacroProfile
from config import Config


def generate_weekly_plan(config: type[Config], week_of: Optional[date] = None, max_retries: int = 3) -> WeeklyPlan:
    """
    Generate a weekly meal plan using LLM.
    
    Args:
        config: Configuration class
        week_of: Optional date for the week. Defaults to today.
        max_retries: Maximum number of retry attempts if parsing fails
        
    Returns:
        WeeklyPlan with meals for Monday through Thursday
    """
    if week_of is None:
        week_of = date.today()
    
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    
    # Calculate servings with leftovers factor
    adult_servings = int(config.ADULT_SERVINGS * config.LEFTOVERS_FACTOR)
    child_servings = int(config.CHILD_SERVINGS * config.LEFTOVERS_FACTOR)
    
    prompt = f"""You are a meal planning assistant creating a weekly dinner menu for a family.

REQUIREMENTS:
- Plan meals for Monday, Tuesday, Wednesday, and Thursday only
- Monday & Tuesday: Meals should be geared towards an adult palate, optimized for HIGH PROTEIN and LOW CARBS
- Wednesday & Thursday: Meals should be geared towards children under 10 years old, with more relaxed macro composition and kid-friendly flavors
- Each meal should require approximately 25-40 minutes of active cooking time
- Scale servings appropriately: {adult_servings} servings for Mon/Tue, {child_servings} servings for Wed/Thu
- No dietary restrictions beyond the macro requirements mentioned above

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
  "meals": [
    {{
      "day": "MONDAY",
      "audience": "adult",
      "recipe": {{
        "title": "Recipe Name",
        "description": "Brief description",
        "servings": {adult_servings},
        "macro_profile": "high_protein_low_carb",
        "prep_time_min": 10,
        "cook_time_min": 30,
        "ingredients": [
          {{
            "name": "ingredient name",
            "quantity": 1.5,
            "unit": "cups",
            "category": "produce"
          }}
        ],
        "steps": [
          {{
            "order": 1,
            "instruction": "Step instruction text"
          }}
        ]
      }}
    }},
    // ... repeat for TUESDAY (adult), WEDNESDAY (kids), THURSDAY (kids)
  ]
}}

IMPORTANT:
- Include exactly 4 meals (one for each day)
- Use "high_protein_low_carb" for Mon/Tue macro_profile
- Use "kid_friendly_balanced" for Wed/Thu macro_profile
- Ensure all ingredients have realistic quantities and units
- Provide clear, actionable cooking steps
- Make sure cooking times are realistic (25-40 minutes total active time)
- Use appropriate ingredient categories: "produce", "meat", "pantry", "dairy", "frozen", "bakery", etc.

Generate a diverse and appealing weekly menu now:"""

    system_prompt = "You are a helpful meal planning assistant. Always respond with valid JSON only, with no markdown or code fences."

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=config.MODEL_NAME,
                max_tokens=config.LLM_MAX_TOKENS,
                temperature=config.LLM_TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            if not response.content:
                raise ValueError("Empty response from LLM")
            content = response.content[0].text
            if not content:
                raise ValueError("Empty response from LLM")

            # Strip optional markdown code fence so we get raw JSON
            content = re.sub(r"^```(?:json)?\s*", "", content.strip())
            content = re.sub(r"\s*```$", "", content)

            # Parse JSON response
            data = json.loads(content)
            
            # Validate and convert to models
            plan = _parse_weekly_plan(data, week_of, config)
            
            # Validate plan structure
            _validate_plan(plan)
            
            return plan
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"JSON parsing error (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)  # Brief delay before retry
                continue
            else:
                raise ValueError(f"Failed to parse JSON response after {max_retries} attempts: {e}")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error generating plan (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
                continue
            else:
                raise
    
    raise RuntimeError(f"Failed to generate plan after {max_retries} attempts")


def _parse_weekly_plan(data: dict, week_of: date, config: type[Config]) -> WeeklyPlan:
    """Parse JSON data into WeeklyPlan model."""
    meals = []
    
    for meal_data in data.get("meals", []):
        recipe_data = meal_data["recipe"]
        
        # Parse ingredients
        ingredients = [
            Ingredient(
                name=ing["name"],
                quantity=float(ing["quantity"]),
                unit=ing["unit"],
                category=ing.get("category")
            )
            for ing in recipe_data["ingredients"]
        ]
        
        # Parse steps
        steps = [
            RecipeStep(
                order=step["order"],
                instruction=step["instruction"]
            )
            for step in recipe_data["steps"]
        ]
        
        # Determine macro profile
        macro_profile_str = recipe_data.get("macro_profile", "").lower()
        if "high_protein" in macro_profile_str or "low_carb" in macro_profile_str:
            macro_profile = MacroProfile.HIGH_PROTEIN_LOW_CARB
        else:
            macro_profile = MacroProfile.KID_FRIENDLY_BALANCED
        
        recipe = Recipe(
            title=recipe_data["title"],
            description=recipe_data["description"],
            servings=int(recipe_data["servings"]),
            macro_profile=macro_profile,
            prep_time_min=int(recipe_data["prep_time_min"]),
            cook_time_min=int(recipe_data["cook_time_min"]),
            ingredients=ingredients,
            steps=steps
        )
        
        planned_meal = PlannedMeal(
            day=DayOfWeek(meal_data["day"]),
            audience=meal_data["audience"],
            recipe=recipe
        )
        
        meals.append(planned_meal)
    
    return WeeklyPlan(meals=meals, week_of=week_of)


def _validate_plan(plan: WeeklyPlan) -> None:
    """Validate that the plan meets all requirements."""
    required_days = {DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY}
    found_days = {meal.day for meal in plan.meals}
    
    if found_days != required_days:
        missing = required_days - found_days
        extra = found_days - required_days
        raise ValueError(f"Plan validation failed: missing days {missing}, extra days {extra}")
    
    if len(plan.meals) != 4:
        raise ValueError(f"Plan must have exactly 4 meals, found {len(plan.meals)}")
    
    # Validate Monday and Tuesday are adult-focused
    monday_meal = plan.get_meal_for_day(DayOfWeek.MONDAY)
    tuesday_meal = plan.get_meal_for_day(DayOfWeek.TUESDAY)
    
    if monday_meal and monday_meal.audience != "adult":
        raise ValueError("Monday meal must be adult-focused")
    if tuesday_meal and tuesday_meal.audience != "adult":
        raise ValueError("Tuesday meal must be adult-focused")
    if monday_meal and monday_meal.recipe.macro_profile != MacroProfile.HIGH_PROTEIN_LOW_CARB:
        raise ValueError("Monday meal must have high_protein_low_carb macro profile")
    if tuesday_meal and tuesday_meal.recipe.macro_profile != MacroProfile.HIGH_PROTEIN_LOW_CARB:
        raise ValueError("Tuesday meal must have high_protein_low_carb macro profile")
    
    # Validate Wednesday and Thursday are kid-focused
    wednesday_meal = plan.get_meal_for_day(DayOfWeek.WEDNESDAY)
    thursday_meal = plan.get_meal_for_day(DayOfWeek.THURSDAY)
    
    if wednesday_meal and wednesday_meal.audience != "kids":
        raise ValueError("Wednesday meal must be kid-focused")
    if thursday_meal and thursday_meal.audience != "kids":
        raise ValueError("Thursday meal must be kid-focused")
    if wednesday_meal and wednesday_meal.recipe.macro_profile != MacroProfile.KID_FRIENDLY_BALANCED:
        raise ValueError("Wednesday meal must have kid_friendly_balanced macro profile")
    if thursday_meal and thursday_meal.recipe.macro_profile != MacroProfile.KID_FRIENDLY_BALANCED:
        raise ValueError("Thursday meal must have kid_friendly_balanced macro profile")
    
    # Validate cooking times
    for meal in plan.meals:
        total_time = meal.recipe.total_time_min
        if total_time < 20 or total_time > 60:
            print(f"Warning: {meal.day} meal has total time {total_time} minutes (expected 25-40 min active cooking)")
        if meal.recipe.cook_time_min < 15 or meal.recipe.cook_time_min > 45:
            print(f"Warning: {meal.day} meal has cook time {meal.recipe.cook_time_min} minutes (expected 25-40 min)")
