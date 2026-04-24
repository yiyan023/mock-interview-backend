import argparse
import os
from datetime import date, datetime, time, timedelta

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

print(SUPABASE_URL, SUPABASE_KEY)

SLOT_DURATION_MINUTES = 60
RULES_TABLE = "availability-rules"
EXCEPTIONS_TABLE = "availability-exceptions"
TIMES_TABLE = "times-table"
DATES_TABLE = "dates-table"

UNAVAILABLE_EXCEPTION = "unavailable"
DAY_OF_WEEK = "day_of_week"
EFFECTIVE_FROM = "effective_from"
EFFECTIVE_UNTIL = "effective_until"
START_TIME = "start_time"
END_TIME = "end_time"


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def block_date(supabase: Client, date: date):
    supabase.rpc(
        "block_date",
        {"target_date": date.isoformat()},
    ).execute()

def fetch_rules(supabase: Client, start_date: date, end_date: date):
    response = (
        supabase.table(RULES_TABLE)
        .select("*")
        .lte("effective_from", end_date.isoformat())
        .execute()
    )

    rules = response.data or []

    return [
        r for r in rules
        if r["effective_until"] is None
        or date.fromisoformat(r["effective_until"]) >= start_date
    ]


def fetch_exceptions(supabase: Client, start_date: date, end_date: date) -> dict:
    response = (
        supabase.table(EXCEPTIONS_TABLE)
        .select("exception_date, exception_type")
        .gte("exception_date", start_date.isoformat())
        .lte("exception_date", end_date.isoformat())
        .execute()
    )
    return {row["exception_date"]: row["exception_type"] for row in (response.data or [])}


def generate_slots_for_date(target_date: date, rules: list) -> list:
    day_of_week = target_date.isoweekday() % 7
    
    slots = []

    for rule in rules:
        if (
            rule[DAY_OF_WEEK] != day_of_week or
            date.fromisoformat(rule[EFFECTIVE_FROM]) > target_date or
            rule[EFFECTIVE_UNTIL] and date.fromisoformat(rule[EFFECTIVE_UNTIL]) < target_date
        ):
            continue
        
        start = time.fromisoformat(rule[START_TIME])
        end = time.fromisoformat(rule[END_TIME])
        
        current = datetime.combine(target_date, start)
        end_dt = datetime.combine(target_date, end)
        
        while current + timedelta(minutes=SLOT_DURATION_MINUTES) <= end_dt + timedelta(seconds=1):
            slots.append(current.time())
            current += timedelta(minutes=SLOT_DURATION_MINUTES)
    
    return slots


def upsert_slots(supabase: Client, target_date: date, slot_times: list) -> int:
    if not slot_times:
        return 0
    
    result = supabase.rpc(
        "insert_timeslots",
        {
            "target_date": target_date.isoformat(),
            "slot_times": [t.isoformat() for t in slot_times],
        },
    ).execute()

    return result.data or 0


def update_dates_table(supabase: Client, target_date: date):
    date_iso = target_date.isoformat()
    
    response = (
        supabase.table(TIMES_TABLE)
        .select("id", count="exact")
        .eq("date", date_iso)
        .eq("is_booked", False)
        .execute()
    )
    available_count = response.count or 0
    block_date(supabase, target_date) if not available_count else update_date_count(supabase, target_date, available_count)


def update_date_count(supabase: Client, target_date: date, available_count: int):
    supabase.rpc(
        "upsert_date_count",
        {
            "target_date": target_date.isoformat(),
            "available_count": available_count,
        },
    ).execute()


def materialize(days_ahead: int = 60):
    supabase = get_client()

    print("Supabase client created successfully.")

    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    
    print(f"Materializing slots from {today} to {end_date}")
    
    rules = fetch_rules(supabase, today, end_date)
    print(f"Rules fetched successfully: {len(rules)} rules found.")
    
    exceptions = fetch_exceptions(supabase, today, end_date)
    print(f"Exceptions fetched successfully: {len(exceptions)} exceptions found.")
    
    total_inserted = 0
    current = today

    print("Starting to materialize slots...")

    while current <= end_date:
        date_iso = current.isoformat()
        
        if exceptions.get(date_iso) == UNAVAILABLE_EXCEPTION:
            block_date(supabase, current)
            current += timedelta(days=1)    
            continue
        
        slot_times = generate_slots_for_date(current, rules)
        inserted = upsert_slots(supabase, current, slot_times)
        total_inserted += inserted
        
        if slot_times:
            update_dates_table(supabase, current)
        
        current += timedelta(days=1)
    
    print(f"Done. Inserted {total_inserted} new slots.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60, help="How many days ahead to materialize")
    args = parser.parse_args()
    materialize(days_ahead=args.days)