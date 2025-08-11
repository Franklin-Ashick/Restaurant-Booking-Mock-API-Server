#!/usr/bin/env python3
"""
Terminal-based Restaurant Booking Chat Interface

A simple command-line interface for interacting with the restaurant booking API.
Perfect for quick testing and development.

Usage:
    python chat_terminal.py
"""

import requests
import json
import re
from datetime import datetime, date
import sys

# Configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

class TerminalBookingAssistant:
    def __init__(self):
        self.conversation_state = {}
        self.current_booking = {}
        self.running = True
    
    def print_banner(self):
        """Display welcome banner"""
        print("\n" + "="*60)
        print("🍽️  RESTAURANT BOOKING ASSISTANT - TERMINAL VERSION")
        print("="*60)
        print("🤖 I can help you with restaurant bookings!")
        print("💡 Type 'help' for available commands")
        print("🚪 Type 'quit' or 'exit' to close")
        print("="*60 + "\n")
    
    def print_help(self):
        """Display help information"""
        help_text = """
🤖 **AVAILABLE COMMANDS**

🔍 **Check Availability:**
   • "Check availability for August 6th for 4 people"
   • "What times are available on Friday?"
   • "Is there availability for 2 people tomorrow?"

📅 **Make a Booking:**
   • "Book a table for 6 people on August 7th at 7 PM"
   • "I want to reserve a table"
   • "Make a reservation for 3 people"

📋 **View Booking Details:**
   • "Show my booking"
   • "What are my reservation details?"
   • "My booking info"

✏️ **Modify Booking:**
   • "Change my booking to August 8th"
   • "Update the time to 8:30 PM"
   • "Modify party size to 5 people"

❌ **Cancel Booking:**
   • "Cancel my reservation"
   • "I need to cancel my booking"

💡 **Other Commands:**
   • "help" - Show this help message
   • "status" - Check API connection
   • "quit" or "exit" - Close the application

💡 **Tips:**
   • Be specific about dates, times, and party sizes
   • Use natural language (e.g., "tomorrow at 7 PM")
   • I'll guide you through each step
        """
        print(help_text)
    
    def check_api_status(self):
        """Check if the booking API is accessible"""
        try:
            response = requests.get(f"{BASE_URL.replace('/api/ConsumerApi/v1/Restaurant/TheHungryUnicorn', '')}/", timeout=5)
            if response.status_code == 200:
                print("✅ API Status: Connected")
                print(f"📡 API URL: {BASE_URL}")
                return True
            else:
                print("❌ API Status: Error")
                return False
        except Exception as e:
            print(f"❌ API Status: Disconnected - {str(e)}")
            return False
    
    def extract_date(self, text):
        """Extract date from text"""
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
                if 1 <= size <= 20:
                    return size
        
        # Look for standalone numbers
        numbers = re.findall(r'\b(\d+)\b', text)
        for num in numbers:
            size = int(num)
            if 1 <= size <= 20:
                return size
        
        return None
    
    def extract_time(self, text):
        """Extract time from text and normalize to HH:MM:SS format"""
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
    
    def handle_availability_search(self, user_message):
        """Handle availability search requests"""
        visit_date = self.extract_date(user_message)
        party_size = self.extract_party_size(user_message)
        
        if not visit_date:
            print("🤖 I'd be happy to check availability for you! What date would you like to dine?")
            print("   (e.g., 'August 6th' or '2025-08-06')")
            return
        
        if not party_size:
            print(f"🤖 Great! I found the date: {visit_date}")
            print("   How many people will be in your party?")
            return
        
        # Make API call to check availability
        print(f"🔍 Checking availability for {party_size} people on {visit_date}...")
        
        try:
            data = {
                "VisitDate": visit_date,
                "PartySize": party_size,
                "ChannelCode": "ONLINE"
            }
            
            response = requests.post(f"{BASE_URL}/AvailabilitySearch", headers=HEADERS, data=data)
            
            if response.status_code == 200:
                availability_data = response.json()
                self.conversation_state['last_availability'] = availability_data
                self.conversation_state['search_date'] = visit_date
                self.conversation_state['search_party_size'] = party_size
                
                # Format the response
                slots = availability_data.get('available_slots', [])
                if slots:
                    print(f"✅ Found availability for {party_size} people on {visit_date}:")
                    print()
                    for i, slot in enumerate(slots[:5], 1):  # Show first 5 slots
                        time_str = slot.get('time', '')
                        available = slot.get('available', False)
                        status = "✅ Available" if available else "❌ Full"
                        print(f"   {i}. {time_str}: {status}")
                    
                    print(f"\n🤖 Would you like to make a booking for one of these times?")
                else:
                    print(f"❌ Sorry, no available slots found for {party_size} people on {visit_date}")
                    print("   Would you like to try a different date or party size?")
                
            else:
                print(f"❌ Error checking availability. Status: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def handle_booking_creation(self, user_message):
        """Handle booking creation requests"""
        if 'last_availability' not in self.conversation_state:
            print("🤖 Let me first check availability for you. What date would you like to dine?")
            return
        
        visit_time = self.extract_time(user_message)
        if not visit_time:
            print("🤖 What time would you like to book? (e.g., '7:30 PM' or '19:30')")
            return
        
        print(f"📅 Creating booking for {self.conversation_state['search_party_size']} people on {self.conversation_state['search_date']} at {visit_time}...")
        
        try:
            data = {
                "VisitDate": self.conversation_state['search_date'],
                "VisitTime": visit_time,
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
                
                print("🎉 Excellent! Your booking has been confirmed!")
                print()
                print(f"📅 Date: {self.conversation_state['search_date']}")
                print(f"🕐 Time: {visit_time}")
                print(f"👥 Party Size: {self.conversation_state['search_party_size']} people")
                print(f"🔢 Booking Reference: {booking_ref}")
                print()
                print("💡 You can check your booking details anytime by asking 'Show my booking'")
                print("   or modify it by saying 'Change my booking'.")
                
            else:
                print(f"❌ Error creating booking. Status: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def handle_booking_info(self, user_message):
        """Handle booking information requests"""
        if not self.current_booking:
            print("🤖 You don't have any active bookings. Would you like to make a new reservation?")
            return
        
        print(f"📋 Retrieving booking details for reference: {self.current_booking['reference']}...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/Booking/{self.current_booking['reference']}", 
                headers=HEADERS
            )
            
            if response.status_code == 200:
                booking_data = response.json()
                
                print("📋 Here are your booking details:")
                print()
                print(f"🔢 Reference: {self.current_booking['reference']}")
                print(f"📅 Date: {self.current_booking['date']}")
                print(f"🕐 Time: {self.current_booking['time']}")
                print(f"👥 Party Size: {self.current_booking['party_size']} people")
                print(f"📧 Email: {booking_data.get('customer_email', 'demo@example.com')}")
                print(f"📱 Phone: {booking_data.get('customer_mobile', '1234567890')}")
                print()
                print("💡 You can modify your booking by saying 'Change my booking'")
                print("   or cancel it by saying 'Cancel my booking'.")
                
            else:
                print(f"❌ Error retrieving booking. Status: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def handle_booking_modification(self, user_message):
        """Handle booking modification requests"""
        if not self.current_booking:
            print("🤖 You don't have any active bookings to modify. Would you like to make a new reservation?")
            return
        
        new_date = self.extract_date(user_message)
        new_time = self.extract_time(user_message)
        new_party_size = self.extract_party_size(user_message)
        
        if not any([new_date, new_time, new_party_size]):
            print("🤖 What would you like to change? You can modify the date, time, or party size.")
            print("   (e.g., 'Change to August 7th' or 'Change time to 8 PM')")
            return
        
        # Prepare update data
        update_data = {}
        if new_date:
            update_data["VisitDate"] = new_date
        if new_time:
            update_data["VisitTime"] = new_time
        if new_party_size:
            update_data["PartySize"] = new_party_size
        
        print(f"✏️ Updating your booking...")
        
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
                
                print("✅ Your booking has been updated successfully!")
                print()
                print(f"🔢 Reference: {self.current_booking['reference']}")
                print(f"📅 Date: {self.current_booking['date']}")
                print(f"🕐 Time: {self.current_booking['time']}")
                print(f"👥 Party Size: {self.current_booking['party_size']} people")
                print()
                print("🤖 Is there anything else you'd like to modify?")
                
            else:
                print(f"❌ Error updating booking. Status: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def handle_booking_cancellation(self, user_message):
        """Handle booking cancellation requests"""
        if not self.current_booking:
            print("🤖 You don't have any active bookings to cancel. Would you like to make a new reservation?")
            return
        
        print(f"❌ Cancelling your booking...")
        
        try:
            data = {
                "micrositeName": "TheHungryUnicorn",
                "bookingReference": self.current_booking['reference'],
                "cancellationReasonId": 1  # Default reason
            }
            
            response = requests.post(
                f"{BASE_URL}/Booking/{self.current_booking['reference']}/Cancel", 
                headers=HEADERS,
                data=data
            )
            
            if response.status_code == 200:
                cancelled_booking = self.current_booking.copy()
                self.current_booking = {}
                
                print("✅ Your booking has been cancelled successfully!")
                print()
                print(f"🔢 Reference: {cancelled_booking['reference']}")
                print(f"📅 Date: {cancelled_booking['date']}")
                print(f"🕐 Time: {cancelled_booking['time']}")
                print(f"👥 Party Size: {cancelled_booking['party_size']} people")
                print()
                print("😔 We're sorry to see you go. Would you like to make a new reservation for another time?")
                
            else:
                print(f"❌ Error cancelling booking. Status: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def process_message(self, user_message):
        """Process user message and return appropriate response"""
        user_message = user_message.lower().strip()
        
        # Check for quit/exit
        if user_message in ['quit', 'exit', 'bye']:
            print("👋 Goodbye! Have a great day!")
            self.running = False
            return
        
        # Check for help
        if user_message == 'help':
            self.print_help()
            return
        
        # Check for status
        if user_message == 'status':
            self.check_api_status()
            return
        
        # Check for availability search
        if any(word in user_message for word in ['available', 'availability', 'check', 'search', 'time', 'slot']):
            self.handle_availability_search(user_message)
            return
        
        # Check for booking creation
        if any(word in user_message for word in ['book', 'reservation', 'reserve', 'make booking']):
            self.handle_booking_creation(user_message)
            return
        
        # Check for booking info
        if any(word in user_message for word in ['my booking', 'booking info', 'reservation details', 'show booking']):
            self.handle_booking_info(user_message)
            return
        
        # Check for booking modification
        if any(word in user_message for word in ['change', 'modify', 'update', 'edit']):
            self.handle_booking_modification(user_message)
            return
        
        # Check for booking cancellation
        if any(word in user_message for word in ['cancel', 'cancellation']):
            self.handle_booking_cancellation(user_message)
            return
        
        # Default response
        print("🤖 Hi! I'm your restaurant booking assistant. I can help you:")
        print("   • Check table availability")
        print("   • Make reservations")
        print("   • View your booking details")
        print("   • Modify existing bookings")
        print("   • Cancel bookings")
        print()
        print("💡 Type 'help' for more information or just tell me what you'd like to do!")
    
    def run(self):
        """Main chat loop"""
        self.print_banner()
        self.check_api_status()
        
        while self.running:
            try:
                user_input = input("\n👤 You: ").strip()
                if user_input:
                    self.process_message(user_input)
                    
                    if not self.running:
                        break
                        
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Have a great day!")
                break
            except EOFError:
                print("\n\n👋 Goodbye! Have a great day!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                print("💡 Please try again or type 'help' for assistance.")

def main():
    """Main function"""
    try:
        assistant = TerminalBookingAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Have a great day!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
