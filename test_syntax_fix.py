import asyncio
import json
from main import run_prompt_driven_evaluation

question = "In an online ticket system, each booking id is formed by combining a city code and a numeric sequence (for example BLR + 1052 -> BLR1052). Write a program that reads the city code and the sequence number as separate inputs and combines them into one booking id without using the plus operator for string concatenation. Store the city code as a String and the sequence number as a String or convert it to String, then use String.concat or a StringBuilder append chain to produce the final booking id."

code = """import java.util.*;

public class BookingID_NoInbuilt {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String city = sc.next();
        String seq = sc.next();

        char[] result = new char[city.length() + seq.length()];

        for (int i = 0; i < city.length(); i++) {
            result[i] = city.charAt(i);
        }
        for (int i = 0; i < seq.length(); i++) {
            result[city.length() + i] = seq.charAt(i);
        }

        System.out.println("Booking ID: " + new String(result));
    }
}"""

async def main():
    res = await run_prompt_driven_evaluation(
        question=question,
        code=code,
        target_language="Java"
    )
    print(json.dumps(res.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
