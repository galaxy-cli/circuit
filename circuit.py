import cmd
import sqlite3
import datetime
import os
import re

DB_FILENAME = "circuit.db"
LOG_FILENAME = "circuit.log"

class CircuitShell(cmd.Cmd):
    intro = "Welcome to Circuit - The exercise automation tool\nUse `cmd` or `help` for commands and `exit` to close.\n"
    shell_name = "Circuit"

    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(DB_FILENAME)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()
        
        self.current_group_id = None
        self.update_prompt()

        self.date_display_format = 1        # Default format for layouts
        self.group_display_enabled = True 


    def _init_db(self):
        """Initializes tables using a single executescript call."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
                reps_per_cycle INTEGER NOT NULL, cycles_per_circuit INTEGER NOT NULL,
                days TEXT NOT NULL, add_reps INTEGER NOT NULL, add_cycles INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                name TEXT NOT NULL, FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            );
        """)

    def update_prompt(self):
        """Standardizes prompt updates with direct execution."""
        name = ""
        if self.current_group_id:
            row = self.conn.execute("SELECT name FROM groups WHERE id = ?", (self.current_group_id,)).fetchone()
            name = row["name"] if row else ""
        self.prompt = f"({self.shell_name}) [{name}] "

    def precmd(self, line):
        self.update_prompt()
        return line

    @staticmethod
    def get_int(prompt, default=None):
        """Unified integer validation replacing multiple prompt_positive functions."""
        while True:
            val = input(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ").strip()
            if not val and default is not None: return default
            if val.isdigit(): return int(val)
            print("ERROR: Please enter a valid positive integer.")

    def prompt_valid(self, label, pattern=None, default=None):
        while True:
            try:
                prompt_text = f"{label} [{default}]: " if default else f"{label}: "
                val = input(prompt_text).strip() or default
                
                if not val: 
                    continue
                if pattern and not re.fullmatch(pattern, val):
                    print(f"!! Invalid format for {label}")
                    continue
                return val

            except KeyboardInterrupt:
                print("\n!! Command cancelled.")
                return None 

    # --- ADD ---
    def do_add(self, arg):
        """Add a new workout group with exercises and settings."""
        print("\n--- NEW WORKOUT GROUP ---")
        name = self.prompt_valid("Group Name", r"[A-Za-z0-9,_\-\s\(\)]+")
        if name is None: return

        ex_raw = self.prompt_valid("Exercises (comma separated)", r"[A-Za-z\s\-,\s]+")
        if ex_raw is None: return
        exercises = [e.strip() for e in ex_raw.split(",") if e.strip()]

        # Use the get_int helper from the previous step
        reps = self.get_int("Reps per cycle", 0)
        cycles = self.get_int("Cycles per circuit", 0)
        
        # Simplified Days Logic
        days_input = input("Days (Mon, Tue... or N/A): ").title()
        days = "" if "N/A" in days_input else ",".join(re.findall(r"Mon|Tue|Wed|Thu|Fri|Sat|Sun", days_input))

        add_r = self.get_int("Reps to add next time (+intensity)", 0)
        add_c = self.get_int("Cycles to add next time (+cardio)", 0)

        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO groups (name, reps_per_cycle, cycles_per_circuit, days, add_reps, add_cycles) VALUES (?,?,?,?,?,?)",
                    (name, reps, cycles, days, add_r, add_c)
                )
                self.conn.executemany("INSERT INTO exercises (group_id, name) VALUES (?, ?)", 
                                    [(cur.lastrowid, ex) for ex in exercises])
                self.current_group_id = cur.lastrowid
            print(f"✓ Created {name} with {len(exercises)} exercises.")
        except sqlite3.IntegrityError:
            print("ERROR: Group name already exists.")

    # --- EDIT ---
    def do_edit(self, arg):
        """Edit an existing workout group or the current selection."""
        # 1. Resolve which group to edit
        gid = self.current_group_id
        if arg.isdigit():
            groups = self.conn.execute("SELECT id FROM groups ORDER BY id").fetchall()
            idx = int(arg) - 1
            if 0 <= idx < len(groups): gid = groups[idx]['id']
        
        if not gid:
            return print("ERROR: Specify a valid index or select a group first.")

        # 2. Fetch current data
        g = self.conn.execute("SELECT * FROM groups WHERE id = ?", (gid,)).fetchone()
        ex_rows = self.conn.execute("SELECT name FROM exercises WHERE group_id = ?", (gid,)).fetchall()
        current_ex = ", ".join([r['name'] for r in ex_rows])

        # 3. Interactive updates using our helpers (keeps old value if input is empty)
        name = self.prompt_valid(f"Group Name [{g['name']}]", r"[A-Za-z0-9,_\-\s\(\)]+", g['name'])
        
        ex_raw = self.prompt_valid(f"Exercises [{current_ex}]", r"[A-Za-z\s\-,\s]+", current_ex)
        exercises = [e.strip() for e in ex_raw.split(",") if e.strip()]

        reps = self.get_int("Reps per cycle", g['reps_per_cycle'])
        cycles = self.get_int("Cycles per circuit", g['cycles_per_circuit'])
        
        days_input = input(f"Days [{g['days']}]: ").title() or g['days']
        days = ",".join(re.findall(r"Mon|Tue|Wed|Thu|Fri|Sat|Sun", days_input))

        add_r = self.get_int("Add reps", g['add_reps'])
        add_c = self.get_int("Add cycles", g['add_cycles'])

        # 4. Save changes
        try:
            with self.conn:
                self.conn.execute("""UPDATE groups SET name=?, reps_per_cycle=?, cycles_per_circuit=?, 
                                    days=?, add_reps=?, add_cycles=? WHERE id=?""",
                                (name, reps, cycles, days, add_r, add_c, gid))
                self.conn.execute("DELETE FROM exercises WHERE group_id = ?", (gid,))
                self.conn.executemany("INSERT INTO exercises (group_id, name) VALUES (?, ?)", 
                                    [(gid, ex) for ex in exercises])
            print(f"✓ Updated {name}")
        except sqlite3.IntegrityError:
            print("ERROR: Name already exists.")

    # --- INDEX ---
    def do_index(self, arg):
        """Usage: index [NUM | remove NUMs | layout NUM]"""
        parts = arg.split()
        groups = self.conn.execute("SELECT id, name FROM groups ORDER BY id").fetchall()
        
        if not groups:
            return print("No workout groups available.")

        # 1. List Groups (Default)
        if not parts:
            for i, g in enumerate(groups, 1):
                print(f"{'*' if self.current_group_id == g['id'] else ' '} {i}. {g['name']}")
            return

        cmd = parts[0].lower()
        
        # Helper to resolve index strings to database IDs
        def get_id(idx_str):
            try:
                return groups[int(idx_str) - 1]["id"]
            except (ValueError, IndexError):
                return None

        # 2. Selection (index NUM)
        if cmd.isdigit():
            gid = get_id(cmd)
            if gid:
                self.current_group_id = gid
                self.update_prompt()
                print(f"Selected group {cmd}.")
            else:
                print(f"ERROR: Index {cmd} not found.")

        # 3. Removal (index remove NUM1 NUM2...)
        elif cmd == "remove":
            ids = [get_id(p) for p in parts[1:] if get_id(p)]
            if not ids: return print("ERROR: Specify valid indexes to remove.")
            
            with self.conn:
                self.conn.executemany("DELETE FROM groups WHERE id = ?", [(i,) for i in ids])
            
            if self.current_group_id in ids:
                self.current_group_id = None
                self.update_prompt()
            print(f"Removed {len(ids)} group(s).")

        # 4. Layout (index layout NUM)
        elif cmd == "layout" and len(parts) > 1:
            gid = get_id(parts[1])
            group = self.conn.execute("SELECT * FROM groups WHERE id = ?", (gid,)).fetchone() if gid else None
            if not group: return print("ERROR: Invalid index.")
            
            exs = self.conn.execute("SELECT name FROM exercises WHERE group_id = ?", (gid,)).fetchall()
            print(f"\n--- {group['name']} ---")
            for i, e in enumerate(exs, 1): print(f"{i}. {e['name']}")
            print(f"{group['reps_per_cycle']} reps | {group['cycles_per_circuit']} cycles")

    # --- LAYOUT ---
    def do_layout(self, arg):
        """Usage: layout [date 1-4 | export]"""
        parts = arg.split()
        
        # 1. Direct Date Setting (Usage: layout date 1)
        if "date" in parts:
            try:
                val = int(parts[parts.index("date") + 1])
                self.date_display_format = val
                print(f"✓ Date format set to {val}")
            except (ValueError, IndexError):
                print("ERROR: Usage: layout date <1-4>")
            return

        # 2. Handle Export logic
        file_handle = None
        if "export" in parts:
            fname = f"circuit_schedule[{datetime.date.today()}].txt"
            file_handle = open(fname, "w")
            file_handle.write("--- CIRCUIT SCHEDULE ---\n")

        def out(msg):
            print(msg)
            if file_handle: file_handle.write(msg + "\n")

        if not self.current_group_id and "export" not in arg:
            print("ERROR: No group selected. Use 'index NUM' first.")
            return
    
        # 3. Core Engine
        groups = self.conn.execute("SELECT * FROM groups").fetchall()
        if self.current_group_id:
            groups = [g for g in groups if g['id'] == self.current_group_id]

        date_fmts = {1: "%a", 2: "%A", 3: "%m/%d", 4: "%m/%d/%y"}
        fmt = date_fmts.get(self.date_display_format, "%a")

        for i in range(7):
            date_obj = datetime.date.today() + datetime.timedelta(days=i)
            day_name = date_obj.strftime("%a")
            
            active = [g for g in groups if self.current_group_id or day_name in g['days']]
            if not active: continue

            out(f"\n{date_obj.strftime(fmt)}")
            for group in active:
                out(f"[{group['name']}]")
                exs = self.conn.execute("SELECT name FROM exercises WHERE group_id=?", (group['id'],)).fetchall()
                for idx, ex in enumerate(exs, 1):
                    out(f"  {idx}. {ex['name']}")
                out(f"  {group['reps_per_cycle']} reps | {group['cycles_per_circuit']} cycles")

        if file_handle:
            file_handle.close()
            print(f"✓ Exported to {fname}")

    # --- LOG ---
    def do_log(self, arg):
        """Usage: log add INDEX(es) | log layout"""
        parts = arg.split()
        if not parts: return print("ERROR: Use `log add INDEX` or `log layout`.")

        # 1. log layout
        if parts[0] == "layout":
            if not os.path.exists(LOG_FILENAME): return print("No log found.")
            with open(LOG_FILENAME, "r") as f: print(f.read())
            return

        # 2. log add
        if parts[0] == "add" and len(parts) > 1:
            groups = self.conn.execute("SELECT * FROM groups ORDER BY id").fetchall()
            try:
                # Parse "1,2,3" or "1 2 3" into database rows
                indices = [int(i.strip()) for i in parts[1].replace(',', ' ').split()]
                selected = [groups[i-1] for i in indices]
            except (ValueError, IndexError):
                return print("ERROR: Invalid index provided.")

            with open(LOG_FILENAME, "a") as f:
                f.write(f"\n--- Workout Log {datetime.date.today()} ---\n")
                for g in selected:
                    exs = self.conn.execute("SELECT name FROM exercises WHERE group_id=?", (g['id'],)).fetchall()
                    ex_list = "\n".join([f"{i}. {e['name']}" for i, e in enumerate(exs, 1)])
                    f.write(f"[{g['name']}]\n{ex_list}\n{g['reps_per_cycle']} reps | {g['cycles_per_circuit']} cycles\n\n")
            
            print(f"✓ Logged: {', '.join(g['name'] for g in selected)} to circuit.log")

    # --- CMD ---
    def do_cmd(self, arg: str) -> None:
        """
    Lists all available commands
        """

        commands = [
            "add",
            "edit",
            "index",
            "layout",
            "log",
        ]
        
        if arg.strip() == "":
            for name in commands:
                print(name)
        else:
            print_error("`cmd` takes no arguments")

    # --- HELP ---
    def do_help(self, arg):
        """List available commands and their descriptions."""
        if arg:
            func = getattr(self, f"do_{arg}", None)
            if func: print(func.__doc__.strip())
            else: print(f"!! No help found for '{arg}'")
        else:
            order = ["cmd", "add", "edit", "index", "layout", "log", "exit"]
            
            print("\n--- AVAILABLE COMMANDS ---")
            for cmd_name in order:
                # Find the function in the class
                attr = f"do_{cmd_name}"
                if hasattr(self, attr):
                    doc = getattr(self, attr).__doc__
                    # Get the first non-empty line of the docstring
                    summary = doc.strip().split('\n')[0] if doc else "No description"
                    print(f"{cmd_name.ljust(10)} - {summary}")
            print()

    # --- EXIT ---
    def do_exit(self, arg):
        """Exit the shell."""
        print("\nClosing shell...")
        return True

# --- EXECUTE 
if __name__ == "__main__":
    app = CircuitShell()
    try:
        app.cmdloop()
    except KeyboardInterrupt:
        app.do_exit(None)