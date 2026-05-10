"""Hotel-reception response handler backed by the FastText intent classifier."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
import random
import re
from typing import Any

logger = logging.getLogger(__name__)

INTENT_RESPONSES: dict[str, list[str]] = {
    "greeting": [
        "Welcome to the hotel! How may I assist you today?",
        "Good day! How can I help you?",
        "Hello and welcome! What can I do for you?",
        "Hi there! How may I make your stay more comfortable?",
        "Welcome! Is there anything you need assistance with?",
        "Good to see you! What brings you to our desk?",
        "Hello! I'm at your service. What can I do?",
        "Welcome! It's a pleasure to have you here.",
        "Greetings! How may I be of assistance?",
        "Hi! I hope you're enjoying your stay so far.",
        "Welcome in! Please let me know how I can help.",
        "Hello there! What can I assist you with today?",
    ],
    "goodbye": [
        "Thank you for visiting. Have a wonderful day!",
        "We hope to see you again soon!",
        "Take care and enjoy the rest of your day!",
        "Goodbye! Safe travels!",
        "It was a pleasure assisting you today.",
        "Farewell! Don't hesitate to return if you need anything.",
        "Enjoy the rest of your stay. Goodbye!",
        "Thank you for stopping by. Have a great one!",
        "Until next time! Wishing you all the best.",
        "Goodbye for now. We're always here to help.",
        "Thanks for chatting with me. Take care!",
        "Safe journey! We look forward to your next visit.",
    ],
    "check_in": [
        "I'd be happy to help you check in. May I have your name, please?",
        "Certainly! Let's get your check-in started.",
        "Welcome! Could you please provide your reservation name?",
        "Of course. May I have your booking details?",
        "Let me assist you with the check-in process.",
        "Absolutely. What name is the reservation under?",
        "I can help with that. Do you have your booking confirmation?",
        "Right away. May I ask for your full name?",
        "Let's get you settled in. Your name, please?",
        "Happy to help! Could I have your reservation details?",
        "Sure thing. Which name did you book under?",
        "Welcome! I'll find your reservation. One moment.",
    ],
    "check_out": [
        "I'll assist you with check-out. What is your room number?",
        "Certainly. May I have your room number, please?",
        "I can help with your check-out right away.",
        "Sure thing! Which room are you checking out from?",
        "Let's complete your check-out process.",
        "Of course. What was your room number?",
        "I'll process that for you now. Room number?",
        "No problem. Which room will you be leaving?",
        "Right away. May I confirm your room number?",
        "Let me finalize your check-out. Which room?",
        "Happy to assist. Could you tell me your room number?",
        "I'll get your bill ready. What room were you in?",
    ],
    "room_inquiry": [
        "Let me check our room availability. What dates are you looking for?",
        "Certainly! What type of room are you interested in?",
        "I'd be happy to help you find a room.",
        "Could you tell me your preferred check-in dates?",
        "Let me see what rooms we currently have available.",
        "We have several room types. Which would suit you best?",
        "I can check availability. When were you planning to stay?",
        "What kind of room are you looking for? Standard or deluxe?",
        "Let me look that up. How many nights will you be staying?",
        "Of course. Any preference for floor or view?",
        "I'll browse our available rooms. Dates please?",
        "We may have something perfect. What dates do you need?",
    ],
    "facilities": [
        "Our facilities include a gym, pool, and restaurant. What would you like to know?",
        "We offer several amenities for our guests.",
        "Our hotel features a spa, swimming pool, and fitness center.",
        "I'd be happy to explain our hotel facilities.",
        "We have many services available to make your stay comfortable.",
        "The gym and pool are on the ground floor. What interests you?",
        "We have a restaurant, bar, and 24-hour room service.",
        "Our facilities are available daily. What would you like to use?",
        "Let me tell you about our amenities. What are you looking for?",
        "From spa to gym, we have it all. What catches your eye?",
        "Our hotel offers complimentary access to most facilities.",
        "Breakfast is served from 6:30 AM. The pool opens at 7.",
    ],
    "wifi": [
        "Our WiFi network is 'HotelGuest'. The password is 'stayhappy2024'.",
        "You can connect to the 'HotelGuest' network.",
        "The WiFi password is available at the front desk as well.",
        "Feel free to use our complimentary WiFi service.",
        "Let me provide you with the internet access details.",
        "The network name is 'HotelGuest' and it's free for all guests.",
        "Connect to 'HotelGuest' - no password needed in the lobby.",
        "WiFi is complimentary throughout the hotel premises.",
        "Our guest WiFi is always on and available to you.",
        "You'll find 'HotelGuest' in your network list. It's free.",
        "Internet access is complimentary. Enjoy your connection!",
        "The WiFi details are also printed on your key card sleeve.",
    ],
    "directions": [
        "Let me help you find your way. Where would you like to go?",
        "Of course! Please tell me your destination.",
        "I'd be happy to provide directions.",
        "Where would you like assistance getting to?",
        "Let me guide you to your destination.",
        "I can point you in the right direction. Where to?",
        "Certainly. Which part of the hotel or city are you looking for?",
        "Tell me where you'd like to go and I'll guide you.",
        "Navigating is easy. What are you trying to find?",
        "Happy to direct you. What's your destination?",
        "I can help with hotel or city directions. Which one?",
        "Lost? Not anymore. Where would you like to go?",
    ],
    "complaint": [
        "I'm sorry to hear that. Let me notify our staff immediately.",
        "I sincerely apologize for the inconvenience.",
        "Thank you for bringing this to our attention.",
        "We're very sorry about the issue you experienced.",
        "Let me resolve this problem for you as quickly as possible.",
        "I understand your frustration. Help is on the way.",
        "That shouldn't have happened. I'll fix this right now.",
        "My apologies. I'll escalate this to the team promptly.",
        "Please accept our sincere apologies. We'll make this right.",
        "I'm very sorry. Let me send someone to assist you.",
        "We take feedback seriously. Thank you for letting us know.",
        "I'll personally ensure this gets resolved for you.",
    ],
    "concierge": [
        "I'd love to help with recommendations. What are you interested in?",
        "Certainly! I can suggest restaurants and attractions nearby.",
        "Our concierge service is happy to assist you.",
        "What kind of activities are you looking for?",
        "I'd be delighted to recommend local experiences.",
        "Looking for dining, sightseeing, or entertainment?",
        "The city has wonderful attractions. What catches your eye?",
        "I have great suggestions. What type of cuisine or activity?",
        "Let me share the best local spots. Any preferences?",
        "From fine dining to hidden gems, what sounds good?",
        "I can book reservations for you as well. Interested?",
        "Our city guide is at your service. What do you enjoy?",
    ],
    "confirm_yes": [
        "Great, let me proceed with that.",
        "Certainly! I'll take care of it.",
        "Perfect, I'll handle that for you.",
        "Absolutely. Please give me a moment.",
        "Done. Let's continue.",
        "Wonderful. I'm on it right now.",
        "Excellent. Leave it with me.",
        "Consider it done. Anything else?",
        "Fantastic. I'll make that happen.",
        "Alright then. Processing now.",
        "Yes, of course. Just a moment please.",
        "Brilliant. Let me sort that out for you.",
    ],
    "confirm_no": [
        "Alright, let me know if you need anything else.",
        "No problem at all.",
        "Understood. Feel free to ask anytime.",
        "That's perfectly fine.",
        "Okay, I'm here if you change your mind.",
        "Not a worry. I'm always available.",
        "Fair enough. What else can I help with?",
        "No worries at all. Take your time.",
        "That's totally fine. I'll be right here.",
        "Alright. Just say the word if you need me.",
        "Sure thing. Let me know if anything changes.",
        "Okay then. Do you need anything else?",
    ],
    "identity": [
        "Thank you. Let me pull up your information.",
        "Got it. One moment while I check the system.",
        "Thank you for confirming your identity.",
        "Let me retrieve your details.",
        "I'll look up your reservation information now.",
        "Perfect. I have your profile right here.",
        "Thank you. Your records are loading now.",
        "I've found your booking. Let's proceed.",
        "Great. I can see your details now.",
        "One moment, please. Accessing your reservation.",
        "Confirmed. I have everything I need.",
        "Thank you for verifying. How can I proceed?",
    ],
    "thanks": [
        "You're welcome! Is there anything else I can help with?",
        "My pleasure!",
        "Happy to help!",
        "You're very welcome.",
        "Anytime! Let me know if you need anything else.",
        "It was my pleasure. Anything else?",
        "Glad to assist! I'm here if you need more help.",
        "No trouble at all. What else can I do?",
        "Always happy to serve. Need anything else?",
        "You're most welcome. Don't hesitate to ask.",
        "The pleasure is all mine. What's next?",
        "That's what I'm here for. Anything else?",
    ],
    "unknown": [
        "I apologize, I didn't quite understand. Could you please rephrase that?",
        "Sorry, could you say that again in another way?",
        "I'm not sure I understood your request.",
        "Could you clarify what you mean?",
        "I'm sorry, but I need a bit more information.",
        "I didn't catch that. Could you try saying it differently?",
        "Pardon me? Could you repeat that please?",
        "I'm still learning. Could you simplify your request?",
        "Sorry about that. What were you trying to ask?",
        "I want to help, but I didn't follow. Try again?",
        "My apologies. Could you word that another way?",
        "Hmm, I'm not following. Can you rephrase for me?",
    ],
}

EMPTY_INPUT_REPLY = "I didn't hear anything. Could you repeat?"

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def get_response(intent: str) -> str:
    responses = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
    return random.choice(responses)


class ResponseHandler:
    """Maps a transcribed guest utterance to a robot reply via FastText."""

    def __init__(
        self,
        classifier: Any | None = None,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.5,
        db_worker: Any | None = None,
    ) -> None:
        if classifier is None:
            try:
                from intent.classifier import IntentClassifier
            except ModuleNotFoundError:
                from src.intent.classifier import IntentClassifier  # type: ignore

            classifier = IntentClassifier(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
            )

        self._classifier = classifier
        self._db_worker = db_worker
        self._last_intent: str | None = None
        self._last_response: str | None = None
        self._pending_action: str | None = None
        self._pending_data: dict[str, Any] = {}
        self._missing_fields: list[str] = []

        missing = [label for label in self._classifier.labels if label not in INTENT_RESPONSES]
        if missing:
            raise RuntimeError(f"INTENT_RESPONSES is missing replies for: {missing}")

    def process(self, text: str) -> str:
        if not text or not text.strip():
            return EMPTY_INPUT_REPLY

        result = self._classifier.predict(text)
        intent = result["intent"]
        confidence = result["confidence"]

        logger.info("\033[36mINTENT %s @ %.2f for %r\033[0m", intent, confidence, text)

        if self._pending_action:
            return self._handle_pending_action(text, intent)
        if intent == "check_in":
            return self._start_check_in(text)
        if intent == "check_out":
            return self._start_check_out(text)
        if intent == "room_inquiry":
            return self._start_availability_check(text)
        if intent == "identity":
            return self._lookup_booking(text)
        return self._random_response(intent)

    def _random_response(self, intent: str) -> str:
        pool = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
        if intent == self._last_intent and len(pool) > 1:
            pool = [reply for reply in pool if reply != self._last_response] or pool
        response = random.choice(pool)
        self._last_intent = intent
        self._last_response = response
        return response

    def _reset_pending(self) -> None:
        self._pending_action = None
        self._pending_data = {}
        self._missing_fields = []

    def _extract_name(self, text: str) -> str | None:
        patterns = [
            r"(?:my name is|i'm|i am|name is|name)\s+([a-z][a-z'-]+)",
            r"(?:booking under|reservation under|under the name)\s+([a-z][a-z'-]+)",
            r"([a-z][a-z'-]+)\s+(?:here|checking in)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        return None

    def _extract_dates(self, text: str) -> tuple[str | None, str | None]:
        year = datetime.now().year
        iso_match = re.search(
            r"(\d{4})-(\d{2})-(\d{2})\s*(?:to|until|-)\s*(\d{4})-(\d{2})-(\d{2})",
            text,
        )
        if iso_match:
            return (
                f"{iso_match[1]}-{iso_match[2]}-{iso_match[3]}",
                f"{iso_match[4]}-{iso_match[5]}-{iso_match[6]}",
            )

        natural_match = re.search(
            r"(\w+)\s+(\d+)(?:st|nd|rd|th)?\s*(?:to|until|-)\s*(\d+)(?:st|nd|rd|th)?",
            text,
            re.IGNORECASE,
        )
        if natural_match:
            month_name = natural_match.group(1).lower()
            if month_name in _MONTHS:
                month = _MONTHS[month_name]
                return (
                    f"{year}-{month:02d}-{int(natural_match.group(2)):02d}",
                    f"{year}-{month:02d}-{int(natural_match.group(3)):02d}",
                )
        return None, None

    def _extract_room_number(self, text: str) -> str | None:
        match = re.search(r"room\s+(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"\b(\d{3})\b", text)
        if match:
            return match.group(1)
        return None

    def _handle_pending_action(self, text: str, intent: str) -> str:
        if self._pending_action == "create_booking":
            return self._continue_booking(text)
        if self._pending_action == "cancel_booking":
            return self._continue_cancel(text)
        if self._pending_action == "check_availability":
            return self._continue_availability(text)
        self._reset_pending()
        return self._random_response(intent)

    def _start_check_in(self, text: str) -> str:
        name = self._extract_name(text)
        check_in, check_out = self._extract_dates(text)
        self._pending_action = "create_booking"
        self._pending_data = {}
        self._missing_fields = []

        if name:
            self._pending_data["guest_name"] = name
        else:
            self._missing_fields.append("guest_name")

        if check_in and check_out:
            self._pending_data["check_in"] = check_in
            self._pending_data["check_out"] = check_out
        else:
            self._missing_fields.extend(["check_in", "check_out"])

        if "guest_name" in self._missing_fields:
            return "Welcome! May I have your name, please?"
        if "check_in" in self._missing_fields:
            return f"Thank you {self._pending_data['guest_name']}. What are your check-in and check-out dates?"
        return self._complete_booking()

    def _continue_booking(self, text: str) -> str:
        if "guest_name" in self._missing_fields:
            name = self._extract_name(text)
            if not name:
                return "I didn't catch your name. Could you repeat it?"
            self._pending_data["guest_name"] = name
            self._missing_fields.remove("guest_name")
            return f"Thank you {name}. What are your check-in and check-out dates?"

        if "check_in" in self._missing_fields or "check_out" in self._missing_fields:
            check_in, check_out = self._extract_dates(text)
            if not check_in or not check_out:
                return "What dates will you be staying? For example, 'May 20th to 22nd'."
            self._pending_data["check_in"] = check_in
            self._pending_data["check_out"] = check_out
            self._missing_fields = [
                field for field in self._missing_fields if field not in {"check_in", "check_out"}
            ]

        if not self._missing_fields:
            return self._complete_booking()
        return "Let me make sure I have everything. Could you repeat that?"

    def _complete_booking(self) -> str:
        if self._db_worker is None:
            self._reset_pending()
            return "Database is not available right now. Please see the front desk."

        data = self._pending_data
        try:
            booking_id = self._db_worker.create_booking(
                guest_name=data.get("guest_name", "Guest"),
                email=data.get("email", ""),
                check_in=data.get("check_in", "2026-01-01"),
                check_out=data.get("check_out", "2026-01-02"),
                guests=int(data.get("guests", 1)),
                room_id=int(data.get("room_id", 1)),
            ).wait(timeout=5.0)
        except TimeoutError:
            self._reset_pending()
            return "I'm having trouble with our booking system. Please wait a moment."
        except Exception:
            logger.exception("Booking creation failed")
            self._reset_pending()
            return "I'm having trouble with our booking system. Please see the front desk."

        guest_name = data.get("guest_name", "Guest")
        self._reset_pending()
        if int(booking_id) > 0:
            return random.choice(
                [
                    f"All set {guest_name}! Booking confirmed. ID: {booking_id}. Enjoy your stay!",
                    f"Confirmed! Your booking ID is {booking_id}, {guest_name}.",
                    f"Done! Booking {booking_id} for {guest_name}. Welcome!",
                ]
            )
        if int(booking_id) == -2:
            return "That room is already booked for those dates. Please let me check another option."
        return f"I'm sorry {guest_name}, there was an issue. Error code: {booking_id}."

    def _start_check_out(self, text: str) -> str:
        room_number = self._extract_room_number(text)
        if room_number:
            return self._complete_cancel(room_number)
        self._pending_action = "cancel_booking"
        self._pending_data = {}
        self._missing_fields = ["room_number"]
        return "I'll help with check-out. What is your room number?"

    def _continue_cancel(self, text: str) -> str:
        room_number = self._extract_room_number(text)
        if room_number:
            return self._complete_cancel(room_number)
        return "I need your room number to proceed with check-out."

    def _complete_cancel(self, room_number: str) -> str:
        if self._db_worker is None:
            self._reset_pending()
            return "Database unavailable. Please see the front desk for check-out."

        try:
            bookings = self._db_worker.list_bookings().wait(timeout=5.0)
        except Exception:
            logger.exception("Booking lookup for check-out failed")
            self._reset_pending()
            return "I'm having trouble accessing bookings right now. Please see the front desk."

        matched = next((row for row in bookings if str(row.get("room_number")) == room_number), None)
        if matched is None:
            self._reset_pending()
            return f"I couldn't find an active booking for room {room_number}."

        try:
            result = self._db_worker.cancel_booking(int(matched["booking_id"])).wait(timeout=5.0)
        except Exception:
            logger.exception("Booking cancel failed")
            self._reset_pending()
            return "The check-out system is not responding right now. Please see the front desk."

        self._reset_pending()
        if int(result) == 0:
            return random.choice(
                [
                    f"Check-out complete for room {room_number}. Thank you for staying with us.",
                    f"Room {room_number} is checked out. We hope you enjoyed your stay.",
                    f"You're all set. Room {room_number} has been checked out successfully.",
                ]
            )
        return f"I couldn't complete check-out for room {room_number}. Please see the front desk."

    def _start_availability_check(self, text: str) -> str:
        check_in, check_out = self._extract_dates(text)
        if not check_in or not check_out:
            self._pending_action = "check_availability"
            self._pending_data = {}
            self._missing_fields = ["check_in", "check_out"]
            return "What dates would you like to stay? For example, 'May 20th to 22nd'."
        return self._complete_availability(check_in, check_out)

    def _continue_availability(self, text: str) -> str:
        check_in, check_out = self._extract_dates(text)
        if not check_in or not check_out:
            return "Please tell me both dates, for example '2026-05-20 to 2026-05-22'."
        return self._complete_availability(check_in, check_out)

    def _complete_availability(self, check_in: str, check_out: str) -> str:
        if self._db_worker is None:
            self._reset_pending()
            return "Database is not available right now. Please ask the front desk."

        try:
            occupied = set(self._db_worker.check_availability(check_in, check_out).wait(timeout=5.0))
            rooms = self._db_worker.list_rooms().wait(timeout=5.0)
        except Exception:
            logger.exception("Availability lookup failed")
            self._reset_pending()
            return "I couldn't check room availability right now. Please try again in a moment."

        available = [room for room in rooms if int(room["room_id"]) not in occupied]
        self._reset_pending()
        if not available:
            return f"Sorry, I don't have any rooms available from {check_in} to {check_out}."

        sample = ", ".join(f"room {room['room_number']} ({room['room_type']})" for room in available[:3])
        extra = "" if len(available) <= 3 else f" plus {len(available) - 3} more"
        return f"I have {len(available)} room(s) available from {check_in} to {check_out}: {sample}{extra}."

    def _lookup_booking(self, text: str) -> str:
        if self._db_worker is None:
            return "Database is not available right now. Please see the front desk."

        name = self._extract_name(text)
        if not name:
            return "Please tell me the name on the booking so I can look it up."

        try:
            bookings = self._db_worker.list_bookings().wait(timeout=5.0)
        except Exception:
            logger.exception("Identity lookup failed")
            return "I'm having trouble accessing booking details right now."

        matched = [
            row for row in bookings
            if str(row.get("guest_name", "")).strip().lower() == name.lower()
        ]
        if not matched:
            return f"I couldn't find an active booking under {name}."

        booking = matched[0]
        return (
            f"I found your booking, {name}. "
            f"Room {booking['room_number']} is reserved from {booking['check_in_date']} "
            f"to {booking['check_out_date']}."
        )
