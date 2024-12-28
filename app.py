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

# Function to fetch weather data for different time periods
@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))  # 5 retries with 2 seconds between each retry
def get_weather_data(latitude, longitude, forecast_days=1):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation", "rain", "cloud_cover", "surface_pressure", "wind_speed_10m"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation_probability", "surface_pressure", "cloud_cover", "visibility", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "precipitation_hours", "windspeed_10m_max"],
        "forecast_days": forecast_days  # Control the forecast duration (1, 3, or 7 days)
    }
    openmeteo = openmeteo_requests.Client(session=cache_session)  # Correct client initialization
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    if forecast_days == 1:
        return response.Daily()  # Return 1-day forecast data
    elif forecast_days == 3:
        return response.Daily()  # Return 3-day forecast data
    elif forecast_days == 7:
        return response.Daily()  # Return 7-day forecast data

# Function to create a plot for the forecast data
def create_forecast_plot(forecast_data, title):
    forecast_df = pd.DataFrame(forecast_data)
    fig = px.line(
        forecast_df,
        x='date',
        y=['temperature_2m_max', 'temperature_2m_min'],
        title=title,
        labels={
            'temperature_2m_max': 'Max Temperature (°C)',
            'temperature_2m_min': 'Min Temperature (°C)',
            'date': 'Date'
        }
    )
    return pio.to_html(fig, full_html=False)

# Route to display the weather data and graph
@app.route('/', methods=['GET', 'POST'])
def index():
    plot_html_7_days = None
    plot_html_3_days = None
    plot_html_1_day = None

    if request.method == 'POST':
        # Get latitude and longitude from form input
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])

        # Fetch weather data for 7 days, 3 days, and 1 day
        forecast_7_days = get_weather_data(latitude, longitude, forecast_days=7)
        forecast_3_days = get_weather_data(latitude, longitude, forecast_days=3)
        forecast_1_day = get_weather_data(latitude, longitude, forecast_days=1)

        # Create the plots for each forecast duration
        plot_html_7_days = create_forecast_plot(forecast_7_days, title='7-Day Weather Forecast')
        plot_html_3_days = create_forecast_plot(forecast_3_days, title='3-Day Weather Forecast')
        plot_html_1_day = create_forecast_plot(forecast_1_day, title='1-Day Weather Forecast')

    # Return the rendered webpage with the graphs
    return render_template('index.html', 
                           plot_html_7_days=plot_html_7_days,
                           plot_html_3_days=plot_html_3_days,
                           plot_html_1_day=plot_html_1_day)


if __name__ == '__main__':
    import os
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))


if __name__ == '__main__':
    import os
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
