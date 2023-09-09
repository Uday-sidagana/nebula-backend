# nebula-backend

This Python script provides a microservice for extracting data from Google Forms. It uses the Flask framework to expose an API endpoint that can parse Google Forms URLs and return structured form data.

### Installation

1. Clone the repository or download the script.

2. Install the required Python packages using pip:

   ```bash
   pip install Flask requests beautifulsoup4
   ```

### Usage

#### Running the Microservice

To start the microservice, run the following command:

```bash
python script.py
```

The script will be accessible at `http://0.0.0.0:8000`. You can change the host and port in the script if needed.

#### Parsing a Google Forms URL

You can use the script to parse a Google Forms URL and retrieve its structured data.

**Example Request:**

```http
GET /?url=<Google_Forms_URL>
```

Replace `<Google_Forms_URL>` with the URL of the Google Form you want to parse.

**Example Response:**

The microservice will respond with JSON data representing the parsed form:

```json
{
    "Title": "Form Title",
    "Header": "Form Header",
    "Desc": "Form Description",
    "Path": "Form Path",
    "Action": "Form Action",
    "Fbzx": "Form Fbzx",
    "SectionCount": 1,
    "AskEmail": false,
    "Fields": [
        {
            "ID": 1,
            "Label": "Field Label",
            "Desc": "Field Description",
            "TypeID": 0,
            "Widgets": [
                {
                    "ID": "widget1",
                    "required": false
                }
            ]
        },
        // Other form fields...
    ]
}
```

### Options

- **-f:** Fetch and parse a Google Forms URL directly from the command line.

```bash
python script.py -f <Google_Forms_URL>
```

### Notes

- This script is designed for educational purposes and might not work with all Google Forms variations.

- Make sure to provide a public URL for Google Forms.

- Error messages will be returned for invalid URLs or other issues.

### Shutting Down

To shut down the microservice gracefully, press `Ctrl+C` in the terminal where it's running.

---

Feel free to use and extend this microservice for your own projects. If you encounter issues or have suggestions for improvements, please let us know.