from flask import Flask, render_template, request, jsonify, session
import requests
import json
from datetime import datetime, date, timedelta
import re
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo  # Python 3.9+ (UK tz)

# UK timezone for date calculations
UK_TZ = ZoneInfo("Europe/London")

def today_uk():
    return datetime.now(UK_TZ).date()

def extract_time_from_text(text: str) -> str | None:
    """Extract time patterns from text and normalize to HH:MM:SS"""
    if not text: return None
    
    # Look for time patterns within the text
    # Pattern: "at 8 PM", "8 PM", "8pm", "19:30", etc.
    time_patterns = [
        r'\bat\s+(\d{1,2})\s+(pm|am)\b',  # "at 8 PM"
        r'\b(\d{1,2})\s+(pm|am)\b',        # "8 PM"
        r'\b(\d{1,2})(pm|am)\b',           # "8pm"
        r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b',  # "19:30" or "19:30:00"
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text.lower())
        if match:
            if 'pm' in pattern or 'am' in pattern:
                # AM/PM format
                h = int(match.group(1))
                if match.group(2) == "pm" and h != 12: h += 12
                if match.group(2) == "am" and h == 12: h = 0
                return f"{h:02d}:00:00"
            else:
                # 24h format
                h, mm = int(match.group(1)), int(match.group(2))
                ss = int(match.group(3)) if match.group(3) else 0
                return f"{h:02d}:{mm:02d}:{ss:02d}"
    
    return None

def normalize_time_to_hhmmss(t: str | None) -> str | None:
    if not t: return None
    # accept "7 pm", "7pm", "19:30", "19:30:15", "12:30", "12:30:00"
    s = t.strip().lower()
    
    print(f"DEBUG: normalize_time_to_hhmmss input: '{t}' -> '{s}'")
    
    # map common am/pm
    m_ampm = re.match(r"^(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?(am|pm)$", s)
    if m_ampm:
        h = int(m_ampm.group(1)); mm = int(m_ampm.group(2) or 0); ss = int(m_ampm.group(3) or 0)
        if m_ampm.group(4) == "pm" and h != 12: h += 12
        if m_ampm.group(4) == "am" and h == 12: h = 0
        result = f"{h:02d}:{mm:02d}:{ss:02d}"
        print(f"DEBUG: AM/PM match -> {result}")
        return result
    
    # 7pm without colon
    m_short = re.match(r"^(\d{1,2})(pm|am)$", s)
    if m_short:
        h = int(m_short.group(1))
        if m_short.group(2) == "pm" and h != 12: h += 12
        if m_short.group(2) == "am" and h == 12: h = 0
        result = f"{h:02d}:00:00"
        print(f"DEBUG: Short AM/PM match -> {result}")
        return result
    
    # Handle "8 PM" format (with space)
    m_space_ampm = re.match(r"^(\d{1,2})\s+(pm|am)$", s)
    if m_space_ampm:
        h = int(m_space_ampm.group(1))
        if m_space_ampm.group(2) == "pm" and h != 12: h += 12
        if m_space_ampm.group(2) == "am" and h == 12: h = 0
        result = f"{h:02d}:00:00"
        print(f"DEBUG: Space AM/PM match -> {result}")
        return result
    
    # 24h forms: "12:30", "19:30", "12:30:00"
    m_24 = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$", s)
    if m_24:
        h, mm, ss = int(m_24.group(1)), int(m_24.group(2)), int(m_24.group(3) or 0)
        result = f"{h:02d}:{mm:02d}:{ss:02d}"
        print(f"DEBUG: 24h match -> {result}")
        return result
    
    # Already in HH:MM:SS format
    if re.match(r"^([01]?\d|2[0-3]):([0-5]\d):([0-5]\d)$", s):
        print(f"DEBUG: Already HH:MM:SS format -> {s}")
        return s
    
    print(f"DEBUG: No time patterns matched")
    return None

MONTHS = "(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"

