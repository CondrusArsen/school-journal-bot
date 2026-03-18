from aiogram import Router, types, F
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import config
import database as db
import keyboards as kb

router = Router()

TEACHER_MODE = "teacher"
DEVELOPER_MODE = "developer"

class ClassStates(StatesGroup):
    waiting_for_class_name = State()

class StartStates(StatesGroup):
    selecting_session_mode = State()

def is_developer_user(user_id: int | None) -> bool:
    return bool(config.DEVELOPER_ID) and str(user_id) == str(config.DEVELOPER_ID)

async def get_session_mode(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("session_mode", TEACHER_MODE)

async def preserve_session_mode_clear(state: FSMContext, fallback_mode: str = TEACHER_MODE) -> str:
    data = await state.get_data()
    session_mode = data.get("session_mode", fallback_mode)
    await state.clear()
    await state.update_data(session_mode=session_mode)
    return session_mode

async def show_teacher_home(message: types.Message, state: FSMContext, *, clear_state: bool = False):
    if clear_state:
        await preserve_session_mode_clear(state, TEACHER_MODE)
    else:
        await state.update_data(session_mode=TEACHER_MODE)

    db.register_teacher(message.from_user.id, message.from_user.full_name)
    classes = db.get_all_classes(message.from_user.id)
    if not classes:
        await message.answer(
            "Введите название вашего первого класса (например, 7А):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(ClassStates.waiting_for_class_name)
        return

    await message.answer("Главное меню", reply_markup=kb.get_main_menu())

async def show_developer_home(message: types.Message, state: FSMContext, *, clear_state: bool = False):
    if clear_state:
        await preserve_session_mode_clear(state, DEVELOPER_MODE)
    else:
        await state.update_data(session_mode=DEVELOPER_MODE)

    await message.answer("Меню разработчика", reply_markup=kb.get_developer_main_menu())

@router.message(CommandStart(), StateFilter("*"))
async def cmd_start_command(message: types.Message, state: FSMContext):
    """Handle /start command from any state."""
    await state.clear()
    db.register_teacher(message.from_user.id, message.from_user.full_name)
    if is_developer_user(message.from_user.id):
        await message.answer(
            "Выберите режим входа:",
            reply_markup=kb.get_role_choice_keyboard()
        )
        await state.set_state(StartStates.selecting_session_mode)
        return

    classes = db.get_all_classes(message.from_user.id)
    if not classes:
        await message.answer(
            f"Здравствуйте, {message.from_user.full_name}! Это ваш личный журнал успеваемости.\n\n"
            "Кажется, у вас еще не создано ни одного класса. Давайте начнем с настройки.\n\n"
            "Введите название вашего первого класса (например, 7А):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.update_data(session_mode=TEACHER_MODE)
        await state.set_state(ClassStates.waiting_for_class_name)
        return

    await state.update_data(session_mode=TEACHER_MODE)
    await message.answer(
        f"Здравствуйте, {message.from_user.full_name}! Вы в главном меню журнала.",
        reply_markup=kb.get_main_menu()
    )

@router.message(StartStates.selecting_session_mode)
async def process_session_mode_selection(message: types.Message, state: FSMContext):
    if not is_developer_user(message.from_user.id):
        await show_teacher_home(message, state, clear_state=True)
        return

    if message.text == "🛠️ Войти как разработчик":
        await show_developer_home(message, state, clear_state=True)
        return

    if message.text == "🧑‍🏫 Войти как учитель":
        await show_teacher_home(message, state, clear_state=True)
        return

    await message.answer("Пожалуйста, выберите один из двух режимов входа.", reply_markup=kb.get_role_choice_keyboard())

@router.message(F.text == "🏠 Главное меню", StateFilter("*"))
async def home_menu_handler(message: types.Message, state: FSMContext):
    """Return to main menu from any state."""
    session_mode = await get_session_mode(state)
    if is_developer_user(message.from_user.id) and session_mode == DEVELOPER_MODE:
        await show_developer_home(message, state, clear_state=True)
        return

    await show_teacher_home(message, state, clear_state=True)

@router.message(F.text == "🔄 Выбрать роль", StateFilter("*"))
async def restart_role_selection(message: types.Message, state: FSMContext):
    if not is_developer_user(message.from_user.id):
        await show_teacher_home(message, state, clear_state=True)
        return

    await state.clear()
    await message.answer("Выберите режим входа:", reply_markup=kb.get_role_choice_keyboard())
    await state.set_state(StartStates.selecting_session_mode)

@router.message(F.text == "🧑‍🏫 Режим учителя", StateFilter("*"))
async def switch_to_teacher_mode(message: types.Message, state: FSMContext):
    if not is_developer_user(message.from_user.id):
        await show_teacher_home(message, state, clear_state=True)
        return

    await show_teacher_home(message, state, clear_state=True)

@router.message(F.text == "➕ Добавить класс", StateFilter("*"))
async def add_class_start(message: types.Message, state: FSMContext):
    if is_developer_user(message.from_user.id) and await get_session_mode(state) == DEVELOPER_MODE:
        await show_developer_home(message, state, clear_state=True)
        return

    await state.set_state(ClassStates.waiting_for_class_name)
    await message.answer("Введите название нового класса (например, 8Б):", reply_markup=kb.get_back_to_menu_keyboard())

@router.message(ClassStates.waiting_for_class_name)
async def process_new_class(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню" or message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню", reply_markup=kb.get_main_menu())
        return

    if message.text in ["➕ Ввести оценки", "📋 Список класса", "📊 Ведомость оценок", "💬 Написать разработчику", "➕ Добавить класс"]:
        await message.answer("Пожалуйста, сначала введите название класса или нажмите «Главное меню».")
        return

    class_name = message.text.strip()
    if not class_name:
        await message.answer("Название класса не может быть пустым. Попробуйте еще раз.")
        return
        
    if not db.add_class(class_name, message.from_user.id):
        await message.answer("Такой класс уже существует или название некорректно. Попробуйте другое имя.")
        return

    await message.answer(
        f"Класс '{class_name}' успешно создан!",
        reply_markup=kb.get_main_menu()
    )
    await state.clear()
