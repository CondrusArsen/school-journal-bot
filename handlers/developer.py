from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import database as db
import keyboards as kb
from utils.average import calculate_average
from handlers.start import DEVELOPER_MODE, get_session_mode, is_developer_user, show_developer_home, show_teacher_home

router = Router()


class DeveloperStates(StatesGroup):
    selecting_teacher = State()
    selecting_class = State()
    selecting_student = State()


async def _ensure_developer_mode(message: types.Message, state: FSMContext) -> bool:
    if not is_developer_user(message.from_user.id):
        await show_teacher_home(message, state, clear_state=True)
        return False

    session_mode = await get_session_mode(state)
    if session_mode != DEVELOPER_MODE:
        await message.answer(
            "Сначала войдите как разработчик через /start или кнопку «Выбрать роль».",
            reply_markup=kb.get_main_menu(),
        )
        return False

    return True


def _format_teacher_button(teacher: dict) -> str:
    return f"{teacher['name']} [{teacher['telegram_id']}]"


def _format_student_button(student: dict) -> str:
    return f"{student['full_name']} [{student['student_id']}]"


async def _show_teachers(message: types.Message, state: FSMContext):
    teachers = db.get_all_teachers_overview()
    if not teachers:
        await message.answer("В базе пока нет ни одного учителя.", reply_markup=kb.get_developer_main_menu())
        return

    teacher_map = {_format_teacher_button(teacher): teacher["telegram_id"] for teacher in teachers}
    lines = ["Выберите учителя для просмотра данных:\n"]
    for teacher in teachers:
        lines.append(
            f"• {teacher['name']} ({teacher['telegram_id']}): "
            f"классов {teacher['class_count']}, учеников {teacher['student_count']}, оценок {teacher['grade_count']}"
        )

    await state.update_data(session_mode=DEVELOPER_MODE, developer_teacher_map=teacher_map)
    await message.answer(
        "\n".join(lines),
        reply_markup=kb.get_developer_teachers_keyboard(list(teacher_map.keys())),
    )
    await state.set_state(DeveloperStates.selecting_teacher)


async def _show_teacher_classes(message: types.Message, state: FSMContext, teacher_id: int):
    summary = db.get_teacher_summary(teacher_id)
    if not summary:
        await message.answer("Учитель не найден.", reply_markup=kb.get_developer_main_menu())
        await show_developer_home(message, state, clear_state=True)
        return

    classes = db.get_teacher_classes_overview(teacher_id)
    class_map = {class_info["name"]: class_info["name"] for class_info in classes}

    lines = [
        f"👨‍🏫 Учитель: {summary['name']}",
        f"ID: {summary['telegram_id']}",
        f"Классов: {summary['class_count']}",
        f"Учеников: {summary['student_count']}",
        f"Оценок: {summary['grade_count']}",
        "",
    ]

    if classes:
        lines.append("Классы:")
        for class_info in classes:
            lines.append(
                f"• {class_info['name']}: учеников {class_info['student_count']}, оценок {class_info['grade_count']}"
            )
        reply_markup = kb.get_developer_classes_keyboard(list(class_map.keys()))
    else:
        lines.append("У этого учителя пока нет классов.")
        reply_markup = kb.get_developer_main_menu()

    await state.update_data(
        session_mode=DEVELOPER_MODE,
        developer_selected_teacher_id=teacher_id,
        developer_selected_teacher_name=summary["name"],
        developer_class_map=class_map,
        developer_student_map={},
    )
    await message.answer("\n".join(lines), reply_markup=reply_markup)
    if classes:
        await state.set_state(DeveloperStates.selecting_class)
    else:
        await state.clear()
        await state.update_data(session_mode=DEVELOPER_MODE)


async def _show_class_students(message: types.Message, state: FSMContext, class_name: str):
    data = await state.get_data()
    teacher_id = data.get("developer_selected_teacher_id")
    teacher_name = data.get("developer_selected_teacher_name", "Неизвестный учитель")
    students = db.get_class_students_overview(class_name, teacher_id)
    student_map = {_format_student_button(student): student["student_id"] for student in students}

    lines = [
        f"🏫 Класс: {class_name}",
        f"Учитель: {teacher_name}",
        f"Учеников: {len(students)}",
        "",
    ]

    if students:
        lines.append("Ученики:")
        for student in students:
            avg_display = student["average"] if student["average"] is not None else "нет"
            lines.append(
                f"• {student['full_name']}: оценок {student['grade_count']}, средний балл {avg_display}"
            )
        reply_markup = kb.get_developer_students_keyboard(list(student_map.keys()))
    else:
        lines.append("В этом классе пока нет учеников.")
        reply_markup = kb.get_developer_classes_keyboard(list((await state.get_data()).get("developer_class_map", {}).keys()))

    await state.update_data(
        session_mode=DEVELOPER_MODE,
        developer_selected_class_name=class_name,
        developer_student_map=student_map,
    )
    await message.answer("\n".join(lines), reply_markup=reply_markup)
    await state.set_state(DeveloperStates.selecting_student)


