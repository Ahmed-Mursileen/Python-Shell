# 🚀 Custom Unix Shell in Python

A lightweight Unix-like shell built from scratch in Python to explore low-level operating system concepts such as process management, job control, and terminal handling.

This project mimics core behavior of traditional shells like Bash using system calls instead of high-level abstractions.

---

## ✨ Features

- Execute system commands using `fork` and `exec`
- Support for pipelines (`|`)
- Input and output redirection (`<`, `>`, `>>`)
- Foreground and background execution (`&`)
- Job control commands: `fg`, `bg`, `jobs`
- Process group management (PGID handling)
- Signal handling (`SIGINT`, `SIGTSTP`)
- Custom colored shell prompt

---

## 🧠 Concepts Demonstrated

- Process creation and execution (`fork`, `exec`)
- Inter-process communication using pipes
- File descriptor manipulation (`dup2`)
- Terminal control (`tcsetpgrp`, `termios`)
- Signal handling and job control
- Difference between built-in and external commands

---

## 🔐 Cybersecurity Relevance

- Understanding how shells execute commands (important for command injection analysis)
- Insight into process spawning and privilege boundaries
- Foundations for studying reverse shells and terminal control
- Practical exposure to Linux internals used in security research

---

## ⚙️ Installation & usage

Clone the repository:

```bash
git clone https://github.com/yourusername/custom-python-shell.git
cd custom-python-shell
python3 myshell2.py
```
---

## 📌 Example Commands
```bash
ls
pstree
cat file.txt | grep hello
sleep 10 &
jobs
fg 1
```
