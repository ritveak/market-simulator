# Use the official Python 3.9 image
FROM python:3.9

# Set the working directory to /app
WORKDIR /app

# Copy your requirements.txt first (for faster builds)
COPY requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of your app's code
COPY . .

# Expose the port Streamlit uses
EXPOSE 7860

# Command to run the app on the required port 7860
CMD ["streamlit", "run", "app.py", "--server.port", "7860", "--server.address", "0.0.0.0"]