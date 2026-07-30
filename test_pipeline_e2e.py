import asyncio
import json
from schemas import CodeReviewRequest, CodeSubmission
from main import review_code


async def test_all():
    print("1. Testing Single Submission...")
    req_single = CodeReviewRequest(
        language="Java",
        submissions=[
            CodeSubmission(
                question_text="Write a program in Java to add two numbers.",
                code="public class Main { public static void main(String[] args) { int a = 5, b = 10; System.out.println(a + b); } }"
            )
        ]
    )
    res_single = await review_code(req_single)
    data_single = res_single.model_dump()
    print("Single Review Overall Score:", data_single["individual_reviews"][0]["scores"]["overall_score"])
    print("Single Review summary_review is None:", data_single["summary_review"] is None)

    print("\n2. Testing Multiple Submissions...")
    req_multi = CodeReviewRequest(
        language="Java",
        submissions=[
            CodeSubmission(
                question_text="Add two numbers",
                code="class Add { public static void main(String[] a){ System.out.println(1+2); } }"
            ),
            CodeSubmission(
                question_text="Print Hello World",
                code="class Hello { public static void main(String[] a){ System.out.println(\"Hello World\"); } }"
            )
        ]
    )
    res_multi = await review_code(req_multi)
    data_multi = res_multi.model_dump()
    print("Multiple Reviews Count:", len(data_multi["individual_reviews"]))
    print("Summary Review Label:", data_multi["summary_review"]["overall_quality_label"])
    print("Summary Review Average Score:", data_multi["summary_review"]["overall_average_score"])


if __name__ == "__main__":
    asyncio.run(test_all())
