import requests

API_KEY = "REMOVED_API_KEY"

def get_weather(city):

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(url)
        data = response.json()

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]

        weather_report = f"""
Weather in {city}

Temperature: {temp}°C
Humidity: {humidity}%
Condition: {description}
"""

        return weather_report

    except:
        return "Unable to fetch weather data."