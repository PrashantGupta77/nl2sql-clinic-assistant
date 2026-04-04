import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

DB_NAME = "clinic.db"

fake = Faker()
Faker.seed(42)
random.seed(42)

SPECIALIZATIONS = [
    ("Dermatology", "Skin Care"),
    ("Cardiology", "Heart Center"),
    ("Orthopedics", "Bone & Joint"),
    ("General", "Primary Care"),
    ("Pediatrics", "Child Care"),
]

CITIES = [
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Lucknow",
]

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]

TARGET_DOCTORS = 15
TARGET_PATIENTS = 200
TARGET_APPOINTMENTS = 500
TARGET_TREATMENTS = 350
TARGET_INVOICES = 300


def random_datetime_within_last_12_months() -> datetime:
    now = datetime.now()
    start = now - timedelta(days=365)
    delta_seconds = int((now - start).total_seconds())
    chosen = start + timedelta(seconds=random.randint(0, delta_seconds))
    return chosen.replace(
        hour=random.randint(9, 18),
        minute=random.choice([0, 15, 30, 45]),
        second=0,
        microsecond=0,
    )


def random_date_within_last_12_months() -> str:
    return random_datetime_within_last_12_months().date().isoformat()


def connect_db() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    return conn, cursor


def drop_tables(cursor: sqlite3.Cursor) -> None:
    cursor.executescript("""
    DROP TABLE IF EXISTS treatments;
    DROP TABLE IF EXISTS appointments;
    DROP TABLE IF EXISTS invoices;
    DROP TABLE IF EXISTS doctors;
    DROP TABLE IF EXISTS patients;
    """)


def create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.executescript("""
    CREATE TABLE patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        date_of_birth DATE,
        gender TEXT,
        city TEXT,
        registered_date DATE
    );

    CREATE TABLE doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT,
        department TEXT,
        phone TEXT
    );

    CREATE TABLE appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        appointment_date DATETIME,
        status TEXT,
        notes TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    );

    CREATE TABLE treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER,
        treatment_name TEXT,
        cost REAL,
        duration_minutes INTEGER,
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    );

    CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        invoice_date DATE,
        total_amount REAL,
        paid_amount REAL,
        status TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    """)


def insert_doctors(cursor: sqlite3.Cursor) -> list[int]:
    doctor_rows = []
    doctor_weights = []

    for i in range(TARGET_DOCTORS):
        specialization, department = SPECIALIZATIONS[i % len(SPECIALIZATIONS)]
        name = f"Dr. {fake.name()}"
        phone = fake.phone_number() if random.random() > 0.10 else None

        doctor_rows.append((name, specialization, department, phone))

        # Higher weight => busier doctor
        weight = random.randint(1, 5)
        doctor_weights.append(weight)

    cursor.executemany("""
        INSERT INTO doctors (name, specialization, department, phone)
        VALUES (?, ?, ?, ?)
    """, doctor_rows)

    return doctor_weights