@router.message(F.text == "📊 Общая статистика", StateFilter("*"))
async def show_system_summary(message: types.Message, state: FSMContext):
    if not await _ensure_developer_mode(message, state):
        return

    summary = db.get_system_summary()
    await state.clear()
    await state.update_data(session_mode=DEVELOPER_MODE)
    await message.answer(
        "\n".join(
            [
                "📊 Общая статистика системы",
                f"Учителей: {summary['teacher_count']}",
                f"Классов: {summary['class_count']}",
                f"Учеников: {summary['student_count']}",
                f"Оценок: {summary['grade_count']}",
            ]
        ),
        reply_markup=kb.get_developer_main_menu(),
    )


@router.message(F.text == "👨‍🏫 Учителя", StateFilter("*"))
async def start_teacher_browsing(message: types.Message, state: FSMContext):
    if not await _ensure_developer_mode(message, state):
        return

    await _show_teachers(message, state)


@router.message(DeveloperStates.selecting_teacher)
async def process_teacher_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await show_developer_home(message, state, clear_state=True)
        return

    if message.text == "🔙 Назад":
        await show_developer_home(message, state, clear_state=True)
        return

    if not await _ensure_developer_mode(message, state):
        return

    data = await state.get_data()
    teacher_map = data.get("developer_teacher_map", {})
    teacher_id = teacher_map.get(message.text)
    if not teacher_id:
        await message.answer("Пожалуйста, выберите учителя из списка.", reply_markup=kb.get_developer_teachers_keyboard(list(teacher_map.keys())))
        return

    await _show_teacher_classes(message, state, teacher_id)


@router.message(DeveloperStates.selecting_class)
async def process_class_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await show_developer_home(message, state, clear_state=True)
        return

    if message.text == "🔙 Назад":
        await _show_teachers(message, state)
        return

    if not await _ensure_developer_mode(message, state):
        return

    data = await state.get_data()
    class_map = data.get("developer_class_map", {})
    class_name = class_map.get(message.text)
    if not class_name:
        await message.answer("Пожалуйста, выберите класс из списка.", reply_markup=kb.get_developer_classes_keyboard(list(class_map.keys())))
        return

    await _show_class_students(message, state, class_name)


@router.message(DeveloperStates.selecting_student)
async def process_student_selection(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await show_developer_home(message, state, clear_state=True)
        return

    if message.text == "🔙 Назад":
        data = await state.get_data()
        teacher_id = data.get("developer_selected_teacher_id")
        if teacher_id:
            await _show_teacher_classes(message, state, teacher_id)
        else:
            await _show_teachers(message, state)
        return

    if not await _ensure_developer_mode(message, state):
        return

    data = await state.get_data()
    student_map = data.get("developer_student_map", {})
    student_id = student_map.get(message.text)
    if not student_id:
        await message.answer("Пожалуйста, выберите ученика из списка.", reply_markup=kb.get_developer_students_keyboard(list(student_map.keys())))
        return

    profile = db.get_student_profile_by_id(student_id)
    if not profile:
        await message.answer("Карточка ученика не найдена.")
        return

    lines = [
        f"👤 Ученик: {profile['full_name']}",
        f"Класс: {profile['class_name']}",
        f"Учитель: {profile['teacher_name']} ({profile['teacher_id']})",
        "",
    ]

    if not profile["grades"]:
        lines.append("Оценок пока нет.")
    else:
        total_grades = []
        lines.append("Оценки по предметам:")
        for subject, grades in profile["grades"].items():
            total_grades.extend(grades)
            avg = calculate_average(grades)
            lines.append(f"• {subject}: {', '.join(map(str, grades))} (средний: {avg})")
        overall_average = calculate_average(total_grades)
        lines.extend(["", f"Всего оценок: {len(total_grades)}", f"Общий средний балл: {overall_average}"])

    await message.answer(
        "\n".join(lines),
        reply_markup=kb.get_developer_students_keyboard(list(student_map.keys())),
    )
