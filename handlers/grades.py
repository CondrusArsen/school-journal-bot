from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import database as db
import keyboards as kb
from handlers.start import home_menu_handler, preserve_session_mode_clear
from grade_parser import parse_grades_text
from utils.speech_to_text import convert_voice_to_text
import os

router = Router()

class GradeStates(StatesGroup):
    selecting_class = State()
    selecting_subject = State()
    selecting_entry_mode = State()
    selecting_specific_student = State()
    waiting_for_input = State()
    entering_sequential_grades = State()

@router.message(F.text == "➕ Ввести оценки", StateFilter("*"))
@router.message(F.text == "📚 Сменить класс", StateFilter("*"))
async def start_grade_entry(message: types.Message, state: FSMContext):
    await preserve_session_mode_clear(state)
    classes = db.get_all_classes(message.from_user.id)
    if not classes:
        await message.answer("У вас еще нет ни одного созданного класса. Пожалуйста, используйте /start.")
        return

    await message.answer("Пожалуйста, выберите класс:", reply_markup=kb.get_classes_keyboard(message.from_user.id))
    await state.set_state(GradeStates.selecting_class)

@router.message(GradeStates.selecting_class)
async def process_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    if message.text == "➕ Добавить класс":
        # Handled by global router in start.py, but for safety:
        return

    if message.text not in db.get_all_classes(message.from_user.id):
        await message.answer("Пожалуйста, выберите класс из меню ниже.")
        return
        
    await state.update_data(active_class=message.text)
    await message.answer("Пожалуйста, выберите предмет:", reply_markup=kb.get_subjects_keyboard())
    await state.set_state(GradeStates.selecting_subject)

@router.message(GradeStates.selecting_subject)
async def process_subject_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        await start_grade_entry(message, state)
        return

    if message.text not in db.get_all_subjects():
        await message.answer("Пожалуйста, выберите предмет из списка.")
        return
        
    await state.update_data(active_subject=message.text)
    
    await message.answer(
        f"Выбран предмет: {message.text}. Как вы хотите ввести оценки?",
        reply_markup=kb.get_entry_mode_keyboard()
    )
    await state.set_state(GradeStates.selecting_entry_mode)

