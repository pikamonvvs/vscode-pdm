import subprocess
import tkinter as tk
from tkinter import ttk


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Process Monitor")

        self.processes = []
        self.process_labels = []
        self.restart_buttons = []

        self.start_button = ttk.Button(root, text="Start Processes", command=self.start_processes)
        self.start_button.pack(pady=10)

        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(pady=10)

        self.update_status()

    def start_processes(self):
        # 예시로 간단한 명령어를 사용합니다. 실제로는 실행할 외부 프로그램을 여기에 넣으세요.
        commands = ["ping -c 4 google.com", "ping -c 4 google.com", "ping -c 4 yahoo.com"]
        for cmd in commands:
            self.start_process(cmd)

    def start_process(self, cmd):
        process = subprocess.Popen(cmd, shell=True)
        self.processes.append(process)
        index = len(self.processes) - 1

        label = ttk.Label(self.status_frame, text=f"Process {index + 1}: Running")
        label.grid(row=index, column=0, padx=5, pady=5)
        self.process_labels.append(label)

        button = ttk.Button(self.status_frame, text="Restart", command=lambda idx=index: self.restart_process(idx))
        button.grid(row=index, column=1, padx=5, pady=5)
        self.restart_buttons.append(button)

    def restart_process(self, index):
        # 기존 프로세스를 종료합니다.
        if self.processes[index].poll() is None:
            self.processes[index].terminate()
            self.processes[index].wait()

        # 프로세스를 재시작합니다.
        cmd = self.processes[index].args
        self.processes[index] = subprocess.Popen(cmd, shell=True)
        self.process_labels[index].config(text=f"Process {index + 1}: Running")

    def update_status(self):
        for i, process in enumerate(self.processes):
            if process.poll() is None:
                self.process_labels[i].config(text=f"Process {i + 1}: Running")
            else:
                self.process_labels[i].config(text=f"Process {i + 1}: Finished")

        # 1초마다 상태를 업데이트합니다.
        self.root.after(1000, self.update_status)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
