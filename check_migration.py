import subprocess

def run():
    result = subprocess.run(
        [r".venv\Scripts\python.exe", "-m", "flask", "db", "upgrade"],
        cwd=r"e:\Projects\emp-management-system\employee-management-backend",
        capture_output=True,
        text=True
    )
    with open("migration_error.txt", "w", encoding="utf-8") as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)

if __name__ == "__main__":
    run()
