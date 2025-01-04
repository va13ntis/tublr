# Step 1: Use the official Python base image
FROM python:3.9-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements file into the container
COPY requirements.txt .

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the FastAPI application code into the container
COPY . .

# Step 6: Expose the port FastAPI will run on
EXPOSE 8000

# Step 7: Run FastAPI using Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
