from pathlib import Path
from datetime import datetime
import json
import csv
import traceback

from backend.analysis.unified_image_analysis import (
    analyze_image_unified
)


# ============================================================
# CONFIGURATION
# ============================================================

TEST_ROOT = Path(
    "data/forensic_tests"
)

RESULTS_DIR = Path(
    "data/forensic_test_results"
)


SUPPORTED_EXTENSIONS = {

    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff"

}


# ============================================================
# EXPECTED LABELS
# ============================================================

EXPECTED_LABELS = {

    "authentic":
        "AUTHENTIC",

    "manipulated":
        "HIGH_RISK",

    "copy_move":
        "HIGH_RISK",

    "ai_generated":
        "HIGH_RISK"

}


# ============================================================
# FIND TEST IMAGES
# ============================================================

def find_test_images():

    images = []

    if not TEST_ROOT.exists():

        print(

            f"[ERROR] Test directory not found: "
            f"{TEST_ROOT}"

        )

        return images

    for category_dir in TEST_ROOT.iterdir():

        if not category_dir.is_dir():

            continue

        category = (

            category_dir.name.lower()

        )

        if category not in EXPECTED_LABELS:

            print(

                f"[WARNING] Unknown category: "
                f"{category}"

            )

            continue

        for image_path in category_dir.rglob("*"):

            if (

                image_path.is_file()

                and

                image_path.suffix.lower()

                in SUPPORTED_EXTENSIONS

            ):

                images.append({

                    "path":

                        image_path,

                    "category":

                        category,

                    "expected":

                        EXPECTED_LABELS[category]

                })

    return images


# ============================================================
# NORMALIZE VERDICT
# ============================================================

def normalize_verdict(
    verdict
):

    if not verdict:

        return "UNKNOWN"

    verdict = str(

        verdict

    ).upper()

    # --------------------------------------------------------
    # Authentic
    # --------------------------------------------------------

    if (

        "AUTHENTIC"

        in verdict

        and

        "RISK"

        not in verdict

    ):

        return "AUTHENTIC"

    # --------------------------------------------------------
    # High Risk
    # --------------------------------------------------------

    if (

        "HIGH RISK"

        in verdict

        or

        "STRONG EVIDENCE"

        in verdict

    ):

        return "HIGH_RISK"

    # --------------------------------------------------------
    # Medium / Low Risk
    # --------------------------------------------------------

    if (

        "MEDIUM"

        in verdict

        or

        "LOW RISK"

        in verdict

    ):

        return "SUSPICIOUS"

    return "UNKNOWN"


# ============================================================
# CHECK RESULT
# ============================================================

def evaluate_result(
    expected,
    actual
):

    # Exact expected match

    if expected == actual:

        return True

    # Manipulated categories can be
    # detected as any risk level.

    if (

        expected == "HIGH_RISK"

        and

        actual in {

            "HIGH_RISK",

            "SUSPICIOUS"

        }

    ):

        return True

    return False


# ============================================================
# RUN SINGLE TEST
# ============================================================

def analyze_single_image(
    test_case
):

    image_path = test_case["path"]

    category = test_case["category"]

    expected = test_case["expected"]

    print()

    print(

        "================================================"

    )

    print(

        f"[TEST] {image_path.name}"

    )

    print(

        f"[CATEGORY] {category}"

    )

    print(

        f"[EXPECTED] {expected}"

    )

    print(

        "================================================"

    )

    # --------------------------------------------------------
    # Create analysis directory
    # --------------------------------------------------------

    analysis_dir = (

        RESULTS_DIR

        /

        "analysis"

        /

        category

        /

        image_path.stem

    )

    analysis_dir.mkdir(

        parents=True,

        exist_ok=True

    )

    try:

        # ----------------------------------------------------
        # Run AI-FORGE
        # ----------------------------------------------------

        result = analyze_image_unified(

            str(image_path),

            str(analysis_dir)

        )

        # ----------------------------------------------------
        # Extract verdict
        # ----------------------------------------------------

        actual_verdict = normalize_verdict(

            result.get(

                "overall_verdict",

                result.get(

                    "verdict",

                    ""

                )

            )

        )

        # ----------------------------------------------------
        # Extract score
        # ----------------------------------------------------

        risk_score = result.get(

            "risk_score",

            result.get(

                "forensic_score",

                0

            )

        )

        # ----------------------------------------------------
        # Important:
        # forensic_score may be 0.0 - 1.0
        # risk_score may be 0 - 100
        # ----------------------------------------------------

        if (

            isinstance(

                risk_score,

                (int, float)

            )

            and

            risk_score <= 1

        ):

            risk_score = round(

                risk_score * 100,

                2

            )

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = result.get(

            "confidence",

            0

        )

        # ----------------------------------------------------
        # Evaluate
        # ----------------------------------------------------

        correct = evaluate_result(

            expected,

            actual_verdict

        )

        status = (

            "PASS"

            if correct

            else

            "FAIL"

        )

        print()

        print(

            f"[EXPECTED] {expected}"

        )

        print(

            f"[AI-FORGE] {actual_verdict}"

        )

        print(

            f"[RISK SCORE] {risk_score}"

        )

        print(

            f"[CONFIDENCE] {confidence}"

        )

        print(

            f"[RESULT] {status}"

        )

        print()

        return {

            "image":

                image_path.name,

            "image_path":

                str(image_path),

            "category":

                category,

            "expected":

                expected,

            "actual":

                actual_verdict,

            "risk_score":

                risk_score,

            "confidence":

                confidence,

            "status":

                status,

            "correct":

                correct,

            "findings":

                result.get(

                    "findings",

                    []

                )

        }

    except Exception as e:

        print()

        print(

            f"[ERROR] Failed to analyze "
            f"{image_path.name}"

        )

        print(

            str(e)

        )

        print()

        traceback.print_exc()

        return {

            "image":

                image_path.name,

            "image_path":

                str(image_path),

            "category":

                category,

            "expected":

                expected,

            "actual":

                "ERROR",

            "risk_score":

                0,

            "confidence":

                0,

            "status":

                "ERROR",

            "correct":

                False,

            "error":

                str(e)

        }


