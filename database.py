import sqlite3
from contextlib import contextmanager

DB_FILE = "journal.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database tables if they do not exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS teachers (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT
            );
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                teacher_id INTEGER,
                FOREIGN KEY (teacher_id) REFERENCES teachers (telegram_id)
            );
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                class_id INTEGER,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            );
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                class_id INTEGER,
                subject_id INTEGER,
                grade INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (class_id) REFERENCES classes (id),
                FOREIGN KEY (subject_id) REFERENCES subjects (id)
            );
        ''')

        cursor.execute("SELECT COUNT(*) FROM subjects")
        if cursor.fetchone()[0] == 0:
            default_subjects = [
                'Русский язык', 'Русская литература', 'Белорусский язык',
                'Белорусская литература', 'Математика', 'ИЗО', 'Музыка',
                'Трудовое обучение', 'Физкультура', 'ОБЖ',
                'Иностранный язык', 'Биология', 'География', 'Физика',
                'Химия', 'Всемирная история', 'История Беларуси',
                'Обществоведение', 'Информатика', 'Искусство', 'Астрономия'
            ]
            cursor.executemany("INSERT INTO subjects (name) VALUES (?)", [(s,) for s in default_subjects])
        conn.commit()

# --- Teacher Management ---

def register_teacher(telegram_id, name):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO teachers (telegram_id, name)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET name = excluded.name
            """,
            (telegram_id, name),
        )
        conn.commit()
    return True

# --- Data Query Helpers ---

def format_student_name(first_name: str, last_name: str) -> str:
    return " ".join(part.strip() for part in (first_name, last_name) if part and part.strip())

def add_class(name: str, teacher_id: int):
    normalized_name = name.strip()
    if not normalized_name:
        return False

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM classes WHERE teacher_id = ? AND lower(name) = lower(?)",
            (teacher_id, normalized_name),
        )
        if c.fetchone():
            return False

        c.execute("INSERT INTO classes (name, teacher_id) VALUES (?, ?)", (normalized_name, teacher_id))
        conn.commit()
    return True

def get_all_classes(teacher_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM classes WHERE teacher_id = ? ORDER BY name COLLATE NOCASE", (teacher_id,))
        return [row[0] for row in c.fetchall()]

def get_all_teachers_overview():
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                t.telegram_id,
                t.name,
                COUNT(DISTINCT c.id) AS class_count,
                COUNT(DISTINCT s.id) AS student_count,
                COUNT(g.id) AS grade_count
            FROM teachers t
            LEFT JOIN classes c ON c.teacher_id = t.telegram_id
            LEFT JOIN students s ON s.class_id = c.id
            LEFT JOIN grades g ON g.student_id = s.id
            GROUP BY t.telegram_id, t.name
            ORDER BY t.name COLLATE NOCASE, t.telegram_id
            """
        )
        return [
            {
                "telegram_id": row[0],
                "name": row[1],
                "class_count": row[2],
                "student_count": row[3],
                "grade_count": row[4],
            }
            for row in c.fetchall()
        ]

def get_all_subjects():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM subjects")
        return [row[0] for row in c.fetchall()]

def get_class_id_by_name(name: str, teacher_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM classes WHERE name = ? AND teacher_id = ?", (name, teacher_id))
        row = c.fetchone()
        return row[0] if row else None

def get_teacher_summary(teacher_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                t.telegram_id,
                t.name,
                COUNT(DISTINCT c.id) AS class_count,
                COUNT(DISTINCT s.id) AS student_count,
                COUNT(g.id) AS grade_count
            FROM teachers t
            LEFT JOIN classes c ON c.teacher_id = t.telegram_id
            LEFT JOIN students s ON s.class_id = c.id
            LEFT JOIN grades g ON g.student_id = s.id
            WHERE t.telegram_id = ?
            GROUP BY t.telegram_id, t.name
            """,
            (teacher_id,),
        )
        row = c.fetchone()

    if not row:
        return None

    return {
        "telegram_id": row[0],
        "name": row[1],
        "class_count": row[2],
        "student_count": row[3],
        "grade_count": row[4],
    }

def get_subject_id_by_name(name: str):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM subjects WHERE name = ?", (name,))
        row = c.fetchone()
        return row[0] if row else None
    
def get_students_by_class(class_name: str, teacher_id: int):
    class_id = get_class_id_by_name(class_name, teacher_id)
    if not class_id:
        return []
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id, first_name, last_name
            FROM students
            WHERE class_id = ?
            ORDER BY first_name COLLATE NOCASE, last_name COLLATE NOCASE
            """,
            (class_id,),
        )
        return c.fetchall()

def get_teacher_classes_overview(teacher_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                c.id,
                c.name,
                COUNT(DISTINCT s.id) AS student_count,
                COUNT(g.id) AS grade_count
            FROM classes c
            LEFT JOIN students s ON s.class_id = c.id
            LEFT JOIN grades g ON g.class_id = c.id
            WHERE c.teacher_id = ?
            GROUP BY c.id, c.name
            ORDER BY c.name COLLATE NOCASE
            """,
            (teacher_id,),
        )
        return [
            {
                "class_id": row[0],
                "name": row[1],
                "student_count": row[2],
                "grade_count": row[3],
            }
            for row in c.fetchall()
        ]
    
def add_student(first_name: str, last_name: str, class_name: str, teacher_id: int):
    class_id = get_class_id_by_name(class_name, teacher_id)
    if not class_id:
        return False

    normalized_first = first_name.strip()
    normalized_last = last_name.strip()
    if not normalized_first or not normalized_last:
        return False

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT 1
            FROM students
            WHERE class_id = ?
            AND (
                (lower(first_name) = lower(?) AND lower(last_name) = lower(?))
                OR
                (lower(first_name) = lower(?) AND lower(last_name) = lower(?))
            )
            """,
            (class_id, normalized_first, normalized_last, normalized_last, normalized_first),
        )
        if c.fetchone():
            return False

        c.execute(
            "INSERT INTO students (first_name, last_name, class_id) VALUES (?, ?, ?)",
            (normalized_first, normalized_last, class_id),
        )
        conn.commit()
    return True
    
def save_grade(student_first: str, student_last: str, class_name: str, subject_name: str, grade: int, teacher_id: int):
    class_id = get_class_id_by_name(class_name, teacher_id)
    subject_id = get_subject_id_by_name(subject_name)
    if not class_id or not subject_id:
        return False
        
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id FROM students 
            WHERE ((first_name = ? AND last_name = ?) OR (first_name = ? AND last_name = ?)) 
            AND class_id = ?
        """, (student_first, student_last, student_last, student_first, class_id))
        row = c.fetchone()
        
        if not row:
            return False
            
        student_id = row[0]
        c.execute("INSERT INTO grades (student_id, class_id, subject_id, grade) VALUES (?, ?, ?, ?)",
                 (student_id, class_id, subject_id, grade))
        conn.commit()
    return True
    
def get_student_grades(student_first: str, student_last: str, class_name: str, teacher_id: int):
    class_id = get_class_id_by_name(class_name, teacher_id)
    if not class_id:
        return None

    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id FROM students 
            WHERE ((first_name = ? AND last_name = ?) OR (first_name = ? AND last_name = ?)) 
            AND class_id = ?
        """, (student_first, student_last, student_last, student_first, class_id))
        row = c.fetchone()
        
        if not row:
            return None
            
        student_id = row[0]
        query = '''
            SELECT s.name as subject_name, g.grade 
            FROM grades g 
            JOIN subjects s ON g.subject_id = s.id 
            WHERE g.student_id = ?
        '''
        c.execute(query, (student_id,))
        rows = c.fetchall()
    
    grades_by_subject = {}
    for subject_name, grade in rows:
        grades_by_subject.setdefault(subject_name, []).append(grade)
        
    return grades_by_subject
    
def find_student_approx(name_query: str, class_name: str, teacher_id: int):
    """Найти студента в классе, используя примерное совпадение."""
    class_id = get_class_id_by_name(class_name, teacher_id)
    if not class_id:
        return None
        
    parts = name_query.lower().strip().split()
    if not parts:
        return None
        
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT first_name, last_name FROM students WHERE class_id = ?", (class_id,))
        students = c.fetchall()
    
    for fn, ln in students:
        fn_l, ln_l = fn.lower(), ln.lower()
        if len(parts) == 1:
            if parts[0] in (fn_l, ln_l):
                return (fn, ln)
        elif len(parts) >= 2:
            p1, p2 = parts[0], parts[1]
            if (p1 == fn_l and p2 == ln_l) or (p1 == ln_l and p2 == fn_l):
                return (fn, ln)
                
    return None

def get_class_grades(class_name: str, subject_name: str, teacher_id: int):
    """Получить все оценки для всех учеников класса по конкретному предмету."""
    class_id = get_class_id_by_name(class_name, teacher_id)
    subject_id = get_subject_id_by_name(subject_name)
    if not class_id or not subject_id:
        return []
    
    with get_db() as conn:
        c = conn.cursor()
        query = '''
            SELECT s.id, s.first_name, s.last_name, g.grade
            FROM students s
            LEFT JOIN grades g ON s.id = g.student_id AND g.subject_id = ?
            WHERE s.class_id = ?
            ORDER BY s.first_name COLLATE NOCASE, s.last_name COLLATE NOCASE, g.created_at
        '''
        c.execute(query, (subject_id, class_id))
        rows = c.fetchall()
    
    res_map = {}
    for sid, fn, ln, grade in rows:
        full_name = format_student_name(fn, ln)
        if full_name not in res_map:
            res_map[full_name] = []
        if grade is not None:
            res_map[full_name].append(grade)
            
    return [{'full_name': name, 'grades': gp} for name, gp in res_map.items()]

def get_class_students_overview(class_name: str, teacher_id: int):
    class_id = get_class_id_by_name(class_name, teacher_id)
    if not class_id:
        return []

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                COUNT(g.id) AS grade_count,
                AVG(g.grade) AS avg_grade
            FROM students s
            LEFT JOIN grades g ON g.student_id = s.id
            WHERE s.class_id = ?
            GROUP BY s.id, s.first_name, s.last_name
            ORDER BY s.first_name COLLATE NOCASE, s.last_name COLLATE NOCASE
            """,
            (class_id,),
        )
        return [
            {
                "student_id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "full_name": format_student_name(row[1], row[2]),
                "grade_count": row[3],
                "average": round(row[4], 2) if row[4] is not None else None,
            }
            for row in c.fetchall()
        ]

def get_student_profile_by_id(student_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                c.name,
                t.telegram_id,
                t.name
            FROM students s
            JOIN classes c ON c.id = s.class_id
            JOIN teachers t ON t.telegram_id = c.teacher_id
            WHERE s.id = ?
            """,
            (student_id,),
        )
        row = c.fetchone()
        if not row:
            return None

        c.execute(
            """
            SELECT sub.name, g.grade
            FROM grades g
            JOIN subjects sub ON sub.id = g.subject_id
            WHERE g.student_id = ?
            ORDER BY sub.name COLLATE NOCASE, g.created_at
            """,
            (student_id,),
        )
        grades_rows = c.fetchall()

    grades_by_subject = {}
    for subject_name, grade in grades_rows:
        grades_by_subject.setdefault(subject_name, []).append(grade)

    return {
        "student_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "full_name": format_student_name(row[1], row[2]),
        "class_name": row[3],
        "teacher_id": row[4],
        "teacher_name": row[5],
        "grades": grades_by_subject,
    }

def get_system_summary():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM teachers")
        teacher_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM classes")
        class_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM students")
        student_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM grades")
        grade_count = c.fetchone()[0]

    return {
        "teacher_count": teacher_count,
        "class_count": class_count,
        "student_count": student_count,
        "grade_count": grade_count,
    }
