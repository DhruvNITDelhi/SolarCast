# Use the official Python 3.12 image
FROM python:3.12

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# Expose the port (Hugging Face expects port 7860)
EXPOSE 7860

# Command to run the FastAPI app on the Hugging Face port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