# ============================================================
# SAVE JSON REPORT
# ============================================================

def save_json_report(
    results,
    output_path
):

    with open(

        output_path,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            results,

            file,

            indent=4,

            default=str

        )


# ============================================================
# SAVE CSV REPORT
# ============================================================

def save_csv_report(
    results,
    output_path
):

    if not results:

        return

    fields = [

        "image",

        "image_path",

        "category",

        "expected",

        "actual",

        "risk_score",

        "confidence",

        "status",

        "correct"

    ]

    with open(

        output_path,

        "w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=fields

        )

        writer.writeheader()

        for result in results:

            row = {

                field:

                    result.get(

                        field,

                        ""

                    )

                for field in fields

            }

            writer.writerow(row)


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    results
):

    if not results:

        print(

            "[ERROR] No test results."

        )

        return

    total = len(results)

    passed = sum(

        1

        for r in results

        if r["status"] == "PASS"

    )

    failed = sum(

        1

        for r in results

        if r["status"] == "FAIL"

    )

    errors = sum(

        1

        for r in results

        if r["status"] == "ERROR"

    )

    accuracy = (

        passed

        /

        total

        *

        100

    )

    print()

    print()

    print(

        "================================================"

    )

    print(

        "          AI-FORGE FORENSIC BENCHMARK"

    )

    print(

        "================================================"

    )

    print(

        f"Total Tests     : {total}"

    )

    print(

        f"Passed          : {passed}"

    )

    print(

        f"Failed          : {failed}"

    )

    print(

        f"Errors          : {errors}"

    )

    print(

        f"Accuracy        : {accuracy:.2f}%"

    )

    print(

        "================================================"

    )


    # --------------------------------------------------------
    # Category-wise results
    # --------------------------------------------------------

    categories = {}

    for result in results:

        category = result["category"]

        if category not in categories:

            categories[category] = {

                "total": 0,

                "passed": 0

            }

        categories[category]["total"] += 1

        if result["status"] == "PASS":

            categories[category]["passed"] += 1

    print()

    print(

        "CATEGORY PERFORMANCE"

    )

    print(

        "------------------------------------------------"

    )

    for category, stats in categories.items():

        category_accuracy = (

            stats["passed"]

            /

            stats["total"]

            *

            100

        )

        print(

            f"{category:<15}"

            f"{stats['passed']}/"

            f"{stats['total']}"

            f"  "

            f"({category_accuracy:.2f}%)"

        )

    print(

        "------------------------------------------------"

    )

    print()


# ============================================================
# MAIN BENCHMARK
# ============================================================

def run_benchmark():

    print()

    print(

        "================================================"

    )

    print(

        "        AI-FORGE FORENSIC TEST RUNNER"

    )

    print(

        "================================================"

    )

    print(

        f"Test Dataset: {TEST_ROOT}"

    )

    print()

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    test_images = find_test_images()

    if not test_images:

        print(

            "[ERROR] No test images found."

        )

        print()

        print(

            "Expected structure:"

        )

        print()

        print(

            "data/forensic_tests/"

        )

        print(

            "├── authentic/"

        )

        print(

            "├── manipulated/"

        )

        print(

            "├── copy_move/"

        )

        print(

            "└── ai_generated/"

        )

        return

    print(

        f"[INFO] Found {len(test_images)} test images."

    )

    print()

    # --------------------------------------------------------
    # Create result directory
    # --------------------------------------------------------

    RESULTS_DIR.mkdir(

        parents=True,

        exist_ok=True

    )

    results = []

    # --------------------------------------------------------
    # Run tests
    # --------------------------------------------------------

    for index, test_case in enumerate(

        test_images,

        start=1

    ):

        print(

            f"\nRunning test "

            f"{index}/{len(test_images)}"

        )

        result = analyze_single_image(

            test_case

        )

        results.append(

            result

        )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )

    json_path = (

        RESULTS_DIR

        /

        f"benchmark_{timestamp}.json"

    )

    csv_path = (

        RESULTS_DIR

        /

        f"benchmark_{timestamp}.csv"

    )

    # --------------------------------------------------------
    # Save reports
    # --------------------------------------------------------

    save_json_report(

        results,

        json_path

    )

    save_csv_report(

        results,

        csv_path

    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(

        results

    )

    print(

        f"JSON Report: {json_path}"

    )

    print(

        f"CSV Report : {csv_path}"

    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_benchmark()