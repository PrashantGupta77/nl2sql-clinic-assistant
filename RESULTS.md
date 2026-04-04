# RESULTS

## Benchmark Summary

- Total Questions: 20
- Passed: 20
- Partial: 0
- Failed: 0

## Detailed Results

### 1. How many patients do we have?
- Expected Behavior: Returns count
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 1

**Generated SQL:**
```sql
SELECT COUNT(*) AS total_patients FROM patients;
```

**Result Preview:**
```json
[[200]]
```

### 2. List all doctors and their specializations
- Expected Behavior: Returns doctor list
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 15
- Execution Time (ms): 2

**Generated SQL:**
```sql
SELECT name, specialization FROM doctors ORDER BY name;
```

**Result Preview:**
```json
[["Dr. Alex Spencer", "General"], ["Dr. Allison Hill", "Dermatology"]]
```

### 3. Show me appointments for last month
- Expected Behavior: Filters by date
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 42
- Execution Time (ms): 562

**Generated SQL:**
```sql
SELECT id, patient_id, doctor_id, appointment_date, status
                    FROM appointments
                    WHERE appointment_date >= date('now', 'start of month', '-1 month')
                      AND appointment_date < date('now', 'start of month')
                    ORDER BY appointment_date;
```

**Result Preview:**
```json
[[36, 40, 7, "2026-03-01 11:15:00", "Cancelled"], [363, 7, 1, "2026-03-01 11:15:00", "Completed"]]
```

### 4. Which doctor has the most appointments?
- Expected Behavior: Aggregation + ordering
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 57

**Generated SQL:**
```sql
SELECT d.name, COUNT(*) AS appointment_count
                    FROM appointments a
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY appointment_count DESC
                    LIMIT 1;
```

**Result Preview:**
```json
[["Dr. Jennifer Robinson", 66]]
```

### 5. What is the total revenue?
- Expected Behavior: SUM of invoice amounts
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 0

**Generated SQL:**
```sql
SELECT SUM(total_amount) AS total_revenue FROM invoices;
```

**Result Preview:**
```json
[[1161635.1600000001]]
```

### 6. Show revenue by doctor
- Expected Behavior: JOIN + GROUP BY
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 15
- Execution Time (ms): 35

**Generated SQL:**
```sql
SELECT d.name,
                           SUM(i.total_amount) AS total_revenue
                    FROM invoices i
                    JOIN appointments a ON i.patient_id = a.patient_id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY total_revenue DESC;
```

**Result Preview:**
```json
[["Dr. Latoya Robbins", 512128.3399999997], ["Dr. Jennifer Robinson", 480063.0099999997]]
```

### 7. How many cancelled appointments last quarter?
- Expected Behavior: Status filter + date
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 0

**Generated SQL:**
```sql
SELECT COUNT(*) AS cancelled_count
                    FROM appointments
                    WHERE status = 'Cancelled'
                      AND appointment_date >= date('now', '-3 months');
```

**Result Preview:**
```json
[[20]]
```

### 8. Top 5 patients by spending
- Expected Behavior: JOIN + ORDER + LIMIT
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 5
- Execution Time (ms): 30

**Generated SQL:**
```sql
SELECT p.first_name,
                           p.last_name,
                           SUM(i.total_amount) AS total_spending
                    FROM invoices i
                    JOIN patients p ON i.patient_id = p.id
                    GROUP BY p.id, p.first_name, p.last_name
                    ORDER BY total_spending DESC
                    LIMIT 5;
```

**Result Preview:**
```json
[["Gina", "Pace", 29878.21], ["Scott", "Harrison", 23750.42]]
```

### 9. Average treatment cost by specialization
- Expected Behavior: Multi-table JOIN + AVG
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 5
- Execution Time (ms): 30

**Generated SQL:**
```sql
SELECT d.specialization,
                           AVG(t.cost) AS avg_treatment_cost
                    FROM treatments t
                    JOIN appointments a ON t.appointment_id = a.id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.specialization
                    ORDER BY avg_treatment_cost DESC;
```

**Result Preview:**
```json
[["Orthopedics", 2668.259222222222], ["Pediatrics", 2565.798840579709]]
```

### 10. Show monthly appointment count for the past 6 months
- Expected Behavior: Date grouping
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 7
- Execution Time (ms): 37

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', appointment_date) AS month,
                           COUNT(*) AS total_appointments
                    FROM appointments
                    WHERE appointment_date >= date('now', '-6 months')
                    GROUP BY month
                    ORDER BY month;
```

**Result Preview:**
```json
[["2025-10", 36], ["2025-11", 38]]
```

### 11. Which city has the most patients?
- Expected Behavior: GROUP BY + COUNT
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 39

**Generated SQL:**
```sql
SELECT city, COUNT(*) AS patient_count
                    FROM patients
                    GROUP BY city
                    ORDER BY patient_count DESC
                    LIMIT 1;
