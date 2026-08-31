import pandas as pd
from pathlib import Path
from rapidfuzz.fuzz import token_set_ratio


# ============================================================
# 1. FILE PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIRECTORY = PROJECT_ROOT / "data" / "input"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "output"

BANK_FILE = INPUT_DIRECTORY / "bank_statements.csv"
LEDGER_FILE = INPUT_DIRECTORY / "company_ledger.csv"
OUTPUT_FILE = OUTPUT_DIRECTORY / "reconciliation_results.csv"


# ============================================================
# 2. LOAD DATA
# ============================================================

OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
bank = pd.read_csv(BANK_FILE)
ledger = pd.read_csv(LEDGER_FILE)

print(f"Bank transactions: {len(bank)}")
print(f"Ledger transactions: {len(ledger)}")


# ============================================================
# 3. STANDARDIZE BANK DATA
# ============================================================

bank = bank.rename(columns={
    "type": "transaction_type",
    "mode": "payment_mode",
    "transactionTimestamp": "transaction_timestamp",
    "valueDate": "value_date",
    "txnId": "transaction_id",
    "currentBalance": "current_balance"
})

bank["value_date"] = pd.to_datetime(
    bank["value_date"],
    errors="coerce"
)

bank["amount"] = pd.to_numeric(
    bank["amount"],
    errors="coerce"
)

bank["reference"] = (
    bank["reference"]
    .fillna("")
    .astype(str)
)

bank["narration"] = (
    bank["narration"]
    .fillna("")
    .astype(str)
)

bank["transaction_type"] = (
    bank["transaction_type"]
    .fillna("")
    .astype(str)
    .str.upper()
)


# ============================================================
# 4. STANDARDIZE LEDGER DATA
# ============================================================

ledger["ledger_date"] = pd.to_datetime(
    ledger["ledger_date"],
    errors="coerce"
)

ledger["amount"] = pd.to_numeric(
    ledger["amount"],
    errors="coerce"
)

ledger["bank_reference"] = (
    ledger["bank_reference"]
    .fillna("")
    .astype(str)
)

ledger["description"] = (
    ledger["description"]
    .fillna("")
    .astype(str)
)

ledger["transaction_type"] = (
    ledger["transaction_type"]
    .fillna("")
    .astype(str)
    .str.upper()
)


# ============================================================
# 5. NORMALIZE DESCRIPTIONS
# ============================================================

def normalize_text(text):

    text = str(text).upper()

    for char in [
        "/", "-", "_", ".", ",",
        ":", ";", "(", ")"
    ]:
        text = text.replace(char, " ")

    return " ".join(text.split())


bank["normalized_description"] = (
    bank["narration"]
    .apply(normalize_text)
)

ledger["normalized_description"] = (
    ledger["description"]
    .apply(normalize_text)
)


# ============================================================
# 6. PREPARE MATCHING KEYS
# ============================================================

bank["amount_key"] = bank["amount"].round(2)
ledger["amount_key"] = ledger["amount"].round(2)


# ============================================================
# 7. DUPLICATE CANDIDATE DETECTION
# ============================================================

bank["duplicate_key"] = (
    bank["transaction_type"].astype(str)
    + "|"
    + bank["amount_key"].astype(str)
    + "|"
    + bank["value_date"].dt.strftime("%Y-%m-%d").fillna("")
    + "|"
    + bank["normalized_description"]
)

ledger["duplicate_key"] = (
    ledger["transaction_type"].astype(str)
    + "|"
    + ledger["amount_key"].astype(str)
    + "|"
    + ledger["ledger_date"].dt.strftime("%Y-%m-%d").fillna("")
    + "|"
    + ledger["normalized_description"]
)

bank_duplicate_keys = set(
    bank.loc[
        bank["duplicate_key"].duplicated(keep=False),
        "duplicate_key"
    ]
)

ledger_duplicate_keys = set(
    ledger.loc[
        ledger["duplicate_key"].duplicated(keep=False),
        "duplicate_key"
    ]
)


# ============================================================
# 8. MATCHING SETUP
# ============================================================

used_ledger = set()
results = []


# ============================================================
# 9. PROCESS BANK TRANSACTIONS
# ============================================================

