from services.audit_service import (
    run_tracking_audit
)


result = run_tracking_audit(
    website_url="https://jandhyalafoods.in/"
    industry_type="b2c"
)


print("\nFINAL AUDIT REPORT\n")

print("=" * 50)

print(
    f"\nWebsite: {result['website_url']}"
)

print(
    f"\nIndustry: {result['industry_type']}"
)

# =========================
# TAGS
# =========================
print("\nDetected Tags:\n")

for tag in result["detected_tags"]:

    print(f"✔ {tag}")

# =========================
# EVENTS
# =========================
print("\nDetected Events:\n")

for event in result["detected_events"]:

    print(f"✔ {event}")

# =========================
# DUPLICATES
# =========================
print("\nDuplicate Tracking:\n")

if result["duplicate_events"]:

    for dup in (
        result["duplicate_events"]
    ):

        print(
            f"⚠ {dup['platform']} fired {dup['count']} times"
        )

else:

    print("No duplicates detected")

# =========================
# MISSING EVENTS
# =========================
print("\nMissing Events:\n")

missing_events = (
    result["industry_validation"]
    ["missing_events"]
)

if missing_events:

    for event in missing_events:

        print(f"❌ {event}")

else:

    print("No missing events")

print("\nAudit Finished")