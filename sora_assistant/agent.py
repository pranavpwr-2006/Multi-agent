import os
import logging
import datetime
import google.cloud.logging
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.cloud import datastore

# --- Setup Logging and Environment ---
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL", "gemini-2.5-flash")
project_id  = os.getenv("GOOGLE_CLOUD_PROJECT")

# --- Datastore Client ---
ds = datastore.Client(project=project_id)

# --- Validation Helpers ---
VALID_PRIORITIES = ["low", "medium", "high"]
VALID_STATUSES = ["pending", "in_progress", "done"]

def validate_date(date: str) -> bool:
    """Validates DD-MM-YY format."""
    try:
        datetime.datetime.strptime(date, "%d-%m-%y")
        return True
    except ValueError:
        return False

def validate_datetime(dt: str) -> bool:
    """Validates DD-MM-YYTHH:MM format."""
    try:
        datetime.datetime.strptime(dt, "%d-%m-%yT%H:%M")
        return True
    except ValueError:
        return False

# --- Date Awareness ---
def get_current_datetime() -> dict:
    """Returns the current date and time."""
    now = datetime.datetime.now()
    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "current_datetime": now.strftime("%Y-%m-%dT%H:%M"),
        "day_of_week": now.strftime("%A"),
    }


# ─────────────────────────────────────────────
# TASK TOOLS
# ─────────────────────────────────────────────

