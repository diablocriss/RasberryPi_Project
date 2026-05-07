from datetime import datetime


class ResponseHandler:
    _RULES = [
        (["hello", "hi", "hey"],               "Hello! How can I help you?"),
        (["bye", "goodbye", "see you"],         "Goodbye! Have a great day."),
        (["what time", "current time"],         None),   # dynamic
        (["how are you", "status"],             "All systems operational. Running MoonShine pipeline."),
    ]

    def process(self, text: str) -> str:
        t = text.lower().strip()
        if not t:
            return "I didn't hear anything. Please try again."
        for keywords, response in self._RULES:
            if any(kw in t for kw in keywords):
                if response is None:
                    return f"The current time is {datetime.now().strftime('%H:%M')}."
                return response
        return "Sorry, please say it again."
