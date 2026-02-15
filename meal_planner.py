"""LLM-based meal planning logic."""
import json
import re
import time
from datetime import date
from typing import Optional
from anthropic import Anthropic
from anthropic import APIStatusError
from models import WeeklyPlan, PlannedMeal, Recipe, RecipeStep, Ingredient, DayOfWeek, MacroProfile
from config import Config

# Retry with backoff for transient API errors (overloaded, rate limit, server unavailable)
RETRYABLE_STATUS_CODES = (429, 503, 529)


def _parse_json_plan(content: str) -> dict:
    """
    Parse JSON from LLM response. Tries normal parse first, then simple repairs
    (trailing commas, truncation at last complete meal) to avoid failing on minor issues.
    """
    first_error = None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        first_error = e

    # Repair 1: Remove trailing comma before ] or }
    repaired = re.sub(r",\s*([\]}])", r"\1", content)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Repair 2: If truncated mid-response, close at last complete meal.
    # Find the last "}, \"day\": \"X\"" (end of one meal, start of next); truncate before it and add ]}
    for day in ("SUNDAY", "SATURDAY", "FRIDAY", "THURSDAY", "WEDNESDAY", "TUESDAY", "MONDAY"):
        pattern = '}, "day": "' + day + '"'
        idx = content.rfind(pattern)
        if idx != -1:
            truncated = content[:idx].rstrip()
            if truncated.endswith(","):
                truncated = truncated[:-1]
            truncated += "\n  ]\n}"
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                break

    if first_error is not None:
        raise first_error
    raise json.JSONDecodeError("JSON repair failed", content, 0)