for bank_index, bank_row in bank.iterrows():

    best_match = None
    match_status = None
    match_reason = None
    confidence = 0

    bank_date = bank_row["value_date"]
    bank_amount = bank_row["amount_key"]
    bank_type = bank_row["transaction_type"]


    # ========================================================
    # LEVEL 1
    # EXACT REFERENCE + AMOUNT + DATE + TYPE
    # ========================================================

    if bank_row["reference"].strip():

        candidates = ledger[
            (~ledger.index.isin(used_ledger))
            &
            (ledger["bank_reference"] == bank_row["reference"])
            &
            (ledger["amount_key"] == bank_amount)
            &
            (ledger["ledger_date"].dt.date == bank_date.date())
            &
            (ledger["transaction_type"] == bank_type)
        ]

        if len(candidates) == 1:

            best_match = candidates.iloc[0]

            match_status = "Matched"

            match_reason = (
                "Exact reference + amount + date + type"
            )

            confidence = 100


    # ========================================================
    # LEVEL 2
    # EXACT AMOUNT + DATE + TYPE
    # ========================================================

    if best_match is None:

        candidates = ledger[
            (~ledger.index.isin(used_ledger))
            &
            (ledger["amount_key"] == bank_amount)
            &
            (ledger["ledger_date"].dt.date == bank_date.date())
            &
            (ledger["transaction_type"] == bank_type)
        ]

        if len(candidates) == 1:

            best_match = candidates.iloc[0]

            match_status = "Matched"

            match_reason = (
                "Exact amount + date + transaction type"
            )

            confidence = 95


    # ========================================================
    # LEVEL 3
    # AMOUNT + TYPE + DATE WINDOW + DESCRIPTION
    # ========================================================

    if best_match is None:

        date_difference = (
            ledger["ledger_date"] - bank_date
        ).abs().dt.days

        candidates = ledger[
            (~ledger.index.isin(used_ledger))
            &
            (ledger["amount_key"] == bank_amount)
            &
            (ledger["transaction_type"] == bank_type)
            &
            (date_difference <= 3)
        ].copy()

        if len(candidates) > 0:

            candidates["similarity"] = candidates[
                "normalized_description"
            ].apply(
                lambda x: token_set_ratio(
                    bank_row["normalized_description"],
                    x
                )
            )

            candidates = candidates.sort_values(
                "similarity",
                ascending=False
            )

            top = candidates.iloc[0]

            similarity = top["similarity"]

            date_diff = abs(
                (top["ledger_date"] - bank_date).days
            )

            if similarity >= 80:

                best_match = top

                if date_diff == 0:

                    match_status = "Potential Match"

                    match_reason = (
                        f"Amount + type match with "
                        f"description similarity "
                        f"{similarity:.0f}%"
                    )

                    confidence = 85

                else:

                    match_status = "Timing Difference"

                    match_reason = (
                        f"Amount + type match, "
                        f"date difference {date_diff} day(s), "
                        f"description similarity "
                        f"{similarity:.0f}%"
                    )

                    confidence = max(
                        70,
                        85 - (date_diff * 5)
                    )


    # ========================================================
    # LEVEL 4
    # HIGH DESCRIPTION SIMILARITY
    # ========================================================

    if best_match is None:

        candidates = ledger[
            (~ledger.index.isin(used_ledger))
            &
            (ledger["transaction_type"] == bank_type)
        ].copy()

        if len(candidates) > 0:

            candidates["similarity"] = candidates[
                "normalized_description"
            ].apply(
                lambda x: token_set_ratio(
                    bank_row["normalized_description"],
                    x
                )
            )

            candidates = candidates[
                candidates["similarity"] >= 85
            ]

            if len(candidates) > 0:

                candidates["amount_difference"] = (
                    candidates["amount"]
                    - bank_row["amount"]
                ).abs()

                candidates["date_difference"] = (
                    candidates["ledger_date"]
                    - bank_date
                ).abs().dt.days

                top = candidates.sort_values(
                    ["similarity", "amount_difference"],
                    ascending=[False, True]
                ).iloc[0]

                similarity = top["similarity"]
                amount_difference = abs(
                    top["amount"] - bank_row["amount"]
                )
                date_difference = abs(
                    (top["ledger_date"] - bank_date).days
                )


                # ------------------------------------------------
                # IMPORTANT V4 FIX:
                # Same amount but large date difference
                # is NOT an amount mismatch.
                # ------------------------------------------------

                if amount_difference == 0:

                    best_match = top

                    if date_difference <= 7:

                        match_status = "Timing Difference"

                        match_reason = (
                            f"Same amount + high description "
                            f"similarity {similarity:.0f}% + "
                            f"date difference {date_difference} day(s)"
                        )

                        confidence = max(
                            65,
                            85 - (date_difference * 5)
                        )

                    else:

                        match_status = "Potential Match"

                        match_reason = (
                            f"Same amount + high description "
                            f"similarity {similarity:.0f}% but "
                            f"date differs by {date_difference} days"
                        )

                        confidence = 60


                # ------------------------------------------------
                # Genuine amount mismatch
                # ------------------------------------------------

                else:

                    best_match = top

                    match_status = "Amount Mismatch"

                    match_reason = (
                        f"Description similarity "
                        f"{similarity:.0f}% but amount differs "
                        f"by ₹{amount_difference:.2f}"
                    )

                    confidence = min(
                        80,
                        similarity
                    )


    # ========================================================
    # 10. SAVE MATCH
    # ========================================================

    if best_match is not None:

        used_ledger.add(best_match.name)

        amount_difference = (
            best_match["amount"]
            - bank_row["amount"]
        )

        date_difference = (
            best_match["ledger_date"]
            - bank_row["value_date"]
        ).days

        duplicate_flag = (
            bank_row["duplicate_key"]
            in bank_duplicate_keys
            or
            best_match["duplicate_key"]
            in ledger_duplicate_keys
        )

        # Do not claim a duplicate with certainty.
        if duplicate_flag:

            duplicate_note = (
                "Duplicate candidate detected"
            )

        else:

            duplicate_note = "No duplicate candidate"


        # Confidence tier
        if confidence >= 90:
            confidence_tier = "High"

        elif confidence >= 70:
            confidence_tier = "Medium"

        else:
            confidence_tier = "Low"


        results.append({

            "bank_transaction_id":
                bank_row["transaction_id"],

            "ledger_id":
                best_match["ledger_id"],

            "bank_date":
                bank_row["value_date"],

            "ledger_date":
                best_match["ledger_date"],

            "bank_amount":
                bank_row["amount"],

            "ledger_amount":
                best_match["amount"],

            "amount_difference":
                round(amount_difference, 2),

            "date_difference_days":
                date_difference,

            "bank_description":
                bank_row["narration"],

            "ledger_description":
                best_match["description"],

            "match_status":
                match_status,

            "match_reason":
                match_reason,

            "confidence_score":
                confidence,

            "confidence_tier":
                confidence_tier,

            "duplicate_flag":
                "Yes" if duplicate_flag else "No",

            "duplicate_note":
                duplicate_note
        })


    # ========================================================
    # 11. NO MATCH FOUND
    # ========================================================

    else:

        duplicate_flag = (
            bank_row["duplicate_key"]
            in bank_duplicate_keys
        )

        if duplicate_flag:

            status = "Duplicate Candidate"

            reason = (
                "Bank transaction appears more than once "
                "and could not be uniquely reconciled"
            )

        else:

            status = "Unmatched Bank Transaction"

            reason = (
                "No suitable ledger transaction found"
            )


        results.append({

            "bank_transaction_id":
                bank_row["transaction_id"],

            "ledger_id":
                None,

            "bank_date":
                bank_row["value_date"],

            "ledger_date":
                None,

            "bank_amount":
                bank_row["amount"],

            "ledger_amount":
                None,

            "amount_difference":
                None,

            "date_difference_days":
                None,

            "bank_description":
                bank_row["narration"],

            "ledger_description":
                None,

            "match_status":
                status,

            "match_reason":
                reason,

            "confidence_score":
                0,

            "confidence_tier":
                "Low",

            "duplicate_flag":
                "Yes" if duplicate_flag else "No",

            "duplicate_note":
                "Duplicate candidate detected"
                if duplicate_flag
                else "No duplicate candidate"
        })


