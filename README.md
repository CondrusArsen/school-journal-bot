# School Journal Bot

A Telegram bot for class teachers to manage classes, students, grades, and progress reports from chat.

The project is built with Python, `aiogram`, and SQLite. It focuses on fast day-to-day teacher workflows such as creating classes, adding students, entering grades in multiple formats, generating summary reports, and exporting grade sheets to Excel.

## What the Bot Does

- registers teachers automatically on first launch
- creates and stores classes in SQLite
- adds students to specific classes
- records grades by subject
- supports three grade entry modes:
  - sequential entry by student list
  - entry for one selected student
  - bulk text or voice-based parsing
- generates class reports in:
  - text format
  - Excel format
- shows student performance summaries
- generates structured student feedback reports
- supports a developer mode for system inspection
- can temporarily disable the bot for regular users through middleware

## Main Features

### Teacher Workflow

- `/start` onboarding
- create the first class if the teacher has none yet
- open the main menu
- choose a class
- add students
- choose a subject
- enter grades
- review class and student performance

### Grade Entry Modes

The bot supports several real-world workflows for entering grades:

1. **By student list**
   - open a class
   - choose a subject
   - go through students one by one
   - add grades using buttons or voice

2. **For one selected student**
   - choose a specific student first
   - enter only their grades

3. **Bulk input**
   - send one text message like:
     ```text
     Ivanov 5 4 Petrov 3
     ```
   - or send a voice message
   - the parser matches students and grades before confirmation

### Reporting

- class grade sheet in Telegram text
- Excel export for a class and subject
- student performance summary
- generated student feedback report with:
  - behavior
  - diligence
  - recommendation
  - focus subjects
  - optional teacher comment

### Developer Mode

If `DEVELOPER_ID` matches the Telegram user ID, the bot allows switching between:

- teacher mode
- developer mode

Developer mode lets you inspect:

- teachers
- classes
- students
- grade data
- overall system summary

## Tech Stack

- Python 3.11+
- aiogram
- SQLite
- python-dotenv
- openpyxl
- SpeechRecognition
- pydub
- static-ffmpeg

## Project Structure

```text
school_journal_bot/
|-- bot.py                    # Application entry point
|-- config.py                 # Environment configuration
|-- database.py               # SQLite schema and data access
|-- grade_parser.py           # Bulk text grade parsing
|-- keyboards.py              # Telegram keyboards
|-- requirements.txt          # Python dependencies
|-- handlers/
|   |-- start.py              # Onboarding and role switching
|   |-- grades.py             # Grade entry flows
|   |-- students.py           # Class and student management
|   |-- reports.py            # Text and Excel reports
|   |-- support.py            # Contact developer flow
|   `-- developer.py          # Developer inspection tools
|-- utils/
|   |-- average.py            # Average calculation helpers
|   |-- excel_export.py       # Excel report generation
|   |-- ai_reporter.py        # Student feedback report builder
|   |-- middleware.py         # Activation middleware
|   `-- speech_to_text.py     # Voice to text helper
`-- tests/
    `-- test_bot_flows.py     # Bot flow tests
```

## Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

CMD:

```bat
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the environment file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

### 5. Fill in `.env`

Required variables:

```env
BOT_TOKEN=your_telegram_bot_token
DEVELOPER_ID=your_telegram_user_id
BOT_ENABLED=True
```

## Run Commands

### Start the bot

```bash
python bot.py
```

### Run tests

```bash
python -m unittest discover -s tests
```

### Optional Windows helper scripts

Run the bot:

```bat
run_bot.bat
```

Run hidden:

```bat
start_bot_hidden.vbs
```

Stop the bot:

```bat
stop_bot.bat
```

## Bot Usage Commands and Flows

### Telegram command

```text
/start
```

### Main menu actions

After onboarding, the teacher can use the menu to:

- enter grades
- open the class list
- generate a grade sheet
- contact the developer

### Example bulk input

```text
Ivanov 5 4 Petrov 3
```

### Example grade flow

1. Start the bot with `/start`
2. Create a class such as `7A`
3. Add students
4. Select a subject
5. Choose a grade entry mode
6. Save grades
7. Generate a text or Excel report

## Notes

- The bot interface is currently oriented toward Russian-speaking teachers and schools.
- SQLite databases are created locally and automatically.
- Voice recognition depends on the local speech stack and FFmpeg-related tooling.
- Default subjects are preloaded during database initialization.

## Testing

The project includes automated flow tests for:

- onboarding
- duplicate class protection
- developer mode
- class management
- sequential grade entry
- bulk grade parsing
- report generation
- support flow
- voice input error handling
- activation middleware behavior

Run them with:

```bash
python -m unittest discover -s tests
```

## Repository Checklist

This repository is prepared to exclude local-only files such as:

- virtual environments
- SQLite databases
- logs
- cache files
- temporary voice files
- `.env`

## Author

Arseniy Atrokhov