def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> dict:
    """Creates a new task and stores it in Datastore."""
    try:
        if not title.strip():
            return {"success": False, "message": "Title cannot be empty."}
        if priority not in VALID_PRIORITIES:
            return {"success": False, "message": "Priority must be low, medium, or high."}
        if due_date and not validate_date(due_date):
            return {"success": False, "message": "due_date must be in DD-MM-YY format."}
        key = ds.key("Task")
        entity = datastore.Entity(key=key)
        entity.update({
        "title":       title,
        "description": description,
        "priority":    priority,
        "due_date":    due_date,
        "status":      "pending",
        "created_at":  datetime.datetime.utcnow().isoformat(),
    })
        ds.put(entity)
        logging.info(f"[Task] Created: {title}")
        return {"success": True, "task_id": entity.key.id, "message": f"Task '{title}' created."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def list_tasks(status: str = "", priority: str = "") -> dict:
    """Lists tasks from Datastore, optionally filtered by status or priority."""
    try:
        query = ds.query(kind="Task")
        if status:
            query.add_filter("status", "=", status)
        if priority:
            query.add_filter("priority", "=", priority)
        tasks = [dict(e) | {"id": e.key.id} for e in query.fetch()]
        return {"tasks": tasks, "count": len(tasks)}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def update_task(task_id: int, title: str = "", description: str = "", 
                priority: str = "", due_date: str = "", status: str = "") -> dict:
    """Updates any field of an existing task."""
    try:
        if status and status not in VALID_STATUSES:
            return {"success": False, "message": "Status must be pending, in_progress, or done."}
        if due_date and not validate_date(due_date):
            return {"success": False, "message": "due_date must be in DD-MM-YY format."}
        key = ds.key("Task", int(task_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Task {task_id} not found."}
        if title: entity["title"] = title
        if description: entity["description"] = description
        if priority: entity["priority"] = priority
        if due_date: entity["due_date"] = due_date
        if status: entity["status"] = status
        ds.put(entity)
        return {"success": True, "message": f"Task {task_id} updated."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def delete_task(task_id: int) -> dict:
    """Deletes a task by ID."""
    try:
        key = ds.key("Task", int(task_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Task {task_id} not found."}
        ds.delete(key)
        return {"success": True, "message": f"Task {task_id} deleted."}
    except Exception as e:
        logging.error(f"[Task] Error deleting task: {e}")
        return {"success": False, "message": f"Failed to delete task: {str(e)}"}

# ─────────────────────────────────────────────
# CALENDAR TOOLS
# ─────────────────────────────────────────────

def create_event(title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> dict:
    """Creates a calendar event in Datastore."""
    try:
        if not title.strip():
            return {"success": False, "message": "Title cannot be empty."}
        if not validate_datetime(start_time):
            return {"success": False, "message": "start_time must be in DD-MM-YYTH:MM format."}
        if not validate_datetime(end_time):
            return {"success": False, "message": "end_time must be in DD-MM-YYTH:MM format."}
        key = ds.key("Event")
        entity = datastore.Entity(key=key)
        entity.update({
        "title":       title,
        "start_time":  start_time,
        "end_time":    end_time,
        "description": description,
        "location":    location,
        "created_at":  datetime.datetime.utcnow().isoformat(),
    })
        ds.put(entity)
        logging.info(f"[Calendar] Event created: {title}")
        return {"success": True, "event_id": entity.key.id, "message": f"Event '{title}' scheduled."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}

def list_events(date: str = "") -> dict:
    """Lists calendar events. Optionally filter by date (YYYY-MM-DD)."""
    try:
        query = ds.query(kind="Event")
        events = [dict(e) | {"id": e.key.id} for e in query.fetch()]
        if date:
            events = [e for e in events if e.get("start_time", "").startswith(date)]
        return {"events": events, "count": len(events)}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}

def update_event(event_id: int, title: str = "", start_time: str = "", end_time: str = "", location: str = "") -> dict:
    """Updates an existing calendar event."""
    try:
        key = ds.key("Event", int(event_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Event {event_id} not found."}
        if title: entity["title"] = title
        if start_time: entity["start_time"] = start_time
        if end_time: entity["end_time"] = end_time
        if location: entity["location"] = location
        ds.put(entity)
        return {"success": True, "message": f"Event {event_id} updated."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def delete_event(event_id: int) -> dict:
    """Deletes a calendar event by ID."""
    try:
        key = ds.key("Event", int(event_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Event {event_id} not found."}
        ds.delete(key)
        return {"success": True, "message": f"Event {event_id} deleted."}
    except Exception as e:
        logging.error(f"[Calendar] Error deleting event: {e}")
        return {"success": False, "message": f"Failed to delete event: {str(e)}"}


# ─────────────────────────────────────────────
# NOTES TOOLS
# ─────────────────────────────────────────────

def create_note(title: str, content: str, tags: str = "") -> dict:
    """Creates a note and stores it in Datastore."""
    try:
        if not title.strip():
            return {"success": False, "message": "Title cannot be empty."}
        if not content.strip():
            return {"success": False, "message": "Content cannot be empty."}
        key = ds.key("Note")
        entity = datastore.Entity(key=key)
        entity.update({
        "title":      title,
        "content":    content,
        "tags":       tags,
        "created_at": datetime.datetime.utcnow().isoformat(),
    })
        ds.put(entity)
        logging.info(f"[Notes] Created: {title}")
        return {"success": True, "note_id": entity.key.id, "message": f"Note '{title}' saved."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def search_notes(query: str) -> dict:
    """Searches notes by title or content keyword."""
    try:
        all_notes = [dict(e) | {"id": e.key.id} for e in ds.query(kind="Note").fetch()]
        results = [
        n for n in all_notes
        if query.lower() in n.get("title", "").lower()
        or query.lower() in n.get("content", "").lower()
    ]
        return {"notes": results, "count": len(results)}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def update_note(note_id: int, title: str = "", content: str = "", tags: str = "") -> dict:
    """Updates an existing note."""
    try:
        key = ds.key("Note", int(note_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Note {note_id} not found."}
        if title: entity["title"] = title
        if content: entity["content"] = content
        if tags: entity["tags"] = tags
        ds.put(entity)
        return {"success": True, "message": f"Note {note_id} updated."}
    except Exception as e:
        logging.error(f"[Task] Error creating task: {e}")
        return {"success": False, "message": f"Failed to create task: {str(e)}"}


def delete_note(note_id: int) -> dict:
    """Deletes a note by ID."""
    try:
        key = ds.key("Note", int(note_id))
        entity = ds.get(key)
        if not entity:
            return {"success": False, "message": f"Note {note_id} not found."}
        ds.delete(key)
        return {"success": True, "message": f"Note {note_id} deleted."}
    except Exception as e:
        logging.error(f"[Notes] Error deleting note: {e}")
        return {"success": False, "message": f"Failed to delete note: {str(e)}"}

# ─────────────────────────────────────────────
# SUB-AGENTS
# ─────────────────────────────────────────────

task_agent = Agent(
    name="task_agent",
    model=model_name,
    description="Manages to-do tasks: create, list, update status, and delete tasks.",
    instruction="""
    You are a Task Manager. Handle all task-related requests.
    - create_task: create with title, description, priority (low/medium/high), due_date
    - list_tasks: list all, filter by status or priority
    - update_task: update status to pending | in_progress | done
    - delete_task: delete by task_id
    Always confirm what action you took.
    """,
    tools=[create_task, list_tasks, update_task, delete_task],
    output_key="task_data",
)

calendar_agent = Agent(
    name="calendar_agent",
    model=model_name,
    description="Manages calendar events: create, list, update, and delete events.",
    instruction="""
    You are a Calendar Manager. Handle all scheduling requests.
    - create_event: use DD-MM-YYTH:MM format for start_time and end_time, description, location
    - list_events: list all, filter by date (DD-MM-YYYY)
    - update_event: update title, start_time, end_time, or location by event_id
    - delete_event: delete by event_id
    Always confirm what action you took.
    """,
    tools=[create_event, list_events, update_event, delete_event],
    output_key="calendar_data",
)

notes_agent = Agent(
    name="notes_agent",
    model=model_name,
    description="Manages notes: create, search, update, and delete notes.",
    instruction="""
    You are a Notes Manager. Handle all note-related requests.
    - create_note: create with title, content, optional tags
    - search_notes: search by keyword
    - update_note: update title, content, or tags by note_id
    - delete_note: delete by note_id
    Always confirm what action you took.
    """,
    tools=[create_note, search_notes, update_note, delete_note],
    output_key="notes_data",
)


# ─────────────────────────────────────────────
# ROOT AGENT
# ─────────────────────────────────────────────

root_agent = Agent(
    name="sora_assistant",
    model=model_name,
    description="Main entry point for the Productivity Assistant.",
   instruction="""
You are a friendly Productivity Assistant that helps with tasks, scheduling, and notes.

IMPORTANT: Before transferring to any sub-agent, ALWAYS call get_current_datetime first
to know today's date. Use it to resolve any relative dates like "today", "tomorrow", 
"next Monday" into actual YYYY-MM-DD dates before passing to the sub-agent.

Based on the user's request, transfer to ONLY the relevant agent:
- For tasks (create, list, update, delete to-dos) → transfer to task_agent
- For scheduling (meetings, events, calendar) → transfer to calendar_agent
- For notes (save, search, update, delete information) → transfer to notes_agent

Only transfer to ONE agent per request. Do not call multiple agents.
After the sub-agent responds, present the result clearly to the user.
""",
    tools=[get_current_datetime],
    sub_agents=[task_agent, calendar_agent, notes_agent],
)