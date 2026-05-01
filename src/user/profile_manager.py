# src/user/profile_manager.py
import json
import os
import tempfile
import shutil
from datetime import datetime


class UserProfileManager:
    def __init__(self):
        BASE_DIR = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.file_path = os.path.join(BASE_DIR, "data", "user_profiles.json")

        # Ensure data directory exists
        data_dir = os.path.dirname(self.file_path)
        os.makedirs(data_dir, exist_ok=True)

        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f, indent=4)

    # ── Core I/O ──────────────────────────────────────────────────────────────

    def load_profiles(self) -> dict:
        """Load all user profiles. Returns {} on any read/parse error."""
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_profiles(self, data: dict) -> bool:
        """
        Save all user profiles atomically.

        BUG FIX 1: Old version wrote directly to user_profiles.json.
        If the app crashed mid-write the file became corrupt JSON and
        ALL profiles were silently lost on the next load.

        Fix: write to a temp file first, then rename (atomic on all
        major OS).  If the write fails, the original file is untouched.

        BUG FIX 4: Old version had no error handling — a full disk or
        locked file raised an unhandled OSError that crashed the app.
        Now caught and returned as False so the caller can handle it.
        """
        try:
            dir_name = os.path.dirname(self.file_path)
            # Write to a temp file in the same directory (same filesystem)
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(data, tmp, indent=4)
                tmp_path = tmp.name
            # Atomic rename — replaces the target file in one OS operation
            shutil.move(tmp_path, self.file_path)
            return True
        except Exception as e:
            print(f"❌ Could not save profiles: {e}")
            # Clean up temp file if it was created
            try:
                if "tmp_path" in dir() and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
            return False

    # ── User CRUD ─────────────────────────────────────────────────────────────

    def get_user(self, username: str) -> dict | None:
        """Return a user's profile dict, or None if not found."""
        return self.load_profiles().get(username)

    def create_or_update_user(self, username: str, settings: dict) -> bool:
        """
        Create or update a user profile.

        BUG FIX 3: Old version called profiles[username].update(settings)
        which would overwrite 'saved_phrases' if 'settings' happened to
        contain that key — deleting all the user's saved phrases silently.

        Fix: explicitly exclude 'saved_phrases' (and other internal keys)
        from the settings dict before merging, so they can never be
        accidentally overwritten by a UI settings save.
        """
        profiles = self.load_profiles()

        # Keys that must never be overwritten by a settings update
        protected_keys = {"saved_phrases", "created_at", "last_phrase_added"}

        # Strip any protected keys from the incoming settings
        safe_settings = {k: v for k, v in settings.items()
                         if k not in protected_keys}

        if username in profiles:
            profiles[username].update(safe_settings)
            profiles[username]["last_updated"] = datetime.now().isoformat()
        else:
            profiles[username] = {
                **safe_settings,
                "created_at":   datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "saved_phrases": [],
            }

        return self.save_profiles(profiles)

    def delete_user(self, username: str) -> bool:
        """Delete a user profile entirely."""
        profiles = self.load_profiles()
        if username in profiles:
            del profiles[username]
            return self.save_profiles(profiles)
        return False

    def list_all_users(self) -> list:
        """Return a list of all registered usernames."""
        return list(self.load_profiles().keys())

    # ── Phrase management ─────────────────────────────────────────────────────

    def add_phrase(self, username: str, phrase: str) -> bool:
        """
        Add a saved phrase for a user.

        BUG FIX 2: Old version silently returned False if the username
        didn't exist yet, giving no feedback and losing the phrase.
        This could happen if the profile save hadn't completed before
        the first add_phrase call (race condition in Streamlit reruns).

        Fix: if the user doesn't exist, create a minimal profile first
        so the phrase is never silently dropped.
        """
        profiles = self.load_profiles()

        # Auto-create a minimal profile if the user doesn't exist yet
        if username not in profiles:
            profiles[username] = {
                "created_at":   datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "saved_phrases": [],
            }

        # Ensure saved_phrases key exists (defensive for old profile files)
        if "saved_phrases" not in profiles[username]:
            profiles[username]["saved_phrases"] = []

        # Avoid duplicates
        if phrase in profiles[username]["saved_phrases"]:
            return False   # already saved — not an error, just a no-op

        profiles[username]["saved_phrases"].append(phrase)
        profiles[username]["last_phrase_added"] = datetime.now().isoformat()
        return self.save_profiles(profiles)

    def get_phrases(self, username: str) -> list:
        """Return the list of saved phrases for a user."""
        return self.load_profiles().get(username, {}).get("saved_phrases", [])

    def delete_phrase(self, username: str, phrase_index: int):
        """
        Delete a saved phrase by index.
        Returns the deleted phrase string, or None if index was invalid.
        """
        profiles = self.load_profiles()

        if username in profiles and "saved_phrases" in profiles[username]:
            phrases = profiles[username]["saved_phrases"]
            if 0 <= phrase_index < len(phrases):
                deleted = phrases.pop(phrase_index)
                profiles[username]["saved_phrases"] = phrases
                self.save_profiles(profiles)
                return deleted
        return None

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_user_stats(self, username: str) -> dict | None:
        """Return a summary dict of a user's profile, or None if not found."""
        user = self.get_user(username)
        if not user:
            return None
        return {
            "username":           username,
            "created_at":         user.get("created_at"),
            "last_updated":       user.get("last_updated"),
            "saved_phrases_count": len(user.get("saved_phrases", [])),
            "theme":              user.get("theme",      "light"),
            "tts_speed":          user.get("tts_speed",  1.0),
            "font_size":          user.get("font_size",  "medium"),
        }