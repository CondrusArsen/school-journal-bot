import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import config
import database as db
import keyboards as kb
from handlers import developer, grades, reports, start, students, support
from utils.middleware import ActivationMiddleware


class MockUser:
    def __init__(self, user_id: int, full_name: str, username: str = "teacher"):
        self.id = user_id
        self.full_name = full_name
        self.username = username


class MockChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class MockVoice:
    def __init__(self, file_id: str = "voice-file"):
        self.file_id = file_id


class MockSentMessage:
    def __init__(self):
        self.edit_text = AsyncMock()
        self.edit_reply_markup = AsyncMock()
        self.delete = AsyncMock()
        self.answer = AsyncMock(side_effect=self._answer)

    async def _answer(self, *args, **kwargs):
        return MockSentMessage()


def build_mock_bot():
    bot = SimpleNamespace()
    bot.get_file = AsyncMock(return_value=SimpleNamespace(file_path="voice/test.oga"))

    async def download_file(_source_path, destination_path):
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"voice")

    bot.download_file = AsyncMock(side_effect=download_file)
    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


class MockMessage:
    def __init__(self, text=None, user_id: int = 123, full_name: str = "Teacher Test", username: str = "teacher", voice=None):
        self.text = text
        self.voice = voice
        self.from_user = MockUser(user_id, full_name, username=username)
        self.chat = MockChat(user_id)
        self.bot = build_mock_bot()
        self.answer = AsyncMock(side_effect=self._answer)

    async def _answer(self, *args, **kwargs):
        return MockSentMessage()


class MockCallback:
    def __init__(self, data: str, user_id: int = 123, message=None):
        self.data = data
        self.from_user = MockUser(user_id, "Teacher Test")
        self.message = message or MockSentMessage()
        self.answer = AsyncMock()


class MockState:
    def __init__(self):
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def get_state(self):
        return self.state.state if self.state else None

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.state = None
        self.data = {}


def last_answer_text(message) -> str:
    return message.answer.await_args_list[-1].args[0]


def first_answer_text(message) -> str:
    return message.answer.await_args_list[0].args[0]


class BotFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        file_descriptor, db_path = tempfile.mkstemp(
            dir=os.getcwd(),
            prefix="test_journal_",
            suffix=".db",
        )
        os.close(file_descriptor)
        os.remove(db_path)

        self.test_db_path = db_path
        self.previous_db_file = db.DB_FILE
        db.DB_FILE = self.test_db_path
        db.init_db()

    def tearDown(self):
        db.DB_FILE = self.previous_db_file
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def bootstrap_class(self, teacher_id: int = 123, class_name: str = "10A"):
        db.register_teacher(teacher_id, "Teacher Test")
        self.assertTrue(db.add_class(class_name, teacher_id))

    def add_student(self, class_name: str, full_name: str, teacher_id: int = 123):
        first_name, last_name = full_name.split(maxsplit=1)
        self.assertTrue(db.add_student(first_name, last_name, class_name, teacher_id))

    async def test_onboarding_and_duplicate_class_protection(self):
        state = MockState()

        start_message = MockMessage("/start")
        await start.cmd_start_command(start_message, state)

        self.assertIs(state.state, start.ClassStates.waiting_for_class_name)
        self.assertIn("Введите название вашего первого класса", last_answer_text(start_message))

        create_message = MockMessage("10A")
        await start.process_new_class(create_message, state)
        self.assertEqual(db.get_all_classes(123), ["10A"])

        duplicate_start = MockMessage("➕ Добавить класс")
        await start.add_class_start(duplicate_start, state)
        duplicate_message = MockMessage("10A")
        await start.process_new_class(duplicate_message, state)

        self.assertIn("уже существует", last_answer_text(duplicate_message).lower())
        self.assertEqual(db.get_all_classes(123), ["10A"])

    async def test_developer_start_prompts_for_role_selection(self):
        state = MockState()

        with patch.object(config, "DEVELOPER_ID", "999"):
            start_message = MockMessage("/start", user_id=999, full_name="Dev User", username="dev")
            await start.cmd_start_command(start_message, state)

        self.assertIs(state.state, start.StartStates.selecting_session_mode)
        self.assertEqual(last_answer_text(start_message), "Выберите режим входа:")

    async def test_developer_mode_can_browse_teachers_classes_and_students(self):
        db.register_teacher(123, "Teacher One")
        db.add_class("10A", 123)
        db.add_student("Иванов", "Иван", "10A", 123)
        db.save_grade("Иванов", "Иван", "10A", "Математика", 9, 123)
        db.save_grade("Иванов", "Иван", "10A", "Русский язык", 8, 123)

        state = MockState()

        with patch.object(config, "DEVELOPER_ID", "999"):
            await state.set_state(start.StartStates.selecting_session_mode)
            role_message = MockMessage("🛠️ Войти как разработчик", user_id=999, full_name="Dev User", username="dev")
            await start.process_session_mode_selection(role_message, state)

            self.assertEqual((await state.get_data())["session_mode"], start.DEVELOPER_MODE)
            self.assertEqual(last_answer_text(role_message), "Меню разработчика")

            teachers_message = MockMessage("👨‍🏫 Учителя", user_id=999, full_name="Dev User", username="dev")
            await developer.start_teacher_browsing(teachers_message, state)
            self.assertIs(state.state, developer.DeveloperStates.selecting_teacher)
            self.assertIn("Teacher One", last_answer_text(teachers_message))

            teacher_selection = MockMessage("Teacher One [123]", user_id=999, full_name="Dev User", username="dev")
            await developer.process_teacher_selection(teacher_selection, state)
            self.assertIs(state.state, developer.DeveloperStates.selecting_class)
            self.assertIn("Классы:", last_answer_text(teacher_selection))
            self.assertIn("10A", last_answer_text(teacher_selection))

            class_selection = MockMessage("10A", user_id=999, full_name="Dev User", username="dev")
            await developer.process_class_selection(class_selection, state)
            self.assertIs(state.state, developer.DeveloperStates.selecting_student)
            self.assertIn("Иванов Иван", last_answer_text(class_selection))

            student_id = db.get_class_students_overview("10A", 123)[0]["student_id"]
            student_selection = MockMessage(f"Иванов Иван [{student_id}]", user_id=999, full_name="Dev User", username="dev")
            await developer.process_student_selection(student_selection, state)
            self.assertIn("Математика: 9", last_answer_text(student_selection))
            self.assertIn("Русский язык: 8", last_answer_text(student_selection))

    async def test_class_management_keeps_student_names_in_consistent_order(self):
        self.bootstrap_class()
        state = MockState()
        await state.update_data(active_class="10A")

        invalid_message = MockMessage("Иванов")
        await students.add_student_process(invalid_message, state)
        self.assertIn("фамилию и имя", last_answer_text(invalid_message).lower())

        add_message = MockMessage("Иванов Иван")
        await students.add_student_process(add_message, state)

        stored_students = db.get_students_by_class("10A", 123)
        self.assertEqual([db.format_student_name(fn, ln) for _, fn, ln in stored_students], ["Иванов Иван"])
        self.assertIn("Иванов Иван", last_answer_text(add_message))

        class_view_message = MockMessage("view")
        await students.show_class_view(class_view_message, state)
        self.assertIn("Иванов Иван", last_answer_text(class_view_message))

        student_keyboard = kb.get_students_keyboard(stored_students)
        self.assertEqual(student_keyboard.keyboard[0][0].text, "Иванов Иван")

        duplicate_message = MockMessage("Иванов Иван")
        await students.add_student_process(duplicate_message, state)
        self.assertIn("уже есть", first_answer_text(duplicate_message).lower())

    async def test_specific_student_flow_only_saves_for_the_selected_student(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        self.add_student("10A", "Петров Петр")

        state = MockState()
        await state.update_data(active_class="10A", active_subject="Математика")

        choose_mode_message = MockMessage("👤 Выбор ученика")
        await grades.process_entry_mode_selection(choose_mode_message, state)
        self.assertIs(state.state, grades.GradeStates.selecting_specific_student)

        student_message = MockMessage("Иванов Иван")
        await grades.process_specific_student_selection(student_message, state)

        data = await state.get_data()
        self.assertEqual(len(data["students"]), 1)
        self.assertEqual(db.format_student_name(data["students"][0][1], data["students"][0][2]), "Иванов Иван")

        await grades.process_sequential_grade_entry(MockMessage("5"), state)
        finish_message = MockMessage("✅ Готово / Следующий")
        await grades.process_sequential_grade_entry(finish_message, state)

        self.assertIsNone(state.state)
        self.assertEqual(db.get_student_grades("Иванов", "Иван", "10A", 123)["Математика"], [5])
        self.assertEqual(db.get_student_grades("Петров", "Петр", "10A", 123), {})

    async def test_home_menu_works_from_grade_subject_selection(self):
        self.bootstrap_class()

        state = MockState()
        await state.update_data(active_class="10A")
        await state.set_state(grades.GradeStates.selecting_subject)

        home_message = MockMessage("🏠 Главное меню")
        await grades.process_subject_selection(home_message, state)

        self.assertIsNone(state.state)
        self.assertEqual(last_answer_text(home_message), "Главное меню")

    async def test_home_menu_works_from_grade_entry_mode_selection(self):
        self.bootstrap_class()

        state = MockState()
        await state.update_data(active_class="10A", active_subject="Математика")
        await state.set_state(grades.GradeStates.selecting_entry_mode)

        home_message = MockMessage("🏠 Главное меню")
        await grades.process_entry_mode_selection(home_message, state)

        self.assertIsNone(state.state)
        self.assertEqual(last_answer_text(home_message), "Главное меню")

    async def test_sequential_editing_and_inline_grade_deletion(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        students_list = db.get_students_by_class("10A", 123)

        state = MockState()
        await state.update_data(
            active_class="10A",
            active_subject="Математика",
            students=students_list,
            current_student_index=0,
            current_student_grades=[],
        )

        await grades.process_sequential_grade_entry(MockMessage("5"), state)
        await grades.process_sequential_grade_entry(MockMessage("6"), state)

        edit_message = MockMessage("✏️ Редактировать")
        await grades.process_sequential_grade_entry(edit_message, state)
        self.assertIn("Редактирование оценок", last_answer_text(edit_message))

        delete_callback = MockCallback("del_grade_0")
        await grades.delete_grade_callback(delete_callback, state)
        self.assertEqual((await state.get_data())["current_student_grades"], [6])

        stop_callback = MockCallback("stop_editing")
        await grades.stop_editing_callback(stop_callback, state)
        self.assertIn("6", stop_callback.message.edit_text.await_args.args[0])

        finish_message = MockMessage("✅ Готово / Следующий")
        await grades.process_sequential_grade_entry(finish_message, state)

        self.assertEqual(db.get_student_grades("Иванов", "Иван", "10A", 123)["Математика"], [6])

    async def test_bulk_input_confirm_and_cancel_paths(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        self.add_student("10A", "Петров Петр")

        state = MockState()
        await state.update_data(active_class="10A", active_subject="Математика")

        bulk_message = MockMessage("Иванов 5 4 Петров 3")
        await grades.process_grades_input(bulk_message, state)

        self.assertIn("Распознано", last_answer_text(bulk_message))
        confirm_callback = MockCallback("confirm_grades")
        await grades.confirm_grades_callback(confirm_callback, state)

        self.assertEqual(db.get_student_grades("Иванов", "Иван", "10A", 123)["Математика"], [5, 4])
        self.assertEqual(db.get_student_grades("Петров", "Петр", "10A", 123)["Математика"], [3])

        cancel_state = MockState()
        await cancel_state.update_data(active_class="10A", active_subject="Математика")
        cancel_message = MockMessage("Иванов 2")
        await grades.process_grades_input(cancel_message, cancel_state)

        cancel_callback = MockCallback("cancel_grades")
        await grades.cancel_grades_callback(cancel_callback, cancel_state)
        self.assertEqual(db.get_student_grades("Иванов", "Иван", "10A", 123)["Математика"], [5, 4])

    async def test_text_and_excel_reports(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        db.save_grade("Иванов", "Иван", "10A", "Математика", 8, 123)
        db.save_grade("Иванов", "Иван", "10A", "Математика", 10, 123)

        state = MockState()
        await reports.process_report_class(MockMessage("10A"), state)
        await reports.process_report_subject(MockMessage("Математика"), state)

        text_report_message = MockMessage("📄 Текстовый отчет")
        await reports.process_report_format(text_report_message, state)
        self.assertIn("Иванов Иван", last_answer_text(text_report_message))
        self.assertIn("Математика", last_answer_text(text_report_message))

        excel_state = MockState()
        await excel_state.update_data(active_class="10A", active_subject="Математика")
        excel_message = MockMessage("excel файл")
        await reports.process_report_format(excel_message, excel_state)

        self.assertTrue(excel_message.bot.send_document.await_count == 1)

    async def test_report_flow_does_not_jump_back_to_class_selection(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        db.save_grade("Иванов", "Иван", "10A", "Математика", 9, 123)

        state = MockState()
        start_message = MockMessage("📊 Ведомость оценок")
        await reports.start_report_flow(start_message, state)
        self.assertIs(state.state, reports.ReportStates.selecting_class)

        class_message = MockMessage("10A")
        await reports.process_report_class(class_message, state)
        self.assertIs(state.state, reports.ReportStates.selecting_subject)
        self.assertIn("Теперь выберите предмет", last_answer_text(class_message))

        subject_message = MockMessage("Математика")
        await reports.process_report_subject(subject_message, state)
        self.assertIs(state.state, reports.ReportStates.selecting_format)
        self.assertEqual(last_answer_text(subject_message), "Выберите формат отчета:")

        format_message = MockMessage("📄 Текстовый отчет")
        await reports.process_report_format(format_message, state)
        self.assertIn("Иванов Иван", last_answer_text(format_message))
        self.assertNotIn("выберите класс", last_answer_text(format_message).lower())

    async def test_ai_report_flow_with_focus_subjects_and_teacher_comment(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        db.save_grade("Иванов", "Иван", "10A", "Математика", 7, 123)

        state = MockState()
        await state.update_data(active_class="10A", current_student=("Иванов", "Иван"))

        await students.request_behavior(MockMessage("📊 Сгенерировать отчет"), state)
        self.assertIs(state.state, students.ClassManagementStates.selecting_behavior)

        await students.request_diligence(MockMessage("👍 Отличное"), state)
        self.assertIs(state.state, students.ClassManagementStates.selecting_diligence)

        await students.request_recommendation(MockMessage("💪 Усидчивый"), state)
        self.assertIs(state.state, students.ClassManagementStates.selecting_recommendation)

        recommendation_message = MockMessage("📈 Подтянуть слабые места")
        await students.request_focus_subjects(recommendation_message, state)
        self.assertIs(state.state, students.ClassManagementStates.selecting_focus_subjects)
        self.assertEqual((await state.get_data())["all_subjects_for_focus"], ["Математика"])

        focus_callback = MockCallback("focus_sub_Математика")
        await students.process_focus_subject_selection(focus_callback, state)
        self.assertIn("Математика", (await state.get_data())["focus_subjects"])

        done_callback = MockCallback("focus_sub_done")
        await students.process_focus_subject_selection(done_callback, state)
        self.assertIs(state.state, students.ClassManagementStates.waiting_for_voice_choice)
        self.assertTrue(done_callback.answer.await_count == 1)

        invalid_choice = MockMessage("Что-то еще")
        await students.process_voice_choice(invalid_choice, state)
        self.assertIn("используйте кнопки", last_answer_text(invalid_choice).lower())

        text_choice = MockMessage("⌨️ Написать текст")
        await students.process_voice_choice(text_choice, state)
        self.assertIs(state.state, students.ClassManagementStates.waiting_for_comment)

        comment_message = MockMessage("сильный прогресс")
        await students.handle_teacher_comment(comment_message, state)
        self.assertIn("ИВАНОВ ИВАН", last_answer_text(comment_message))
        self.assertIn("Сильный прогресс.", last_answer_text(comment_message))
        self.assertIsNone(state.state)

    async def test_generate_report_button_keeps_student_report_context(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")
        db.save_grade("Иванов", "Иван", "10A", "Математика", 8, 123)

        state = MockState()
        await state.update_data(active_class="10A")

        start_message = MockMessage("👤 Успеваемость ученика")
        await students.report_start(start_message, state)
        self.assertIs(state.state, students.ClassManagementStates.viewing_report)

        student_message = MockMessage("Иванов Иван")
        await students.report_process(student_message, state)
        self.assertIs(state.state, students.ClassManagementStates.viewing_report)
        self.assertIn("Успеваемость", last_answer_text(student_message))

        generate_message = MockMessage("📊 Сгенерировать отчет")
        await students.request_behavior(generate_message, state)
        self.assertIs(state.state, students.ClassManagementStates.selecting_behavior)
        self.assertEqual(last_answer_text(generate_message), "Выберите характеристику поведения ученика:")

    async def test_support_flow_cancel_and_send(self):
        state = MockState()
        await state.set_state(grades.GradeStates.selecting_class)

        prompt_message = MockMessage("💬 Написать разработчику")
        await support.contact_developer_prompt(prompt_message, state)
        self.assertIs(state.state, support.SupportStates.waiting_for_message)

        cancel_message = MockMessage("🔙 Отмена")
        await support.process_support_message(cancel_message, state, build_mock_bot())
        self.assertIsNone(state.state)
        self.assertIn("отменена", last_answer_text(cancel_message).lower())

        await state.set_state(grades.GradeStates.selecting_class)
        send_prompt_message = MockMessage("💬 Написать разработчику")
        await support.contact_developer_prompt(send_prompt_message, state)

        support_bot = build_mock_bot()
        with patch.object(config, "DEVELOPER_ID", "999"):
            send_message = MockMessage("Нужна помощь")
            await support.process_support_message(send_message, state, support_bot)

        self.assertTrue(support_bot.send_message.await_count == 1)
        forwarded_text = support_bot.send_message.await_args.kwargs["text"]
        self.assertIn("Экран/Состояние", forwarded_text)

    async def test_voice_errors_are_handled_for_bulk_input_and_comments(self):
        self.bootstrap_class()
        self.add_student("10A", "Иванов Иван")

        bulk_state = MockState()
        await bulk_state.update_data(active_class="10A", active_subject="Математика")
        with patch("handlers.grades.convert_voice_to_text", AsyncMock(return_value="ERROR_UNINTELLIGIBLE")):
            voice_message = MockMessage(user_id=123, voice=MockVoice())
            await grades.process_grades_input(voice_message, bulk_state)
        self.assertIn("Речь неразборчива", last_answer_text(voice_message))

        comment_state = MockState()
        await comment_state.set_state(students.ClassManagementStates.waiting_for_comment)
        await comment_state.update_data(active_class="10A", current_student=("Иванов", "Иван"))
        with patch("utils.speech_to_text.convert_voice_to_text", AsyncMock(return_value="ERROR_UNINTELLIGIBLE")):
            voice_comment_message = MockMessage(user_id=123, voice=MockVoice("comment-voice"))
            await students.handle_teacher_comment(voice_comment_message, comment_state)
        self.assertIn("Не удалось распознать голос", last_answer_text(voice_comment_message))
        self.assertIs(comment_state.state, students.ClassManagementStates.waiting_for_comment)

    async def test_activation_middleware_blocks_non_developer_when_disabled(self):
        middleware = ActivationMiddleware()
        blocked_message = MockMessage("Привет", user_id=111)
        allowed_message = MockMessage("Привет", user_id=222)
        handler = AsyncMock(return_value="ok")

        with patch("utils.middleware.types.Message", MockMessage), patch.object(config, "BOT_ENABLED", False), patch.object(config, "DEVELOPER_ID", "999"):
            result = await middleware(handler, blocked_message, {})
        self.assertIsNone(result)
        self.assertIn("не включен", last_answer_text(blocked_message).lower())
        self.assertEqual(handler.await_count, 0)

        with patch("utils.middleware.types.Message", MockMessage), patch.object(config, "BOT_ENABLED", False), patch.object(config, "DEVELOPER_ID", "222"):
            result = await middleware(handler, allowed_message, {})
        self.assertEqual(result, "ok")
        self.assertEqual(handler.await_count, 1)