def parse_date_natural(text: str) -> date | None:
    t = text.lower()
    d0 = today_uk()
    
    print(f"DEBUG: parse_date_natural input: '{text}' -> '{t}'")
    print(f"DEBUG: today_uk() = {d0}")
    
    # keywords
    if "today" in t: 
        print(f"DEBUG: Found 'today' keyword")
        return d0
    if "tomorrow" in t or "tmr" in t: 
        print(f"DEBUG: Found 'tomorrow' keyword")
        return d0 + timedelta(days=1)
    if "this weekend" in t:
        # Saturday upcoming (or today if it's Sat)
        wd = d0.weekday()  # 0=Mon..6=Sun
        sat = d0 + timedelta(days=(5 - wd) % 7)
        print(f"DEBUG: Found 'this weekend' keyword -> {sat}")
        return sat
    
    # explicit weekday: "on Saturday", "next Friday"
    wk_map = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
    for name, idx in wk_map.items():
        if f"next {name}" in t or f"on {name}" in t or t.strip()==name:
            wd = d0.weekday()
            delta = (idx - wd) % 7
            if delta == 0: delta = 7  # "next" same weekday → a week later
            result = d0 + timedelta(days=delta)
            print(f"DEBUG: Found weekday '{name}' -> {result}")
            return result
    
    # "August 7", "7 Aug", "Aug 7th"
    m1 = re.search(rf"\b({MONTHS})[a-z]*\.?\s+(\d{{1,2}})(st|nd|rd|th)?\b", t)
    if m1:
        mon = m1.group(1)[:3]
        day = int(m1.group(2))
        year = d0.year
        print(f"DEBUG: Pattern 1 match: month='{mon}', day={day}, year={year}")
        # if that date already passed this year, roll to next year
        mon_num = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"].index(mon) + 1
        try:
            cand = date(year, mon_num, day)
            if cand < d0: 
                cand = date(year+1, mon_num, day)
                print(f"DEBUG: Date {cand} was in past, rolled to next year")
            print(f"DEBUG: Pattern 1 result: {cand}")
            return cand
        except ValueError:
            print(f"DEBUG: Pattern 1 ValueError")
            return None
    
    # "7 August"
    m2 = re.search(rf"\b(\d{{1,2}})\s+({MONTHS})[a-z]*\.?(st|nd|rd|th)?\b", t)
    if m2:
        day = int(m2.group(1)); mon = m2.group(2)[:3]
        year = d0.year
        print(f"DEBUG: Pattern 2 match: day={day}, month='{mon}', year={year}")
        mon_num = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"].index(mon) + 1
        try:
            cand = date(year, mon_num, day)
            if cand < d0: 
                cand = date(year+1, mon_num, day)
                print(f"DEBUG: Date {cand} was in past, rolled to next year")
            print(f"DEBUG: Pattern 2 result: {cand}")
            return cand
        except ValueError:
            print(f"DEBUG: Pattern 2 ValueError")
            return None
    
    # ISO date fallback
    m3 = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", t)
    if m3:
        try:
            cand = datetime.strptime(m3.group(1), "%Y-%m-%d").date()
            print(f"DEBUG: ISO date match: {cand}")
            return cand
        except ValueError:
            print(f"DEBUG: ISO date ValueError")
            return None
    
    print(f"DEBUG: No date patterns matched")
    return None

def parse_party(text: str) -> int | None:
    m = re.search(r"\b(\d+)\s*(people|persons|guests|pax|party|seats?)\b", text.lower())
    if m: return int(m.group(1))
    m2 = re.search(r"\b([1-9]|1[0-2])\b", text)  # conservative
    return int(m2.group(1)) if m2 else None

def not_past(d: date) -> bool:
    return d >= today_uk()

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'restaurant_booking_secret_key')

# Configuration

# Load from environment variables
BASE_URL_PREFIX = os.getenv("BASE_URL_PREFIX", "http://localhost:8547/api/ConsumerApi/v1/Restaurant")
RESTAURANT = os.getenv("RESTAURANT", "TheHungryUnicorn")
BASE_URL = f"{BASE_URL_PREFIX}/{RESTAURANT}"

TOKEN = os.getenv("BOOKING_API_TOKEN")
if not TOKEN:
    raise RuntimeError("BOOKING_API_TOKEN environment variable is required. Please set it in your .env file or environment.")

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded"
}