@router.message(GradeStates.selecting_entry_mode)
async def process_entry_mode_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        data = await state.get_data()
        await message.answer("Пожалуйста, выберите предмет:", reply_markup=kb.get_subjects_keyboard())
        await state.set_state(GradeStates.selecting_subject)
        return

    if message.text == "📝 Массовый ввод":
        await message.answer(
            "Режим массового ввода.\nПришлите сообщение со списком учеников и оценками (текстом или голосом).\nНапример: 'Иванов 5 4, Петров 3'",
            reply_markup=kb.get_back_to_menu_keyboard()
        )
        await state.set_state(GradeStates.waiting_for_input)
    elif message.text == "📋 По списку учеников":
        data = await state.get_data()
        active_class = data.get("active_class")
        students = db.get_students_by_class(active_class, message.from_user.id)
        
        if not students:
            await message.answer(f"В классе {active_class} нет учеников. Сначала добавьте учеников.")
            return

        await state.update_data(students=students, current_student_index=0, current_student_grades=[])
        
        student = students[0]
        student_name = db.format_student_name(student[1], student[2])
        
        await message.answer(
            f"Ввод оценок для класса {active_class}, предмет: {data.get('active_subject')}\n\n"
            f"Ученик 1 из {len(students)}: <b>{student_name}</b>\n"
            "Выберите оценки кнопками или надиктуйте их голосом.",
            reply_markup=kb.get_grades_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(GradeStates.entering_sequential_grades)
    elif message.text == "👤 Выбор ученика":
        data = await state.get_data()
        active_class = data.get("active_class")
        students = db.get_students_by_class(active_class, message.from_user.id)
        
        if not students:
            await message.answer(f"В классе {active_class} нет учеников.")
            return

        await message.answer(
            "Пожалуйста, выберите ученика из списка:",
            reply_markup=kb.get_students_keyboard(students)
        )
        await state.set_state(GradeStates.selecting_specific_student)
    else:
        await message.answer("Пожалуйста, выберите режим из меню.")

@router.message(GradeStates.selecting_specific_student)
async def process_specific_student_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад":
        data = await state.get_data()
        await message.answer(
            f"Выбран предмет: {data.get('active_subject')}. Как вы хотите ввести оценки?",
            reply_markup=kb.get_entry_mode_keyboard()
        )
        await state.set_state(GradeStates.selecting_entry_mode)
        return

    data = await state.get_data()
    active_class = data.get("active_class")
    students = db.get_students_by_class(active_class, message.from_user.id)
    
    # Simple search for the student in the list
    selected_student = None
    for s in students:
        if db.format_student_name(s[1], s[2]) == message.text:
            selected_student = s
            break
            
    if not selected_student:
        await message.answer("Пожалуйста, выберите ученика из предложенного списка.")
        return

    await state.update_data(students=[selected_student], current_student_index=0, current_student_grades=[])
    
    await message.answer(
        f"Ввод оценок для <b>{db.format_student_name(selected_student[1], selected_student[2])}</b>\n"
        "Выберите оценки кнопками или надиктуйте их голосом.",
        reply_markup=kb.get_grades_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GradeStates.entering_sequential_grades)

@router.message(GradeStates.entering_sequential_grades)
async def process_sequential_grade_entry(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    data = await state.get_data()
    students = data.get("students", [])
    index = data.get("current_student_index", 0)
    current_grades = data.get("current_student_grades", [])
    active_class = data.get("active_class")
    active_subject = data.get("active_subject")
    
    if not students:
        await message.answer("Ошибка: список учеников пуст. Попробуйте начать заново.")
        await state.clear()
        return

    # 1. Handle Back button
    if message.text == "🔙 Назад":
        if index > 0:
            # Go to previous student
            new_index = index - 1
            await state.update_data(current_student_index=new_index, current_student_grades=[])
            student = students[new_index]
            await message.answer(
                f"Ученик {new_index + 1} из {len(students)}: <b>{db.format_student_name(student[1], student[2])}</b>\n"
                "Выберите оценки или нажмите 'Следующий'.",
                reply_markup=kb.get_grades_keyboard(),
                parse_mode="HTML"
            )
        else:
            # Back to entry mode selection
            data = await state.get_data()
            await message.answer(
                f"Выбран предмет: {data.get('active_subject')}. Как вы хотите ввести оценки?",
                reply_markup=kb.get_entry_mode_keyboard()
            )
            await state.set_state(GradeStates.selecting_entry_mode)
        return

    # 2. Handle Skip / Next student
    if message.text in ["✅ Готово / Следующий", "⏭️ Пропустить / Далее"]:
        # Save accumulated grades if any
        if current_grades:
            student = students[index]
            for g in current_grades:
                db.save_grade(student[1], student[2], active_class, active_subject, int(g), message.from_user.id)
        
        # Move to next student
        new_index = index + 1
        if new_index < len(students):
            await state.update_data(current_student_index=new_index, current_student_grades=[])
            student = students[new_index]
            await message.answer(
                f"Успешно сохранено для предыдущего ученика.\n\n"
                f"Ученик {new_index + 1} из {len(students)}: <b>{db.format_student_name(student[1], student[2])}</b>\n"
                "Выберите оценки или нажмите 'Следующий'.",
                reply_markup=kb.get_grades_keyboard(),
                parse_mode="HTML"
            )
        else:
            # All students processed
            await message.answer(
                "✅ Ввод оценок завершен для всего класса!",
                reply_markup=kb.get_main_menu()
            )
            await state.clear()
        return

    # 3. Handle Grades button (0-10)
    if message.text and message.text.isdigit() and 0 <= int(message.text) <= 10:
        grade = int(message.text)
        current_grades.append(grade)
        await state.update_data(current_student_grades=current_grades)
        
        student = students[index]
        grades_str = ", ".join(map(str, current_grades))
        await message.answer(
            f"Добавлена оценка: {grade}\n"
            f"Текущие оценки <b>{db.format_student_name(student[1], student[2])}</b>: {grades_str}\n"
            "Вы можете добавить еще или нажать 'Следующий'.",
            reply_markup=kb.get_grades_keyboard(),
            parse_mode="HTML"
        )
        return

    # 4. Handle Voice or Arbitrary Text (for the current student)
    text = ""
    if message.voice:
        msg = await message.answer("Обработка голоса для текущего ученика...")
        os.makedirs("temp_voice", exist_ok=True)
        file_id = message.voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = f"temp_voice/{file_id}.oga"
        await message.bot.download_file(file.file_path, file_path)
        try:
            text = await convert_voice_to_text(file_path)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
        await msg.delete()
    else:
        text = message.text

    if text and not text.startswith("ERROR_"):
        # Extract grades from text (similar to grade_parser but only for one student)
        import re
        processed_text = text.lower().replace(',', ' ').replace(';', ' ')
        num_map = {"десять": "10", "девять": "9", "восемь": "8", "семь": "7", "шесть": "6", "пять": "5", "четыре": "4", "три": "3", "два": "2", "один": "1", "ноль": "0"}
        for word, digit in num_map.items():
            processed_text = processed_text.replace(word, digit)
        
        found_grades = [int(g) for g in re.findall(r'10|[0-9]', processed_text)]
        
        if found_grades:
            current_grades.extend(found_grades)
            await state.update_data(current_student_grades=current_grades)
            student = students[index]
            grades_str = ", ".join(map(str, current_grades))
            await message.answer(
                f"Распознано: {', '.join(map(str, found_grades))}\n"
                f"Текущие оценки <b>{db.format_student_name(student[1], student[2])}</b>: {grades_str}\n"
                "Вы можете добавить еще или нажать 'Следующий'.",
                reply_markup=kb.get_grades_keyboard(),
                parse_mode="HTML"
            )
            return

    # 5. Handle Edit button
    if message.text == "✏️ Редактировать":
        if not current_grades:
            await message.answer("У этого ученика еще нет введенных оценок для редактирования.")
            return
            
        student = students[index]
        await message.answer(
            f"Редактирование оценок <b>{db.format_student_name(student[1], student[2])}</b>.\nНажмите на оценку, чтобы удалить её:",
            reply_markup=kb.get_edit_grades_inline_keyboard(current_grades),
            parse_mode="HTML"
        )
        return

    # 6. Handle Bulk Entry button (legacy support if needed, though now a separate mode)
    if message.text == "📝 Массовый ввод":
        await message.answer(
            "Режим массового ввода.\n"
            "Вы можете отправить текст (например: 'Иванов 5 4, Петров 3') "
            "или голосовое сообщение со списком учеников и оценок.",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="🔙 Назад к списку")]],
                resize_keyboard=True
            )
        )
        await state.set_state(GradeStates.waiting_for_input)
        return

    await message.answer("Пожалуйста, используйте кнопки на клавиатуре.")

