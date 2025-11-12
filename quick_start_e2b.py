#!/usr/bin/env python3
"""
Quick Start: Run PostHog Analysis in E2B Sandbox

This is the SIMPLEST way to get started.
Just set your API keys and run this script!
"""

from e2b import Sandbox
import os

# ============================================================================
# CONFIGURATION - Set your API keys here or via environment variables
# ============================================================================

E2B_API_KEY = os.getenv('E2B_API_KEY', 'YOUR_E2B_KEY_HERE')
POSTHOG_API_KEY = 'phx_YOUR_KEY_HERE'
POSTHOG_PROJECT_ID = '245832'

# ============================================================================
# ANALYSIS SCRIPT - This runs inside the E2B sandbox
# ============================================================================

ANALYSIS_SCRIPT = f"""
import sys
import json

# Add driver to Python path
sys.path.insert(0, '/home/user')

# Import PostHog driver
from posthog_driver import PostHogClient

print("=" * 70)
print("  PostHog Analysis Running in E2B Sandbox")
print("=" * 70)

# Initialize client
print("\\n🔧 Connecting to PostHog...")
client = PostHogClient(
    api_key='{POSTHOG_API_KEY}',
    project_id='{POSTHOG_PROJECT_ID}'
)

# Test connection
if client.health_check():
    project_info = client.get_project_info()
    print(f"✓ Connected to: {{project_info.get('name', 'Unknown project')}}")
else:
    print("⚠️  Connection issue, but continuing...")

# Query 1: Top events in last 7 days
print("\\n" + "=" * 70)
print("QUERY 1: Top Events (Last 7 Days)")
print("=" * 70)

query1 = '''
SELECT
    event,
    count() as total_events,
    count(DISTINCT distinct_id) as unique_users
FROM events
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY event
ORDER BY total_events DESC
LIMIT 10
'''

try:
    results = client.query(query1)

    print("\\n{{:<40}} {{:>15}} {{:>15}}".format("Event", "Total Events", "Unique Users"))
    print("-" * 70)

    for i, event in enumerate(results[:10], 1):
        # Handle both dict and list results
        if isinstance(event, dict):
            event_name = event.get('event', 'Unknown')
            total = event.get('total_events', 0)
            users = event.get('unique_users', 0)
        else:
            event_name = str(event[0]) if len(event) > 0 else 'Unknown'
            total = int(event[1]) if len(event) > 1 else 0
            users = int(event[2]) if len(event) > 2 else 0

        print(f"{{i:2}}. {{event_name:<37}} {{total:>12,}} {{users:>15,}}")

    print(f"\\n✓ Found {{len(results)}} events")

except Exception as e:
    print(f"\\n❌ Error: {{e}}")

# Query 2: User activity distribution
print("\\n" + "=" * 70)
print("QUERY 2: User Activity Distribution")
print("=" * 70)

query2 = '''
SELECT
    CASE
        WHEN event_count < 5 THEN 'Low activity (1-4 events)'
        WHEN event_count < 20 THEN 'Medium activity (5-19 events)'
        ELSE 'High activity (20+ events)'
    END as activity_level,
    count() as user_count
FROM (
    SELECT distinct_id, count() as event_count
    FROM events
    WHERE timestamp >= now() - INTERVAL 30 DAY
    GROUP BY distinct_id
)
GROUP BY activity_level
ORDER BY user_count DESC
'''

try:
    results = client.query(query2)

    print("\\n{{:<35}} {{:>20}}".format("Activity Level", "Number of Users"))
    print("-" * 70)

    total_users = 0
    for result in results:
        if isinstance(result, dict):
            level = result.get('activity_level', 'Unknown')
            count = result.get('user_count', 0)
        else:
            level = str(result[0]) if len(result) > 0 else 'Unknown'
            count = int(result[1]) if len(result) > 1 else 0

        print(f"{{level:<35}} {{count:>20,}}")
        total_users += count

    print("-" * 70)
    print(f"{{'':<35}} {{total_users:>20,}}")

    print(f"\\n✓ Analyzed {{total_users:,}} users")

except Exception as e:
    print(f"\\n❌ Error: {{e}}")

# Query 3: Conversion funnel
print("\\n" + "=" * 70)
print("QUERY 3: Purchase Conversion Funnel")
print("=" * 70)

funnel_steps = [
    ('Viewed pages', "$pageview"),
    ('Logged in', "user_logged_in"),
    ('Purchased subscription', "subscription_purchased"),
]

print("\\n{{:<30}} {{:>20}} {{:>20}}".format("Step", "Users", "Conversion Rate"))
print("-" * 70)

prev_count = None
for step_name, event_name in funnel_steps:
    query = f'''
    SELECT count(DISTINCT distinct_id) as users
    FROM events
    WHERE event = '{{event_name}}'
        AND timestamp >= now() - INTERVAL 30 DAY
    '''

    try:
        result = client.query(query)
        if result:
            if isinstance(result[0], dict):
                count = result[0].get('users', 0)
            else:
                count = int(result[0][0]) if len(result[0]) > 0 else 0

            if prev_count is not None:
                rate = (count / prev_count * 100) if prev_count > 0 else 0
                print(f"{{step_name:<30}} {{count:>20,}} {{rate:>19.1f}}%")
            else:
                print(f"{{step_name:<30}} {{count:>20,}} {{'-':>20}}")

            prev_count = count
    except Exception as e:
        print(f"{{step_name:<30}} {{'-':>20}} {{'-':>20}}")

print("\\n" + "=" * 70)
print("✅ Analysis Complete!")
print("=" * 70)
print("\\nThis analysis ran securely in an E2B cloud sandbox.")
print("The sandbox has been automatically cleaned up.\\n")
"""

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run PostHog analysis in E2B sandbox."""

    print("\n" + "╔" + "=" * 76 + "╗")
    print("║" + " " * 20 + "PostHog in E2B - Quick Start" + " " * 28 + "║")
    print("╚" + "=" * 76 + "╝\n")

    # Validate credentials
    if E2B_API_KEY == 'YOUR_E2B_KEY_HERE':
        print("❌ Error: E2B API key not set!")
        print("\nPlease either:")
        print("  1. Set E2B_API_KEY environment variable:")
        print("     export E2B_API_KEY='your_key_here'")
        print("\n  2. Or edit this script and replace YOUR_E2B_KEY_HERE")
        print("\nGet your E2B API key at: https://e2b.dev")
        return

    print("🚀 Step 1: Creating E2B sandbox...")
    print("   (This creates an isolated Ubuntu VM in the cloud)")

    try:
        sandbox = Sandbox(api_key=E2B_API_KEY)
        print("   ✓ Sandbox created!")
    except Exception as e:
        print(f"\n❌ Failed to create sandbox: {e}")
        print("\nTroubleshooting:")
        print("  - Check your E2B API key is correct")
        print("  - Ensure you have E2B credits")
        print("  - Visit https://e2b.dev/dashboard")
        return

    try:
        # Upload PostHog driver files
        print("\n📦 Step 2: Uploading PostHog driver to sandbox...")

        driver_files = {
            '__init__.py': 'posthog_driver/__init__.py',
            'client.py': 'posthog_driver/client.py',
            'exceptions.py': 'posthog_driver/exceptions.py'
        }

        for remote_name, local_path in driver_files.items():
            try:
                with open(local_path, 'r') as f:
                    content = f.read()
                    sandbox.files.write(
                        f'/home/user/posthog_driver/{remote_name}',
                        content
                    )
            except FileNotFoundError:
                print(f"\n❌ Error: Cannot find {local_path}")
                print("   Make sure you're running this from the posthog-driver directory")
                return

        print("   ✓ Driver uploaded!")

        # Install dependencies
        print("\n📥 Step 3: Installing dependencies...")
        print("   (Installing requests and python-dotenv)")

        result = sandbox.commands.run('pip install requests python-dotenv')
        if result.exit_code == 0:
            print("   ✓ Dependencies installed!")
        else:
            print(f"   ⚠️  Install warning: {result.stderr[:100]}")
            print("   (Continuing anyway...)")

        # Run analysis
        print("\n🔍 Step 4: Running PostHog analysis...\n")
        print("─" * 78)

        result = sandbox.run_code(
            code=ANALYSIS_SCRIPT,
            envs={'PYTHONPATH': '/home/user'}
        )

        if result.error:
            print(f"\n❌ Execution error:\n{result.error}")
        else:
            print(result.logs.stdout)

        print("─" * 78)

    finally:
        print("\n🧹 Step 5: Cleaning up sandbox...")
        sandbox.kill()
        print("   ✓ Sandbox destroyed!\n")

    print("╔" + "=" * 76 + "╗")
    print("║" + " " * 30 + "All Done!" + " " * 36 + "║")
    print("╚" + "=" * 76 + "╝\n")

    print("💡 What just happened:")
    print("   1. Created isolated cloud VM (E2B sandbox)")
    print("   2. Uploaded PostHog driver code")
    print("   3. Installed Python dependencies")
    print("   4. Ran analytics queries securely")
    print("   5. Destroyed VM (no traces left)")
    print()
    print("📊 Your PostHog data was analyzed without touching your local machine!")
    print()
    print("Next steps:")
    print("   • Check E2B_GUIDE.md for advanced usage")
    print("   • Try integrating with Claude agents")
    print("   • Build custom analysis scripts")
    print()


if __name__ == '__main__':
    main()