class BookingAssistant:
    def __init__(self):
        self.conversation_state = {}
        self.current_booking = {}
    
    def process_message(self, user_message):
        """Process user message and return appropriate response"""
        user_message = user_message.lower().strip()
        
        # Get or create session for this user
        session_id = "default"  # In a real app, use user ID or session ID
        sess = get_or_create_session(session_id)
        
        # Smart intent detection
        intent = self.detect_intent(user_message)
        
        # Debug logging
        print(f"DEBUG: User message: '{user_message}'")
        print(f"DEBUG: Detected intent: '{intent}'")
        print(f"DEBUG: Current session intent: '{sess['intent']}'")
        print(f"DEBUG: Current slots: {sess['slots']}")
        
        # If we have an active booking intent, continue with slot filling
        if sess["intent"] == "book":
            print("DEBUG: Continuing booking conversation")
            # Check if user is changing the date (e.g., "today", "tomorrow")
            new_date = parse_date_natural(user_message)
            if new_date:
                print("DEBUG: User changed date in booking mode, updating date slot")
                sess["slots"]["date"] = new_date
                # Check if we have all required slots now
                missing = next_missing_booking_slot(sess)
                if not missing:
                    # All slots filled, proceed with booking
                    return self.handle_booking_creation(user_message)
                else:
                    # Still missing slots, ask for next one
                    if missing == "time":
                        return {"reply": "What time?", "action": "ask_time"}
                    elif missing == "party":
                        return {"reply": "How many people?", "action": "ask_party"}
            
            return self.handle_booking_creation(user_message)
        
        # If we have an active availability intent, check if user wants to book
        if sess["intent"] == "check_availability":
            print("DEBUG: Continuing availability conversation")
            # Check if user is trying to book (has time/party info)
            if extract_time_from_text(user_message) or parse_party(user_message):
                print("DEBUG: User wants to book after availability check, switching to booking mode")
                sess["intent"] = "book"
                # Pre-fill slots from availability context
                if sess.get("availability_context"):
                    context = sess["availability_context"]
                    if context.get("date") and not sess["slots"]["date"]:
                        sess["slots"]["date"] = context["date"]
                    if context.get("party_size") and not sess["slots"]["party"]:
                        sess["slots"]["party"] = context["party_size"]
                return self.handle_booking_creation(user_message)
            
            # Check if user is changing the date (e.g., "today", "tomorrow")
            new_date = parse_date_natural(user_message)
            if new_date:
                print("DEBUG: User changed date, updating availability context")
                sess["availability_context"]["date"] = new_date
                return self.handle_availability_search(user_message)
                
            return self.handle_availability_search(user_message)
        
        # If we have an active booking intent, continue with slot filling
        if sess["intent"] == "book":
            print("DEBUG: Continuing booking conversation")
            
            # Check if user is selecting a time from suggestions
            selected_time = extract_time_from_text(user_message)
            if selected_time:
                print(f"DEBUG: User selected time: {selected_time}")
                sess["slots"]["time"] = selected_time
                # Now try to book with the selected time
                return self.handle_booking_creation(user_message)
            
            # Check if user is changing the date (e.g., "today", "tomorrow")
            new_date = parse_date_natural(user_message)
            if new_date:
                print("DEBUG: User changed date in booking mode, updating date slot")
                sess["slots"]["date"] = new_date
                # Check if we have all required slots now
                missing = next_missing_booking_slot(sess)
                if not missing:
                    # All slots filled, proceed with booking
                    return self.handle_booking_creation(user_message)
                else:
                    # Still missing slots, ask for next one
                    if missing == "time":
                        return {"reply": "What time?", "action": "ask_time"}
                    elif missing == "party":
                        return {"reply": "How many people?", "action": "ask_party"}
            
            return self.handle_booking_creation(user_message)
        
        # Handle explicit intents first (HIGH PRIORITY) - these always take precedence
        if intent == "check_availability":
            print("DEBUG: User explicitly wants availability, resetting session")
            sess["intent"] = "check_availability"
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.handle_availability_search(user_message)
        elif intent == "show_booking":
            print("DEBUG: User wants to see booking info - clearing current session")
            sess["intent"] = None
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.handle_booking_info(user_message)
        elif intent == "modify_booking":
            print("DEBUG: User wants to modify booking - clearing current session")
            sess["intent"] = None
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.handle_booking_modification(user_message)
        elif intent == "cancel_booking":
            print("DEBUG: User wants to cancel booking - clearing current session")
            sess["intent"] = None
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.handle_booking_cancellation(user_message)
        elif intent == "help":
            print("DEBUG: User wants help - clearing current session")
            sess["intent"] = None
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.get_help_message()
        elif intent == "reset" or user_message.lower().strip() == "reset":
            print("DEBUG: Resetting conversation state")
            # Clear the entire session
            session_id = "default"
            SESSIONS[session_id] = {
                "intent": None,
                "slots": {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None},
                "availability_context": None
            }
            return {"reply": "Conversation reset! How can I help you today?", "action": "reset"}
        elif intent == "book":
            print("DEBUG: User wants to book")
            # Clear old slots for new booking
            sess["intent"] = "book"
            sess["slots"] = {"date": None, "time": None, "party": None, "name": None, "email": None, "mobile": None, "ref": None}
            sess["availability_context"] = None
            return self.handle_booking_creation(user_message)
        
        # If no clear intent but has date/time/party info, assume booking intent
        if any([parse_date_natural(user_message), extract_time_from_text(user_message), parse_party(user_message)]):
            print("DEBUG: Assuming booking intent from date/time/party info")
            sess["intent"] = "book"
            return self.handle_booking_creation(user_message)
        
        print("DEBUG: No clear intent, returning default response")
        return self.get_default_response()
    
    def detect_intent(self, user_message):
        """Detect user intent from message"""
        text = user_message.lower()
        
        print(f"DEBUG: detect_intent analyzing: '{text}'")
        
        # Check availability - HIGH PRIORITY
        if any(word in text for word in ['available', 'availability', 'check', 'search', 'time', 'slot', 'when']):
            print(f"DEBUG: Intent detected as 'check_availability'")
            return "check_availability"
        
        # Book reservation
        if any(word in text for word in ['book', 'reservation', 'reserve', 'make booking', 'table for', 'dinner', 'lunch']):
            print(f"DEBUG: Intent detected as 'book'")
            return "book"
        
        # Show booking
        if any(word in text for word in ['my booking', 'booking info', 'reservation details', 'show booking', 'what time', 'show my']):
            print(f"DEBUG: Intent detected as 'show_booking'")
            return "show_booking"
        
        # Modify booking
        if any(word in text for word in ['change', 'modify', 'update', 'edit', 'move']):
            print(f"DEBUG: Intent detected as 'modify_booking'")
            return "modify_booking"
        
        # Cancel booking
        if any(word in text for word in ['cancel', 'cancellation']):
            print(f"DEBUG: Intent detected as 'cancel_booking'")
            return "cancel_booking"
        
        # Help
        if 'help' in text:
            print(f"DEBUG: Intent detected as 'help'")
            return "help"
        
        # If no clear intent but has date/time/party info, assume booking intent
        if any([parse_date_natural(text), normalize_time_to_hhmmss(text), parse_party(text)]):
            print(f"DEBUG: Intent detected as 'book' (from date/time/party info)")
            return "book"
        
        print(f"DEBUG: Intent detected as 'unknown'")
        return "unknown"
    
    def extract_date(self, text):
        """Extract date from text (simple pattern matching)"""
        # Look for patterns like "2025-08-06", "August 6", "6th August", etc.
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2})[st|nd|rd|th]?\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})[st|nd|rd|th]?'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if len(match.groups()) == 1:
                    if '-' in match.group(1):
                        return match.group(1)
                    else:
                        # Convert to YYYY-MM-DD format (default to 2025)
                        return f"2025-{match.group(1).zfill(2)}-01"
                else:
                    # Handle month name patterns
                    month_map = {
                        'january': '01', 'february': '02', 'march': '03', 'april': '04',
                        'may': '05', 'june': '06', 'july': '07', 'august': '08',
                        'september': '09', 'october': '10', 'november': '11', 'december': '12'
                    }
                    if match.group(1).isdigit():
                        day = match.group(1).zfill(2)
                        month = month_map.get(match.group(2), '01')
                    else:
                        day = match.group(2).zfill(2)
                        month = month_map.get(match.group(1), '01')
                    return f"2025-{month}-{day}"
        
        return None
    
    def extract_party_size(self, text):
        """Extract party size from text"""
        # Look for numbers followed by people/person/guests
        patterns = [
            r'(\d+)\s+(people?|person|guests?)',
            r'party\s+of\s+(\d+)',
            r'(\d+)\s+guests?',
            r'for\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                size = int(match.group(1))
                if 1 <= size <= 20:  # Reasonable party size
                    return size
        
        # Look for standalone numbers
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            size = int(num)
            if 1 <= size <= 20:
                return size
        
        return None
    
    def validate_party_size(self, size):
        """Validate party size is within acceptable range"""
        if not size or not isinstance(size, int):
            return False, "Party size must be a number"
        if size < 1 or size > 20:
            return False, "Party size must be between 1 and 20 people"
        return True, None
    
    def validate_date(self, date_str):
        """Validate date format and ensure it's not in the past"""
        try:
            # Parse the date
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if parsed_date < today:
                return False, "Date cannot be in the past"
            
            return True, None
        except ValueError:
            return False, "Invalid date format. Please use YYYY-MM-DD"
    
    def validate_time(self, time_str):
        """Validate time format"""
        if not time_str:
            return False, "Time is required"
        
        # Check if it's in HH:MM:SS format
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$'
        if not re.match(time_pattern, time_str):
            return False, "Time must be in HH:MM:SS format"
        
        return True, None
    
    def validate_cancellation_reason(self, reason_id):
        """Validate cancellation reason ID"""
        if not reason_id or not isinstance(reason_id, int):
            return False, "Cancellation reason ID must be a number"
        if reason_id < 1 or reason_id > 5:
            return False, "Cancellation reason ID must be between 1 and 5"
        return True, None
    
    def extract_time(self, text):
        """Extract time from text and normalize to HH:MM:SS format"""
        # Look for time patterns
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2})\s*o\'?clock',
            r'(\d{1,2})h'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if ':' in pattern:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    ampm = match.group(3) if len(match.groups()) > 2 else None
                else:
                    hour = int(match.group(1))
                    minute = 0
                    ampm = match.group(2) if len(match.groups()) > 1 else None
                
                # Convert to 24-hour format
                if ampm:
                    if ampm == 'pm' and hour != 12:
                        hour += 12
                    elif ampm == 'am' and hour == 12:
                        hour = 0
                
                # Normalize to HH:MM:SS format
                return f"{hour:02d}:{minute:02d}:00"
        
        return None
    
    def hhmm_to_hhmmss(self, time_str):
        """Convert HH:MM to HH:MM:SS format"""
        if not time_str:
            return None
        
        parts = time_str.split(":")
        if len(parts) == 2:
            return f"{parts[0]}:{parts[1]}:00"
        elif len(parts) == 3:
            return time_str
        else:
            return None
    
    def handle_availability_search(self, user_message):
        """Handle availability search requests with smart parsing"""
        # Get current session
        session_id = "default"
        sess = get_or_create_session(session_id)
        
        # Set intent to availability
        sess["intent"] = "check_availability"
        
        # Use the new smart parsers
        d = parse_date_natural(user_message)
        p = parse_party(user_message) or 2  # Default to 2 if not specified
        
        if not d:
            return {
                "reply": "Tell me the date (e.g., today, tomorrow, this weekend, 7 Aug, 2025-08-20).",
                "action": "ask_date"
            }
        
        if not not_past(d):
            return {
                "reply": "❌ That date is in the past. Try tomorrow or a future date.",
                "action": "validation_error"
            }
        
        # Check availability via API
        res = api_check_availability(d.strftime("%Y-%m-%d"), p)
        
        if "error" in res:
            return {
                "reply": f"❌ Error checking availability: {res['error']}",
                "action": "api_error"
            }
        
        # Store for potential booking
        self.conversation_state['last_availability'] = res
        self.conversation_state['search_date'] = d.strftime("%Y-%m-%d")
        self.conversation_state['search_party_size'] = p
        
        # Store in session for smooth transition to booking
        session_id = "default"
        sess = get_or_create_session(session_id)
        sess["availability_context"] = {
            "date": d,
            "party_size": p,
            "available_times": [s["time"] for s in res.get("available_slots", []) if s.get("available")]
        }
        
        # Format response with clickable buttons
        times = [s["time"] for s in res.get("available_slots", []) if s.get("available")]
        if times:
            # Create clickable time buttons
            time_buttons = []
            for time in times[:6]:  # Show up to 6 times
                # Convert HH:MM:SS to readable format (e.g., "13:00:00" -> "1:00 PM")
                try:
                    time_obj = datetime.strptime(time, "%H:%M:%S")
                    display_time = time_obj.strftime("%I:%M %p").lstrip("0")
                except:
                    display_time = time
                
                time_buttons.append(f'<button class="time-btn" onclick="selectTime(\'{time}\', \'{d.strftime("%Y-%m-%d")}\', {p})">{display_time}</button>')
            
            buttons_html = " ".join(time_buttons)
            
            return {
                "reply": f"Available times on {d} for {p} people:\n\n{buttons_html}\n\n💡 Click a time to book, or tell me which time you prefer!",
                "action": "availability_found",
                "data": res,
                "html": buttons_html
            }
        else:
            return {
                "reply": f"No slots on {d} for {p} people. Try another date?",
                "action": "no_availability",
                "data": res
            }
    
    def handle_booking_creation(self, user_message):
        """Handle booking creation requests with smart slot-filling"""
        # Get or create session for this user
        session_id = "default"  # In a real app, use user ID or session ID
        sess = get_or_create_session(session_id)
        sess["intent"] = "book"
        
        # Fill slots from user message
        fill_booking_slots(sess, user_message)
        
        # Check what's missing
        missing = next_missing_booking_slot(sess)
        if missing == "date":
            return {
                "reply": "What date would you like? (e.g., today, tomorrow, 2025-08-20, 7 Aug)",
                "action": "ask_date"
            }
        if missing == "time":
            return {
                "reply": "What time? (e.g., 7 pm, 19:30)",
                "action": "ask_time"
            }
        if missing == "party":
            return {
                "reply": "How many people?",
                "action": "ask_party"
            }
        
        # All slots filled, validate and proceed
        d = sess["slots"]["date"]
        tm = sess["slots"]["time"]
        p = sess["slots"]["party"]
        
        if not not_past(d):
            sess["slots"]["date"] = None
            return {
                "reply": "That date is in the past. Pick another date (e.g., tomorrow or Saturday).",
                "action": "validation_error"
            }
        
        # 1) Check availability
        avail = api_check_availability(d.strftime("%Y-%m-%d"), p)
        
        if "error" in avail:
            return {
                "reply": f"❌ Error checking availability: {avail['error']}",
                "action": "api_error"
            }
        
        slots = [s["time"] for s in avail.get("available_slots", []) if s.get("available")]
        if not slots:
            return {
                "reply": f"No slots on {d} for {p} people. Try another date?",
                "action": "no_availability"
            }
        
        # If requested time is not available, suggest nearest options and alternative dates
        if tm not in slots:
            # Format available times for display
            available_times = []
            for time in slots[:4]:
                try:
                    time_obj = datetime.strptime(time, "%H:%M:%S")
                    display_time = time_obj.strftime("%I:%M %p").lstrip("0")
                except:
                    display_time = time
                available_times.append(display_time)
            
            # Check next and previous dates for availability
            next_date = d + timedelta(days=1)
            prev_date = d - timedelta(days=1)
            
            next_avail = api_check_availability(next_date.strftime("%Y-%m-%d"), p)
            prev_avail = api_check_availability(prev_date.strftime("%Y-%m-%d"), p)
            
            next_slots = [s["time"] for s in next_avail.get("available_slots", []) if s.get("available")]
            prev_slots = [s["time"] for s in prev_avail.get("available_slots", []) if s.get("available")]
            
            reply = f"❌ {tm} isn't available on {d} for {p} people.\n\n"
            reply += f"**Available times on {d}:** {', '.join(available_times)}\n\n"
            
            if next_slots:
                reply += f"**Next day ({next_date}):** {', '.join(next_slots[:3])}\n"
            if prev_slots:
                reply += f"**Previous day ({prev_date}):** {', '.join(prev_slots[:3])}\n"
            
            reply += "\n💡 **Choose an option:**\n"
            reply += f"• Pick from available times on {d}\n"
            if next_slots:
                reply += f"• Try {next_date}\n"
            if prev_slots:
                reply += f"• Try {prev_date}\n"
            reply += "• Pick a different date"
            
            # Update session to allow user to select from alternatives
            sess["intent"] = "book"
            sess["slots"]["date"] = d
            sess["slots"]["party"] = p
            
            return {
                "reply": reply,
                "action": "time_unavailable",
                "data": {
                    "requested_date": d.strftime("%Y-%m-%d"),
                    "requested_time": tm,
                    "available_times": slots,
                    "next_date": next_date.strftime("%Y-%m-%d") if next_slots else None,
                    "prev_date": prev_date.strftime("%Y-%m-%d") if prev_slots else None
                }
            }
        
        # 2) Proceed to booking
        customer = {
            "FirstName": sess["slots"]["name"] or "Guest",
            "Surname": "User",
            "Email": sess["slots"]["email"] or "guest@example.com",
            "Mobile": sess["slots"]["mobile"] or "07000000000"
        }
        
        res = api_book(d.strftime("%Y-%m-%d"), tm, p, customer)
        
        if "error" in res:
            return {
                "reply": f"❌ Booking failed: {res['error']}",
                "action": "booking_error"
            }
        
        if "booking_reference" in res:
            sess["slots"]["ref"] = res["booking_reference"]
            
            # Update current booking for the assistant
            self.current_booking = {
                'reference': res["booking_reference"],
                'date': d.strftime("%Y-%m-%d"),
                'time': tm,
                'party_size': p
            }
            
            reply = f"🎉 Booked! Ref {res['booking_reference']} on {d} at {tm} for {p} people."
            return {
                "reply": reply,
                "action": "booking_created",
                "data": res
            }
        
        return {
            "reply": f"❌ Booking failed: {res.get('detail','unknown error')}",
            "action": "booking_error"
        }
    
    def handle_booking_info(self, user_message):
        """Handle booking information requests"""
        if not self.current_booking:
            return {
                "reply": "You don't have any active bookings. Would you like to make a new reservation?",
                "action": "no_booking"
            }
        
        try:
            response = requests.get(
                f"{BASE_URL}/Booking/{self.current_booking['reference']}", 
                headers=HEADERS
            )
            
            if response.status_code == 200:
                booking_data = response.json()
                
                reply = f"📋 Here are your booking details:\n\n"
                reply += f"🔢 Reference: {self.current_booking['reference']}\n"
                reply += f"📅 Date: {self.current_booking['date']}\n"
                reply += f"🕐 Time: {self.current_booking['time']}\n"
                reply += f"👥 Party Size: {self.current_booking['party_size']} people\n"
                reply += f"📧 Email: {booking_data.get('customer_email', 'demo@example.com')}\n"
                reply += f"📱 Phone: {booking_data.get('customer_mobile', '1234567890')}\n\n"
                reply += "You can modify your booking by saying 'Change my booking' or cancel it by saying 'Cancel my booking'."
                
                return {
                    "reply": reply,
                    "action": "booking_info_shown",
                    "data": booking_data
                }
            else:
                return {
                    "reply": f"Sorry, I couldn't retrieve your booking details. Please try again.",
                    "action": "error"
                }
        
        except Exception as e:
            return {
                "reply": f"Sorry, I encountered an error while retrieving your booking: {str(e)}",
                "action": "error"
            }
    
    def handle_booking_modification(self, user_message):
        """Handle booking modification requests"""
        if not self.current_booking:
            return {
                "reply": "You don't have any active bookings to modify. Would you like to make a new reservation?",
                "action": "no_booking"
            }
        
        # Extract what to modify
        new_date = self.extract_date(user_message)
        new_time = self.extract_time(user_message)
        new_party_size = self.extract_party_size(user_message)
        
        if not any([new_date, new_time, new_party_size]):
            return {
                "reply": "What would you like to change? You can modify the date, time, or party size. (e.g., 'Change to August 7th' or 'Change time to 8 PM')",
                "action": "ask_modification"
            }
        
        # Prepare update data
        update_data = {}
        if new_date:
            update_data["VisitDate"] = new_date
        if new_time:
            update_data["VisitTime"] = new_time
        if new_party_size:
            update_data["PartySize"] = new_party_size
        
        try:
            response = requests.patch(
                f"{BASE_URL}/Booking/{self.current_booking['reference']}", 
                headers=HEADERS,
                data=update_data
            )
            
            if response.status_code == 200:
                # Update local booking info
                if new_date:
                    self.current_booking['date'] = new_date
                if new_time:
                    self.current_booking['time'] = new_time
                if new_party_size:
                    self.current_booking['party_size'] = new_party_size
                
                reply = f"✅ Your booking has been updated successfully!\n\n"
                reply += f"🔢 Reference: {self.current_booking['reference']}\n"
                reply += f"📅 Date: {self.current_booking['date']}\n"
                reply += f"🕐 Time: {self.current_booking['time']}\n"
                reply += f"👥 Party Size: {self.current_booking['party_size']} people\n\n"
                reply += "Is there anything else you'd like to modify?"
                
                return {
                    "reply": reply,
                    "action": "booking_modified",
                    "data": response.json()
                }
            else:
                return {
                    "reply": f"Sorry, I couldn't update your booking. Please try again or contact support.",
                    "action": "error"
                }
        
        except Exception as e:
            return {
                "reply": f"Sorry, I encountered an error while updating your booking: {str(e)}",
                "action": "error"
            }
    
    def handle_booking_cancellation(self, user_message):
        """Handle booking cancellation requests"""
        if not self.current_booking:
            return {
                "reply": "You don't have any active bookings to cancel. Would you like to make a new reservation?",
                "action": "no_booking"
            }
        
        try:
            # Validate cancellation reason ID
            reason_id = 1  # Default reason
            is_valid_reason, reason_error = self.validate_cancellation_reason(reason_id)
            if not is_valid_reason:
                return {
                    "reply": f"❌ {reason_error}",
                    "action": "validation_error"
                }
            
            data = {
                "micrositeName": "TheHungryUnicorn",
                "bookingReference": self.current_booking['reference'],
                "cancellationReasonId": str(reason_id)  # Convert to string as API expects
            }
            
            response = requests.post(
                f"{BASE_URL}/Booking/{self.current_booking['reference']}/Cancel", 
                headers=HEADERS,
                data=data
            )
            
            if response.status_code == 200:
                cancelled_booking = self.current_booking.copy()
                self.current_booking = {}
                
                reply = f"✅ Your booking has been cancelled successfully.\n\n"
                reply += f"🔢 Reference: {cancelled_booking['reference']}\n"
                reply += f"📅 Date: {cancelled_booking['date']}\n"
                reply += f"🕐 Time: {cancelled_booking['time']}\n"
                reply += f"👥 Party Size: {cancelled_booking['party_size']} people\n\n"
                reply += "We're sorry to see you go. Would you like to make a new reservation for another time?"
                
                return {
                    "reply": reply,
                    "action": "booking_cancelled",
                    "data": response.json()
                }
            else:
                return {
                    "reply": f"Sorry, I couldn't cancel your booking. Please try again or contact support.",
                    "action": "error"
                }
        
        except Exception as e:
            return {
                "reply": f"Sorry, I encountered an error while cancelling your booking: {str(e)}",
                "action": "error"
            }
    
    def get_help_message(self):
        """Return help message"""
        return {
            "reply": """🤖 **Restaurant Booking Assistant - Help**

Here's what I can help you with:

🔍 **Check Availability**
- "Check availability for August 6th for 4 people"
- "What times are available on Friday?"

📅 **Make a Booking**
- "Book a table for 6 people on August 7th at 7 PM"
- "I want to reserve a table"

📋 **View Booking Details**
- "Show my booking"
- "What are my reservation details?"

✏️ **Modify Booking**
- "Change my booking to August 8th"
- "Update the time to 8:30 PM"

❌ **Cancel Booking**
- "Cancel my reservation"
- "I need to cancel my booking"

💡 **Tips:**
- Be specific about dates, times, and party sizes
- You can say "help" anytime for this message
- Say "reset" if the conversation gets stuck
- I'll guide you through each step of the process

What would you like to do today?""",
            "action": "help_shown"
        }
    
    def get_welcome_message(self):
        """Get welcome message with quick action buttons"""
        return {
            "reply": """Welcome to The Hungry Unicorn! 🦄

I'm your personal booking assistant. I can help you:

• Check table availability 📅
• Make reservations 🎯
• View your booking details 📋
• Modify existing bookings ✏️
• Cancel bookings ❌

**Quick Actions:**
<button class="quick-btn" onclick="sendQuickMessage('Book a table')">📅 Book a Table</button>
<button class="quick-btn" onclick="sendQuickMessage('Check availability')">🔍 Check Availability</button>
<button class="quick-btn" onclick="sendQuickMessage('Show my booking')">📋 Show My Booking</button>
<button class="quick-btn" onclick="sendQuickMessage('Help')">❓ Help</button>

**Or just type naturally:**
"I'd like to book a table for 4 people next Friday at 7pm"
"Can you show me availability for this weekend?""",
            "action": "welcome",
            "html": """<button class="quick-btn" onclick="sendQuickMessage('Book a table')">📅 Book a Table</button>
<button class="quick-btn" onclick="sendQuickMessage('Check availability')">🔍 Check Availability</button>
<button class="quick-btn" onclick="sendQuickMessage('Show my booking')">📋 Show My Booking</button>
<button class="quick-btn" onclick="sendQuickMessage('Help')">❓ Help</button>"""
        }
    
    def get_default_response(self):
        """Return default response when intent is unclear"""
        return {
            "reply": """Hi! I'm your restaurant booking assistant. I can help you:

• Check table availability
• Make reservations
• View your booking details
• Modify existing bookings
• Cancel bookings

What would you like to do? You can say "help" for more information.""",
            "action": "default"
        }