@router.message(GradeStates.waiting_for_input)
async def process_grades_input(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Назад к списку":
        data = await state.get_data()
        students = data.get("students", [])
        index = data.get("current_student_index", 0)
        # Guard against empty students list (entered bulk mode from main menu, not "By list")
        if not students or index >= len(students):
            await message.answer(
                f"Выберите предмет: {data.get('active_subject', '')}. Как вы хотите ввести оценки?",
                reply_markup=kb.get_entry_mode_keyboard()
            )
            await state.set_state(GradeStates.selecting_entry_mode)
            return
        student = students[index]
        await message.answer(
            f"Возврат к списку. Ученик: <b>{db.format_student_name(student[1], student[2])}</b>",
            reply_markup=kb.get_grades_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(GradeStates.entering_sequential_grades)
        return
    if message.text == "🔙 Назад":
        # Back to entry mode selection
        data = await state.get_data()
        await message.answer(
            f"Выбран предмет: {data.get('active_subject')}. Как вы хотите ввести оценки?",
            reply_markup=kb.get_entry_mode_keyboard()
        )
        await state.set_state(GradeStates.selecting_entry_mode)
        return

    data = await state.get_data()
    active_class = data.get("active_class")
    
    if message.voice:
        msg = await message.answer("Обработка голосового сообщения...")
        
        # Create temp directory if it doesn't exist
        os.makedirs("temp_voice", exist_ok=True)
        file_id = message.voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = f"temp_voice/{file_id}.oga"
        
        await message.bot.download_file(file.file_path, file_path)
        
        try:
            text = await convert_voice_to_text(file_path)
        finally:
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)
                
        await msg.delete()
    else:
        text = message.text

    if not text or text.startswith("ERROR_"):
        error_msg = "Я не смог распознать голосовое сообщение."
        if text:
            if "UNINTELLIGIBLE" in text:
                error_msg += "\nРечь неразборчива. Попробуйте говорить четче."
            elif "REQUEST_FAILED" in text:
                error_msg += "\nОшибка сервиса распознавания. Проверьте интернет."
            else:
                error_msg += f"\nТехническая ошибка: {text}"
        
        await message.answer(error_msg)
        return
        
    results, errors = parse_grades_text(text, active_class, message.from_user.id)
    
    if not results and not errors:
        await message.answer("Ввод не найден. Попробуйте снова или нажмите 'Назад'.")
        return

    response_text = "Распознано:\n\n"
    for r in results:
        grades_str = ", ".join(map(str, r['grades']))
        response_text += f"{r['display_name']}: {grades_str}\n"
        
    if errors:
        response_text += "\nОшибки:\n" + "\n".join(errors)

    if not results:
        await message.answer("Действительные оценки не распознаны.\n" + response_text)
        return

    await state.update_data(parsed_results=results)
    await message.answer(response_text, reply_markup=kb.get_confirmation_keyboard())

@router.callback_query(F.data.startswith("del_grade_"))
async def delete_grade_callback(callback: types.CallbackQuery, state: FSMContext):
    grade_index = int(callback.data.split("_")[-1])
    data = await state.get_data()
    current_grades = data.get("current_student_grades", [])
    
    if 0 <= grade_index < len(current_grades):
        removed_grade = current_grades.pop(grade_index)
        await state.update_data(current_student_grades=current_grades)
        
        # Update the message with new keyboard
        if not current_grades:
            await callback.message.edit_text("Все оценки удалены. Введите новые оценки кнопками или голосом.")
            await callback.answer(f"Оценка {removed_grade} удалена")
            return
            
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_edit_grades_inline_keyboard(current_grades)
        )
        await callback.answer(f"Оценка {removed_grade} удалена")
    else:
        await callback.answer("Ошибка: оценка не найдена.")

