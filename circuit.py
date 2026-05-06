#!/usr/bin/env python3
import cmd
import sqlite3
import datetime
import os
import re

DB_FILENAME = "circuit.db"
LOG_FILENAME = "circuit.log"

############ UI ############
def prompt_input(prompt_text):
    return input(f"{prompt_text} ")

def print_info(msg):
    print(f"{msg}")

def print_usage(msg):
    print(f"USAGE: {msg}")

def print_error(msg):
    print(f"ERROR: {msg}")

def print_title(title):
    print(f'--- {title} ---'.upper())

def print_EOF():
    print(f"\n\nEnter `exit` to close shell\n")

def print_no_index_number():
    print(f"ERROR: Enter an index number")

def print_index_does_not_exist():
    print(f"ERROR: No such index exists")


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

        self.date_display_format = 1        # DEFAULT: `layout set date` 
        self.group_display_enabled = True   # DEFAULT: `layout set group`

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

        self.conn.commit()

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

    def precmd(self, line: str) -> str:
        self.update_prompt()
        return line

    def emptyline(self) -> bool:
        return False

    ############ Logic ############
    # edit
    def prompt_positive_int(self, prompt: str, default: int) -> int:
        while True:
            val = prompt_input(f"{prompt} [{default}]: ").strip()
            
            if not val:
                return default
            
            if re.fullmatch(r"\d+", val):
                return int(val)
            
            print_error("Please enter a valid positive integer.")

    def input_positive_int(prompt: str) -> int:
        while True:
            val = prompt_input(prompt).strip()
            
            if re.fullmatch(r"\d+", val):
                num = int(val)
                
                if num >= 0:
                    return num
            
            print_error("Please enter a valid positive integer.")

    ############ Commands ############
    ### add ###
    def do_add(self, arg: str) -> None:
        """
Add a new workout group with exercises, schedule, and progressive overload settings.

This interactive command guides you step-by-step to create a new workout group composed of multiple exercises,
specifying how often and when you want to perform them, along with settings to progressively increase workload.
        """
        if arg.strip() == "":
            print_title('workouts')

            while True:
                group_name = prompt_input("Group name (ex. Workout A, Leg Day): ").strip()
                
                if group_name and re.fullmatch(r"[A-Za-z0-9,_\-\s\(\)]+", group_name):
                    break
                
                print_error("Group name must contain only letters, digits, commas, underscores, dashes, spaces, and parentheses.")
            
            while True:
                exercises_input = prompt_input("Add exercises (ex. Squats, Push ups) (use `,` to separate): ").strip()
                exercises = [e.strip() for e in exercises_input.split(",") if e.strip()]
                valid_exercise_pattern = re.compile(r"^[A-Za-z\s\-]+$")
                
                if exercises and all(valid_exercise_pattern.fullmatch(ex) for ex in exercises):
                    break
                
                print_error("Each exercise must contain only letters, spaces, and dashes (e.g. 'Push ups', 'Leg-Press'). Please try again.")
            
            print_info(f'\n"{group_name}" created')
            print_info(f"{', '.join(exercises)} added to {group_name}\n")



            print_title('circuits')
            
            print_info("Rep = Repetition of an exercise\nCycle = A single completion of a circuit\nCircuit = Sequentially progressing through a number of exercises\n")
            
            # ---> weight_per_rep = self.input_weight("Weight per rep?: ")
            reps_per_cycle = self.input_positive_int("Rep per cycle?: ")
            cycles_per_circuit = self.input_positive_int("Cycles per circuit?: ")
            
            print_info(f"\n{reps_per_cycle} reps each per cycle")
            print_info(f"{cycles_per_circuit} cycles in circuit\n")



            print_title('schedule')
            valid_days_set = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "N/A"}
            
            while True:
                days_input = prompt_input("Workout days on? (Mon|Tue|Wed|Thu|Fri|Sat|Sun, or N/A if not scheduled) (use `,` to separate): ").strip()
                days_list_raw = re.findall(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun|N/?A)", days_input, re.IGNORECASE)
                days_list = [day.upper() if day.lower() == "n/a" else day.capitalize() for day in days_list_raw]
                
                if len(days_list) == 1 and days_list[0] == "N/A":
                    days_list = []
                    break
                elif days_list and all(day in valid_days_set - {"N/A"} for day in days_list):
                    break
                else:
                    print_error("Invalid days input. Please enter days as Mon, Tue, Wed, etc., separated by commas, or just 'N/A' if not scheduled.")
            
            print_info(f"\nScheduled {', '.join(days_list) if days_list else 'No scheduled days (N/A)'}\n")



            print_title('progressive overload')

            # ---> add_weight = self.input_weight("Weight added next workout? (+weight)")
            add_reps = self.input_positive_int("Reps added next workout? (+intensity): ")
            add_cycles = self.input_positive_int("Cycles added next workout? (+cardio): ")
            
            # ---> "weight added to next workout"
            print_info(f"\n{add_reps} reps added to next workout")
            print_info(f"{add_cycles} cycles added to next workout\n")
            
            c = self.conn.cursor()



            try:
                c.execute("""
                    INSERT INTO groups (name, reps_per_cycle, cycles_per_circuit, days, add_reps, add_cycles)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (group_name, reps_per_cycle, cycles_per_circuit, ",".join(days_list), add_reps, add_cycles))
                group_id = c.lastrowid
                
                for ex in exercises:
                    c.execute("INSERT INTO exercises (group_id, name) VALUES (?, ?)", (group_id, ex))
                
                self.conn.commit()
                self.current_group_id = group_id
                self.update_prompt()
                
                print_info(f"âœ“ Added {group_name}")
            
            except sqlite3.IntegrityError:
                print_error("Group name already exists. Choose a different name.")
        else:
            print_error("`add` takes no arguments")

    ### edit ###
    def do_edit(self, arg: str) -> None:
        """
Edit an existing workout group interactively.

This command allows you to modify the details of a previously created workout group,
including its name, exercises, schedule, and progressive overload settings. You can specify
the workout group either by supplying its index number or by editing the currently selected group.
        """
        if arg.strip() == "":
            arg = arg.strip()
            c = self.conn.cursor()
            c.execute("SELECT id, name FROM groups ORDER BY id")
            groups = c.fetchall()
            
            if not groups:
                print_info("No workout groups available.")
                return

            group_id = None
            group_name = None
            
            if not arg:
                if self.current_group_id is None:
                    print_error("No group selected to edit. Please use 'index NUM' to select a group first or specify the index here.")
                    return
                
                c.execute("SELECT id, name FROM groups WHERE id = ?", (self.current_group_id,))
                row = c.fetchone()
                
                if not row:
                    print_error("Currently selected group no longer exists. Please select a valid group.")
                    self.current_group_id = None
                    self.update_prompt()
                    return

                group_id = row["id"]
                group_name = row["name"]

            else:
                try:
                    idx = int(arg)
                except ValueError:
                    print_error("Invalid index number")
                    return
                
                if idx < 1 or idx > len(groups):
                    print_error(f"Index {idx} does not exist.")
                    return
                
                group = groups[idx - 1]
                group_id = group["id"]
                group_name = group["name"]
            
            c.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            group_data = c.fetchone()
            
            if not group_data:
                print_error("Failed to fetch group data.")
                return
            
            c.execute("SELECT name FROM exercises WHERE group_id = ? ORDER BY id", (group_id,))
            exercises = [row["name"] for row in c.fetchall()]

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

        print_title('workouts')

        while True:
            new_group_name = prompt_input(f"New group name [{group_data['name']}]: ").strip()
            
            if not new_group_name:
                new_group_name = group_data['name']
                break
            
            if re.fullmatch(r"[A-Za-z0-9,_\-\s\(\)]+", new_group_name):
                break
            
            print_error("Group name must contain only letters, digits, commas, underscores, dashes, spaces, and parentheses.")
        
        while True:
            exercises_prompt = f"Edit exercises (use `,` to separate) [{', '.join(exercises)}]: "
            new_exercises_input = prompt_input(exercises_prompt).strip()
            
            if not new_exercises_input:
                new_exercises = exercises
                break
            
            new_exercises = [e.strip() for e in new_exercises_input.split(",") if e.strip()]
            valid_exercise_pattern = re.compile(r"^[A-Za-z\s\-]+$")
            
            if new_exercises and all(valid_exercise_pattern.fullmatch(ex) for ex in new_exercises):
                break
            
            print_error("Each exercise must contain only letters, spaces, and dashes (e.g. 'Push ups', 'Leg-Press'). Please try again.")
        
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

            print_title('schedule')

            valid_days_set = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "N/A"}
            previous_days_str = group_data['days'] or ""
            
            while True:
                prompt_text = f"Workout days on? (Mon|Tue|Wed|Thu|Fri|Sat|Sun, or N/A if not scheduled) (use `,` to separate) [{previous_days_str}]: "
                days_input = prompt_input(prompt_text).strip()
                
                if not days_input:
                    days_list_raw = re.findall(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun|N/?A)", previous_days_str, re.IGNORECASE)
                    days_list = [day.upper() if day.lower() == "n/a" else day.capitalize() for day in days_list_raw]
                    
                    if len(days_list) == 1 and days_list[0] == "N/A":
                        days_list = []
                    break
                
                days_list_raw = re.findall(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun|N/?A)", days_input, re.IGNORECASE)
                days_list = [day.upper() if day.lower() == "n/a" else day.capitalize() for day in days_list_raw]
                
                if len(days_list) == 1 and days_list[0] == "N/A":
                    days_list = []
                    break
                elif days_list and all(day in valid_days_set - {"N/A"} for day in days_list):
                    break
                else:
                    print_error("Invalid days input. Please enter days as Mon, Tue, Wed, etc., separated by commas, or just 'N/A' if not scheduled.")
            
            print_info(f"\nScheduled {', '.join(days_list) if days_list else 'No scheduled days (N/A)'}\n")



            print_title('progressive overload')

            # ---> new_weight_per_cycle = self.
            new_reps_per_cycle = self.prompt_positive_int("Edit reps per cycle", group_data['reps_per_cycle'])
            new_cycles_per_circuit = self.prompt_positive_int("Edit cycles per circuit", group_data['cycles_per_circuit'])
            
            add_reps = self.prompt_positive_int("Edit reps for next workout", group_data['add_reps'])
            add_cycles = self.prompt_positive_int("Edit cycles for next workout", group_data['add_cycles'])

            print_info(f"\n{add_reps} reps saved for next workout")
            print_info(f"{add_cycles} cycles saved for next workout\n")



            try:
                c.execute("""
                    UPDATE groups
                    SET name = ?, reps_per_cycle = ?, cycles_per_circuit = ?, days = ?, add_reps = ?, add_cycles = ?
                    WHERE id = ?
                """, (new_group_name, new_reps_per_cycle, new_cycles_per_circuit, ",".join(days_list), add_reps, add_cycles, group_id))
                c.execute("DELETE FROM exercises WHERE group_id = ?", (group_id,))
                
                for ex in new_exercises:
                    c.execute("INSERT INTO exercises (group_id, name) VALUES (?, ?)", (group_id, ex))
                
                self.conn.commit()
                self.current_group_id = group_id
                self.update_prompt()
                
                print_info(f"Edited {new_group_name}")
            
            except sqlite3.IntegrityError:
                print_error("Group name already exists. Choose a different name.")
        else:
            print_error("`edit` takes no arguments")


    ### index ###
    def do_index(self, arg: str) -> None:
        """
Manage and select workout groups by their index number.

This command allows you to list all workout groups, select one for editing or viewing,
remove groups, or display detailed layout information about a specific group.

USAGE
    index NUM
    index remove NUM
    index layout NUM
        """
        arg = arg.strip()
        c = self.conn.cursor()
        c.execute("SELECT id, name FROM groups ORDER BY id")
        groups = c.fetchall()


        # index
        if not groups:
            print_info("No workout groups available.")
            return
        
        def print_groups():
            for idx, group in enumerate(groups, 1):
                prefix = "*" if self.current_group_id == group["id"] else " "
                print_info(f"{prefix} {idx}. {group['name']}")
        
        if not arg:
            print_groups()
            return
        
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


        # index | remove
        if cmd == "remove":
            if len(parts) < 2:
                print_error("Specify index(es) to remove, e.g. 'index remove 2 3'.")
                return
            index_parts = parts[1:] 
            
            try:
                indexes = [int(i) for i in index_parts]
            except ValueError:
                print_error("All indexes must be valid integers.")
                return
            
            invalid_indexes = [i for i in indexes if i < 1 or i > len(groups)]
            
            if invalid_indexes:
                print_error(f"Index(es) do not exist: {', '.join(map(str, invalid_indexes))}")
                return
            
            groups_to_remove = [groups[i - 1] for i in indexes]
            
            try:
                for group in groups_to_remove:
                    c.execute("DELETE FROM exercises WHERE group_id = ?", (group["id"],))
                    c.execute("DELETE FROM groups WHERE id = ?", (group["id"],))
                self.conn.commit()
            except Exception as e:
                print_error(f"Failed to remove group(s): {e}")
                return
            
            removed_group_ids = {g["id"] for g in groups_to_remove}
            
            if self.current_group_id in removed_group_ids:
                self.current_group_id = None
                self.update_prompt()
            
            removed_names = ", ".join(g["name"] for g in groups_to_remove)
            print_info(f"Removed workout group(s): {removed_names}")
            c.execute("SELECT id, name FROM groups ORDER BY id")
            new_groups = c.fetchall()
            
            if new_groups:
                for idx, group in enumerate(new_groups, 1):
                    prefix = "*" if self.current_group_id == group["id"] else " "
            else:
                print_info("No workout groups available.")
            return


        # index | layout
        elif cmd == "layout":
            if len(parts) != 2:
                print_error("Usage: index layout <NUM>")
                return
            
            try:
                idx = int(parts[1])
            except ValueError:
                print_error("Invalid index number for layout.")
                return
            
            if idx < 1 or idx > len(groups):
                print_error(f"Index {idx} does not exist.")
                return
            
            group_brief = groups[idx - 1]
            group_id = group_brief["id"]
            c.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            group = c.fetchone()
            
            if not group:
                print_error("Group data not found.")
                return
            
            c.execute("SELECT name FROM exercises WHERE group_id = ? ORDER BY id", (group_id,))
            exercises = [row["name"] for row in c.fetchall()]
            print_info(f"Group {idx}: {group['name']}")
            
            for i, ex in enumerate(exercises, 1):
                print_info(f"{i}. {ex}")
            
            days = (group['days'] or "").strip()
            
            if days:
                reps = group['reps_per_cycle']
                cycles = group['cycles_per_circuit']
            else:
                reps = group['reps_per_cycle']
                cycles = group['cycles_per_circuit']
            
            print_info(f'{reps} reps | {cycles} cycles')
            return

        else:
            if len(parts) != 1:
                print_error("Only one index number can be specified for selection.")
                return
            
            try:
                idx = int(parts[0])
            except ValueError:
                print_error("Not an index number.")
                return
            
            if idx < 1 or idx > len(groups):
                print_error(f"Index {idx} does not exist.")
                return
            
            group = groups[idx - 1]
            
            self.current_group_id = group["id"]
            self.update_prompt()
            
            print_info(f"Selected workout group {idx}. {group['name']}")



    ### layout ###
    def do_layout(self, arg: str) -> None:
        """
Layout workouts grouped by day, with customizable display formats and export capabilities.

This command displays your weekly workout schedule, organized by the days on which workouts
occur. It supports multiple display formats for dates and exercise details, visibility toggles,
exporting the layout to a text file, and viewing specific workout groups by index.

USAGE
    layout set date [1-4]
    layout set group [on/off]
    layout set unit [lb/kg]
    layout export
        """
        arg = arg.strip()
        if arg == "set":
            print(self.do_layout.__doc__)
            return
        if arg == "":
            self._layout_core()
            return


        # layout | set
        if arg.startswith("set "):
            parts = arg.split()
            if len(parts) < 3:
                if len(parts) < 3:
                    print_usage("layout set date <1-4>")
                    return
            setting_key = parts[1].lower()


            # layout | set | date
            if setting_key == "date":
                if len(parts) == 3 and parts[2].isdigit():
                    num = int(parts[2])
                    if num in [1, 2, 3, 4]:
                        self.date_display_format = num
                        print_info(f"Date format set to option {num}")
                    else:
                        print_usage("Choose 1-4.")
                    return


            # layout | set | group
            elif setting_key == "group":
                if len(parts) == 3:
                    val = parts[2].lower()
                    if val in ["on", "off"]:
                        self.group_display_enabled = (val == "on")
                        print_info(f"Group display set to: {val}")
                    else:
                        print_error("Invalid value for group display. Use 'on' or 'off'.")
                else:
                    print_usage("layout set group on|off")
                return

            else:
                print_error(f"No '{setting_key}' command in `layout set` command.")
                return

        # layout | export
        if arg == "export":
            output_buffer = StringIO()
            header = r'''        
  ___(_)_ __ ___ _   _(_) |_ 
 / __| | '__/ __| | | | | __|
| (__| | | | (__| |_| | | |_ 
 \___|_|_|  \___|\__,_|_|\__|
                             
'''
            output_buffer.write(header)

            def buffer_print_info(text=""):
                output_buffer.write(text + "\n")
            orig_print_info = globals().get("print_info")
            globals()["print_info"] = buffer_print_info
            
            try:
                self.do_layout("")
            
            finally:
                globals()["print_info"] = orig_print_info
            
            file_date = datetime.date.today().strftime("%Y-%m-%d")
            filename = f"circuit_schedule[{file_date}].txt"
            
            try:
                with open(filename, "w") as f:
                    f.write(output_buffer.getvalue())
                
                print_info(f"Exported workout schedule to {filename}")
            
            except Exception as e:
                print_error(f"Failed to export to file: {e}")
            
            return


    def _layout_core(self) -> None:
        c = self.conn.cursor()
        c.execute("SELECT * FROM groups ORDER BY id")
        groups = c.fetchall()
        
        if not groups:
            print_info("No workout groups available.")
            return
        
        valid_days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        valid_days_num = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
        day_workouts = {day: [] for day in valid_days_order}
        
        for group in groups:
            days_list = [d.strip() for d in group['days'].split(',') if d.strip() in valid_days_order]
            for occ_idx, day in enumerate(days_list, start=1):
                day_workouts[day].append((group, occ_idx))
        
        today = datetime.date.today()
        next_7_days = [today + datetime.timedelta(days=i) for i in range(7)]
        dates_and_weekdays = [(d, d.strftime("%a")) for d in next_7_days]
        
        for date_obj, day_name in dates_and_weekdays:
            workouts = day_workouts.get(day_name, []) 
            
            if not workouts:
                continue
            
            if self.date_display_format == 1:
                day_display = day_name            
            
            elif self.date_display_format == 2:
                day_display = date_obj.strftime("%A")
            
            elif self.date_display_format == 3:
                day_display = f"{date_obj.month}/{date_obj.day}"
            
            elif self.date_display_format == 4:
                try:
                    day_display = date_obj.strftime("%-m/%-d/%y")
                except Exception:
                    day_display = f"{date_obj.month}/{date_obj.day}/{str(date_obj.year)[2:]}"
            
            else:
                day_display = day_name
            
            print_info(day_display)
            
            for group, occ_idx in workouts:
                c.execute("SELECT name FROM exercises WHERE group_id = ? ORDER BY id", (group['id'],))
                exercises = [row['name'] for row in c.fetchall()]
                reps = group['reps_per_cycle'] + (group['add_reps'] * occ_idx)
                cycles = group['cycles_per_circuit'] + (group['add_cycles'] * occ_idx)
                
                if self.group_display_enabled:
                    print_info(group['name'])
                
                for idx, ex in enumerate(exercises, 1):
                    print_info(f"{idx}. {ex}")
                
                print_info(f'{reps} reps | {cycles} cycles\n')
        
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

    ### log ###
    def do_log(self, arg: str) -> None:
        """
Manage workout completion logs by adding daily workout layouts and displaying the full log.

USAGE
    log add [index NUM] 
    log layout
        """
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

        arg = arg.strip().lower()
        c = self.conn.cursor()

        # log | add
        if arg.startswith("add"):
            parts = arg.split(maxsplit=1)
            if len(parts) != 2:
                print_error("Usage: log add INDEX[,INDEX,...]")
                return
            index_str = parts[1]

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
            for idx in indexes:
                if idx < 1 or idx > len(groups):
                    print_error(f"Index {idx} does not exist.")
                    return

            selected_groups = [groups[i - 1] for i in indexes]
            group_names = [g["name"] for g in selected_groups]

            log_lines = []
            log_lines.append(f"Workout Log {datetime.date.today().strftime('%m/%d/%Y')}: {', '.join(group_names)}")

            for group in selected_groups:
                group_id = group["id"]
                group_name = group["name"]
                c.execute("SELECT name FROM exercises WHERE group_id = ? ORDER BY id", (group_id,))
                exercises = [row["name"] for row in c.fetchall()]
                
                if not exercises:
                    print_info(f"No exercises found for group '{group_name}'. Nothing added.")
                    continue

                reps = group["reps_per_cycle"] + group["add_reps"] * 0
                cycles = group["cycles_per_circuit"] + group["add_cycles"] * 0

                for i, ex in enumerate(exercises, 1):
                    log_lines.append(f"{i}. {ex}")
                
                log_lines.append(f"{reps} reps | {cycles} cycles")
                log_lines.append("")

            try:
                with open(LOG_FILENAME, "a", encoding="utf-8") as f:
                    f.write("\n".join(log_lines) + "\n")
                
                print_info(f"Workout layouts for groups '{', '.join(group_names)}' added to log.")
            
            except Exception as e:
                print_error(f"Failed to write to log: {e}")


        # log | layout
        elif arg == "layout":
            if not os.path.exists(LOG_FILENAME):
                print_info("No workout log found yet.")
                return
            try:
                with open(LOG_FILENAME, "r", encoding="utf-8") as f:
                    content = f.read()

                if not content.strip():
                    print_info("Workout log is empty.")

                else:
                    print_info(f"--- Workout Log ({LOG_FILENAME}) ---")
                    print(content)

            except Exception as e:
                print_error(f"Failed to read log: {e}")

        else:
            print_error("Use `log add INDEX` or `log layout`.")



    ### cmd ###
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


    ### help ###
    def do_help(self, arg: str) -> None:
        """
    Shows help for commands.  
        """
        commands = {
            "add": "Add a new exercise",
            "edit": "Edit an exercise by index",
            "index": "List all exercises",
            "layout": "Layout one or all exercise schedules",
            "log": "Add/layout logs for exercise"
        }
        

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

    ### exit ###
    def do_exit(self, arg: str) -> bool:
        """
    Exits the shell.
        """
        print("Goodbye!")
        self.conn.close()
        return True


    def do_EOF(self, arg: str) -> bool:
        print_EOF()
        return False



############ Run ############
if __name__ == "__main__":
    shell = CircuitShell()
    while True:
        try:
            shell.cmdloop()
            break
        except KeyboardInterrupt:
            print_EOF()

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
        app.do_exit(None)