# Session management for slot-filling
SESSIONS = {}

def get_or_create_session(session_id):
    """Get existing session or create new one with empty slots"""
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "flow": None,  # "book", "check", etc.
            "slots": { 
                "date": None, 
                "time": None, 
                "party": None, 
                "name": None, 
                "email": None, 
                "mobile": None, 
                "ref": None 
            },
            "suggest": {    # store last suggestions to interpret the user's next reply
                "date": None,
                "times": [],           # e.g. ["19:00:00","19:30:00","20:30:00"]
                "alt_date": None,
                "alt_times": []
            }
        }
    return SESSIONS[session_id]

def fill_booking_slots(sess, text: str):
    """Fill booking slots from user text - only fill what's missing"""
    slots = sess["slots"]
    
    print(f"DEBUG: fill_booking_slots input: '{text}'")
    print(f"DEBUG: Current slots before filling: {slots}")
    
    # Fill date if missing
    if slots["date"] is None:
        d = parse_date_natural(text)
        if d and not_past(d): 
            slots["date"] = d
            print(f"DEBUG: Filled date slot: {d}")
    
    # Fill time if missing
    if slots["time"] is None:
        tm = extract_time_from_text(text)
        if tm: 
            slots["time"] = tm
            print(f"DEBUG: Filled time slot: {tm}")
    
    # Fill party if missing
    if slots["party"] is None:
        p = parse_party(text)
        if p: 
            slots["party"] = p
            print(f"DEBUG: Filled party slot: {p}")
    
    # naive contact extraction; improve as needed
    if slots["email"] is None:
        m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if m: 
            slots["email"] = m.group(0)
            print(f"DEBUG: Filled email slot: {m.group(0)}")
    
    if slots["mobile"] is None:
        m = re.search(r"\b(\+?\d{10,14})\b", text.replace(" ", ""))
        if m: 
            slots["mobile"] = m.group(1)
            print(f"DEBUG: Filled mobile slot: {m.group(1)}")
    
    if slots["name"] is None:
        m = re.search(r"\bfor\s+\d+\s+([A-Za-z]+)\b", text)  # "for 2 John"
        if m: 
            slots["name"] = m.group(1).title()
            print(f"DEBUG: Filled name slot: {m.group(1).title()}")
    
    print(f"DEBUG: Slots after filling: {slots}")

