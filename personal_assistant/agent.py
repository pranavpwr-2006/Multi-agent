import os
import logging
import datetime
import google.cloud.logging
from dotenv import load_dotenv

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from google.cloud import datastore

# --- Setup Logging and Environment ---
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL", "gemini-2.5-flash")
project_id  = os.getenv("GOOGLE_CLOUD_PROJECT")

# --- Datastore Client ---
ds = datastore.Client(project=project_id)


def add_prompt_to_state(tool_context: ToolContext, prompt: str) -> dict:
    """Saves the user's initial prompt to the shared agent state."""
    tool_context.state["PROMPT"] = prompt
    logging.info(f"[State] PROMPT saved: {prompt}")
    return {"status": "success"}


def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "") -> dict:
    """Creates a new task and stores it in Datastore."""
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


def list_tasks(status: str = "", priority: str = "") -> dict:
    """Lists tasks from Datastore, optionally filtered by status or priority."""
    query = ds.query(kind="Task")
    if status:
        query.add_filter("status", "=", status)
    if priority:
        query.add_filter("priority", "=", priority)
    tasks = [dict(e) | {"id": e.key.id} for e in query.fetch()]
    return {"tasks": tasks, "count": len(tasks)}


def update_task_status(task_id: int, status: str) -> dict:
    """Updates the status of an existing task (pending | in_progress | done)."""
    key = ds.key("Task", int(task_id))
    entity = ds.get(key)
    if not entity:
        return {"success": False, "message": f"Task {task_id} not found."}
    entity["status"] = status
    ds.put(entity)
    return {"success": True, "message": f"Task {task_id} updated to '{status}'."}


def create_event(title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> dict:
    """Creates a calendar event in Datastore."""
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


def list_events(date: str = "") -> dict:
    """Lists calendar events. Optionally filter by date (YYYY-MM-DD)."""
    query = ds.query(kind="Event")
    events = [dict(e) | {"id": e.key.id} for e in query.fetch()]
    if date:
        events = [e for e in events if e.get("start_time", "").startswith(date)]
    return {"events": events, "count": len(events)}


def create_note(title: str, content: str, tags: str = "") -> dict:
    """Creates a note and stores it in Datastore."""
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


def search_notes(query: str) -> dict:
    """Searches notes by title or content keyword."""
    all_notes = [dict(e) | {"id": e.key.id} for e in ds.query(kind="Note").fetch()]
    results = [
        n for n in all_notes
        if query.lower() in n.get("title", "").lower()
        or query.lower() in n.get("content", "").lower()
    ]
    return {"notes": results, "count": len(results)}


task_agent = Agent(
    name="task_agent",
    model=model_name,
    description="Manages to-do tasks: create, list, and update task status.",
    instruction="""
    You are a Task Manager. Based on the user's PROMPT, handle task-related requests.
    - To create a task: use create_task with title, description, priority (low/medium/high), due_date.
    - To list tasks: use list_tasks, optionally filter by status or priority.
    - To update a task: use update_task_status with task_id and new status.
    Always confirm what action you took.
    PROMPT: { PROMPT }
    """,
    tools=[create_task, list_tasks, update_task_status],
    output_key="task_data",
)

calendar_agent = Agent(
    name="calendar_agent",
    model=model_name,
    description="Manages calendar events: schedule and list events.",
    instruction="""
    You are a Calendar Manager. Based on the user's PROMPT, handle scheduling requests.
    - To create an event: use create_event with title, start_time, end_time (ISO format YYYY-MM-DDTHH:MM), description, location.
    - To list events: use list_events, optionally filter by date (YYYY-MM-DD).
    Always confirm what action you took.
    PROMPT: { PROMPT }
    """,
    tools=[create_event, list_events],
    output_key="calendar_data",
)

notes_agent = Agent(
    name="notes_agent",
    model=model_name,
    description="Manages notes: save and search information.",
    instruction="""
    You are a Notes Manager. Based on the user's PROMPT, handle note-related requests.
    - To create a note: use create_note with title, content, and optional tags.
    - To search notes: use search_notes with a keyword query.
    Always confirm what action you took.
    PROMPT: { PROMPT }
    """,
    tools=[create_note, search_notes],
    output_key="notes_data",
)

response_formatter = Agent(
    name="response_formatter",
    model=model_name,
    description="Synthesizes outputs from all sub-agents into a clear, friendly response.",
    instruction="""
    You are the final step in the productivity assistant workflow.
    Combine the results from task_data, calendar_data, and notes_data into one clear,
    friendly summary for the user.
    - Only mention sections that have actual data.
    - Be concise and helpful.
    - If an action was taken (created/updated), confirm it clearly.
    task_data:     { task_data }
    calendar_data: { calendar_data }
    notes_data:    { notes_data }
    """,
)

productivity_workflow = SequentialAgent(
    name="productivity_workflow",
    description="Coordinates task, calendar, and notes agents to handle user requests.",
    sub_agents=[
        task_agent,
        calendar_agent,
        notes_agent,
        response_formatter,
    ],
)

root_agent = Agent(
    name="greeter",
    model=model_name,
    description="Main entry point for the Productivity Assistant.",
    instruction="""
    You are a friendly Productivity Assistant.
    - Greet the user and let them know you can help with tasks, scheduling, and notes.
    - When the user tells you what they need, use 'add_prompt_to_state' to save their request.
    - Then transfer control to 'productivity_workflow'.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[productivity_workflow],
)