@router.callback_query(F.data == "stop_editing")
async def stop_editing_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    students = data.get("students", [])
    index = data.get("current_student_index", 0)
    current_grades = data.get("current_student_grades", [])

    if not students or index >= len(students):
        await callback.message.edit_text("Редактирование завершено.")
        await callback.answer("Список учеников устарел.")
        return

    student = students[index]
    
    grades_str = ", ".join(map(str, current_grades)) if current_grades else "нет"
    await callback.message.edit_text(
        f"Редактирование завершено.\n"
        f"Текущие оценки <b>{db.format_student_name(student[1], student[2])}</b>: {grades_str}",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_grades")
async def confirm_grades_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    results = data.get("parsed_results", [])
    active_class = data.get("active_class")
    active_subject = data.get("active_subject")
    
    saved_count = 0
    for r in results:
        for grade in r['grades']:
            if db.save_grade(r['first_name'], r['last_name'], active_class, active_subject, grade, callback.from_user.id):
                saved_count += 1
                
    await callback.message.edit_text(f"Успешно сохранено оценок: {saved_count}!")
    
    await callback.message.answer("Главное меню", reply_markup=kb.get_main_menu())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_grades")
async def cancel_grades_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Ввод оценок отменен.")
    await callback.message.answer("Главное меню", reply_markup=kb.get_main_menu())
    await state.clear()
    await callback.answer()
