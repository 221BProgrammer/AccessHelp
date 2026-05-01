# src/emergency/alert.py
import os
import time
import json
import requests
import webbrowser
import threading
from datetime import datetime

# ── Optional: pygame for LOCAL alarm (on the server/laptop running the app) ──
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False
    print("⚠️ pygame not available — local alarm sound disabled.")

# ── Twilio (primary SMS provider) ────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("⚠️ Twilio not installed. Run: pip install twilio")

# ── GPS / location libraries ──────────────────────────────────────────────────
try:
    import gpsd
    GPSD_AVAILABLE = True
except ImportError:
    GPSD_AVAILABLE = False

try:
    import geocoder
    GEOCODER_AVAILABLE = True
except ImportError:
    GEOCODER_AVAILABLE = False


class EmergencySystem:
    def __init__(self):
        BASE_DIR = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.alarm_path   = os.path.join(BASE_DIR, "src", "emergency", "alarm.mp3")
        self.contacts_file = os.path.join(BASE_DIR, "data", "emergency_contacts.json")

        # ── Cooldown ──────────────────────────────────────────────────────────
        self.last_alert_time = 0
        self.alert_cooldown  = 30          # seconds between alerts

        # ── Twilio config (read from environment variables) ───────────────────
        # Set these in your terminal before running:
        #   export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxx"
        #   export TWILIO_AUTH_TOKEN="your_auth_token"
        #   export TWILIO_PHONE_NUMBER="+1xxxxxxxxxx"   ← your Twilio number
        self.twilio_account_sid   = os.environ.get("TWILIO_ACCOUNT_SID",   "")
        self.twilio_auth_token    = os.environ.get("TWILIO_AUTH_TOKEN",    "")
        self.twilio_phone_number  = os.environ.get("TWILIO_PHONE_NUMBER",  "")

        self.twilio_configured = (
            TWILIO_AVAILABLE
            and bool(self.twilio_account_sid)
            and bool(self.twilio_auth_token)
            and bool(self.twilio_phone_number)
        )

        if self.twilio_configured:
            self.twilio_client = TwilioClient(
                self.twilio_account_sid, self.twilio_auth_token
            )
            print("✅ Twilio SMS + Voice Call client ready!")
        else:
            self.twilio_client = None
            print("⚠️ Twilio not configured.")
            print("   Set these environment variables before running:")
            print("   export TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxx'")
            print("   export TWILIO_AUTH_TOKEN='your_auth_token'")
            print("   export TWILIO_PHONE_NUMBER='+1xxxxxxxxxx'")
            print("   Sign up free at https://www.twilio.com")

        # ── NOTE: TextBelt removed — it is blocked in India ───────────────────
        # Twilio is the only reliable option for Indian numbers (+91xxxxxxxxxx).
        # Free Twilio trial gives ~$15 credit which covers hundreds of SMS + calls.

        # ── GPS init ──────────────────────────────────────────────────────────
        self.gps_enabled = False
        self._init_gps()
        self.location = self._get_location()

    # ══════════════════════════════════════════════════════════════════════════
    # GPS / LOCATION
    # ══════════════════════════════════════════════════════════════════════════

    def _init_gps(self):
        if not GPSD_AVAILABLE:
            return
        try:
            gpsd.connect()
            self.gps_enabled = True
            print("✅ GPS module connected!")
        except Exception as e:
            print(f"GPS init error: {e}")
            self.gps_enabled = False

    def _get_precise_gps_location(self):
        if not self.gps_enabled or not GPSD_AVAILABLE:
            return None
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:
                return {
                    "latitude":  packet.lat,
                    "longitude": packet.lon,
                    "altitude":  getattr(packet, "alt", "Unknown"),
                    "accuracy":  "high (GPS)",
                }
        except Exception as e:
            print(f"GPS read error: {e}")
        return None

    def _get_location(self):
        """Try GPS → IP-API → geocoder → unknown fallback."""

        # 1. GPS (most accurate)
        loc = self._get_precise_gps_location()
        if loc:
            print("📍 Location source: GPS")
            return loc

        # 2. IP-API
        try:
            r = requests.get("https://ipapi.co/json/", timeout=5)
            if r.status_code == 200:
                d = r.json()
                print("📍 Location source: IP-API")
                return {
                    "latitude":  d.get("latitude",     "Unknown"),
                    "longitude": d.get("longitude",    "Unknown"),
                    "city":      d.get("city",         "Unknown"),
                    "region":    d.get("region",       "Unknown"),
                    "country":   d.get("country_name", "Unknown"),
                    "postal":    d.get("postal",       "Unknown"),
                    "ip":        d.get("ip",           "Unknown"),
                    "accuracy":  "medium (IP)",
                }
        except Exception as e:
            print(f"IP location error: {e}")

        # 3. geocoder
        if GEOCODER_AVAILABLE:
            try:
                g = geocoder.ip("me")
                if g.ok:
                    print("📍 Location source: geocoder fallback")
                    return {
                        "latitude":  g.latlng[0] if g.latlng else "Unknown",
                        "longitude": g.latlng[1] if g.latlng else "Unknown",
                        "city":    g.city    or "Unknown",
                        "region":  g.state   or "Unknown",
                        "country": g.country or "Unknown",
                        "accuracy": "low (IP geocoder)",
                    }
            except Exception as e:
                print(f"Geocoder error: {e}")

        print("⚠️ Could not determine location.")
        return {
            "latitude":  "Unknown",
            "longitude": "Unknown",
            "city":      "Unknown",
            "region":    "Unknown",
            "country":   "Unknown",
            "ip":        "Unknown",
            "accuracy":  "none",
        }

    def _refresh_location(self):
        self.location = self._get_location()
        return self.location

    def _get_google_maps_link(self):
        lat = self.location.get("latitude")
        lon = self.location.get("longitude")
        if lat != "Unknown" and lon != "Unknown":
            return f"https://www.google.com/maps?q={lat},{lon}"
        return "https://www.google.com/maps"

    # ══════════════════════════════════════════════════════════════════════════
    # PHONE-NUMBER HANDLING
    # ══════════════════════════════════════════════════════════════════════════

    def _clean_phone_number(self, phone: str) -> str:
        """
        Strip spaces/dashes but keep the leading '+' and country code
        exactly as the user entered it.  We never add a country code
        automatically — the user must include it (e.g. +91xxxxxxxxxx).
        """
        # Remove everything except digits and leading +
        digits = "".join(c for c in phone if c.isdigit() or c == "+")
        # Ensure only one leading +
        if digits.count("+") > 1:
            digits = "+" + digits.replace("+", "")
        return digits

    # ══════════════════════════════════════════════════════════════════════════
    # SMS SENDING
    # ══════════════════════════════════════════════════════════════════════════

    def _send_twilio_sms(self, phone: str, message: str) -> bool:
        if not self.twilio_configured:
            print("❌ Twilio not configured — cannot send SMS.")
            return False
        try:
            clean = self._clean_phone_number(phone)
            self.twilio_client.messages.create(
                body=message[:1600],
                from_=self.twilio_phone_number,
                to=clean,
            )
            print(f"✅ Twilio SMS → {phone}")
            return True
        except Exception as e:
            print(f"❌ Twilio SMS error: {e}")
            return False

    def _make_twilio_alarm_call(self, phone: str, fall_detected: bool = False) -> bool:
        """
        Call the contact's phone using Twilio.
        When they pick up, they hear a spoken alarm message.
        This is the closest thing to "playing an alarm on their phone"
        from a remote web app — their phone rings loudly and they
        hear the emergency message when they answer.

        HOW IT WORKS:
        - Twilio calls the contact's number
        - When answered, Twilio reads out a TwiML message (text-to-speech)
        - The contact hears: "EMERGENCY ALERT. [Name] needs help immediately.
                             This is an automated call from AccessHelp."
        - Their phone rings with full ringtone volume — they cannot miss it
        """
        if not self.twilio_configured:
            print("❌ Twilio not configured — cannot make alarm call.")
            return False
        try:
            clean  = self._clean_phone_number(phone)
            maps   = self._get_google_maps_link()
            city   = self.location.get("city", "unknown location")
            alert_type = "A fall has been detected" if fall_detected else "An emergency S O S has been triggered"

            # TwiML — what Twilio speaks when the contact picks up
            # <Say> uses Twilio's text-to-speech engine
            # Repeating twice ensures they hear it even if distracted
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-IN">
        Emergency Alert. Emergency Alert.
        {alert_type} by one of your contacts.
        Their current location is {city}.
        This is an automated emergency call from AccessHelp.
        Please check your messages for the location link and respond immediately.
        Repeating.
        {alert_type} by one of your contacts.
        Their location is {city}.
        Please respond immediately.
    </Say>
    <Pause length="1"/>