# ============================================================
# 12. UNMATCHED LEDGER TRANSACTIONS
# ============================================================

for ledger_index, ledger_row in ledger.iterrows():

    if ledger_index not in used_ledger:

        duplicate_flag = (
            ledger_row["duplicate_key"]
            in ledger_duplicate_keys
        )

        if duplicate_flag:

            status = "Duplicate Candidate"

            reason = (
                "Ledger transaction appears more than once "
                "and was not uniquely reconciled"
            )

        else:

            status = "Unmatched Ledger Transaction"

            reason = (
                "No suitable bank transaction found"
            )


        results.append({

            "bank_transaction_id":
                None,

            "ledger_id":
                ledger_row["ledger_id"],

            "bank_date":
                None,

            "ledger_date":
                ledger_row["ledger_date"],

            "bank_amount":
                None,

            "ledger_amount":
                ledger_row["amount"],

            "amount_difference":
                None,

            "date_difference_days":
                None,

            "bank_description":
                None,

            "ledger_description":
                ledger_row["description"],

            "match_status":
                status,

            "match_reason":
                reason,

            "confidence_score":
                0,

            "confidence_tier":
                "Low",

            "duplicate_flag":
                "Yes" if duplicate_flag else "No",

            "duplicate_note":
                "Duplicate candidate detected"
                if duplicate_flag
                else "No duplicate candidate"
        })


