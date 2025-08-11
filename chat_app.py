from flask import Flask, render_template, request, jsonify, session
import requests
import json
from datetime import datetime, date
import re

app = Flask(__name__)
app.secret_key = 'restaurant_booking_secret_key'

# Configuration
import os

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
        
        # Check for availability search
        if any(word in user_message for word in ['available', 'availability', 'check', 'search', 'time', 'slot']):
            return self.handle_availability_search(user_message)
        
        # Check for booking creation
        elif any(word in user_message for word in ['book', 'reservation', 'reserve', 'make booking']):
            return self.handle_booking_creation(user_message)
        
        # Check for booking info
        elif any(word in user_message for word in ['my booking', 'booking info', 'reservation details', 'show booking']):
            return self.handle_booking_info(user_message)
        
        # Check for booking modification
        elif any(word in user_message for word in ['change', 'modify', 'update', 'edit']):
            return self.handle_booking_modification(user_message)
        
        # Check for booking cancellation
        elif any(word in user_message for word in ['cancel', 'cancellation']):
            return self.handle_booking_cancellation(user_message)
        
        # Help command
        elif 'help' in user_message:
            return self.get_help_message()
        
        # Default response
        else:
            return self.get_default_response()
    
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
        """Handle availability search requests"""
        visit_date = self.extract_date(user_message)
        party_size = self.extract_party_size(user_message)
        
        if not visit_date:
            return {
                "reply": "I'd be happy to check availability for you! What date would you like to dine? (e.g., 'August 6th' or '2025-08-06')",
                "action": "ask_date"
            }
        
        if not party_size:
            return {
                "reply": f"Great! I found the date: {visit_date}. How many people will be in your party?",
                "action": "ask_party_size",
                "date": visit_date
            }
        
        # Validate inputs before API call
        is_valid_party, party_error = self.validate_party_size(party_size)
        if not is_valid_party:
            return {
                "reply": f"❌ {party_error}",
                "action": "validation_error"
            }
        
        is_valid_date, date_error = self.validate_date(visit_date)
        if not is_valid_date:
            return {
                "reply": f"❌ {date_error}",
                "action": "validation_error"
            }
        
        # Make API call to check availability
        try:
            data = {
                "VisitDate": visit_date,
                "PartySize": party_size,
                "ChannelCode": "ONLINE"
            }
            
            response = requests.post(f"{BASE_URL}/AvailabilitySearch", headers=HEADERS, data=data, timeout=10)
            response.raise_for_status()
            
            availability_data = response.json()
            self.conversation_state['last_availability'] = availability_data
            self.conversation_state['search_date'] = visit_date
            self.conversation_state['search_party_size'] = party_size
            
            # Format the response
            slots = availability_data.get('available_slots', [])
            if slots:
                slot_info = []
                for slot in slots[:5]:  # Show first 5 slots
                    time_str = slot.get('time', '')
                    available = slot.get('available', False)
                    status = "✅ Available" if available else "❌ Full"
                    slot_info.append(f"{time_str}: {status}")
                
                reply = f"Perfect! I found availability for {party_size} people on {visit_date}:\n\n" + "\n".join(slot_info)
                reply += "\n\nWould you like to make a booking for one of these times?"
            else:
                reply = f"I'm sorry, but I couldn't find available slots for {party_size} people on {visit_date}. Would you like to try a different date or party size?"
            
            return {
                "reply": reply,
                "action": "availability_found",
                "data": availability_data
            }
        
        except requests.HTTPError as e:
            error_detail = response.text[:200] if hasattr(response, 'text') else str(e)
            return {
                "reply": f"❌ API error {response.status_code}: {error_detail}",
                "action": "api_error"
            }
        except requests.RequestException as e:
            return {
                "reply": f"❌ Network error: {str(e)}",
                "action": "network_error"
            }
        except Exception as e:
            return {
                "reply": f"❌ Unexpected error: {str(e)}",
                "action": "error"
            }
    
    def handle_booking_creation(self, user_message):
        """Handle booking creation requests"""
        # Check if we have availability data
        if 'last_availability' not in self.conversation_state:
            return {
                "reply": "Let me first check availability for you. What date would you like to dine?",
                "action": "ask_date"
            }
        
        # Extract time if provided
        visit_time = self.extract_time(user_message)
        if not visit_time:
            return {
                "reply": "What time would you like to book? (e.g., '7:30 PM' or '19:30')",
                "action": "ask_time"
            }
        
        # Validate time format
        is_valid_time, time_error = self.validate_time(visit_time)
        if not is_valid_time:
            return {
                "reply": f"❌ {time_error}",
                "action": "validation_error"
            }
        
        # For demo purposes, create a simple booking
        try:
            data = {
                "VisitDate": self.conversation_state['search_date'],
                "VisitTime": visit_time,  # Already in HH:MM:SS format
                "PartySize": self.conversation_state['search_party_size'],
                "ChannelCode": "ONLINE",
                "SpecialRequests": "",
                "Customer[FirstName]": "Demo",
                "Customer[Surname]": "Customer",
                "Customer[Email]": "demo@example.com",
                "Customer[Mobile]": "1234567890"
            }
            
            response = requests.post(f"{BASE_URL}/BookingWithStripeToken", headers=HEADERS, data=data)
            
            if response.status_code == 200:
                booking_data = response.json()
                booking_ref = booking_data.get('booking_reference', 'DEMO123')
                
                self.current_booking = {
                    'reference': booking_ref,
                    'date': self.conversation_state['search_date'],
                    'time': visit_time,
                    'party_size': self.conversation_state['search_party_size']
                }
                
                reply = f"🎉 Excellent! Your booking has been confirmed!\n\n"
                reply += f"📅 Date: {self.conversation_state['search_date']}\n"
                reply += f"🕐 Time: {visit_time}\n"
                reply += f"👥 Party Size: {self.conversation_state['search_party_size']} people\n"
                reply += f"🔢 Booking Reference: {booking_ref}\n\n"
                reply += "You can check your booking details anytime by asking 'Show my booking' or modify it by saying 'Change my booking'."
                
                return {
                    "reply": reply,
                    "action": "booking_created",
                    "data": booking_data
                }
            else:
                return {
                    "reply": f"Sorry, I couldn't create the booking. Please try again or contact support.",
                    "action": "error"
                }
        
        except Exception as e:
            return {
                "reply": f"Sorry, I encountered an error while creating the booking: {str(e)}",
                "action": "error"
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
- I'll guide you through each step of the process

What would you like to do today?""",
            "action": "help_shown"
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

# Initialize the booking assistant
assistant = BookingAssistant()

@app.route("/")
def index():
    """Main chat interface"""
    return render_template("chat.html")

@app.route("/send", methods=["POST"])
def send():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({"reply": "Please enter a message.", "action": "error"})
        
        # Process the message
        response = assistant.process_message(user_message)
        
        return jsonify(response)
    
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
