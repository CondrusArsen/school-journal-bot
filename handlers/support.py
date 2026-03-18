from aiogram import Router, F, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import config
import keyboards as kb
from handlers.start import home_menu_handler

router = Router()

class SupportStates(StatesGroup):
    waiting_for_message = State()

STATE_NAMES = {
    "GradeStates:selecting_class": "Выбор класса (ввод оценок)",
    "GradeStates:selecting_subject": "Выбор предмета (ввод оценок)",
    "GradeStates:selecting_entry_mode": "Выбор режима ввода оценок",
    "GradeStates:selecting_specific_student": "Выбор конкретного ученика",
    "GradeStates:waiting_for_input": "Массовый ввод оценок",
    "GradeStates:entering_sequential_grades": "Последовательный ввод оценок",
    "ClassManagementStates:selecting_class": "Выбор класса (список)",
    "ClassManagementStates:class_view": "Просмотр класса",
    "ClassManagementStates:adding_student": "Добавление ученика",
    "ClassManagementStates:viewing_report": "Успеваемость ученика",
    "ClassManagementStates:selecting_behavior": "Выбор поведения для AI-отчета",
    "ClassManagementStates:selecting_diligence": "Выбор прилежания для AI-отчета",
    "ClassManagementStates:selecting_recommendation": "Выбор рекомендации для AI-отчета",
    "ReportStates:selecting_class": "Выбор класса (ведомость)",
    "ReportStates:selecting_subject": "Выбор предмета (ведомость)",
}

@router.message(F.text == "💬 Написать разработчику", StateFilter("*"))
async def contact_developer_prompt(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    await state.update_data(previous_state=current_state)
    
    await message.answer(
        "Напишите ваше сообщение разработчику:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="🔙 Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(SupportStates.waiting_for_message)

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "🏠 Главное меню":
        await home_menu_handler(message, state)
        return

    if message.text == "🔙 Отмена":
        await message.answer("Отправка сообщения отменена.", reply_markup=kb.get_main_menu())
        await state.clear()
        return

    developer_id = config.DEVELOPER_ID
    data = await state.get_data()
    prev_state_raw = data.get("previous_state")
    prev_state_name = STATE_NAMES.get(prev_state_raw, "Главное меню")
    
    if not developer_id:
        await message.answer("Telegram ID разработчика не настроен.", reply_markup=kb.get_main_menu())
        await state.clear()
        return
        
    forward_text = (
        f"📢 Сообщение в поддержку от пользователя\n"
        f"ID пользователя: {message.from_user.id}\n"
        f"Никнейм: @{message.from_user.username or 'N/A'}\n"
        f"📍 Экран/Состояние: {prev_state_name} ({prev_state_raw})\n\n"
        f"Сообщение:\n{message.text}"
    )
    
    try:
        await bot.send_message(chat_id=developer_id, text=forward_text)
        await message.answer("Ваше сообщение было отправлено разработчику.", reply_markup=kb.get_main_menu())
    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение: {e}", reply_markup=kb.get_main_menu())
        
    await state.clear()
