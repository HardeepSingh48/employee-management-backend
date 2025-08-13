-- Grant permissions to sspl_user for database operations
-- Run this as postgres superuser: psql -U postgres -d sspl_db -f grant_permissions.sql

-- Grant schema permissions
GRANT CREATE ON SCHEMA public TO sspl_user;
GRANT USAGE ON SCHEMA public TO sspl_user;

-- Grant table permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sspl_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sspl_user;

-- Grant default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sspl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO sspl_user;

-- Make sspl_user owner of the database (optional but recommended)
ALTER DATABASE sspl_db OWNER TO sspl_user;

-- Verify permissions
\dp public.*
