# db-migration-project

This project is designed to manage database migrations and seed initial data for development and testing purposes.

## Project Structure

- **src/migrations**: Contains SQL files for database migrations.
  - `001_initial_schema.sql`: SQL commands to create the initial database schema.
  
- **src/seeds**: Contains SQL files for seeding initial data.
  - `seed_data.sql`: SQL commands to insert initial data into the database tables.

- **src/scripts**: Contains TypeScript scripts for migration operations.
  - `migrate.ts`: Function to execute migration scripts.
  - `rollback.ts`: Function to revert the last migration.

- **config**: Contains configuration files.
  - `database.config.ts`: Database connection settings.

## Getting Started

1. **Install Dependencies**: Run `npm install` to install the required packages.
2. **Configure Database**: Update the `config/database.config.ts` file with your database connection settings.
3. **Run Migrations**: Use the `migrate` script to apply migrations.
4. **Seed Database**: Use the `seed_data.sql` file to insert initial data for testing.

## Usage

- To run migrations, execute the `migrate` script.
- To rollback the last migration, execute the `rollback` script.

## License

This project is licensed under the MIT License.