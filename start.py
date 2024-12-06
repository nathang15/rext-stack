import subprocess
import os

def main():
    frontend_cmd = 'cd frontend && npm start'
    backend_cmd = 'uvicorn run:app --host 0.0.0.0 --port 5000'
    if os.name == 'nt':
        subprocess.Popen(['start', 'cmd', '/k', frontend_cmd], shell=True)
    else:
        subprocess.Popen(['osascript', '-e', f'tell app "Terminal" to do script "{frontend_cmd}"'])
    
    if os.name == 'nt':
        subprocess.Popen(['start', 'cmd', '/k', backend_cmd], shell=True)
    else:
        subprocess.Popen(['osascript', '-e', f'tell app "Terminal" to do script "{backend_cmd}"'])

if __name__ == "__main__":
    main()