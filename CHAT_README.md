# 🍽️ Restaurant Booking Chat Interface

A complete restaurant booking system with an intelligent chat interface that allows users to check availability, make reservations, and manage bookings through natural language conversation.

## 🚀 Quick Start

### 1. Environment Setup (10 mins)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your API token and configuration

# Start the mock API server
python -m app

# In a new terminal, start the chat interface
python chat_app.py
```

### 2. Access Points

- **🌐 Web Chat Interface**: http://localhost:5000
- **📚 API Documentation**: http://localhost:8547/docs
- **🔧 Mock API Server**: http://localhost:8547

## 🎯 Features

### ✅ Core User Stories Implemented

1. **🔍 Check Availability**
   - Natural language date and party size extraction
   - Real-time availability search via API
   - Formatted time slot display

2. **📅 Book a Reservation**
   - Guided booking flow
   - Date, time, and party size collection
   - Automatic customer data generation for demo

3. **📋 Check Reservation Info**
   - Retrieve booking details by reference
   - Display comprehensive booking information
   - Easy access to modification options

4. **✏️ Modify Booking**
   - Update date, time, or party size
   - Real-time API updates
   - Confirmation of changes

5. **❌ Cancel Booking**
   - Simple cancellation process
   - Confirmation and cleanup
   - Option to make new reservations

## 🛠️ Technical Implementation

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Flask Backend   │    │  Mock API       │
│   (HTML/JS)     │◄──►│  (chat_app.py)   │◄──►│  (FastAPI)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components

1. **Flask Web Application** (`chat_app.py`)
   - RESTful API endpoints
   - Natural language processing
   - Conversation state management
   - API integration layer

2. **HTML/CSS/JavaScript Frontend** (`templates/chat.html`)
   - Modern, responsive design
   - Real-time chat interface
   - Quick action buttons
   - Status indicators

3. **Terminal Interface** (`chat_terminal.py`)
   - Command-line alternative
   - Same functionality as web interface
   - Perfect for testing and development

4. **Mock API Server** (existing)
   - FastAPI-based restaurant booking API
   - SQLite database with sample data
   - JWT authentication

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Copy the example file
cp env.example .env

# Edit .env with your values
BOOKING_API_TOKEN=your-token-here
BASE_URL_PREFIX=http://localhost:8547/api/ConsumerApi/v1/Restaurant
RESTAURANT=TheHungryUnicorn
FLASK_SECRET_KEY=your-secret-key
FLASK_DEBUG=True
```

**Required Variables:**
- `BOOKING_API_TOKEN`: Your API authentication token
- `BASE_URL_PREFIX`: Base URL for the API
- `RESTAURANT`: Restaurant name identifier

### Bearer Token Setup

Every API request includes:
```python
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....",
    "Content-Type": "application/x-www-form-urlencoded"
}
```

## 📱 Usage Examples

### Web Interface

1. **Open**: http://localhost:5000
2. **Check Availability**: "Check availability for August 6th for 4 people"
3. **Make Booking**: "Book a table for 6 people on August 7th at 7 PM"
4. **View Booking**: "Show my booking"
5. **Modify**: "Change my booking to August 8th"
6. **Cancel**: "Cancel my reservation"

### Terminal Interface

```bash
python chat_terminal.py

# Available commands:
help                    # Show help
status                  # Check API connection
check availability      # Search for available slots
book table             # Make a reservation
show my booking        # View booking details
change my booking      # Modify existing booking
cancel my booking      # Cancel reservation
quit                   # Exit application
```

## 🧠 Natural Language Processing

### Date Extraction
- **Formats**: "August 6th", "2025-08-06", "6th August"
- **Defaults**: Automatically sets year to 2025
- **Flexibility**: Handles various date formats

### Time Extraction
- **Formats**: "7:30 PM", "19:30", "7 PM", "7 o'clock"
- **Conversion**: Automatic 12/24 hour format conversion
- **Validation**: Ensures reasonable time ranges

### Party Size Extraction
- **Patterns**: "4 people", "party of 6", "for 3 guests"
- **Validation**: Range 1-20 people
- **Fallback**: Extracts standalone numbers

## 🔌 API Integration

