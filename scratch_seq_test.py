import asyncio
import json
import httpx

test_cases = [
    {
        "name": "Question 1: Ticket ID (Reversed append order)",
        "problem": "In an online ticket system, each booking id is formed by combining a city code and a numeric sequence (for example BLR + 1052 -> BLR1052). Write a program that reads the city code and the sequence number as separate inputs and combines them into one booking id without using the plus operator for string concatenation. Store the city code as a String and the sequence number as a String or convert it to String, then use String.concat or a StringBuilder append chain to produce the final booking id.",
        "code": """import java.util.*;

public class BookingID {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String city = sc.next();
        String seq = sc.next();
        StringBuilder sb = new StringBuilder();
        sb.append(seq);
        sb.append(city);

        System.out.println("Booking ID: " + sb.toString());
    }
}""",
        "language": "Java"
    },
    {
        "name": "Question 2: Fibonacci Question (Correct Code)",
        "problem": "Write a Java program to print the first N numbers of the Fibonacci sequence starting from 0 and 1, separated by spaces.",
        "code": """import java.util.Scanner;

public class Fibonacci {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int a = 0, b = 1;
        for (int i = 0; i < n; i++) {
            System.out.print(a + " ");
            int c = a + b;
            a = b;
            b = c;
        }
    }
}""",
        "language": "Java"
    },
    {
        "name": "Question 3: Prime Check (Syntax Typo - missing semicolon)",
        "problem": "Write a Java program to check if an integer input is prime. Print 'Prime' or 'Not Prime'.",
        "code": """import java.util.Scanner;

public class PrimeCheck {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in)
        int n = sc.nextInt();
        boolean isPrime = true;
        if (n <= 1) isPrime = false;
        for (int i = 2; i <= Math.sqrt(n); i++) {
            if (n % i == 0) { isPrime = false; break; }
        }
        if (isPrime) System.out.println("Prime");
        else System.out.println("Not Prime");
    }
}""",
        "language": "Java"
    }
]

async def test_sequential_fresh_evaluations():
    print("Testing Sequential Submissions for Fresh Context Evaluation...\n")
    from main import run_prompt_driven_evaluation
    for tc in test_cases:
        print(f"=== Running {tc['name']} ===")
        res = await run_prompt_driven_evaluation(
            question=tc["problem"],
            code=tc["code"],
            target_language=tc["language"]
        )
        res_dict = res.model_dump()
        review = res_dict["individual_reviews"][0]
        print("Feedback:", review["correctness_feedback"])
        print("Common Errors:", review["common_errors"])
        print("Strengths:", review["strengths"])
        print("Weaknesses:", review["weaknesses"])
        print("Recommendations:", review["recommendations"])
        print("Scores:", review["scores"])
        print("-" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_sequential_fresh_evaluations())

