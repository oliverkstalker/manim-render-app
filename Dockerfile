FROM manimcommunity/manim:stable

# Install required Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copy app code
COPY app.py /app/app.py
WORKDIR /app

# Drop to non-root user
USER manimuser

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
