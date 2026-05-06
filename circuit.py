#!/usr/bin/env python3
import cmd, sqlite3, datetime, os, re

DB_FILENAME = "circuit.db"
LOG_FILENAME = "circuit.log"

class CircuitShell(cmd.Cmd):
    intro = "Welcome to Circuit - Exercise Automation\nType 'help' or '?' for commands.\n"
    prompt = "(Circuit) "

    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(DB_FILENAME, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.current_group_id, self.date_format = None, 1
        self._init_db()

    def _init_db(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
                reps_per_cycle INTEGER, cycles_per_circuit INTEGER,
                days TEXT, add_reps INTEGER, add_cycles INTEGER
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER,
                name TEXT, FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            );''')

    def update_prompt(self):
        name = ""
        if self.current_group_id:
            row = self.conn.execute("SELECT name FROM groups WHERE id=?", (self.current_group_id,)).fetchone()
            name = row["name"] if row else ""
        self.prompt = f"(Circuit) [{name}] "

    def _get_input(self, label, pattern=None, default=None, is_int=False):
        while True:
            try:
                p = f"{label} [{default}]: " if default is not None else f"{label}: "
                val = input(p).strip() or default
                if val is None: continue
                if is_int and str(val).isdigit(): return int(val)
                if not is_int and (not pattern or re.fullmatch(pattern, str(val))): return val
                print("!! Invalid input")
            except KeyboardInterrupt:
                print("\n!! Command cancelled."); raise

    def _resolve_id(self, arg):
        groups = self.conn.execute("SELECT id FROM groups ORDER BY id").fetchall()
        match = re.search(r'\d+', arg)
        try: return groups[int(match.group())-1]['id'] if match else self.current_group_id
        except (ValueError, IndexError): return None

    def do_help(self, arg):
        """Show command list or specific command help."""
        if arg:
            func = getattr(self, f'do_{arg}', None)
            if func: print(func.__doc__)
            else: print(f"!! No help for '{arg}'")
        else:
            for c in ["add", "edit", "index", "layout", "log", "exit", "help"]: print(c)

    def do_add(self, arg):
        """Add a new workout group: add"""
        try:
            name = self._get_input("Group Name", r"[A-Za-z0-9,\s\-(\)]+")
            exs = self._get_input("Exercises (comma)", r"[A-Za-z\s\-,]+")
            reps, cycles = self._get_input("Reps/cycle", is_int=True, default=0), self._get_input("Cycles/circuit", is_int=True, default=0)
            days = ",".join(re.findall(r"Mon|Tue|Wed|Thu|Fri|Sat|Sun", input("Days: ").title()))
            with self.conn:
                cur = self.conn.execute("INSERT INTO groups VALUES (NULL,?,?,?,?,?,?)", (name, reps, cycles, days, 0, 0))
                for ex in [e.strip() for e in exs.split(",") if e.strip()]:
                    self.conn.execute("INSERT INTO exercises (group_id, name) VALUES (?,?)", (cur.lastrowid, ex))
                self.current_group_id = cur.lastrowid
            self.update_prompt(); print(f"✓ Created {name}")
        except KeyboardInterrupt: pass

    def do_edit(self, arg):
        """Edit a workout group's details: edit [idx]"""
        try:
            gid = self._resolve_id(arg)
            if not gid: return print("!! Select a group first")
            g = self.conn.execute("SELECT * FROM groups WHERE id=?", (gid,)).fetchone()
            name = self._get_input("Name", default=g['name'])
            reps, cycles = self._get_input("Reps", is_int=True, default=g['reps_per_cycle']), self._get_input("Cycles", is_int=True, default=g['cycles_per_circuit'])
            days_raw = input(f"Days [{g['days']}]: ").title() or g['days']
            days = ",".join(re.findall(r"Mon|Tue|Wed|Thu|Fri|Sat|Sun", days_raw))
            self.conn.execute("UPDATE groups SET name=?, reps_per_cycle=?, cycles_per_circuit=?, days=? WHERE id=?", (name, reps, cycles, days, gid))
            self.update_prompt(); print(f"✓ Updated {name}")
        except KeyboardInterrupt: pass

    def do_index(self, arg):
        """List groups or select by index: index [idx | remove idx]"""
        groups = self.conn.execute("SELECT id, name FROM groups ORDER BY id").fetchall()
        if "remove" in arg:
            ids = [groups[int(i)-1]['id'] for i in arg.split() if i.isdigit()]
            self.conn.executemany("DELETE FROM groups WHERE id=?", [(i,) for i in ids])
            if self.current_group_id in ids: self.current_group_id = None
            return self.update_prompt()
        for i, g in enumerate(groups, 1): print(f"{'*' if self.current_group_id == g['id'] else ' '} {i}. {g['name']}")
        if arg.isdigit(): self.current_group_id = self._resolve_id(arg); self.update_prompt()

    def do_layout(self, arg):
        """Display schedule or workout details: layout [NUM | set date 1-4 | export]"""
        if "set date" in arg:
            self.date_format = int(re.search(r'\d', arg).group() or 1)
            return print(f"✓ Date format set to {self.date_format}")

        lines = ["--- SCHEDULE ---"]
        fmts = {1: "%a", 2: "%A", 3: "%m/%d", 4: "%m/%d/%Y"}
        fmt = fmts.get(self.date_format, "%a")
        
        target_gid = self._resolve_id(arg) if any(c.isdigit() for c in arg) else None
        groups = self.conn.execute("SELECT * FROM groups" + (" WHERE id=?" if target_gid else ""), ([target_gid] if target_gid else [])).fetchall()

        for i in range(1 if target_gid else 7):
            date = datetime.date.today() + datetime.timedelta(days=i)
            active = [g for g in groups if target_gid or date.strftime("%a") in (g['days'] or "")]
            if active:
                if not target_gid: lines.append(date.strftime(fmt))
                for g in active:
                    lines.append(f"[{g['name']}]")
                    exs = self.conn.execute("SELECT name FROM exercises WHERE group_id=?", (g['id'],)).fetchall()
                    for idx, e in enumerate(exs, 1): lines.append(f"{idx}. {e['name']}")
                    lines.append(f"{g['reps_per_cycle']} reps | {g['cycles_per_circuit']} cycles\n")

        print("\n".join(lines).strip())
        if "export" in arg:
            fn = f"schedule_{datetime.date.today()}.txt"
            with open(fn, "w") as f: f.write("\n".join(lines))
            print(f"✓ Exported layout to {fn}")

    def do_log(self, arg):
        """Add to log or view layout: log add [idx] | log layout"""
        if "layout" in arg:
            if os.path.exists(LOG_FILENAME): 
                with open(LOG_FILENAME, "r") as f: print(f.read())
        elif "add" in arg:
            gid = self._resolve_id(arg.replace("add","").strip())
            if not gid: return print("!! Select a group")
            g = self.conn.execute("SELECT name, reps_per_cycle FROM groups WHERE id=?", (gid,)).fetchone()
            with open(LOG_FILENAME, "a") as f: f.write(f"{datetime.date.today()} - {g['name']} ({g['reps_per_cycle']} reps)\n")
            print("✓ Logged")

    def do_exit(self, arg):
        """Exit the program."""
        print("...")
        return True
    def do_EOF(self, arg): return self.do_exit(None)

if __name__ == "__main__":
    try: CircuitShell().cmdloop()
    except KeyboardInterrupt: print("\nUse 'exit' to quit.")