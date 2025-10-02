-- SQL script to add performance indexes to the employees table
-- Run this in your PostgreSQL database

-- Composite index for bulk lookups
CREATE INDEX IF NOT EXISTS idx_employee_phone_email ON employees (phone_number, email);

-- Individual indexes for search operations
CREATE INDEX IF NOT EXISTS idx_employee_phone ON employees (phone_number);
CREATE INDEX IF NOT EXISTS idx_employee_email ON employees (email);
CREATE INDEX IF NOT EXISTS idx_employee_adhar ON employees (adhar_number);
CREATE INDEX IF NOT EXISTS idx_employee_pan ON employees (pan_card_number);
CREATE INDEX IF NOT EXISTS idx_employee_name ON employees (first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_employee_department ON employees (department_id);
CREATE INDEX IF NOT EXISTS idx_employee_status ON employees (employment_status);
CREATE INDEX IF NOT EXISTS idx_employee_site ON employees (site_id);

-- For date range queries
CREATE INDEX IF NOT EXISTS idx_employee_hire_date ON employees (hire_date);

-- Optional: To remove indexes later, use:
-- DROP INDEX IF EXISTS idx_employee_phone_email;
-- DROP INDEX IF EXISTS idx_employee_phone;
-- DROP INDEX IF EXISTS idx_employee_email;
-- DROP INDEX IF EXISTS idx_employee_adhar;
-- DROP INDEX IF EXISTS idx_employee_pan;
-- DROP INDEX IF EXISTS idx_employee_name;
-- DROP INDEX IF EXISTS idx_employee_department;
-- DROP INDEX IF EXISTS idx_employee_status;
-- DROP INDEX IF EXISTS idx_employee_site;
-- DROP INDEX IF EXISTS idx_employee_hire_date;