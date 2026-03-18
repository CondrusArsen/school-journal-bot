from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import database as db

def _get_nav_buttons():
    """Вспомогательная функция для получения кнопок навигации."""
    return [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]

def _build_single_column_keyboard(items, *, include_back=True, include_home=True):
    kb = [[KeyboardButton(text=item)] for item in items]
    if include_back and include_home:
        kb.append(_get_nav_buttons())
    elif include_back:
        kb.append([_get_nav_buttons()[0]])
    elif include_home:
        kb.append([_get_nav_buttons()[1]])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_menu():
    kb = [
        [KeyboardButton(text="➕ Ввести оценки")],
        [KeyboardButton(text="📋 Список класса"), KeyboardButton(text="📊 Ведомость оценок")],
        [KeyboardButton(text="💬 Написать разработчику")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_classes_keyboard(teacher_id: int):
    classes = db.get_all_classes(teacher_id)
    kb = [[KeyboardButton(text=c)] for c in classes]
    kb.append([KeyboardButton(text="➕ Добавить класс")])
    kb.append(_get_nav_buttons())
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_subjects_keyboard():
    subjects = db.get_all_subjects()
    # Группировка предметов по 2 в ряд
    kb = [
        [KeyboardButton(text=subjects[i]), KeyboardButton(text=subjects[i+1])] 
        if i + 1 < len(subjects) else [KeyboardButton(text=subjects[i])]
        for i in range(0, len(subjects), 2)
    ]
    kb.append(_get_nav_buttons())
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_class_view_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить ученика"), KeyboardButton(text="👤 Успеваемость ученика")],
        [_get_nav_buttons()[0], _get_nav_buttons()[1]],
        [KeyboardButton(text="💬 Написать разработчику")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_confirmation_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm_grades"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_grades")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_entry_mode_keyboard():
    kb = [
        [KeyboardButton(text="📋 По списку учеников")],
        [KeyboardButton(text="👤 Выбор ученика")],
        [KeyboardButton(text="📝 Массовый ввод")],
        _get_nav_buttons()
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_to_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[_get_nav_buttons()], resize_keyboard=True)

def get_role_choice_keyboard():
    kb = [
        [KeyboardButton(text="🛠️ Войти как разработчик")],
        [KeyboardButton(text="🧑‍🏫 Войти как учитель")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_developer_main_menu():
    kb = [
        [KeyboardButton(text="👨‍🏫 Учителя"), KeyboardButton(text="📊 Общая статистика")],
        [KeyboardButton(text="🧑‍🏫 Режим учителя"), KeyboardButton(text="🔄 Выбрать роль")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_developer_teachers_keyboard(teacher_labels):
    return _build_single_column_keyboard(teacher_labels)

def get_developer_classes_keyboard(class_labels):
    return _build_single_column_keyboard(class_labels)

def get_developer_students_keyboard(student_labels):
    return _build_single_column_keyboard(student_labels)

def get_grades_keyboard():
    kb = [
        [KeyboardButton(text=str(i)) for i in range(6)],
        [KeyboardButton(text=str(i)) for i in range(6, 11)],
        [KeyboardButton(text="✅ Готово / Следующий"), KeyboardButton(text="⏭️ Пропустить / Далее")],
        [KeyboardButton(text="✏️ Редактировать")],
        _get_nav_buttons()
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_edit_grades_inline_keyboard(grades):
    """Инлайн-кнопки для удаления конкретных оценок."""
    kb = []
    row = []
    for i, g in enumerate(grades):
        row.append(InlineKeyboardButton(text=f"❌ {g}", callback_data=f"del_grade_{i}"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="✅ Готово", callback_data="stop_editing")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_students_keyboard(students):
    kb = [[KeyboardButton(text=db.format_student_name(fn, ln))] for _, fn, ln in students]
    kb.append(_get_nav_buttons())
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_report_start_keyboard():
    kb = [
        [KeyboardButton(text="📊 Сгенерировать отчет")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_report_format_keyboard():
    kb = [
        [KeyboardButton(text="📄 Текстовый отчет"), KeyboardButton(text="excel файл")],
        [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_behavior_keyboard():
    kb = [
        [KeyboardButton(text="👍 Отличное"), KeyboardButton(text="⚡ Активное")],
        [KeyboardButton(text="😐 Среднее"), KeyboardButton(text="🧘 Спокойное")],
        [KeyboardButton(text="👎 Плохое"), KeyboardButton(text="⚠️ Нужна мотивация")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_diligence_keyboard():
    kb = [
        [KeyboardButton(text="💪 Усидчивый"), KeyboardButton(text="🚀 Самостоятельный")],
        [KeyboardButton(text="🌟 Старательный"), KeyboardButton(text="🧐 Внимательный")],
        [KeyboardButton(text="📵 Отвлекается"), KeyboardButton(text="🧱 Требуется контроль")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_recommendation_keyboard():
    kb = [
        [KeyboardButton(text="🚀 Продолжать в том же духе"), KeyboardButton(text="📈 Подтянуть слабые места")],
        [KeyboardButton(text="📝 Повторить правила"), KeyboardButton(text="📚 Больше читать")],
        [KeyboardButton(text="⏳ Уделить время ДЗ"), KeyboardButton(text="⏭️ Пропустить")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_subjects_focus_keyboard(subjects, selected_subjects=None):
    selected_subjects = set(selected_subjects or [])
    kb = [
        [
            InlineKeyboardButton(
                text=f"✅ {subjects[i]}" if subjects[i] in selected_subjects else subjects[i],
                callback_data=f"focus_sub_{subjects[i]}",
            ),
            InlineKeyboardButton(
                text=f"✅ {subjects[i+1]}" if subjects[i + 1] in selected_subjects else subjects[i + 1],
                callback_data=f"focus_sub_{subjects[i+1]}",
            ),
        ]
        if i + 1 < len(subjects) else [
            InlineKeyboardButton(
                text=f"✅ {subjects[i]}" if subjects[i] in selected_subjects else subjects[i],
                callback_data=f"focus_sub_{subjects[i]}",
            )
        ]
        for i in range(0, len(subjects), 2)
    ]
    kb.append([InlineKeyboardButton(text="✅ Готово / Нет таких", callback_data="focus_sub_done")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_voice_comment_keyboard():
    kb = [
        [KeyboardButton(text="🎤 Записать голос"), KeyboardButton(text="⌨️ Написать текст")],
        [KeyboardButton(text="⏭️ Пропустить"), KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
