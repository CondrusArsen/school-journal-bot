def clean_and_format_text(text):
    """Fixes capitalization and punctuation for voice-recognized text."""
    if not text:
        return ""
    text = text.strip()
    if not text:
        return ""
    # Capitalize first letter
    text = text[0].upper() + text[1:]
    # Add dot if missing and no other punctuation at end
    if text[-1] not in ".!?":
        text += "."
    return text

def generate_student_report(first_name, last_name, grades_dict, behavior=None, diligence=None, recommendation=None, focus_subjects=None, teacher_comment=None):
    """
    Generates a more detailed, personalized, and 'human' student report.
    """
    display_name = " ".join(part for part in (first_name, last_name) if part)

    if not grades_dict:
        return (f"🌟 **Здравствуйте!** К сожалению, по ученику {display_name} в журнале пока нет оценок. "
                "Как только они появятся, я сразу составлю подробный аналитический отчет для вас.")

    all_grades = []
    subject_summaries = []
    for subject, grades in grades_dict.items():
        avg = sum(grades) / len(grades)
        all_grades.extend(grades)
        grades_str = ", ".join(map(str, grades))
        subject_summaries.append(f"  • {subject}: {grades_str} (средний балл {avg:.1f})")

    total_avg = sum(all_grades) / len(all_grades)
    
    # Mapping for natural phrases
    behavior_map = {
        "Отличное": "демонстрирует примерное поведение и вежливость",
        "Активное": "проявляет высокую активность и энтузиазм на уроках",
        "Среднее": "ведет себя спокойно, придерживаясь общих правил",
        "Спокойное": "сосредоточен и не отвлекается на посторонние дела",
        "Плохое": "иногда нарушает дисциплину, что мешает учебному процессу",
        "Нужна мотивация": "нуждается в дополнительном поощрении для вовлечения в работу"
    }
    
    diligence_map = {
        "Усидчивый": "отличается прекрасной усидчивостью и глубиной проработки тем",
        "Самостоятельный": "умеет самостоятельно организовывать свою работу",
        "Старательный": "очень старательно подходит к выполнению каждого задания",
        "Внимательный": "всегда внимателен к деталям и объяснениям учителя",
        "Отвлекается": "быстро теряет концентрацию, что сказывается на результате",
        "Требуется контроль": "лучше работает, когда чувствует четкое руководство и контроль"
    }

    # Clean up prefixes from buttons
    b_key = behavior.replace("👍 ", "").replace("⚡ ", "").replace("😐 ", "").replace("🧘 ", "").replace("👎 ", "").replace("⚠️ ", "") if behavior else ""
    d_key = diligence.replace("💪 ", "").replace("🚀 ", "").replace("🌟 ", "").replace("🧐 ", "").replace("📵 ", "").replace("🧱 ", "") if diligence else ""
    r_clean = recommendation.replace("🚀 ", "").replace("📈 ", "").replace("📝 ", "").replace("📚 ", "").replace("⏳ ", "") if recommendation else ""

    b_phrase = behavior_map.get(b_key, b_key.lower())
    d_phrase = diligence_map.get(d_key, d_key.lower())

    report = (
        f"📋 **ПЕРСОНАЛЬНЫЙ ОБЗОР: {display_name.upper()}**\n\n"
        f"Здравствуйте! Подготовил для вас аналитический отчет о школьной жизни вашего ребенка. \n\n"
        f"📈 **Академические показатели:**\n"
        f"Общая успеваемость на текущий момент: **{total_avg:.1f}**\n\n"
        f"📚 **Детализация по предметам:**\n"
        + "\n".join(subject_summaries) + "\n\n"
    )
    
    if behavior or diligence:
        report += "🧠 **Включенность в учебный процесс:**\n"
        parts = []
        if behavior:
            parts.append(b_phrase)
        if diligence:
            parts.append(d_phrase)
        
        if len(parts) == 2:
            report += f"На занятиях ученик {parts[0]}, а также {parts[1]}. "
        elif len(parts) == 1:
            report += f"На занятиях ученик {parts[0]}. "
        report += "\n\n"

    if focus_subjects:
        subjects_str = ", ".join(focus_subjects)
        report += "🔍 **Области для развития:**\n"
        report += f"На данный момент я рекомендую обратить более пристальное внимание на: **{subjects_str}**. "
        report += "Это поможет укрепить фундамент знаний по этим дисциплинам.\n\n"

    if r_clean:
        report += f"💡 **Рекомендация:** {r_clean}.\n\n"
    elif total_avg < 6:
        report += "💡 **Рекомендация:** Сейчас важно сосредоточиться на регулярном повторении материала и качественном выполнении домашних заданий.\n\n"
        
    if teacher_comment:
        formatted_comment = clean_and_format_text(teacher_comment)
        report += f"📝 **Индивидуальный комментарий учителя:**\n_{formatted_comment}_\n\n"
        report += "Этот комментарий поможет вам лучше понять нюансы работы ребенка в классе."
        
    return report
