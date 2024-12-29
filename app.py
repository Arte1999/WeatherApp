import openmeteo_requests
import requests_cache
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed
from flask import Flask, render_template, request
import plotly.express as px
import plotly.io as pio
import os
import logging

# Initialize Flask app
app = Flask(__name__)

# Set up logging to capture detailed errors
logging.basicConfig(level=logging.DEBUG)  # Log everything (DEBUG level)

# Check if the app is running on Vercel (serverless environment)
if os.getenv('VERCEL') == '1':
    # Disable caching on Vercel (serverless) by not initializing requests_cache
    cache_session = None
else:
    # Use caching for local or other environments
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)

# Function to fetch weather data
@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))  # Retry 5 times with 2 seconds between retries
def get_weather_data(latitude, longitude):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation", "rain", "cloud_cover", "surface_pressure", "wind_speed_10m"],
            "hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation_probability", "surface_pressure", "cloud_cover", "visibility", "wind_speed_10m"]
        }

        # Only initialize the client if caching is enabled
        if cache_session:
            openmeteo = openmeteo_requests.Client(session=cache_session)  # Correct client initialization
        else:
            openmeteo = openmeteo_requests.Client()  # Initialize without cache

        # Send the request to Open-Meteo API
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Process hourly data
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()
        hourly_surface_pressure = hourly.Variables(4).ValuesAsNumpy()
        hourly_cloud_cover = hourly.Variables(5).ValuesAsNumpy()
        hourly_visibility = hourly.Variables(6).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(7).ValuesAsNumpy()

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
        hourly_data["apparent_temperature"] = hourly_apparent_temperature
        hourly_data["precipitation_probability"] = hourly_precipitation_probability
        hourly_data["surface_pressure"] = hourly_surface_pressure
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["visibility"] = hourly_visibility
        hourly_data["wind_speed_10m"] = hourly_wind_speed_10m

        return pd.DataFrame(data=hourly_data)
    
    except Exception as e:
        logging.error("Error in get_weather_data: %s", str(e))
        raise

# Route to display the weather data and graph
@app.route('/', methods=['GET', 'POST'])
def index():
    plot_html = None
    if request.method == 'POST':
        try:
            # Get latitude and longitude from form input
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])

            # Fetch the weather data
            hourly_dataframe = get_weather_data(latitude, longitude)

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
        
        except Exception as e:
            logging.error("Error in POST request: %s", str(e))
            plot_html = f"An error occurred: {str(e)}"

    # Return the rendered webpage with the graph
    return render_template('index.html', plot_html=plot_html)

if __name__ == "__main__":
    app.run(debug=True)
