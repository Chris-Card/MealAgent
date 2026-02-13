"""Main entry point for the weekly dinner planning agent."""
import argparse
import sys
from datetime import date
from typing import Optional
from config import Config
from meal_planner import generate_weekly_plan
from grocery_list import generate_grocery_list
from email_builder import build_email_content
from gmail_smtp import send_email


def main(dry_run: bool = False, week_of: Optional[date] = None):
    """Run the weekly meal planning pipeline."""
    # Validate configuration
    errors = Config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease set the required environment variables or create a .env file.")
        sys.exit(1)
    
    try:
        # Generate weekly meal plan
        print("Generating weekly meal plan...")
        plan = generate_weekly_plan(Config, week_of=week_of)
        print(f"✓ Generated plan for {len(plan.meals)} meals")
        
        # Generate grocery list
        print("Generating grocery list...")
        grocery_list = generate_grocery_list(plan, Config)
        print(f"✓ Generated grocery list with {len(grocery_list)} items")
        
        # Build email content
        print("Building email content...")
        html_content, text_content = build_email_content(plan, grocery_list)
        print("✓ Email content built")
        
        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN - Email would be sent to:", Config.TARGET_EMAIL)
            print("="*80)
            print("\nTEXT VERSION:")
            print(text_content)
            if Config.INCLUDE_HTML_EMAIL:
                print("\n" + "="*80)
                print("HTML VERSION:")
                print(html_content)
            print("\n" + "="*80)
        else:
            # Send email
            print(f"Sending email to {Config.TARGET_EMAIL}...")
            subject = f"Weekly Dinner Plan (Week of {plan.week_of.strftime('%Y-%m-%d')})"
            send_email(
                Config,
                Config.TARGET_EMAIL,
                subject,
                html_content,
                text_content
            )
            print("✓ Email sent successfully!")
        
        print("\nWeekly meal planning complete!")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate weekly dinner plan and send via email")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate plan but don't send email (print to console instead)"
    )
    parser.add_argument(
        "--week-of",
        type=str,
        help="Date for the week (YYYY-MM-DD format). Defaults to today."
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Alias for --dry-run"
    )
    
    args = parser.parse_args()
    
    week_of_date = None
    if args.week_of:
        try:
            week_of_date = date.fromisoformat(args.week_of)
        except ValueError:
            print(f"Error: Invalid date format '{args.week_of}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    
    main(dry_run=(args.dry_run or args.no_email), week_of=week_of_date)
