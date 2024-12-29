import openmeteo_requests
import requests_cache
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed
from flask import Flask, render_template, request
import plotly.express as px
import plotly.io as pio
import time

# Initialize Flask app
app = Flask(__name__)

# Setup the Open-Meteo API client with cache (expires after 1 hour)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)

# Function to fetch weather data
@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def get_weather_data(latitude, longitude):
    start_time = time.time()  # Log the start time for optimization analysis

    # Setup the API request
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation", "rain", "cloud_cover", "surface_pressure", "wind_speed_10m"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation_probability", "surface_pressure", "cloud_cover", "visibility", "wind_speed_10m"]
    }

    # Make the API call (using the cached session)
    openmeteo = openmeteo_requests.Client(session=cache_session)
    try:
        responses = openmeteo.weather_api(url, params=params)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return empty dataframe on error
    
    response = responses[0]
    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
        "apparent_temperature": hourly.Variables(2).ValuesAsNumpy(),
        "precipitation_probability": hourly.Variables(3).ValuesAsNumpy(),
        "surface_pressure": hourly.Variables(4).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(5).ValuesAsNumpy(),
        "visibility": hourly.Variables(6).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(7).ValuesAsNumpy()
    }

    # Convert to DataFrame
    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Log how much time the request took
    elapsed_time = time.time() - start_time
    print(f"API request and data processing took {elapsed_time:.2f} seconds")

    return hourly_dataframe

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

        if hourly_dataframe.empty:
            return render_template('index.html', error_message="Unable to fetch weather data.")

        # Create the Plotly graph
        fig = px.line(
            hourly_dataframe,
            x='date',
            y=['temperature_2m', 'relative_humidity_2m', 'apparent_temperature', 
               'precipitation_probability', 'surface_pressure', 'cloud_cover', 
               'visibility', 'wind_speed_10m'],
            title='Hourly Weather Data',
            labels={
                'temperature_2m': 'Temperature (°C)',
                'relative_humidity_2m': 'Humidity (%)',
                'apparent_temperature': 'Apparent Temperature (°C)',
                'precipitation_probability': 'Precipitation Probability (%)',
                'surface_pressure': 'Surface Pressure (hPa)',
                'cloud_cover': 'Cloud Cover (%)',
                'visibility': 'Visibility (km)',
                'wind_speed_10m': 'Wind Speed (m/s)',
                'date': 'Date and Time'
            }
        )

        # Convert Plotly figure to HTML
        plot_html = pio.to_html(fig, full_html=False)

    # Return the rendered webpage with the graph
    return render_template('index.html', plot_html=plot_html)


