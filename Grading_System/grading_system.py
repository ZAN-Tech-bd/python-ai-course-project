import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.json")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def grade_from_score(score):
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def gpa_from_grade(grade):
    return {"A+": 4.0, "A": 3.7, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}[grade]


def add_student(data):
    student_id = input("Enter student ID: ").strip()
    if student_id in data:
        print("A student with this ID already exists.")
        return
    name = input("Enter student name: ").strip()
    data[student_id] = {"name": name, "subjects": {}}
    save_data(data)
    print(f"Student '{name}' added successfully.")


def add_scores(data):
    student_id = input("Enter student ID: ").strip()
    if student_id not in data:
        print("Student not found.")
        return
    while True:
        subject = input("Enter subject name (or blank to stop): ").strip()
        if not subject:
            break
        score_raw = input(f"Enter score for {subject} (0-100): ").strip()
        try:
            score = float(score_raw)
            if not (0 <= score <= 100):
                print("Score must be between 0 and 100.")
                continue
        except ValueError:
            print("Invalid score. Enter a number.")
            continue
        data[student_id]["subjects"][subject] = score
        print(f"{subject}: {score} -> Grade {grade_from_score(score)}")
    save_data(data)


def student_report(data, student_id):
    student = data[student_id]
    subjects = student["subjects"]
    print(f"\nReport for {student['name']} (ID: {student_id})")
    print("-" * 40)
    if not subjects:
        print("No scores recorded yet.")
        return
    total_gpa = 0
    for subject, score in subjects.items():
        grade = grade_from_score(score)
        total_gpa += gpa_from_grade(grade)
        print(f"{subject:<20} Score: {score:<6} Grade: {grade}")
    avg_score = sum(subjects.values()) / len(subjects)
    avg_gpa = total_gpa / len(subjects)
    print("-" * 40)
    print(f"Average Score: {avg_score:.2f}")
    print(f"Overall Grade: {grade_from_score(avg_score)}")
    print(f"GPA: {avg_gpa:.2f}")


def view_student(data):
    student_id = input("Enter student ID: ").strip()
    if student_id not in data:
        print("Student not found.")
        return
    student_report(data, student_id)


def view_all(data):
    if not data:
        print("No students recorded yet.")
        return
    for student_id in data:
        student_report(data, student_id)
        print()


def delete_student(data):
    student_id = input("Enter student ID: ").strip()
    if student_id not in data:
        print("Student not found.")
        return
    name = data[student_id]["name"]
    confirm = input(f"Delete '{name}' (ID: {student_id})? [y/N]: ").strip().lower()
    if confirm == "y":
        del data[student_id]
        save_data(data)
        print("Student deleted.")
    else:
        print("Cancelled.")


def print_menu():
    print("\n===== Grading System =====")
    print("1. Add Student")
    print("2. Add/Update Scores")
    print("3. View Student Report")
    print("4. View All Students")
    print("5. Delete Student")
    print("6. Exit")


def main():
    data = load_data()
    actions = {
        "1": add_student,
        "2": add_scores,
        "3": view_student,
        "4": view_all,
        "5": delete_student,
    }
    while True:
        print_menu()
        choice = input("Choose an option (1-6): ").strip()
        if choice == "6":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action(data)
        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    main()