def insert_patients(cursor: sqlite3.Cursor) -> None:
    patient_rows = []

    for _ in range(TARGET_PATIENTS):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email() if random.random() > 0.15 else None
        phone = fake.phone_number() if random.random() > 0.12 else None
        dob = fake.date_of_birth(minimum_age=1, maximum_age=85).isoformat()
        gender = random.choice(["M", "F"])
        city = random.choice(CITIES)
        registered_date = random_date_within_last_12_months()

        patient_rows.append((
            first_name,
            last_name,
            email,
            phone,
            dob,
            gender,
            city,
            registered_date,
        ))

    cursor.executemany("""
        INSERT INTO patients (
            first_name,
            last_name,
            email,
            phone,
            date_of_birth,
            gender,
            city,
            registered_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, patient_rows)


def build_weighted_patient_pool() -> list[int]:
    weighted_ids = []
    for patient_id in range(1, TARGET_PATIENTS + 1):
        if patient_id <= 40:
            weight = random.randint(5, 10)   # repeat visitors
        elif patient_id <= 120:
            weight = random.randint(2, 4)
        else:
            weight = 1
        weighted_ids.extend([patient_id] * weight)
    return weighted_ids


def build_weighted_doctor_pool(doctor_weights: list[int]) -> list[int]:
    weighted_ids = []
    for doctor_id, weight in enumerate(doctor_weights, start=1):
        weighted_ids.extend([doctor_id] * (weight * 10))
    return weighted_ids


def insert_appointments(cursor: sqlite3.Cursor, doctor_weights: list[int]) -> None:
    patient_pool = build_weighted_patient_pool()
    doctor_pool = build_weighted_doctor_pool(doctor_weights)

    appointment_rows = []

    for _ in range(TARGET_APPOINTMENTS):
        patient_id = random.choice(patient_pool)
        doctor_id = random.choice(doctor_pool)
        appointment_dt = random_datetime_within_last_12_months().strftime("%Y-%m-%d %H:%M:%S")
        status = random.choices(
            APPOINTMENT_STATUSES,
            weights=[20, 55, 15, 10],
            k=1,
        )[0]
        notes = fake.sentence(nb_words=8) if random.random() > 0.25 else None

        appointment_rows.append((
            patient_id,
            doctor_id,
            appointment_dt,
            status,
            notes,
        ))

    cursor.executemany("""
        INSERT INTO appointments (
            patient_id,
            doctor_id,
            appointment_date,
            status,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, appointment_rows)


def insert_treatments(cursor: sqlite3.Cursor) -> None:
    completed_ids = [
        row[0]
        for row in cursor.execute("""
            SELECT id
            FROM appointments
            WHERE status = 'Completed'
        """).fetchall()
    ]

    if not completed_ids:
        raise RuntimeError("No completed appointments found; cannot create treatments.")

    treatment_names = [
        "Consultation",
        "X-Ray",
        "Blood Test",
        "Skin Therapy",
        "ECG",
        "Fracture Care",
        "Vaccination",
        "Follow-up",
        "Physiotherapy",
        "Pediatric Checkup",
    ]

    treatment_rows = []

    while len(treatment_rows) < TARGET_TREATMENTS:
        appointment_id = random.choice(completed_ids)
        treatment_name = random.choice(treatment_names)
        cost = round(random.uniform(50, 5000), 2)
        duration_minutes = random.randint(15, 120)

        treatment_rows.append((
            appointment_id,
            treatment_name,
            cost,
            duration_minutes,
        ))

    cursor.executemany("""
        INSERT INTO treatments (
            appointment_id,
            treatment_name,
            cost,
            duration_minutes
        )
        VALUES (?, ?, ?, ?)
    """, treatment_rows)


def insert_invoices(cursor: sqlite3.Cursor) -> None:
    patient_ids = [row[0] for row in cursor.execute("SELECT id FROM patients").fetchall()]
    invoice_rows = []

    for _ in range(TARGET_INVOICES):
        patient_id = random.choice(patient_ids)
        invoice_date = random_date_within_last_12_months()
        total_amount = round(random.uniform(100, 8000), 2)

        status = random.choices(
            INVOICE_STATUSES,
            weights=[55, 25, 20],
            k=1,
        )[0]

        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(random.uniform(0, total_amount * 0.70), 2)
        else:
            paid_amount = round(random.uniform(0, total_amount * 0.30), 2)

        invoice_rows.append((
            patient_id,
            invoice_date,
            total_amount,
            paid_amount,
            status,
        ))

    cursor.executemany("""
        INSERT INTO invoices (
            patient_id,
            invoice_date,
            total_amount,
            paid_amount,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, invoice_rows)


def fetch_scalar(cursor: sqlite3.Cursor, query: str) -> int:
    return cursor.execute(query).fetchone()[0]


def print_summary(cursor):
    print("\nDatabase created successfully.\n")

    print(f"Patients: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM patients')}")
    print(f"Doctors: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM doctors')}")
    print(f"Appointments: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM appointments')}")
    print(f"Treatments: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM treatments')}")
    print(f"Invoices: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM invoices')}")

    completed_query = "SELECT COUNT(*) FROM appointments WHERE status = 'Completed'"
    print(f"Completed Appointments: {fetch_scalar(cursor, completed_query)}")

    print(f"Null Patient Emails: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM patients WHERE email IS NULL')}")
    print(f"Null Patient Phones: {fetch_scalar(cursor, 'SELECT COUNT(*) FROM patients WHERE phone IS NULL')}")

    print("\nAppointment status breakdown:")
    for status, count in cursor.execute("""
        SELECT status, COUNT(*)
        FROM appointments
        GROUP BY status
        ORDER BY COUNT(*) DESC
    """).fetchall():
        print(f"  {status}: {count}")

    print("\nInvoice status breakdown:")
    for status, count in cursor.execute("""
        SELECT status, COUNT(*)
        FROM invoices
        GROUP BY status
        ORDER BY COUNT(*) DESC
    """).fetchall():
        print(f"  {status}: {count}")


def main() -> None:
    conn, cursor = connect_db()
    try:
        drop_tables(cursor)
        create_tables(cursor)

        doctor_weights = insert_doctors(cursor)
        insert_patients(cursor)
        insert_appointments(cursor, doctor_weights)
        insert_treatments(cursor)
        insert_invoices(cursor)

        conn.commit()
        print_summary(cursor)
    finally:
        conn.close()


if __name__ == "__main__":
    main()