```

**Result Preview:**
```json
[["Delhi", 31]]
```

### 12. List patients who visited more than 3 times
- Expected Behavior: HAVING clause
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 53
- Execution Time (ms): 149

**Generated SQL:**
```sql
SELECT p.first_name,
                           p.last_name,
                           COUNT(a.id) AS visit_count
                    FROM appointments a
                    JOIN patients p ON a.patient_id = p.id
                    GROUP BY p.id, p.first_name, p.last_name
                    HAVING COUNT(a.id) > 3
                    ORDER BY visit_count DESC;
```

**Result Preview:**
```json
[["Amanda", "Reed", 12], ["Jimmy", "Rogers", 11]]
```

### 13. Show unpaid invoices
- Expected Behavior: Status filter
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 143
- Execution Time (ms): 49

**Generated SQL:**
```sql
SELECT id, patient_id, invoice_date, total_amount, paid_amount, status
                    FROM invoices
                    WHERE status IN ('Pending', 'Overdue')
                    ORDER BY invoice_date DESC;
```

**Result Preview:**
```json
[[169, 69, "2026-04-03", 7483.62, 313.69, "Pending"], [189, 101, "2026-03-31", 812.98, 57.43, "Overdue"]]
```

### 14. What percentage of appointments are no-shows?
- Expected Behavior: Percentage calculation
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 0

**Generated SQL:**
```sql
SELECT ROUND(
                        100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*),
                        2
                    ) AS no_show_percentage
                    FROM appointments;
```

**Result Preview:**
```json
[[10.4]]
```

### 15. Show the busiest day of the week for appointments
- Expected Behavior: Date function
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 1
- Execution Time (ms): 30

**Generated SQL:**
```sql
SELECT CASE strftime('%w', appointment_date)
                               WHEN '0' THEN 'Sunday'
                               WHEN '1' THEN 'Monday'
                               WHEN '2' THEN 'Tuesday'
                               WHEN '3' THEN 'Wednesday'
                               WHEN '4' THEN 'Thursday'
                               WHEN '5' THEN 'Friday'
                               WHEN '6' THEN 'Saturday'
                           END AS weekday,
                           COUNT(*) AS total_appointments
                    FROM appointments
                    GROUP BY weekday
                    ORDER BY total_appointments DESC
                    LIMIT 1;
```

**Result Preview:**
```json
[["Wednesday", 78]]
```

### 16. Revenue trend by month
- Expected Behavior: Time series
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 13
- Execution Time (ms): 32

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', invoice_date) AS month,
                           SUM(total_amount) AS total_revenue
                    FROM invoices
                    GROUP BY month
                    ORDER BY month;
```

**Result Preview:**
```json
[["2025-04", 73655.76], ["2025-05", 104680.70000000003]]
```

### 17. Average appointment duration by doctor
- Expected Behavior: AVG + GROUP BY
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 15
- Execution Time (ms): 33

**Generated SQL:**
```sql
SELECT d.name,
                           AVG(t.duration_minutes) AS avg_duration_minutes
                    FROM treatments t
                    JOIN appointments a ON t.appointment_id = a.id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY avg_duration_minutes DESC;
```

**Result Preview:**
```json
[["Dr. Nathan Cortez", 92.66666666666667], ["Dr. Melinda Jones", 85.22222222222223]]
```

### 18. List patients with overdue invoices
- Expected Behavior: JOIN + filter
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 58
- Execution Time (ms): 1

**Generated SQL:**
```sql
SELECT DISTINCT p.first_name, p.last_name, p.city
                    FROM invoices i
                    JOIN patients p ON i.patient_id = p.id
                    WHERE i.status = 'Overdue'
                    ORDER BY p.last_name, p.first_name;
```

**Result Preview:**
```json
[["Ariel", "Barton", "Hyderabad"], ["Peter", "Barton", "Delhi"]]
```

### 19. Compare revenue between departments
- Expected Behavior: JOIN + GROUP BY
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 5
- Execution Time (ms): 33

**Generated SQL:**
```sql
SELECT d.department,
                           SUM(i.total_amount) AS total_revenue
                    FROM invoices i
                    JOIN appointments a ON i.patient_id = a.patient_id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.department
                    ORDER BY total_revenue DESC;
```

**Result Preview:**
```json
[["Primary Care", 884583.5299999998], ["Child Care", 736776.2599999999]]
```

### 20. Show patient registration trend by month
- Expected Behavior: Date grouping
- Status: **Pass**
- Notes: SQL executed successfully and returned rows
- Source: verified_seed_match
- Row Count: 13
- Execution Time (ms): 32

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', registered_date) AS month,
                           COUNT(*) AS registrations
                    FROM patients
                    GROUP BY month
                    ORDER BY month;
```

**Result Preview:**
```json
[["2025-04", 17], ["2025-05", 23]]
```
