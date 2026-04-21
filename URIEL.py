import os
import shlex
import signal
import sys
import termios

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"

jobs = []
job_counter = 1

shell_terminal = sys.stdin.fileno()
shell_pgid = os.getpgrp()
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
signal.signal(signal.SIGTTIN, signal.SIG_IGN)

# Save shell terminal attributes
shell_attrs = termios.tcgetattr(shell_terminal)

def parse_command(tokens):
    cmd = []
    infile = None
    outfile = None
    append = False

    it = iter(tokens)
    for t in it:
        if t == "<":
            infile = next(it, None)
        elif t == ">":
            outfile = next(it, None)
            append = False
        elif t == ">>":
            outfile = next(it, None)
            append = True
        else:
            cmd.append(t)

    return cmd, infile, outfile, append

def colored_prompt():
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    return f"{BOLD}{BLUE}uriel{RESET}:{CYAN}{cwd}{RESET}$ "

def run_pipeline(parts, background=False):
    global job_counter
    processes = []
    prev_read = None
    pgid = None
    command_line = " | ".join(" ".join(p) for p in parts)

    for i, tokens in enumerate(parts):
        cmd, infile, outfile, append = parse_command(tokens)

        if i < len(parts) - 1:
            read_fd, write_fd = os.pipe()
        else:
            read_fd = write_fd = None

        pid = os.fork()
        if pid == 0:
            # ----- CHILD -----

            # FIX 1: Correct process group setup
            if pgid is None:
                os.setpgid(0, 0)      # first child becomes leader
            else:
                os.setpgid(0, pgid)  # join pipeline group

            # FIX 2: restore default signals
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)

            # FIX 3: DO NOT touch terminal here (parent only)

            if prev_read is not None:
                os.dup2(prev_read, 0)
            if write_fd is not None:
                os.dup2(write_fd, 1)

            if infile:
                fd = os.open(infile, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)

            if outfile:
                flags = os.O_WRONLY | os.O_CREAT
                flags |= os.O_APPEND if append else os.O_TRUNC
                fd = os.open(outfile, flags, 0o644)
                os.dup2(fd, 1)
                os.close(fd)

            if prev_read is not None:
                os.close(prev_read)
            if read_fd is not None:
                os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

            try:
                os.execvpe(cmd[0], cmd, os.environ)
            except FileNotFoundError:
                os.write(2, f"{RED}Command not found: {cmd[0]}{RESET}\n".encode())
                os._exit(1)

        else:
            # ----- PARENT -----

            # FIX 4: mirror PGID assignment
            if pgid is None:
                pgid = pid
            os.setpgid(pid, pgid)

            processes.append(pid)

            if prev_read is not None:
                os.close(prev_read)
            if write_fd is not None:
                os.close(write_fd)

            prev_read = read_fd

    jobs.append({
        'id': job_counter,
        'pgid': pgid,
        'cmd': command_line,
        'status': 'running' if background else 'foreground'
    })
    job_counter += 1

    # FIX 5: terminal control ONLY here
    if not background:
        os.tcsetpgrp(shell_terminal, pgid)

        for pid in processes:
            _, status = os.waitpid(pid, os.WUNTRACED)
            if os.WIFSTOPPED(status):
                jobs[-1]['status'] = 'stopped'
                print(f"\n{YELLOW}[{jobs[-1]['id']}] Stopped {command_line}{RESET}")
                break

        os.tcsetpgrp(shell_terminal, shell_pgid)
        termios.tcsetattr(shell_terminal, termios.TCSADRAIN, shell_attrs)
    else:
        print(f"{GREEN}[{jobs[-1]['id']}] {pgid} running in background{RESET}")

def run_shell():
    while True:
        try:
            os.write(1, colored_prompt().encode())
            line = os.read(0, 4096).decode().strip()
        except OSError:
            break

        if not line:
            continue
        if line == "exit":
            break

        if line.startswith("fg "):
            _, job_id = line.split()
            bring_foreground(int(job_id))
            continue
        elif line.startswith("bg "):
            _, job_id = line.split()
            resume_background(int(job_id))
            continue
        elif line == "jobs":
            print_jobs()
            continue

        background = line.endswith("&")
        if background:
            line = line[:-1].strip()

        parts = [shlex.split(p) for p in line.split("|")]

        if parts[0][0] == "cd":
            try:
                os.chdir(parts[0][1] if len(parts[0]) > 1 else os.path.expanduser("~"))
            except Exception as e:
                os.write(2, f"{RED}{e}{RESET}\n".encode())
            continue

        run_pipeline(parts, background)

def bring_foreground(job_id):
    for job in jobs:
        if job['id'] == job_id:
            pgid = job['pgid']
            os.tcsetpgrp(shell_terminal, pgid)
            os.killpg(pgid, signal.SIGCONT)

            _, status = os.waitpid(-pgid, 0)
            if os.WIFSTOPPED(status):
                job['status'] = 'stopped'
                print(f"\n{YELLOW}[{job['id']}] Stopped {job['cmd']}{RESET}")
            else:
                jobs.remove(job)

            os.tcsetpgrp(shell_terminal, shell_pgid)
            termios.tcsetattr(shell_terminal, termios.TCSADRAIN, shell_attrs)
            break

def resume_background(job_id):
    for job in jobs:
        if job['id'] == job_id:
            os.killpg(job['pgid'], signal.SIGCONT)
            job['status'] = 'running'
            print(f"{GREEN}[{job['id']}] {job['pgid']} resumed in background{RESET}")
            break

def print_jobs():
    for job in jobs:
        color = GREEN if job['status'] == 'running' else YELLOW
        print(f"{color}[{job['id']}] {job['status']} {job['cmd']}{RESET}")

def main():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    run_shell()

if __name__ == "__main__":
    main()
