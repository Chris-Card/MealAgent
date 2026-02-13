"""Email content building and formatting."""
from datetime import date
from models import WeeklyPlan, Ingredient, DayOfWeek
from grocery_list import format_grocery_list_for_display


def build_email_content(plan: WeeklyPlan, grocery_list: list[Ingredient]) -> tuple[str, str]:
    """
    Build HTML and plain text email content from meal plan and grocery list.
    
    Args:
        plan: Weekly meal plan
        grocery_list: Aggregated grocery list
        
    Returns:
        Tuple of (html_content, text_content)
    """
    html_content = _build_html_email(plan, grocery_list)
    text_content = _build_text_email(plan, grocery_list)
    
    return html_content, text_content


def _build_html_email(plan: WeeklyPlan, grocery_list: list[Ingredient]) -> str:
    """Build HTML email content."""
    html_parts = []
    
    # Header
    html_parts.append("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .meal-card { background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .meal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .meal-title { font-size: 1.3em; font-weight: bold; color: #2c3e50; }
        .meal-meta { color: #7f8c8d; font-size: 0.9em; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }
        .badge-adult { background: #e8f5e9; color: #2e7d32; }
        .badge-kids { background: #fff3e0; color: #e65100; }
        .ingredients { margin: 15px 0; }
        .ingredients ul { list-style: none; padding-left: 0; }
        .ingredients li { padding: 5px 0; border-bottom: 1px solid #ecf0f1; }
        .steps { margin: 15px 0; }
        .steps ol { padding-left: 20px; }
        .steps li { margin: 10px 0; }
        .grocery-list { background: #fff; border: 2px solid #3498db; padding: 20px; border-radius: 4px; margin: 30px 0; }
        .grocery-list h2 { margin-top: 0; }
        .category { margin: 15px 0; }
        .category-title { font-weight: bold; color: #2c3e50; margin-bottom: 8px; text-transform: uppercase; }
        .grocery-item { padding: 5px 0; }
    </style>
</head>
<body>
""")
    
    # Title
    week_str = plan.week_of.strftime("%B %d, %Y")
    html_parts.append(f'<h1>Weekly Dinner Plan (Week of {week_str})</h1>')
    
    # Weekly Overview
    html_parts.append('<h2>Weekly Overview</h2>')
    html_parts.append('<div style="margin-bottom: 30px;">')
    
    day_order = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY]
    for day in day_order:
        meal = plan.get_meal_for_day(day)
        if meal:
            badge_class = "badge-adult" if meal.audience == "adult" else "badge-kids"
            badge_text = "Adult • High Protein / Low Carb" if meal.audience == "adult" else "Kids • Kid-Friendly"
            macro_desc = "High Protein / Low Carb" if meal.audience == "adult" else "Kid-Friendly"
            
            html_parts.append(f"""
            <div class="meal-card">
                <div class="meal-header">
                    <div>
                        <span class="meal-title">{day.value.title()}: {meal.recipe.title}</span>
                        <span class="badge {badge_class}">{badge_text}</span>
                    </div>
                    <div class="meal-meta">
                        {meal.recipe.total_time_min} min ({meal.recipe.prep_time_min} prep + {meal.recipe.cook_time_min} cook)
                    </div>
                </div>
                <p>{meal.recipe.description}</p>
            </div>
            """)
    
    html_parts.append('</div>')
    
    # Detailed Recipes
    html_parts.append('<h2>Recipes</h2>')
    for day in day_order:
        meal = plan.get_meal_for_day(day)
        if meal:
            badge_class = "badge-adult" if meal.audience == "adult" else "badge-kids"
            badge_text = "Adult • High Protein / Low Carb" if meal.audience == "adult" else "Kids • Kid-Friendly"
            
            html_parts.append(f"""
            <div class="meal-card">
                <div class="meal-header">
                    <span class="meal-title">{day.value.title()}: {meal.recipe.title}</span>
                    <span class="badge {badge_class}">{badge_text}</span>
                </div>
                <p><strong>Description:</strong> {meal.recipe.description}</p>
                <p><strong>Servings:</strong> {meal.recipe.servings} | <strong>Time:</strong> {meal.recipe.total_time_min} min ({meal.recipe.prep_time_min} prep + {meal.recipe.cook_time_min} cook)</p>
                
                <div class="ingredients">
                    <strong>Ingredients:</strong>
                    <ul>
            """)
            
            for ing in meal.recipe.ingredients:
                qty_str = str(int(ing.quantity)) if ing.quantity == int(ing.quantity) else str(ing.quantity)
                html_parts.append(f'<li>{qty_str} {ing.unit} {ing.name}</li>')
            
            html_parts.append('</ul></div>')
            
            html_parts.append('<div class="steps"><strong>Instructions:</strong><ol>')
            for step in sorted(meal.recipe.steps, key=lambda s: s.order):
                html_parts.append(f'<li>{step.instruction}</li>')
            html_parts.append('</ol></div>')
            
            html_parts.append('</div>')
    
    # Grocery List
    html_parts.append('<div class="grocery-list">')
    html_parts.append('<h2>Grocery List</h2>')
    
    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for ing in grocery_list:
        by_category[ing.category].append(ing)
    
    sorted_categories = sorted([cat for cat in by_category.keys() if cat], key=str.lower)
    if None in by_category:
        sorted_categories.append(None)
    
    for category in sorted_categories:
        if category:
            html_parts.append(f'<div class="category"><div class="category-title">{category}</div>')
        else:
            html_parts.append('<div class="category"><div class="category-title">Other</div>')
        
        for ing in sorted(by_category[category], key=lambda x: x.name.lower()):
            qty_str = str(int(ing.quantity)) if ing.quantity == int(ing.quantity) else str(ing.quantity)
            html_parts.append(f'<div class="grocery-item">☐ {qty_str} {ing.unit} {ing.name}</div>')
        
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # Footer
    html_parts.append("""
</body>
</html>
""")
    
    return "".join(html_parts)


def _build_text_email(plan: WeeklyPlan, grocery_list: list[Ingredient]) -> str:
    """Build plain text email content."""
    lines = []
    
    # Header
    week_str = plan.week_of.strftime("%B %d, %Y")
    lines.append("=" * 80)
    lines.append(f"Weekly Dinner Plan (Week of {week_str})")
    lines.append("=" * 80)
    lines.append("")
    
    # Weekly Overview
    lines.append("WEEKLY OVERVIEW")
    lines.append("-" * 80)
    lines.append("")
    
    day_order = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY]
    for day in day_order:
        meal = plan.get_meal_for_day(day)
        if meal:
            audience_label = "Adult • High Protein / Low Carb" if meal.audience == "adult" else "Kids • Kid-Friendly"
            lines.append(f"{day.value.title()}: {meal.recipe.title}")
            lines.append(f"  {audience_label}")
            lines.append(f"  Time: {meal.recipe.total_time_min} min ({meal.recipe.prep_time_min} prep + {meal.recipe.cook_time_min} cook)")
            lines.append(f"  {meal.recipe.description}")
            lines.append("")
    
    # Detailed Recipes
    lines.append("")
    lines.append("=" * 80)
    lines.append("RECIPES")
    lines.append("=" * 80)
    lines.append("")
    
    for day in day_order:
        meal = plan.get_meal_for_day(day)
        if meal:
            audience_label = "Adult • High Protein / Low Carb" if meal.audience == "adult" else "Kids • Kid-Friendly"
            lines.append(f"{day.value.title()}: {meal.recipe.title}")
            lines.append(f"[{audience_label}]")
            lines.append("-" * 80)
            lines.append(f"Description: {meal.recipe.description}")
            lines.append(f"Servings: {meal.recipe.servings}")
            lines.append(f"Time: {meal.recipe.total_time_min} min ({meal.recipe.prep_time_min} prep + {meal.recipe.cook_time_min} cook)")
            lines.append("")
            lines.append("Ingredients:")
            for ing in meal.recipe.ingredients:
                qty_str = str(int(ing.quantity)) if ing.quantity == int(ing.quantity) else str(ing.quantity)
                lines.append(f"  • {qty_str} {ing.unit} {ing.name}")
            lines.append("")
            lines.append("Instructions:")
            for step in sorted(meal.recipe.steps, key=lambda s: s.order):
                lines.append(f"  {step.order}. {step.instruction}")
            lines.append("")
            lines.append("")
    
    # Grocery List
    lines.append("=" * 80)
    lines.append("GROCERY LIST")
    lines.append("=" * 80)
    lines.append("")
    
    # Use the formatting function from grocery_list
    grocery_text = format_grocery_list_for_display(grocery_list)
    lines.append(grocery_text)
    lines.append("")
    
    return "\n".join(lines)
