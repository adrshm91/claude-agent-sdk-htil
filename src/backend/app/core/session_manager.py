import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import ProcessError

from .session import AgentSession

logger = logging.getLogger(__name__)

# System message patterns to filter out from previews
SYSTEM_MESSAGE_PATTERNS = [
    r"^<command-name>",
    r"^<command-message>",
    r"^<command-args>",
    r"^<local-command-stdout>",
    r"^<system-reminder>",
    r"^Caveat:",
    r"^This session is being continued from a previous",
    r"^Invalid API key",
    r'^\{"subtasks":',
    r"CRITICAL: You MUST respond with ONLY a JSON",
    r"^Warmup$",
]

# Compiled regex for performance
SYSTEM_MESSAGE_REGEX = re.compile("|".join(SYSTEM_MESSAGE_PATTERNS))


def _is_system_message(content: str) -> bool:
    """Check if a message content is a system message that should be filtered."""
    if not content:
        return False
    return bool(SYSTEM_MESSAGE_REGEX.search(content))


def _extract_text_content(content: Any) -> str | None:
    """Extract text content from various message content formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and len(content) > 0:
        first_block = content[0]
        if isinstance(first_block, dict):
            return first_block.get("text", "")
        if isinstance(first_block, str):
            return first_block
    return None


def _parse_jsonl_sessions(file_path: Path) -> dict[str, Any]:
    """
    Parse a JSONL session file and extract session metadata.

    Returns a dict with:
        - session_id: str
        - summary: str
        - message_count: int
        - last_activity: datetime
        - cwd: str
        - last_user_message: str
        - last_assistant_message: str
        - first_user_msg_uuid: str (for timeline grouping)
        - entries: list (raw entries for grouping)
    """
    sessions: dict[str, dict] = {}
    entries: list[dict] = []
    pending_summaries: dict[str, str] = {}  # leafUuid -> summary

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    entries.append(entry)

                    # Handle summary entries without sessionId
                    if (
                        entry.get("type") == "summary"
                        and entry.get("summary")
                        and not entry.get("sessionId")
                        and entry.get("leafUuid")
                    ):
                        pending_summaries[entry["leafUuid"]] = entry["summary"]

                    session_id = entry.get("sessionId")
                    if not session_id:
                        continue

                    if session_id not in sessions:
                        sessions[session_id] = {
                            "id": session_id,
                            "summary": "New Session",
                            "message_count": 0,
                            "last_activity": datetime.now(timezone.utc),
                            "cwd": entry.get("cwd", ""),
                            "last_user_message": None,
                            "last_assistant_message": None,
                            "first_user_msg_uuid": None,
                            "parent_uuid": None,
                        }

                    session = sessions[session_id]

                    # Apply pending summary if parentUuid matches
                    if (
                        session["summary"] == "New Session"
                        and entry.get("parentUuid")
                        and entry["parentUuid"] in pending_summaries
                    ):
                        session["summary"] = pending_summaries[entry["parentUuid"]]

                    # Update summary from summary entries
                    if entry.get("type") == "summary" and entry.get("summary"):
                        session["summary"] = entry["summary"]

                    # Track messages
                    msg = entry.get("message", {})
                    role = msg.get("role")
                    content = msg.get("content")

                    if role == "user" and content:
                        text_content = _extract_text_content(content)
                        if text_content and not _is_system_message(text_content):
                            session["last_user_message"] = text_content
                            # Track first user message UUID for timeline grouping
                            if entry.get("parentUuid") is None and entry.get("uuid"):
                                if not session["first_user_msg_uuid"]:
                                    session["first_user_msg_uuid"] = entry["uuid"]

                    elif role == "assistant" and content:
                        # Skip API error messages
                        if entry.get("isApiErrorMessage"):
                            continue
                        text_content = _extract_text_content(content)
                        if text_content and not _is_system_message(text_content):
                            session["last_assistant_message"] = text_content

                    session["message_count"] += 1

                    if entry.get("timestamp"):
                        try:
                            session["last_activity"] = datetime.fromisoformat(
                                entry["timestamp"].replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                except json.JSONDecodeError:
                    continue

        # Set final summary based on messages if no summary exists
        for session in sessions.values():
            if session["summary"] == "New Session":
                last_msg = (
                    session["last_user_message"] or session["last_assistant_message"]
                )
                if last_msg:
                    session["summary"] = (
                        last_msg[:50] + "..." if len(last_msg) > 50 else last_msg
                    )

        return {
            "sessions": list(sessions.values()),
            "entries": entries,
        }

    except Exception:
        return {"sessions": [], "entries": []}


class SessionManager:
    """Manages user sessions.

    Each session maintains its own SDK client, conversation history,
    and permission state. Supports session creation, restoration,
    and cleanup.
    """

    def __init__(self):
        """Initialize the session manager."""
        self._current_session: AgentSession | None = None
        self._session_dir = Path.home() / ".claude" / "projects"

    @property
    def has_active_session(self) -> bool:
        """Check if there is an active session."""
        return self._current_session is not None

    async def create_session(
        self,
    ) -> AgentSession:
        """
        Create a new session or resume an existing one.
        Only one session can be active at a time.

        Returns:
            The AgentSession instance
        """

        # Clean up existing session if any
        await self.close_session()

        self._current_session = AgentSession()

        await self._current_session.connect()

        return self._current_session

    async def get_session(
        self,
        session_id: str,
    ) -> AgentSession:
        """
        Get an active session by ID, attempting to resume if it exists in Claude.

        Args:
            session_id: The session ID to resume

        Returns:
            The AgentSession instance (either resumed or newly created)

        Raises:
            HTTPException: If session creation fails after resume attempt fails
        """

        if (
            self._current_session is not None
            and session_id == self._current_session.session_id
        ):
            logger.info(f"Using existing active session: {session_id}")
            return self._current_session

        # Clean up existing session if any
        await self.close_session()

        # Try to resume the session with minimal configuration
        self._current_session = AgentSession()

        try:
            await self._current_session.connect(session_id)
            logger.info(f"✓ Auto-resumed session: {session_id}")
            return self._current_session
        except ProcessError as e:
            logger.warning(
                f"Failed to resume session {session_id}: exit_code={e.exit_code} | stderr={e.stderr!r}"
            )
            logger.info(
                "Session doesn't exist in Claude, creating a new session instead"
            )

            # Clean up the failed session attempt
            self._current_session = None

            # Fall back to creating a new session
            return await self.create_session()

    async def close_session(self):
        """
        Close and cleanup a session.

        Args:
            session_id: The session ID to close
        """
        if self._current_session is not None:
            await self._current_session.disconnect()
            self._current_session = None

    def list_available_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        group_timelines: bool = True,
    ) -> dict[str, Any]:
        """
        List all available sessions (both active in-memory and persisted on disk),
        with pagination and timeline grouping support.

        Timeline grouping merges multiple sessions that share the same first user message
        (i.e., sessions that were resumed from the same conversation) into a single entry,
        showing only the most recent one.

        Args:
            limit: Maximum number of sessions to return (default: 20).
            offset: Number of sessions to skip for pagination (default: 0).
            group_timelines: Whether to group sessions by timeline (default: True).

        Returns:
            Dict with:
                - sessions: List of session information dictionaries
                - has_more: Whether there are more sessions available
                - total: Total number of sessions (after grouping)
                - offset: Current offset
                - limit: Current limit
        """

        all_entries: list[dict] = []
        all_sessions: dict[str, dict] = {}  # session_id -> session data
        session_ids_seen: set[str] = set()

        if self._current_session and self._current_session.session_id:
            path_key = (
                self._current_session.cwd.replace("/", "-").replace("_", "-")
                if self._current_session.cwd
                else "default"
            )
            # Try to parse session file for metadata
            session_file_path = (
                self.session_dir
                / path_key
                / f"{self._current_session.session_id}.jsonl"
            )
            session_data = {
                "id": self._current_session.session_id,
                "summary": "Active session",
                "message_count": self._current_session.message_count,
                "last_activity": self._current_session.last_activity,
                "cwd": self._current_session.cwd or "",
                "last_user_message": None,
                "last_assistant_message": None,
                "first_user_msg_uuid": None,
                "project": path_key,
                "active": True,
            }

            if session_file_path.exists():
                parsed = _parse_jsonl_sessions(session_file_path)
                for s in parsed["sessions"]:
                    if s["id"] == self._current_session.session_id:
                        session_data.update(
                            {
                                "summary": s["summary"],
                                "message_count": s["message_count"],
                                "last_activity": s["last_activity"],
                                "last_user_message": s["last_user_message"],
                                "last_assistant_message": s["last_assistant_message"],
                                "first_user_msg_uuid": s["first_user_msg_uuid"],
                            }
                        )
                        break
                all_entries.extend(parsed["entries"])
            all_sessions[self._current_session.session_id] = session_data
            session_ids_seen.add(self._current_session.session_id)

        # Then, scan persisted sessions from disk
        if self.session_dir.exists():
            project_dirs = list(self.session_dir.iterdir())

            # Sort by modification time (newest first) for early exit optimization
            project_dirs_with_mtime = []

            for pd in project_dirs:
                if pd.exists() and pd.is_dir():
                    try:
                        mtime = pd.stat().st_mtime
                        project_dirs_with_mtime.append((pd, mtime))
                    except Exception:
                        project_dirs_with_mtime.append((pd, 0))

            project_dirs_with_mtime.sort(key=lambda x: x[1], reverse=True)

            for project_dir, _ in project_dirs_with_mtime:
                # Get all jsonl files sorted by mtime
                session_files = []
                for sf in project_dir.glob("*.jsonl"):
                    try:
                        session_files.append((sf, sf.stat().st_mtime))
                    except Exception:
                        continue

                session_files.sort(key=lambda x: x[1], reverse=True)

                for session_file, _ in session_files:
                    session_id = session_file.stem

                    if session_id in session_ids_seen:
                        continue

                    parsed = _parse_jsonl_sessions(session_file)
                    all_entries.extend(parsed["entries"])

                    for s in parsed["sessions"]:
                        if s["id"] not in all_sessions:
                            all_sessions[s["id"]] = {
                                **s,
                                "project": project_dir.name,
                                "active": False,
                            }

                    session_ids_seen.add(session_id)

                    # Early exit optimization
                    if len(all_sessions) >= (limit + offset) * 2:
                        break

        # Timeline grouping: group sessions by first user message UUID
        if group_timelines:
            session_groups: dict[str, dict] = {}  # first_user_msg_uuid -> group data
            session_to_group: dict[str, str] = {}  # session_id -> first_user_msg_uuid

            for session_id, session in all_sessions.items():
                first_uuid = session.get("first_user_msg_uuid")
                if not first_uuid:
                    # No first user message UUID, treat as standalone
                    continue
                if first_uuid not in session_groups:
                    session_groups[first_uuid] = {
                        "latest_session": session,
                        "all_sessions": [session],
                    }
                else:
                    group = session_groups[first_uuid]
                    group["all_sessions"].append(session)

                    # Update latest if this session is more recent
                    if (
                        session["last_activity"]
                        > group["latest_session"]["last_activity"]
                    ):
                        group["latest_session"] = session

                session_to_group[session_id] = first_uuid

            # Build final session list
            grouped_session_ids: set[str] = set()
            for group in session_groups.values():
                for s in group["all_sessions"]:
                    grouped_session_ids.add(s["id"])

            # Sessions from groups (only show latest)
            visible_sessions = []
            for first_uuid, group in session_groups.items():
                session = {**group["latest_session"]}
                if len(group["all_sessions"]) > 1:
                    session["is_grouped"] = True
                    session["group_size"] = len(group["all_sessions"])
                    session["group_sessions"] = [s["id"] for s in group["all_sessions"]]
                visible_sessions.append(session)

            # Add standalone sessions (not in any group)
            for session_id, session in all_sessions.items():
                if session_id not in grouped_session_ids:
                    visible_sessions.append(session)
        else:
            visible_sessions = list(all_sessions.values())

        # Filter out sessions with JSON-like summaries (Task Master errors)
        visible_sessions = [
            s for s in visible_sessions if not s.get("summary", "").startswith('{ "')
        ]

        # Sort by last activity (newest first)
        visible_sessions.sort(
            key=lambda x: (
                x["last_activity"]
                if isinstance(x["last_activity"], datetime)
                else datetime.fromisoformat(
                    str(x["last_activity"]).replace("Z", "+00:00")
                )
            ),
            reverse=True,
        )

        total = len(visible_sessions)
        paginated = visible_sessions[offset : offset + limit]
        has_more = offset + limit < total

        # Format output
        result_sessions = []
        for s in paginated:
            last_activity = s["last_activity"]
            if isinstance(last_activity, datetime):
                modified = last_activity.isoformat()
            else:
                modified = str(last_activity)

            result = {
                "session_id": s["id"],
                "modified": modified,
                "preview": s.get("summary", "No preview")[:100],
                "project": s.get("project", ""),
                "message_count": s.get("message_count", 0),
                "first_message": (s.get("last_user_message") or "")[:100]
                if s.get("last_user_message")
                else None,
                "active": s.get("active", False),
                "cwd": s.get("cwd", ""),
            }

            # Add grouping metadata if present
            if s.get("is_grouped"):
                result["is_grouped"] = True
                result["group_size"] = s["group_size"]
                result["group_sessions"] = s["group_sessions"]

            result_sessions.append(result)

        return {
            "sessions": result_sessions,
            "has_more": has_more,
            "total": total,
            "offset": offset,
            "limit": limit,
        }
