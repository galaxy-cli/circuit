# circuit
A lightweight, command-line workout automation tool designed to manage and track circuit-style exercises with progressive overload.

## Features
- Circuit Management: Create and organize workouts into groups with specific repetition and cycle counts.
- Progressive Overload: Automatically track and add repetitions or cycles to your next session to ensure steady progress.
- Flexible Scheduling: Plan your week by assigning workout groups to specific days (Mon–Sun).
- Session Logging: Save completed layouts to a local log file for a permanent history of your training.
- Exportable Layouts: Generate and export your weekly schedule into clean text files.

## Commands
| Command | Description |
| :--- | :--- |
| `add` | Interactively create a new workout group and exercises. |
| `edit` | Modify existing group details, schedules, or overload settings. |
| `index` | List all groups, select a group, or remove specific indexes. |
| `layout` | View your scheduled workouts or export them to a file. |
| `log` | Record a completed session to your permanent log file. |
| `exit` | Securely close the database and exit the shell. |

## Quick Start
1. **Launch**: Run the script to enter the interactive shell.
2. **Create**: Use add to build your first workout (e.g., "Leg Day").
3. **Select**: Use index 1 to focus on your new group.
4. **View**: Type layout to see your reps and cycles for the day.
5. **Track**: Use log add 1 after your workout to save your progress.
