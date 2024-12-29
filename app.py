import openmeteo_requests
import pandas as pd
from flask import Flask, render_template, request
import plotly.express as px
import plotly.io as pio

# Initialize Flask app
app = Flask(__name__)

# Function to fetch weather data with optimized API call
def get_weather_data(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation_probability"],
        "timezone": "auto"  # Automatically set timezone to prevent unnecessary timezone calculations
    }

    openmeteo = openmeteo_requests.Client()
    
    try:
        # Call the API and get the data
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Process only the relevant parts (limit data processing to minimize delay)
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(3).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature_2m": hourly_temperature_2m,
            "relative_humidity_2m": hourly_relative_humidity_2m,
            "apparent_temperature": hourly_apparent_temperature,
            "precipitation_probability": hourly_precipitation_probability
        }

        return pd.DataFrame(data=hourly_data)

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

# Route to display the weather data and graph
@app.route('/', methods=['GET', 'POST'])
def index():
    plot_html = None
    if request.method == 'POST':
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])

        # Fetch the weather data
        hourly_dataframe = get_weather_data(latitude, longitude)

        if hourly_dataframe is not None:
            # Create the Plotly graph
            fig = px.line(
                hourly_dataframe,
                x='date',
                y=['temperature_2m', 'relative_humidity_2m', 'apparent_temperature', 'precipitation_probability'],
                title='Hourly Weather Data',
                labels={
                    'temperature_2m': 'Temperature (°C)',
                    'relative_humidity_2m': 'Humidity (%)',
                    'apparent_temperature': 'Apparent Temperature (°C)',
                    'precipitation_probability': 'Precipitation Probability (%)',
                    'date': 'Date and Time'
                }
            )

            # Convert Plotly figure to HTML
            plot_html = pio.to_html(fig, full_html=False)

    # Return the rendered webpage with the graph
    return render_template('index.html', plot_html=plot_html)

if __name__ == '__main__':
    app.run(debug=True)