def generate_weekly_plan(config: type[Config], week_of: Optional[date] = None, max_retries: int = 3) -> WeeklyPlan:
    """
    Generate a weekly meal plan using LLM.
    
    Args:
        config: Configuration class
        week_of: Optional date for the week. Defaults to today.
        max_retries: Maximum number of retry attempts if parsing fails
        
    Returns:
        WeeklyPlan with meals for all seven days (Monday through Sunday)
    """
    if week_of is None:
        week_of = date.today()

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # Calculate servings with leftovers factor
    adult_servings = int(config.ADULT_SERVINGS * config.LEFTOVERS_FACTOR)
    child_servings = int(config.CHILD_SERVINGS * config.LEFTOVERS_FACTOR)

    meal_types_str = ", ".join(config.MEAL_TYPES) if config.MEAL_TYPES else "high_protein, vegetarian, kid_friendly, balanced"
    avoid_str = "None" if not config.ALLERGIES_AVOID else ", ".join(config.ALLERGIES_AVOID)

    prompt = f"""You are a meal planning assistant creating a weekly dinner menu for a family.

REQUIREMENTS:
- Plan meals for ALL SEVEN DAYS: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, and Sunday.
- Each day must have exactly one dinner.
- MEAL TYPES to use across the week (vary by day): {meal_types_str}. Assign each day one of these types so the week includes a good mix (e.g. some High Protein, some Vegetarian, some Kid Friendly, etc.).
- ALLERGIES / INGREDIENTS TO AVOID (do not use in any recipe): {avoid_str}. Do not include these or any derivative (e.g. no peanut oil if peanuts are avoided).
- Each meal should require approximately 25-45 minutes of active cooking time.
- Servings: use {adult_servings} for adult-oriented meals (high_protein, high_protein_low_carb, low_carb, balanced) and {child_servings} for kid_friendly meals. For vegetarian/vegan use {adult_servings} unless you mark audience as "kids".
- Set "audience" to "adult" or "kids" per meal based on the meal type and style.

BREVITY (required so all 7 days fit in one response):
- Maximum 6 ingredients per recipe. Maximum 4 steps per recipe.
- Description: one short sentence only.
- Each instruction: one short sentence only (e.g. "Heat oil in a pan and add onions."). No paragraphs or lists inside a step.

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
  "meals": [
    {{
      "day": "MONDAY",
      "audience": "adult",
      "meal_type": "high_protein",
      "recipe": {{
        "title": "Recipe Name",
        "description": "Brief description",
        "servings": {adult_servings},
        "macro_profile": "high_protein_low_carb",
        "meal_type": "high_protein",
        "prep_time_min": 10,
        "cook_time_min": 30,
        "ingredients": [
          {{ "name": "ingredient name", "quantity": 1.5, "unit": "cups", "category": "produce" }}
        ],
        "steps": [
          {{ "order": 1, "instruction": "Step instruction text" }}
        ]
      }}
    }},
    // ... one object for TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY (same structure)
  ]
}}

IMPORTANT:
- Include exactly 7 meals: one for MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY.
- "meal_type" must be one of: {meal_types_str} (use snake_case). Match "macro_profile" to meal_type where applicable (high_protein/high_protein_low_carb, kid_friendly/kid_friendly_balanced, vegetarian/vegan/balanced).
- Do not use any ingredient from the avoid list.
- Ensure all ingredients have realistic quantities and units.
- Provide clear, actionable cooking steps (one short line per step; no newlines inside the instruction string).
- Use appropriate ingredient categories: "produce", "meat", "pantry", "dairy", "frozen", "bakery", etc.

JSON RULES (critical for valid output):
- Every string value must be on one line. No newlines inside JSON strings.
- Escape any double quote inside a string with a backslash (e.g. \\").
- Respect the 6-ingredient and 4-step maximums so the response is not truncated.

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

            # Parse JSON (with repair attempt on failure)
            data = _parse_json_plan(content)
            
            # Validate and convert to models
            plan = _parse_weekly_plan(data, week_of, config)
            
            # Validate plan structure
            _validate_plan(plan)
            
            return plan
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"JSON parsing error (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2)
                continue
            else:
                raise ValueError(f"Failed to parse JSON response after {max_retries} attempts: {e}")
        except APIStatusError as e:
            if getattr(e, "status_code", None) in RETRYABLE_STATUS_CODES and attempt < max_retries - 1:
                delay = 5 * (2 ** attempt)  # 5s, 10s, 20s
                print(f"API overloaded/unavailable (attempt {attempt + 1}/{max_retries}, status={e.status_code}). Retrying in {delay}s...")
                time.sleep(delay)
                continue
            raise
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

        ingredients = [
            Ingredient(
                name=ing["name"],
                quantity=float(ing["quantity"]),
                unit=ing["unit"],
                category=ing.get("category"),
            )
            for ing in recipe_data["ingredients"]
        ]

        steps = [
            RecipeStep(order=step["order"], instruction=step["instruction"])
            for step in recipe_data["steps"]
        ]

        macro_profile_str = (recipe_data.get("macro_profile") or "").lower()
        if "high_protein" in macro_profile_str or "low_carb" in macro_profile_str:
            macro_profile = MacroProfile.HIGH_PROTEIN_LOW_CARB
        elif "kid_friendly" in macro_profile_str or "balanced" in macro_profile_str:
            macro_profile = MacroProfile.KID_FRIENDLY_BALANCED
        else:
            macro_profile = MacroProfile.BALANCED

        meal_type = (recipe_data.get("meal_type") or meal_data.get("meal_type") or "balanced").strip().lower().replace(" ", "_")

        recipe = Recipe(
            title=recipe_data["title"],
            description=recipe_data["description"],
            servings=int(recipe_data["servings"]),
            macro_profile=macro_profile,
            meal_type=meal_type,
            prep_time_min=int(recipe_data["prep_time_min"]),
            cook_time_min=int(recipe_data["cook_time_min"]),
            ingredients=ingredients,
            steps=steps,
        )

        planned_meal = PlannedMeal(
            day=DayOfWeek(meal_data["day"]),
            audience=meal_data.get("audience", "adult"),
            meal_type=meal_type,
            recipe=recipe,
        )
        meals.append(planned_meal)

    return WeeklyPlan(meals=meals, week_of=week_of)


def _validate_plan(plan: WeeklyPlan) -> None:
    """Validate that the plan has all seven days and basic structure."""
    required_days = {
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
        DayOfWeek.SATURDAY,
        DayOfWeek.SUNDAY,
    }
    found_days = {meal.day for meal in plan.meals}

    if found_days != required_days:
        missing = required_days - found_days
        extra = found_days - required_days
        raise ValueError(f"Plan validation failed: missing days {missing}, extra days {extra}")

    if len(plan.meals) != 7:
        raise ValueError(f"Plan must have exactly 7 meals, found {len(plan.meals)}")

    for meal in plan.meals:
        total_time = meal.recipe.total_time_min
        if total_time < 15 or total_time > 75:
            print(f"Warning: {meal.day} meal has total time {total_time} minutes (expected 25-45 min active cooking)")
        if meal.recipe.cook_time_min < 10 or meal.recipe.cook_time_min > 55:
            print(f"Warning: {meal.day} meal has cook time {meal.recipe.cook_time_min} minutes (expected 25-45 min)")