# ============================================================
# 13. CREATE RESULT DATAFRAME
# ============================================================

reconciliation = pd.DataFrame(results)


# ============================================================
# 14. CONTROL CHECKS
# ============================================================

bank_covered = reconciliation[
    reconciliation["bank_transaction_id"].notna()
]["bank_transaction_id"].nunique()

ledger_covered = reconciliation[
    reconciliation["ledger_id"].notna()
]["ledger_id"].nunique()

print("\n========================================")
print("CONTROL CHECKS")
print("========================================")

print(
    f"Bank source records:        {len(bank)}"
)

print(
    f"Bank records in output:     {bank_covered}"
)

print(
    f"Ledger source records:      {len(ledger)}"
)

print(
    f"Ledger records in output:   {ledger_covered}"
)

print(
    f"Bank coverage check:        "
    f"{'PASS' if bank_covered == len(bank) else 'FAIL'}"
)

print(
    f"Ledger coverage check:      "
    f"{'PASS' if ledger_covered == len(ledger) else 'FAIL'}"
)


# ============================================================
# 15. SAVE OUTPUT
# ============================================================

reconciliation.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 16. SUMMARY
# ============================================================

print("\n========================================")
print("RECONCILIATION SUMMARY - VERSION 4")
print("========================================")

summary = (
    reconciliation["match_status"]
    .value_counts()
)

print(summary)


# ============================================================
# 17. RECONCILIATION METRICS
# ============================================================

matched_count = (
    reconciliation["match_status"]
    == "Matched"
).sum()

total_bank = len(bank)

strict_rate = (
    matched_count / total_bank
) * 100


resolved_statuses = [
    "Matched",
    "Potential Match",
    "Timing Difference",
    "Amount Mismatch"
]

resolved_count = (
    reconciliation["match_status"]
    .isin(resolved_statuses)
    .sum()
)

resolved_rate = (
    resolved_count / total_bank
) * 100


print("\n========================================")
print("RECONCILIATION METRICS")
print("========================================")

print(
    f"Strict reconciliation rate: "
    f"{strict_rate:.2f}%"
)

print(
    f"Resolved / classified rate: "
    f"{resolved_rate:.2f}%"
)

print(
    f"Total output records: "
    f"{len(reconciliation)}"
)


# ============================================================
# 18. CONFIDENCE DISTRIBUTION
# ============================================================

print("\n========================================")
print("CONFIDENCE TIERS")
print("========================================")

print(
    reconciliation["confidence_tier"]
    .value_counts()
)


# ============================================================
# 19. OUTPUT LOCATION
# ============================================================

print("\n========================================")
print("OUTPUT")
print("========================================")

print(
    Path(OUTPUT_FILE).resolve()
)
