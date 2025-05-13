# test_app_line3.py
import inspect

try:
    with open("app.py", "r") as f:
        lines = f.readlines()
        if len(lines) >= 3:
            line_content = lines[2].strip()
            print(f"Line 3 of app.py according to this script: '{line_content}'")
        else:
            print("app.py has less than 3 lines.")
except FileNotFoundError:
    print("app.py not found in current directory.")

print("\nAttempting to import app as a module to see what Python executes...")
try:
    import app
except ImportError as e:
    print(f"ImportError during 'import app': {e}")
    try:
        import sys
        if 'app' in sys.modules:
            app_module_obj = sys.modules['app']
            source_lines, starting_line_no = inspect.getsourcelines(app_module_obj)
            if len(source_lines) >= 3:
                line_content_module = source_lines[2].strip()
                print(f"Line 3 of 'app' module Python tried to load: '{line_content_module}'")
        else:
            print("Module 'app' not found in sys.modules after ImportError.")
            if hasattr(e, 'path') and e.path:
                print(f"Attempting to read file from ImportError path: {e.path}")
                try:
                    with open(e.path, "r") as f_err:
                        lines_err = f_err.readlines()
                        if len(lines_err) >=3:
                            line_content_error_path = lines_err[2].strip()
                            print(f"Line 3 of file ({e.path}) causing error: '{line_content_error_path}'")
                except Exception as fe:
                    print(f"Could not read file from error path: {fe}")

    except Exception as ie:
        print(f"Could not inspect source of 'app' module after initial ImportError: {ie}")
except Exception as e:
    print(f"Other error during 'import app': {e}") 