import requests

API_KEY = "REMOVED_API_KEY"

def get_coordinates(city):

    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},IN&limit=1&appid={API_KEY}"

    response = requests.get(url).json()

    lat = response[0]["lat"]
    lon = response[0]["lon"]

    return lat, lon
def get_weather(city):

    lat, lon = get_coordinates(city)

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"

    response = requests.get(url).json()

    weather = {
        "temperature": response["main"]["temp"],
        "humidity": response["main"]["humidity"],
        "condition": response["weather"][0]["description"]
    }

    return weather
print(get_weather("Ongole"))