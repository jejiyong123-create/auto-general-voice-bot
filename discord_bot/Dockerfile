# Use the official Python image as a base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .
COPY bot.py /app

# Expose the port for the health server
EXPOSE 8000

# Set the command to run the bot
CMD ["python", "bot.py"]