def next_missing_booking_slot(sess):
    """Find the next missing slot for booking"""
    s = sess["slots"]
    if s["date"] is None: return "date"
    if s["time"] is None: return "time"
    if s["party"] is None: return "party"
    # For a minimal flow, contact can be optional; ask later if you want
    return None

def ok(reply, action="success"):
    """Helper to return JSON response"""
    return jsonify({"reply": reply, "action": action})

def api_check_availability(visit_date: str, party_size: int):
    """Check availability via API"""
    try:
        data = {
            "VisitDate": visit_date,
            "PartySize": party_size,
            "ChannelCode": "ONLINE"
        }
        
        response = requests.post(f"{BASE_URL}/AvailabilitySearch", headers=HEADERS, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.HTTPError as e:
        error_detail = response.text[:200] if hasattr(response, 'text') else str(e)
        return {"error": f"API error {response.status_code}: {error_detail}"}
    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def api_book(visit_date: str, visit_time: str, party_size: int, customer: dict):
    """Create booking via API"""
    try:
        data = {
            "VisitDate": visit_date,
            "VisitTime": visit_time,
            "PartySize": party_size,
            "ChannelCode": "ONLINE",
            "SpecialRequests": "",
            "Customer[FirstName]": customer.get("FirstName", "Demo"),
            "Customer[Surname]": customer.get("Surname", "Customer"),
            "Customer[Email]": customer.get("Email", "demo@example.com"),
            "Customer[Mobile]": customer.get("Mobile", "1234567890")
        }
        
        response = requests.post(f"{BASE_URL}/BookingWithStripeToken", headers=HEADERS, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.HTTPError as e:
        error_detail = response.text[:200] if hasattr(response, 'text') else str(e)
        return {"error": f"API error {response.status_code}: {error_detail}"}
    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Initialize the booking assistant
assistant = BookingAssistant()

@app.route("/")
def index():
    """Main chat interface"""
    return render_template("chat.html")

@app.route("/welcome")
def welcome():
    """Get welcome message with quick actions"""
    assistant = BookingAssistant()
    return jsonify(assistant.get_welcome_message())

@app.route("/send", methods=["POST"])
def send():
    """Handle chat messages with session management"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"reply": "Please enter a message.", "action": "error"})
        
        # Process the message with the assistant
        response = assistant.process_message(user_message)
        
        return response  # Already a JSON response
    
    except Exception as e:
        return jsonify({
            "reply": f"Sorry, I encountered an error: {str(e)}",
            "action": "error"
        })

@app.route("/status")
def status():
    """Check if the booking API is accessible"""
    try:
        response = requests.get(f"{BASE_URL.replace('/api/ConsumerApi/v1/Restaurant/TheHungryUnicorn', '')}/", timeout=5)
        return jsonify({"status": "connected", "api_url": BASE_URL})
    except:
        return jsonify({"status": "disconnected", "api_url": BASE_URL})

if __name__ == "__main__":
    print("🚀 Starting Restaurant Booking Chat Interface...")
    print(f"📡 API Base URL: {BASE_URL}")
    print(f"🔑 Bearer Token: {TOKEN[:20]}...")
    print("🌐 Web Interface: http://localhost:5001")
    print("📚 API Documentation: http://localhost:8547/docs")
    print("\nPress Ctrl+C to stop the server")
    
    app.run(host="0.0.0.0", port=5001, debug=True)