</Response>"""

            self.twilio_client.calls.create(
                twiml=twiml,
                from_=self.twilio_phone_number,
                to=clean,
            )
            print(f"✅ Twilio alarm call → {phone}")
            return True

        except Exception as e:
            print(f"❌ Twilio call error: {e}")
            return False

    def _send_sms(self, phone: str, message: str) -> bool:
        """Send SMS via Twilio. TextBelt removed — blocked in India."""
        if self.twilio_configured:
            return self._send_twilio_sms(phone, message)
        print("❌ No SMS provider configured. Please set up Twilio.")
        return False

    def _send_email(self, email: str, message: str) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            smtp_server    = os.environ.get("SMTP_SERVER",    "smtp.gmail.com")
            smtp_port      = int(os.environ.get("SMTP_PORT",  "587"))
            sender_email   = os.environ.get("SENDER_EMAIL",   "")
            sender_password = os.environ.get("SENDER_PASSWORD", "")

            if not sender_email or not sender_password:
                print("⚠️ Email credentials not configured.")
                return False

            msg = MIMEMultipart()
            msg["From"]    = sender_email
            msg["To"]      = email
            msg["Subject"] = "🚨 EMERGENCY ALERT — AccessHelp"
            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print(f"✅ Email → {email}")
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # LOCAL ALARM  (plays on the machine running the app, in a background thread)
    # ══════════════════════════════════════════════════════════════════════════

    def _play_local_alarm(self):
        """
        Play the alarm sound locally (on the server/laptop) without
        blocking the Streamlit UI thread.
        """
        if not PYGAME_AVAILABLE:
            return

        def _alarm():
            try:
                pygame.mixer.music.load(self.alarm_path)
                pygame.mixer.music.play()
                time.sleep(5)
                pygame.mixer.music.stop()
            except Exception as e:
                print(f"Alarm error: {e}")

        threading.Thread(target=_alarm, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD ALERT MESSAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_alert_message(self, fall_detected: bool) -> str:
        """
        Build the SMS text that will be sent to emergency contacts.
        Includes live GPS link so the contact can see exactly where you are.
        """
        timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji      = "⚠️ FALL DETECTED ⚠️" if fall_detected else "🆘 EMERGENCY SOS 🆘"
        maps_link  = self._get_google_maps_link()

        lat = self.location.get("latitude",  "Unknown")
        lon = self.location.get("longitude", "Unknown")
        city   = self.location.get("city",   "")
        region = self.location.get("region", "")
        accuracy = self.location.get("accuracy", "unknown")

        lines = [
            emoji,
            f"Time: {timestamp}",
            "",
            "📍 LIVE LOCATION:",
        ]

        if lat != "Unknown":
            lines.append(f"Coordinates: {lat}, {lon}")
            lines.append(f"📌 Open in Maps: {maps_link}")
        else:
            lines.append("Location: Could not determine")

        if city:
            lines.append(f"Area: {city}, {region}")

        lines.append(f"Accuracy: {accuracy}")
        lines.append("")
        lines.append("This is an automated alert from AccessHelp.")
        lines.append("Please respond immediately!")

        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC TRIGGER METHODS
    # ══════════════════════════════════════════════════════════════════════════

    def trigger_alert(self, fall_detected: bool = False) -> bool:
        """
        Main emergency trigger:
        1. Checks cooldown
        2. Refreshes GPS location
        3. Plays local alarm (background thread — UI never freezes)
        4. Sends SMS to every saved contact (includes live Google Maps link)
        5. Sends email if configured
        6. Opens Google Maps in browser
        7. Logs the event
        """
        # ── Cooldown guard ────────────────────────────────────────────────────
        now = time.time()
        if now - self.last_alert_time < self.alert_cooldown:
            remaining = int(self.alert_cooldown - (now - self.last_alert_time))
            print(f"⚠️ Cooldown active — wait {remaining}s")
            return False
        self.last_alert_time = now

        # ── Refresh location ──────────────────────────────────────────────────
        self._refresh_location()

        # ── Build message ─────────────────────────────────────────────────────
        message = self._build_alert_message(fall_detected)
        print("=" * 60)
        print(message)
        print("=" * 60)

        # ── Play local alarm in background (UI stays responsive) ──────────────
        self._play_local_alarm()

        # ── Send SMS + alarm call to all contacts ────────────────────────────
        contacts = self._get_emergency_contacts()
        if contacts:
            sms_sent   = 0
            calls_made = 0
            for contact in contacts:
                phone = contact.get("phone", "").strip()
                email = contact.get("email", "").strip()
                name  = contact.get("name",  "Contact")

                if phone:
                    # 1. Send SMS with full location details
                    personalised = message + f"\n\n— Sent by {name}'s AccessHelp app"
                    if self._send_sms(phone, personalised):
                        sms_sent += 1

                    # 2. Make an alarm call so their phone rings loudly
                    #    Even if they miss the SMS, the ringing phone will
                    #    alert them. When they pick up they hear the message.
                    if self._make_twilio_alarm_call(phone, fall_detected):
                        calls_made += 1

                if email:
                    self._send_email(email, message)

            print(f"✅ SMS sent to {sms_sent}/{len(contacts)} contacts.")
            print(f"✅ Alarm calls made to {calls_made}/{len(contacts)} contacts.")
        else:
            print("⚠️ No emergency contacts saved. Add contacts in the app.")

        # ── Open maps in browser ──────────────────────────────────────────────
        try:
            webbrowser.open(self._get_google_maps_link())
        except Exception:
            pass

        # ── Log event ─────────────────────────────────────────────────────────
        self._log_alert(fall_detected)

        return True

    def trigger_fall_alert(self) -> bool:
        return self.trigger_alert(fall_detected=True)

    # ══════════════════════════════════════════════════════════════════════════
    # CONTACT MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def _get_emergency_contacts(self) -> list:
        try:
            if os.path.exists(self.contacts_file):
                with open(self.contacts_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading contacts: {e}")
        return []

    def add_emergency_contact(self, name: str, phone: str, email: str = "") -> bool:
        """
        Save a new emergency contact.
        Phone number must include country code, e.g. +91xxxxxxxxxx for India.
        """
        # Validate that phone has a country code (starts with +)
        clean = self._clean_phone_number(phone)
        if not clean.startswith("+"):
            print(
                "⚠️ Phone number must include country code (e.g. +91xxxxxxxxxx). "
                "Contact NOT saved."
            )
            return False

        contacts = self._get_emergency_contacts()
        contacts.append(
            {
                "name":  name,
                "phone": clean,
                "email": email,
                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        with open(self.contacts_file, "w") as f:
            json.dump(contacts, f, indent=2)
        print(f"✅ Contact saved: {name} ({clean})")
        return True

    def remove_emergency_contact(self, index: int) -> bool:
        contacts = self._get_emergency_contacts()
        if 0 <= index < len(contacts):
            removed = contacts.pop(index)
            with open(self.contacts_file, "w") as f:
                json.dump(contacts, f, indent=2)
            print(f"✅ Removed: {removed['name']}")
            return True
        return False

    def test_alert(self) -> bool:
        """
        Send a harmless test SMS AND a test call to all contacts.
        Use this to verify Twilio is working before a real emergency.
        """
        if not self.twilio_configured:
            print("❌ Twilio not configured — test cannot run.")
            print("   Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")
            return False

        maps_link = self._get_google_maps_link()
        test_message = (
            "🔔 TEST — AccessHelp\n"
            "This is a TEST alert. No action needed.\n"
            f"📌 Test location link: {maps_link}\n"
            "If you received this SMS and a call, the emergency system is working!"
        )
        contacts = self._get_emergency_contacts()
        if not contacts:
            print("⚠️ No contacts found. Add contacts in the app first.")
            return False

        for contact in contacts:
            phone = contact.get("phone", "").strip()
            name  = contact.get("name", "Contact")
            if phone:
                # Test SMS
                self._send_sms(phone, test_message)
                # Test call — uses a short test TwiML message
                try:
                    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-IN">
        This is a test call from AccessHelp.
        The emergency alert system is working correctly.
        No action is needed. Thank you.
    </Say>
</Response>"""
                    clean = self._clean_phone_number(phone)
                    self.twilio_client.calls.create(
                        twiml=twiml,
                        from_=self.twilio_phone_number,
                        to=clean,
                    )
                    print(f"✅ Test call → {name} ({phone})")
                except Exception as e:
                    print(f"❌ Test call error: {e}")

        print("✅ Test SMS and calls sent! Check your phone.")
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # LOGGING
    # ══════════════════════════════════════════════════════════════════════════

    def _log_alert(self, fall_detected: bool):
        log_file = os.path.join(os.path.dirname(self.contacts_file), "emergency_log.txt")
        try:
            with open(log_file, "a") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Type    : {'Fall Detected' if fall_detected else 'Manual SOS'}\n")
                f.write(f"Location: {self.location}\n")
                f.write(f"Maps    : {self._get_google_maps_link()}\n")
        except Exception as e:
            print(f"Log error: {e}")


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    emergency = EmergencySystem()
    print("\n✅ Emergency system initialized successfully!")
    print(f"📍 Current location: {emergency.location}")
    print(f"🗺️  Maps link: {emergency._get_google_maps_link()}")