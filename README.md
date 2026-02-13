# Weekly Dinner Planning AI Agent

An AI-powered agent that generates weekly dinner meal plans (Monday through Thursday) tailored to your family's needs, complete with recipes, cooking instructions, and a consolidated grocery list.

## Features

- **Smart Meal Planning**: Monday & Tuesday meals are optimized for adult palates with high protein and low carbs. Wednesday & Thursday meals are kid-friendly with more relaxed macro composition.
- **Complete Recipes**: Each meal includes detailed ingredients and step-by-step cooking instructions.
- **Grocery List**: Automatically aggregates all ingredients across the week into a single, organized shopping list.
- **Email Delivery**: Sends the complete meal plan directly to your email inbox every Monday.

## Setup

### Prerequisites

- Python 3.8 or higher
- Anthropic API key (Claude)
- Gmail account with app password enabled

### Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root. Copy the example below and fill in your values:
   ```env
   # Gmail Configuration
   GMAIL_USERNAME=your.email@gmail.com
   GMAIL_APP_PASSWORD=your_16_character_app_password_here
   TARGET_EMAIL=your.email@gmail.com

   # Claude / Anthropic Configuration
   ANTHROPIC_API_KEY=sk-ant-your-api-key-here
   MODEL_NAME=claude-3-5-haiku-latest

   # Servings Configuration
   ADULT_SERVINGS=2
   CHILD_SERVINGS=2
   LEFTOVERS_FACTOR=1.3

   # Optional LLM Configuration
   LLM_TEMPERATURE=0.7
   LLM_MAX_TOKENS=4000

   # Optional Behavior Configuration
   RUN_DAY=MONDAY
   TIMEZONE=America/New_York
   INCLUDE_HTML_EMAIL=true
   ```

   **Getting an Anthropic API Key**:
   - Go to [Anthropic Console](https://console.anthropic.com/)
   - Sign in or create an account
   - Navigate to **API Keys** and create a key
   - Copy the key and use it as `ANTHROPIC_API_KEY` (it starts with `sk-ant-`)

### Gmail App Password Setup

**Important**: You cannot use your regular Gmail password. You must create an app-specific password.

1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (must be enabled first)
3. Scroll down to **App passwords** section
4. Click **App passwords** (you may need to sign in again)
5. Select **Mail** as the app and **Other (Custom name)** as the device
6. Enter a name like "Meal Planning Agent"
7. Click **Generate**
8. Copy the generated 16-character password (it will look like: `abcd efgh ijkl mnop`)
9. Use this password (without spaces) as your `GMAIL_APP_PASSWORD` in the `.env` file

**Note**: If you don't see "App passwords" option, make sure 2-Step Verification is enabled first.

## Usage

### Manual Run

Run the agent manually:
```bash
python run_on_monday.py
```

### Dry Run (Testing)

Test without sending an email (useful for debugging):
```bash
python run_on_monday.py --dry-run
```

This will generate the meal plan and print it to the console without sending an email. You can also use `--no-email` as an alias.

### Test with Specific Week

Generate a plan for a specific week:
```bash
python run_on_monday.py --week-of 2024-01-15 --dry-run
```

### Scheduled Execution (Windows Task Scheduler)

To automatically run the agent every Monday:

1. Open **Task Scheduler** (search for it in Windows Start menu)
2. Click **Create Basic Task** (or **Create Task** for more options)
3. **General Tab**:
   - Name: "Weekly Meal Planning Agent"
   - Description: "Generates and emails weekly dinner plan"
   - Select **"Run whether user is logged on or not"**
   - Check **"Run with highest privileges"** (if needed)
4. **Triggers Tab**:
   - Click **New**
   - Begin the task: **On a schedule**
   - Settings: **Weekly**
   - Day: **Monday**
   - Time: Choose your preferred time (e.g., 8:00 AM)
   - Recur every: **1 weeks**
   - Click **OK**
5. **Actions Tab**:
   - Click **New**
   - Action: **Start a program**
   - Program/script: `python` (or full path like `C:\Python39\python.exe`)
   - Add arguments: `run_on_monday.py`
   - Start in: `G:\MealAgent` (your project folder path)
   - Click **OK**
6. **Conditions Tab** (optional):
   - Uncheck **"Start the task only if the computer is on AC power"** if you want it to run on battery
7. **Settings Tab** (optional):
   - Check **"Allow task to be run on demand"**
   - Check **"Run task as soon as possible after a scheduled start is missed"**
   - Set **"If the task fails, restart every"** to 10 minutes with up to 3 attempts
8. Click **OK** and enter your Windows password if prompted

**Testing the Scheduled Task**:
- Right-click the task in Task Scheduler and select **Run** to test it immediately
- Check the **History** tab to see if it ran successfully

## Configuration

All configuration is managed through environment variables in your `.env` file. See `config.py` for the complete list of options.

### Key Configuration Options

- **GMAIL_USERNAME**: Your Gmail address (sender)
- **GMAIL_APP_PASSWORD**: Gmail app password (16 characters, see setup instructions above)
- **TARGET_EMAIL**: Email address to receive the meal plan
- **ANTHROPIC_API_KEY**: Your Anthropic (Claude) API key
- **MODEL_NAME**: Claude model to use (default: `claude-3-5-haiku-latest` for cost efficiency, or `claude-3-5-sonnet-latest` for higher quality)
- **ADULT_SERVINGS**: Number of servings for Monday/Tuesday meals (default: 2)
- **CHILD_SERVINGS**: Number of servings for Wednesday/Thursday meals (default: 2)
- **LEFTOVERS_FACTOR**: Multiplier for leftovers (1.3 = 30% extra, default: 1.3)
- **LLM_TEMPERATURE**: Creativity level (0.0-2.0, default: 0.7)

## Project Structure

- `run_on_monday.py` - Main entry point script
- `config.py` - Configuration management and environment variable loading
- `models.py` - Pydantic data models for meals, recipes, and ingredients
- `meal_planner.py` - LLM-based meal planning with JSON schema validation
- `grocery_list.py` - Ingredient aggregation and grocery list generation
- `email_builder.py` - HTML and plain text email content formatting
- `gmail_smtp.py` - Gmail SMTP email sending with retry logic
- `test_grocery_list.py` - Unit tests for grocery list functionality

## Testing

Run the grocery list unit tests:
```bash
python test_grocery_list.py
```

## Troubleshooting

### Email Not Sending
- Verify your Gmail app password is correct (16 characters, no spaces)
- Ensure 2-Step Verification is enabled on your Google account
- Check that `GMAIL_USERNAME` and `GMAIL_APP_PASSWORD` are set correctly in `.env`
- Try running with `--dry-run` first to verify the plan generates correctly

### LLM Errors
- Verify your `ANTHROPIC_API_KEY` is valid and has credits
- Check your internet connection
- Try a different model name (e.g., `claude-3-5-haiku-latest`, `claude-3-5-sonnet-latest`, or `claude-haiku-4-5`)
- Increase `LLM_MAX_TOKENS` if recipes are being cut off

### Plan Validation Errors
- The agent validates that Monday/Tuesday are adult-focused and Wednesday/Thursday are kid-focused
- If validation fails, the agent will retry up to 3 times
- Check the console output for specific validation error messages

## How It Works

1. **Meal Planning**: Uses Anthropic's Claude API to generate a weekly meal plan with 4 recipes (Mon-Thu)
2. **Macro Optimization**: Monday/Tuesday focus on high protein, low carbs for adults
3. **Kid-Friendly Meals**: Wednesday/Thursday focus on familiar, kid-friendly flavors
4. **Grocery Aggregation**: Combines ingredients across all meals, normalizing units and quantities
5. **Email Formatting**: Creates both HTML and plain text versions of the meal plan
6. **Email Delivery**: Sends via Gmail SMTP with automatic retries on failure

## License

MIT
