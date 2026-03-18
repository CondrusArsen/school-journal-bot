from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import database as db
import keyboards as kb
from handlers.start import home_menu_handler, preserve_session_mode_clear
from utils.average import calculate_average
from utils.ai_reporter import generate_student_report

router = Router()

class ClassManagementStates(StatesGroup):
    selecting_class = State()
    class_view = State()
    adding_student = State()
    viewing_report = State()
    selecting_behavior = State()
    selecting_diligence = State()
    selecting_recommendation = State()
    selecting_focus_subjects = State()
    waiting_for_voice_choice = State()
    waiting_for_comment = State()

@router.message(F.text == "📋 Список класса", StateFilter("*"))
async def start_class_management(message: types.Message, state: FSMContext):
    await preserve_session_mode_clear(state)
    classes = db.get_all_classes(message.from_user.id)
    if not classes:
        await message.answer("У вас еще нет ни одного созданного класса. Пожалуйста, используйте /start.")
        return

    await message.answer("Выберите класс для просмотра:", reply_markup=kb.get_classes_keyboard(message.from_user.id))
    await state.set_state(ClassManagementStates.selecting_class)

@router.message(ClassManagementStates.selecting_class)
async def process_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    if message.text == "➕ Добавить класс":
        return

    if message.text not in db.get_all_classes(message.from_user.id):
        await message.answer("Пожалуйста, выберите класс из меню.")
        return
        
    await state.update_data(active_class=message.text)
    await show_class_view(message, state)

async def show_class_view(message: types.Message, state: FSMContext):
    data = await state.get_data()
    active_class = data.get("active_class")
    students = db.get_students_by_class(active_class, message.from_user.id)
    
    if not students:
        text = f"В классе {active_class} пока нет учеников."
    else:
        text = f"Ученики класса {active_class}:\n\n"
        for i, (_, fn, ln) in enumerate(students, start=1):
            text += f"{i}. {db.format_student_name(fn, ln)}\n"
            
    await message.answer(text, reply_markup=kb.get_class_view_menu())
    await state.set_state(ClassManagementStates.class_view)