### Endpoints Used

1. **POST** `/AvailabilitySearch` - Check table availability
2. **POST** `/BookingWithStripeToken` - Create new booking
3. **GET** `/Booking/{ref}` - Retrieve booking details
4. **PATCH** `/Booking/{ref}` - Update existing booking
5. **POST** `/Booking/{ref}/Cancel` - Cancel booking

### Request Examples

```python
# Check Availability
data = {
    "VisitDate": "2025-08-06",
    "PartySize": 2,
    "ChannelCode": "ONLINE"
}
response = requests.post(f"{BASE_URL}/AvailabilitySearch", headers=headers, data=data)

# Create Booking
data = {
    "VisitDate": "2025-08-06",
    "VisitTime": "19:30",
    "PartySize": 2,
    "ChannelCode": "ONLINE",
    "Customer[FirstName]": "John",
    "Customer[Surname]": "Doe",
    "Customer[Email]": "john@example.com"
}
response = requests.post(f"{BASE_URL}/BookingWithStripeToken", headers=headers, data=data)
```

## 🎨 User Interface Features

### Web Interface
- **Responsive Design**: Works on desktop and mobile
- **Real-time Chat**: Instant message processing
- **Quick Actions**: One-click common operations
- **Status Indicators**: API connection monitoring
- **Modern UI**: Gradient backgrounds and smooth animations

### Terminal Interface
- **Color-coded Output**: Easy-to-read responses
- **Interactive Prompts**: Guided user experience
- **Error Handling**: Clear error messages
- **Help System**: Comprehensive command documentation

## 🧪 Testing

### Manual Testing

1. **Start both servers**:
   ```bash
   # Terminal 1: Mock API
   python -m app
   
   # Terminal 2: Web Chat
   python chat_app.py
   
   # Terminal 3: Terminal Chat (optional)
   python chat_terminal.py
   ```

2. **Test scenarios**:
   - Check availability for various dates/party sizes
   - Make a booking and verify creation
   - View booking details
   - Modify booking information
   - Cancel booking and verify cleanup

### API Testing

```bash
# Test API directly
curl -X POST "http://localhost:8547/api/ConsumerApi/v1/Restaurant/TheHungryUnicorn/AvailabilitySearch" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "VisitDate=2025-08-06&PartySize=2&ChannelCode=ONLINE"
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Mock API: 8547
   - Web Chat: 5000
   - Ensure ports are available

2. **API Connection**
   - Check if mock server is running
   - Verify Bearer token is valid
   - Check network connectivity

3. **Dependencies**
   - Ensure all requirements are installed
   - Use virtual environment if needed
   - Check Python version compatibility

### Debug Mode

```bash
# Enable debug logging
export FLASK_DEBUG=1
python chat_app.py

# Check API status
curl http://localhost:5000/status
```

## 🔮 Future Enhancements

### Potential Improvements

1. **Advanced NLP**
   - Machine learning intent recognition
   - Context-aware conversations
   - Multi-language support

2. **Enhanced UI**
   - Calendar picker for dates
   - Time slot visualization
   - Booking confirmation emails

3. **Integration Features**
   - Payment processing
   - SMS notifications
   - Calendar integration

4. **Analytics**
   - Conversation analytics
   - User behavior tracking
   - Performance metrics

## 📚 Documentation

### Additional Resources

- **API Documentation**: http://localhost:8547/docs
- **Source Code**: Check individual Python files
- **Database Schema**: See `app/models.py`
- **API Routes**: See `app/routers/`

### Code Structure

```
├── chat_app.py              # Flask web application
├── chat_terminal.py         # Terminal interface
├── templates/
│   └── chat.html           # Web interface template
├── app/                     # Mock API server
│   ├── main.py             # FastAPI application
│   ├── routers/            # API endpoints
│   └── models.py           # Database models
└── requirements.txt         # Python dependencies
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Add docstrings to functions
- Include type hints where possible
- Write comprehensive tests

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation
3. Check server logs for errors
4. Verify all services are running

---

**🎉 Happy Booking! 🎉**

The restaurant booking chat interface is now ready to use! Start with the web interface for the best user experience, or use the terminal version for quick testing and development.
