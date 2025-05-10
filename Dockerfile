# Use a Python image based on Alpine Linux
FROM python:3.11-alpine

#Create the directories
RUN mkdir -p /app
RUN mkdir -p /app/plugins

# Set the working directory
WORKDIR /app

# Install wget and build dependencies
#RUN apk add --no-cache wget

# Install core dependencies
RUN pip install --no-cache-dir \
    cryptography \
    pyasyncore \
    boto3 \
    prompt_toolkit \
    google-auth \
    requests

# Download the emailproxy.py from the plugins branch
RUN wget -O /app/emailproxy.py https://raw.githubusercontent.com/simonrob/email-oauth2-proxy/plugins/emailproxy.py
RUN wget -O /app/plugins/BasePlugin.py https://raw.githubusercontent.com/simonrob/email-oauth2-proxy/plugins/plugins/BasePlugin.py


# Copy the shell script into the container
COPY run_email_proxy.sh /app/

# Make the shell script executable
RUN chmod +x /app/run_email_proxy.sh

# Run the shell script
CMD ["/bin/sh", "/app/run_email_proxy.sh"]
