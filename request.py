import requests

BASE_URL = "http://127.0.0.1:8000"

def set_profile():
    print("\n--- Enter Your Profile ---")
    name = input("Name: ")
    age = input("Age: ")
    weight = input("Weight (kg): ")
    height = input("Height (cm): ")
    strengths = input("Strengths: ")
    weaknesses = input("Weaknesses: ")
    expertise = input("Expertise level (Beginner/Intermediate/Advanced): ")
    time = input("Free time for football everyday (minutes): ")

    # Convert numbers safely
    profile_data = {
        "name": name if name else None,
        "age": int(age) if age else None,
        "weight": float(weight) if weight else None,
        "height": float(height) if height else None,
        "strengths": strengths if strengths else None,
        "weaknesses": weaknesses if weaknesses else None,
        "expertise": expertise if expertise else None,
        "time": int(time) if time else None,
    }

    resp = requests.post(f"{BASE_URL}/v1/user/profile", json=profile_data)
    print("\nProfile Response:", resp.json())


def get_profile():
    print("\n--- Fetching User Profile ---")
    resp = requests.get(f"{BASE_URL}/v1/user/profile")
    print(resp.json())


def ask_coach():
    while True:
        query = input("\nAsk Soccer Coach (or type 'exit' to quit): ")
        if query.lower() == "exit":
            break
        resp = requests.post(f"{BASE_URL}/v1/coach", json={"query": query})
        print("\nCoach:", resp.json()["answer"])


if __name__ == "__main__":
    set_profile()
    get_profile()
    ask_coach()
