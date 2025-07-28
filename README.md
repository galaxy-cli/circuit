# 🏋️ Circuit – Terminal-Based Workout Planner

**Circuit** is a Python shell app for planning, tracking, and progressing your circuit-style workout routines right from the command line. No extra dependencies, just Python's standard library.

---

## ✅ Features

- Interactive terminal shell using Python's `cmd`
- Manage workout groups: add/edit/delete
- Auto-progress reps & cycle counts (progressive overload)
- Weekly layout viewer & export to `.txt`
- Workout log with date stamps (in `circuit.log`)
- SQLite-backed persistent storage
- Fully offline – no 3rd-party libraries needed

---

## 🚀 How to Use

### 1. Clone this repo

```
git clone https://github.com/your-username/circuit-shell.git
cd circuit-shell
```

### 2. Run the app

```
python circuit.py
```

You’ll enter the interactive shell with commands like:

- `add` – Add a new workout group
- `edit` – Modify existing group
- `index` – List or select groups
- `layout` – See weekly plan
- `log` – Write or read workout logs
- `exit` – Quit the shell

Type `help` or `help <command>` anytime.

---

## 🧾 Example

```
> add
Group name: Push Day
Exercises: Push ups, Dips
Reps per cycle: 12
Cycles per circuit: 3
Workout days: Mon, Thu
Add reps: 1
Add cycles: 0
```

```
> log add
✓ Workout for today saved to circuit.log
```

```
> layout
Monday
Push Day
1. Push ups
2. Dips
12 reps each per cycle
3 cycles in circuit
```

---

## 💾 Files

- `circuit.db` – stores all workout data
- `circuit.log` – your workout history
- `circuit_schedule[DATE].txt` – exported weekly plans

---

## 📄 License

[MIT License](LICENSE)