@router.message(ClassManagementStates.class_view, F.text == "➕ Добавить ученика")
async def add_student_start(message: types.Message, state: FSMContext):
    await message.answer("Введите фамилию и имя ученика (например, Иванов Иван):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(ClassManagementStates.adding_student)

@router.message(ClassManagementStates.adding_student)
async def add_student_process(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        await show_class_view(message, state)
        return

    if not message.text or len(message.text.split()) < 2:
        await message.answer("Пожалуйста, укажите фамилию и имя (Иванов Иван).")
        return
        
    parts = message.text.split()
    fn, ln = parts[0], " ".join(parts[1:])
    
    data = await state.get_data()
    active_class = data.get("active_class")
    
    if db.add_student(fn, ln, active_class, message.from_user.id):
        await message.answer(f"Ученик {db.format_student_name(fn, ln)} добавлен в {active_class}.")
    else:
        await message.answer("Такой ученик уже есть в классе или данные введены некорректно.")
        
    await show_class_view(message, state)

@router.message(ClassManagementStates.class_view, F.text == "👤 Успеваемость ученика")
async def report_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    active_class = data.get("active_class")
    students = db.get_students_by_class(active_class, message.from_user.id)
    
    if not students:
        await message.answer(f"В классе {active_class} пока нет учеников.")
        return
        
    await message.answer("Выберите ученика для просмотра отчета:", reply_markup=kb.get_students_keyboard(students))
    await state.set_state(ClassManagementStates.viewing_report)

@router.message(ClassManagementStates.viewing_report, F.text == "📊 Сгенерировать отчет")
async def request_behavior(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите характеристику поведения ученика:",
        reply_markup=kb.get_behavior_keyboard()
    )
    await state.set_state(ClassManagementStates.selecting_behavior)

@router.message(ClassManagementStates.viewing_report)
async def report_process(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return
    if message.text == "🔙 Назад":
        await show_class_view(message, state)
        return
    # "📊 Сгенерировать отчет" is handled by the more-specific handler above (request_behavior)

    data = await state.get_data()
    active_class = data.get("active_class")

    matched = db.find_student_approx(message.text, active_class, message.from_user.id)
    if not matched:
        await message.answer(f"Ученик '{message.text}' не найден. Пожалуйста, выберите из списка.")
        return

    fn, ln = matched
    await state.update_data(current_student=(fn, ln))
    grades_dict = db.get_student_grades(fn, ln, active_class, message.from_user.id)
    display_name = db.format_student_name(fn, ln)

    if not grades_dict:
        report = f"У ученика {display_name} пока нет оценок."
    else:
        report = f"📋 **Успеваемость: {display_name}**\n\n"
        for subject, grades in grades_dict.items():
            avg = calculate_average(grades)
            grades_str = ", ".join(map(str, grades))
            report += f"📚 {subject}: {grades_str} (Средний: {avg})\n"

    await message.answer(report, reply_markup=kb.get_report_start_keyboard())
    # Stay in viewing_report to handle "📊 Сгенерировать отчет"

@router.message(ClassManagementStates.selecting_behavior, F.text.in_(["👍 Отличное", "⚡ Активное", "😐 Среднее", "🧘 Спокойное", "👎 Плохое", "⚠️ Нужна мотивация", "🏠 Главное меню"]))
async def request_diligence(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    await state.update_data(behavior_text=message.text)
    await message.answer(
        "Насколько ученик прилежен в учебе?",
        reply_markup=kb.get_diligence_keyboard()
    )
    await state.set_state(ClassManagementStates.selecting_diligence)

@router.message(ClassManagementStates.selecting_diligence, F.text.in_(["💪 Усидчивый", "🚀 Самостоятельный", "🌟 Старательный", "🧐 Внимательный", "📵 Отвлекается", "🧱 Требуется контроль", "🏠 Главное меню"]))
async def request_recommendation(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    await state.update_data(diligence_text=message.text)
    await message.answer(
        "Выберите рекомендацию для родителей (или пропустите):",
        reply_markup=kb.get_recommendation_keyboard()
    )
    await state.set_state(ClassManagementStates.selecting_recommendation)

@router.message(ClassManagementStates.selecting_recommendation)
async def request_focus_subjects(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    await state.update_data(recommendation_text=message.text if message.text != "⏭️ Пропустить" else None)
    
    data = await state.get_data()
    student_data = data.get("current_student")
    active_class = data.get("active_class")
    fn, ln = student_data
    
    grades_dict = db.get_student_grades(fn, ln, active_class, message.from_user.id)
    subjects = list(grades_dict.keys()) if grades_dict else []
    selected_focus_subjects = [subject for subject in data.get("focus_subjects", []) if subject in subjects]
    await state.update_data(all_subjects_for_focus=subjects, focus_subjects=selected_focus_subjects)
    
    await message.answer(
        "Выберите предметы, на которые родителям стоит обратить внимание (нажмите несколько или 'Готово'):",
        reply_markup=kb.get_subjects_focus_keyboard(subjects, selected_subjects=selected_focus_subjects)
    )
    await state.set_state(ClassManagementStates.selecting_focus_subjects)

@router.callback_query(F.data.startswith("focus_sub_"), ClassManagementStates.selecting_focus_subjects)
async def process_focus_subject_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    focus_subjects = data.get("focus_subjects", [])
    subjects_list = data.get("all_subjects_for_focus", [])
    
    subject = callback.data.replace("focus_sub_", "")
    
    if subject == "done":
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None) # Remove inline kb
        await callback.message.answer(
            "Хотите добавить личный комментарий к отчету?",
            reply_markup=kb.get_voice_comment_keyboard()
        )
        await state.set_state(ClassManagementStates.waiting_for_voice_choice)
        return

    if subject not in subjects_list:
        await callback.answer("Этот предмет больше недоступен.", show_alert=True)
        return

    if subject in focus_subjects:
        focus_subjects.remove(subject)
        await callback.answer(f"Удалено: {subject}")
    else:
        focus_subjects.append(subject)
        await callback.answer(f"Добавлено: {subject}")
    
    await state.update_data(focus_subjects=focus_subjects)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_subjects_focus_keyboard(subjects_list, selected_subjects=focus_subjects)
        )
    except Exception:
        pass # Message might be the same

@router.message(ClassManagementStates.waiting_for_voice_choice)
async def process_voice_choice(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return
    
    if message.text == "⏭️ Пропустить":
        await finalize_report_and_send(message, state)
        return

    if message.text == "🎤 Записать голос":
        await message.answer("Отправьте голосовое сообщение с вашим комментарием:", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "⌨️ Написать текст":
        await message.answer("Введите текст вашего комментария:", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer("Пожалуйста, используйте кнопки ниже.", reply_markup=kb.get_voice_comment_keyboard())
        return
    
    await state.set_state(ClassManagementStates.waiting_for_comment)

@router.message(ClassManagementStates.waiting_for_comment, F.voice | F.text)
async def handle_teacher_comment(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        await message.answer("Хотите добавить личный комментарий к отчету?", reply_markup=kb.get_voice_comment_keyboard())
        await state.set_state(ClassManagementStates.waiting_for_voice_choice)
        return

    comment_text = ""
    if message.voice:
        msg = await message.answer("⏳ Расшифровываю голос...")
        import os
        from utils.speech_to_text import convert_voice_to_text
        
        file_id = message.voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        # Ensure temp dir exists
        os.makedirs("temp_voice", exist_ok=True)
        local_path = f"temp_voice/{file_id}.ogg"
        await message.bot.download_file(file_path, local_path)

        try:
            comment_text = await convert_voice_to_text(local_path)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        await msg.delete()

        if not comment_text or comment_text.startswith("ERROR_"):
            await message.answer("Не удалось распознать голос. Пожалуйста, попробуйте еще раз или напишите текстом.")
            return
        await message.answer(f"Распознано: <i>{comment_text}</i>", parse_mode="HTML")
    else:
        comment_text = message.text

    await state.update_data(teacher_comment=comment_text)
    await finalize_report_and_send(message, state)

async def finalize_report_and_send(message: types.Message, state: FSMContext):
    
    data = await state.get_data()
    student_data = data.get("current_student")
    if not student_data:
        await message.answer("Ошибка: данные ученика потеряны.", reply_markup=kb.get_main_menu())
        await state.clear()
        return
        
    fn, ln = student_data
    active_class = data.get("active_class")
    behavior = data.get("behavior_text")
    diligence = data.get("diligence_text")
    recommendation = data.get("recommendation_text")
    focus_subjects = data.get("focus_subjects", [])
    teacher_comment = data.get("teacher_comment")
    
    # Re-fetch grades
    grades_dict = db.get_student_grades(fn, ln, active_class, message.from_user.id)
    
    report = generate_student_report(
        fn, ln, grades_dict, 
        behavior=behavior, 
        diligence=diligence, 
        recommendation=recommendation,
        focus_subjects=focus_subjects,
        teacher_comment=teacher_comment
    )
    
    await message.answer(report, reply_markup=kb.get_main_menu())
    await state.clear()

@router.message(ClassManagementStates.class_view, F.text == "🔙 Назад")
async def back_to_class_selection(message: types.Message, state: FSMContext):
    await start_class_management(message, state)
