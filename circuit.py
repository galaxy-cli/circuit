import cmd
import re
import sqlite3
import datetime
import os
from io import StringIO

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

def print_EOF():
    print(f"\n\nEnter `exit` to close shell\n")

def print_no_index_number():
    print(f"ERROR: Enter an index number")

def print_index_does_not_exist():
    print(f"ERROR: No such index exists")

class CircuitShell(cmd.Cmd):

    ############ Shell ############
    shell = "Circuit"
    prompt = f"({shell}) [] "

    def __init__(self):
        super().__init__()
        print(f"Welcome to {self.shell} - The circuit-style exercise automation tool")
        print("`cmd` for commands, `help` or `?` for help, and `exit` to exit shell.\n")
        self.conn = sqlite3.connect(DB_FILENAME)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.current_group_id = None
        self.update_prompt()
        self.date_display_format = 1        # DEFAULT: `layout set date` 
        self.group_display_enabled = True   # DEFAULT: `layout set group`


    def create_tables(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                reps_per_cycle INTEGER NOT NULL,
                cycles_per_circuit INTEGER NOT NULL,
                days TEXT NOT NULL,
                add_reps INTEGER NOT NULL,
                add_cycles INTEGER NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def update_prompt(self):
        if self.current_group_id is not None:
            c = self.conn.cursor()
            c.execute("SELECT name FROM groups WHERE id = ?", (self.current_group_id,))
            row = c.fetchone()
            name = row["name"] if row else ""
        else:
            name = ""
        self.prompt = f"({self.shell}) [{name}] "

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

    # ---> def input_weight()

    ############ Commands ############
    ### add ###
    def do_add(self, arg: str) -> None:
        """
Add a new workout group with exercises, schedule, and progressive overload settings.

This interactive command guides you step-by-step to create a new workout group composed of multiple exercises,
specifying how often and when you want to perform them, along with settings to progressively increase workload.
        """
        if arg.strip() == "":
            # add ---> workout
            print_info("--- WORKOUTS ---")
            
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


            # add ---> circuits
            print_info("--- CIRCUITS ---")
            
            print_info("Rep = Repetition of an exercise\nCycle = A single completion of a circuit\nCircuit = Sequentially progressing through a number of exercises\n")
            
            # ---> weight_per_rep = self.input_weight("Weight per rep?: ")
            reps_per_cycle = self.input_positive_int("Rep per cycle?: ")
            cycles_per_circuit = self.input_positive_int("Cycles per circuit?: ")
            
            print_info(f"\n{reps_per_cycle} reps each per cycle")
            print_info(f"{cycles_per_circuit} cycles in circuit\n")


            # add ---> schedule
            print_info("--- SCHEDULE ---")
            
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


            # add --> progressive overload
            print_info("--- PROGRESSIVE OVERLOAD ---")
            
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


            # edit ---> workout
            print_info("--- WORKOUTS ---")
            
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


            # edit ---> schedule
            print_info("--- SCHEDULE ---")
            
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


            # edit ---> progressive overload
            print_info("--- PROGRESSIVE OVERLOAD ---")
            
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
        
        parts = arg.split()
        cmd = parts[0].lower()


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
            
            # layout | set date
            if setting_key == "date":
                if len(parts) == 3 and parts[2].isdigit():
                    num = int(parts[2])
                    if num in [1, 2, 3, 4]:
                        self.date_display_format = num
                        print_info(f"Date format set to option {num}")
                    else:
                        print_usage("Choose 1-4.")
                    return
            
            # layout | set group
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

        
        # layout | set unit

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


        # layout | index
        if arg.lower().startswith("index "):
            parts = arg.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1])
                c = self.conn.cursor()
                c.execute("SELECT * FROM groups ORDER BY id")
                groups = c.fetchall()
                
                if not groups:
                    print_info("No workout groups available.")
                    return
                
                if idx < 1 or idx > len(groups):
                    print_error(f"Index {idx} does not exist.")
                    return
                
                group = groups[idx - 1]
                
                c.execute("SELECT name FROM exercises WHERE group_id = ? ORDER BY id", (group['id'],))
                exercises = [row['name'] for row in c.fetchall()]
                
                print_info(f"{idx}. {group['name']}")
                
                for i, ex in enumerate(exercises, 1):
                    print_info(f"{i}. {ex}")
                
                scheduled_days = [d.strip() for d in (group['days'] or "").split(",") if d.strip()]
                
                if scheduled_days:
                    occ_idx = 1
                    reps = group['reps_per_cycle'] + (group['add_reps'] * occ_idx)
                    cycles = group['cycles_per_circuit'] + (group['add_cycles'] * occ_idx)
                else:
                    reps = group['reps_per_cycle']
                    cycles = group['cycles_per_circuit']
                
                print_info(f'{reps} | {cycles}')
                return
        
        print_error(f"Unknown argument '{arg}' for layout.")


    ### layout core logic
    def _layout_core(self) -> None:
        """
        Internal helper that performs the actual layout printing.
        Uses self.date_display_format and self.group_display_enabled.
        Calls print_info to output text.

        Prints workouts grouped by actual upcoming dates in order,
        not just fixed weekday order, for date formats 3 and 4.
        """
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


    ### log ###
    def do_log(self, arg: str) -> None:
        """
Manage workout completion logs by adding daily workout layouts and displaying the full log.

This command helps you keep a record of completed workouts by logging the workout layout 
for specific dates and reviewing the accumulated workout history.

USAGE
    log add [index NUM] 
    log layout
        """
        arg = arg.strip().lower()
        c = self.conn.cursor()

        # log | add
        if arg.startswith("add"):
            parts = arg.split(maxsplit=1)
            if len(parts) != 2:
                print_error("Usage: log add INDEX[,INDEX,...]")
                return
            index_str = parts[1]
            try:
                indexes = [int(x.strip()) for x in index_str.split(",")]
            except ValueError:
                print_error("Indexes must be valid integers separated by commas.")
                return

            c.execute("SELECT * FROM groups ORDER BY id")
            groups = c.fetchall()
            if not groups:
                print_info("No workout groups available.")
                return

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

                reps = group["reps_per_cycle"] + group["add_reps"] * 0  # just base occurrence
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
        
        if arg:
            func = getattr(self, "do_" + arg, None)
            if func and func.__doc__:
                print(func.__doc__)
            else:
                print(f"No help for '{arg}'")
        else:
            for cmd_name, desc in commands.items():
                print(f"{cmd_name.ljust(10)} {desc}")


    ### exit ###
    def do_exit(self, arg: str) -> bool:
        """
    Exits the shell.
        """
        print("Goodbye!")
        self.conn.close()
        return True
    

    ### exit ###
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
