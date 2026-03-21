import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


class WeatherService:
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY

    def get_weather(self, city: str) -> str:
        """
        Fetches current weather for a specific city.
        """
        if not self.api_key:
            return "Error: Weather service is not configured (Missing API Key)."

        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }

        try:
            # Set a timeout so your bot doesn't hang if the weather API is down
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                temp = data["main"]['temp']
                desc = data["weather"][0]["description"].capitalize()
                humidity = data['main']['humidity']
                
                return (f"🌤 *Weather in {city.title()}:*\n"
                        f"🌡 Temperature: {temp}°C\n"
                        f"☁ Description: {desc}\n"
                        f"💧 Humidity: {humidity}%")
            elif response.status_code == 404:
                return f"Could not find weather for '{city}'. Please check the spelling."
            else:
                return "Sorry, I couldn't fetch the weather right now."
                
        except requests.exceptions.RequestException as e:
            # Log the error in a real app (print for now)
            logger.error("Weather API error: %s", e)
            return "Connection error. Please try again later."