import openmeteo_requests
import requests_cache
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed
from flask import Flask, render_template, request
import plotly.express as px
import plotly.io as pio

# Initialize Flask app
app = Flask(__name__)

# Setup the Open-Meteo API client with cache
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)

# Function to fetch weather data with retry logic
@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))  # 5 retries with 2 seconds between each retry
def get_weather_data(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation_probability", "wind_speed_10m"]
    }
    openmeteo = openmeteo_requests.Client(session=cache_session)  # Correct client initialization
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(2).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(3).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )
    }
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
    hourly_data["precipitation_probability"] = hourly_precipitation_probability
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m

    return pd.DataFrame(data=hourly_data)

# Route to display the weather data and graph
@app.route('/', methods=['GET', 'POST'])
def index():
    plot_html = None
    if request.method == 'POST':
        # Get latitude and longitude from form input
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])

        # Fetch the weather data
        hourly_dataframe = get_weather_data(latitude, longitude)

        # Create the Plotly graph
        fig = px.line(
            hourly_dataframe,
            x='date',
            y=['temperature_2m', 'relative_humidity_2m', 'precipitation_probability', 'wind_speed_10m'],
            title='Hourly Weather Data',
            labels={
                'temperature_2m': 'Temperature (°C)',
                'relative_humidity_2m': 'Humidity (%)',
                'precipitation_probability': 'Precipitation Probability (%)',
                'wind_speed_10m': 'Wind Speed (m/s)',
                'date': 'Date and Time'
            }
        )

        # Convert Plotly figure to HTML
        plot_html = pio.to_html(fig, full_html=False)

    # Return the rendered webpage with the graph
    return render_template('index.html', plot_html=plot_html)  # Correct path


