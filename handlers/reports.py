import os
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile
import database as db
import keyboards as kb
from handlers.start import preserve_session_mode_clear
from utils.average import calculate_average
from utils.excel_export import create_excel_report

router = Router()

class ReportStates(StatesGroup):
    selecting_class = State()
    selecting_subject = State()
    selecting_format = State()

@router.message(F.text == "📊 Ведомость оценок", StateFilter("*"))
async def start_report_flow(message: types.Message, state: FSMContext):
    await preserve_session_mode_clear(state)
    classes = db.get_all_classes(message.from_user.id)
    if not classes:
        await message.answer("У вас еще нет ни одного созданного класса.")
        return
        
    await message.answer("Выберите класс для ведомости:", reply_markup=kb.get_classes_keyboard(message.from_user.id))
    await state.set_state(ReportStates.selecting_class)

@router.message(ReportStates.selecting_class)
async def process_report_class(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
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
    await message.answer(f"Выбран класс: {message.text}. Теперь выберите предмет:", reply_markup=kb.get_subjects_keyboard())
    await state.set_state(ReportStates.selecting_subject)

@router.message(ReportStates.selecting_subject)
async def process_report_subject(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return
        
    if message.text == "🔙 Назад":
        await message.answer("Выберите класс для ведомости:", reply_markup=kb.get_classes_keyboard(message.from_user.id))
        await state.set_state(ReportStates.selecting_class)
        return

    if message.text not in db.get_all_subjects():
        await message.answer("Пожалуйста, выберите предмет из меню.")
        return
        
    await state.update_data(active_subject=message.text)
    await message.answer("Выберите формат отчета:", reply_markup=kb.get_report_format_keyboard())
    await state.set_state(ReportStates.selecting_format)

@router.message(ReportStates.selecting_format)
async def process_report_format(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return
        
    if message.text == "🔙 Назад":
        data = await state.get_data()
        active_class = data.get("active_class")
        await message.answer(f"Выбран класс: {active_class}. Теперь выберите предмет:", reply_markup=kb.get_subjects_keyboard())
        await state.set_state(ReportStates.selecting_subject)
        return

    data = await state.get_data()
    active_class = data.get("active_class")
    subject = data.get("active_subject")
    
    grades_data = db.get_class_grades(active_class, subject, message.from_user.id)
    
    if not grades_data:
        await message.answer(f"В классе {active_class} пока нет учеников или оценок по предмету {subject}.", reply_markup=kb.get_main_menu())
        await state.clear()
        return

    if message.text == "📄 Текстовый отчет":
        report = "📊 **Ведомость оценок**\n"
        report += f"🏫 Класс: {active_class}\n"
        report += f"📚 Предмет: {subject}\n\n"
        
        for i, item in enumerate(grades_data, start=1):
            name = item['full_name']
            grades = item['grades']
            grades_str = ", ".join(map(str, grades)) if grades else "Нет оценок"
            avg = calculate_average(grades) if grades else 0.0
            report += f"{i}. {name}: {grades_str} (Средний: {avg})\n"
            
        await message.answer(report, reply_markup=kb.get_main_menu())
        await state.clear()
        
    elif message.text == "excel файл":
        await message.answer("Генерирую Excel файл, пожалуйста, подождите...")
        file_path = create_excel_report(active_class, subject, grades_data)
        
        try:
            excel_file = FSInputFile(file_path)
            await message.bot.send_document(message.chat.id, excel_file, caption=f"Ведомость: {active_class} - {subject}")
            await message.answer("Файл успешно отправлен!", reply_markup=kb.get_main_menu())
        except Exception as e:
            await message.answer(f"Ошибка при отправке файла: {e}", reply_markup=kb.get_main_menu())
        finally:
            if os.path.exists(file_path):
                # We could delete it, but maybe keep for a bit? 
                # Better delete to save space
                os.remove(file_path)
        await state.clear()
    else:
        await message.answer("Пожалуйста, выберите формат из предложенных кнопок.")
