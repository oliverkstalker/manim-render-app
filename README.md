# Manim Render Service (Backend)

This is the **backend rendering service** for the Math Animation Tool. It receives Python code via a REST API, runs it using [Manim CE](https://docs.manim.community/), and returns the rendered video as an `.mp4` file. This service is designed to be run on a secure, isolated server to avoid executing untrusted code on the main web server.

---

## Purpose

* Accept Python + Manim code via `/render` endpoint.
* Parse the class name and render the animation.
* Return the resulting `.mp4` video file as a binary stream.

This backend is intended to be paired with a separate frontend (see **Math Animation Tool (Frontend)**) which handles the user interface and authentication.

---

## Project Structure

* **`app.py`**
  Flask application that:

  * Accepts POST requests with Python code.
  * Detects the main `Scene` subclass in the code.
  * Writes code to a temporary `.py` file.
  * Invokes the Manim CLI to render it.
  * Searches for the resulting `.mp4` and streams it back.

---

## Setup Instructions

### Requirements

* Python 3.8+
* [Manim CE](https://docs.manim.community/en/stable/installation.html) installed and available in the environment
* Flask

### Installation

```bash
pip install flask
pip install manim  # if not already installed
```

### Running the Server

```bash
python app.py
```

It will start a development server on `http://127.0.0.1:5000`.

---

## API Endpoint

### `POST /render`

**Payload:**

```json
{
  "code": "<python code using Manim>"
}
```

**Returns:**

* `200 OK` with binary `.mp4` stream if successful
* `400` if no code or malformed payload
* `500` if rendering fails
* `504` if rendering times out (default timeout: 5 minutes)

---

## Maintainer Notes

* **Security:** This code executes arbitrary Python. Only run this on a secure, isolated machine or container.

* **Temp Directory:** All rendering is done in `/tmp`. Change `MEDIA_DIR` if needed.

* **Output Location:** The code searches for output in:

  1. `/tmp/media/videos/...`
  2. `/tmp/scene_<id>.mp4`
  3. fallback: global `/tmp/**/*.mp4`

* **Scene Detection:** Scene class must follow:

  ```python
  class MyScene(Scene):
  ```

  The system extracts the first matching class name.

* **Cleaning Up:** Temporary Python files are deleted after rendering, but rendered videos are kept unless cleaned manually.

---

## Troubleshooting

* **"No Scene class found"**:

  * Ensure your code defines a class inheriting from `Scene`, e.g., `class Example(Scene):`

* **Render times out:**

  * Code must render within 5 minutes. Check for infinite loops or large resolution issues.

* **Cannot locate `.mp4`**:

  * Manim output structure may differ by version. Update `glob` paths if needed.

* **Permission errors**:

  * Ensure `/tmp` or `MEDIA_DIR` is writable by the process user.

---

## Example Input Code

```python
from manim import *

class IntroScene(Scene):
    def construct(self):
        txt = Text("Hello, Math World!")
        self.play(Write(txt))
```

---

## Credits

Backend Manim rendering service maintained by Oliver Stalker.
Designed for use with the Texas A\&M University Math Learning Center.

---
