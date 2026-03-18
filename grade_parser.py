import re
import database as db

def parse_grades_text(text: str, active_class: str, teacher_id: int):
    """
    Parse text like 'Иванов Сергей 3 2 5 Петров Артем 4 5' or 'Иванов пять четыре' into a list of parsed grades.
    Robustly handles concatenated numbers and Russian word-numbers.
    """
    # 1. Basic cleaning and word-to-digit replacement
    text = text.lower().replace(',', ' ').replace(';', ' ').strip()
    
    num_map = {
        "ноль": "0", "нолик": "0",
        "десять": "10", "десятка": "10",
        "девять": "9", "девятка": "9",
        "восемь": "8", "восьмерка": "8",
        "семь": "7", "семерка": "7",
        "шесть": "6", "шестерка": "6",
        "пять": "5", "пятерка": "5",
        "четыре": "4", "четверка": "4",
        "три": "3", "тройка": "3",
        "два": "2", "двойка": "2", "две": "2",
        "один": "1", "единица": "1"
    }
    for word, digit in num_map.items():
        text = text.replace(word, digit)
    
    # 2. Tokenize by space and special chars
    tokens = text.split()
    
    results = []
    errors = []
    
    current_name_parts = []
    current_grades = []
    
    def process_current_group():
        nonlocal current_name_parts, current_grades
        if not current_name_parts:
            return
            
        name_query = " ".join(current_name_parts).strip()
        if not name_query or not current_grades:
            return

        matched = db.find_student_approx(name_query, active_class, teacher_id)
        if matched:
            results.append({
                "first_name": matched[0],
                "last_name": matched[1],
                "grades": current_grades,
                "display_name": f"{matched[0]} {matched[1]}"
            })
        else:
            errors.append(f"Ученик не найден в классе {active_class} для: '{name_query}'.")
        
        current_name_parts = []
        current_grades = []

    for t in tokens:
        # Check if token contains valid grades 0-10.
        # This regex picks up 10s and then single digits 0-9.
        grades_in_token = re.findall(r'10|[0-9]', t)
        # Check if the token is mostly numeric (to avoid parsing 'Александр3' as name part if intended)
        digit_count = sum(c.isdigit() for c in t)
        
        # If the token is purely digits or ends with digits, it's likely grades
        if digit_count > 0:
            # If we were building a name and now we see numbers, OR if it's purely numbers
            if t.isdigit():
                # Correctly handle 54 -> [5, 4]
                if grades_in_token:
                    current_grades.extend([int(g) for g in grades_in_token])
                    continue
            else:
                # Mix of letters and digits, e.g. 'Иванов5' or '11А'
                # If the digits in token are at the end, maybe it's grades spoken too fast
                if re.search(r'\d+$', t):
                    temp_name = re.sub(r'\d+', '', t).strip()
                    if temp_name:
                        current_name_parts.append(temp_name)
                    if grades_in_token:
                        current_grades.extend([int(g) for g in grades_in_token])
                    continue

        # If we have grades already, it means we've started a NEW student name group.
        if current_grades and not any(c.isdigit() for c in t):
            process_current_group()
            
        current_name_parts.append(t)
            
    # Process the last group
    process_current_group()
    
    # Handle remaining errors
    if current_name_parts and not current_grades:
         errors.append(f"Для '{' '.join(current_name_parts)}' не найдено ни одной оценки (0-10).")

    return results, errors
