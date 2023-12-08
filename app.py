# python app.py -f "https://docs.google.com/forms/d/e/1FAIpQLSfrcnr9voFQTb085IAfoTrJcstSOHy09dmbzzX5bzEWJ5s_TA/viewform?usp=sf_link"
import json
import logging
import re
import signal
import sys
import urllib.parse
import requests
import mysql.connector
from mysql.connector import errorcode
import time

from enum import Enum
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from flask import Flask, request, Response, g
from flask.cli import with_appcontext

# sql
mysql_config = {
    'user': 'root',
    'password': 'KK10293847kk!',
    'host': 'fe80::c9ec:878b:6e6:8c2b%12',
    'database': 'neb',
}

mysql_conn = mysql.connector.connect(**mysql_config)
mysql_cursor = mysql_conn.cursor()


app = Flask(__name__)


class FieldType(Enum):
    FieldShort = 0
    FieldParagraph = 1
    FieldChoices = 2
    FieldDropdown = 3
    FieldCheckboxes = 4
    FieldLinear = 5
    FieldTitle = 6
    FieldGrid = 7
    FieldSection = 8
    FieldDate = 9
    FieldTime = 10
    FieldImage = 11
    FieldVideo = 12
    FieldUpload = 13


class Widget(dict):
    pass


class Option(dict):
    pass


class Field:
    def __init__(self, ID, Label, Desc, TypeID, Widgets):
        self.ID = ID
        self.Label = Label
        self.Desc = Desc
        self.TypeID = TypeID
        self.Widgets = Widgets


class Fields(list):
    pass


class Form:
    def __init__(self):
        self.Title = ""
        self.Header = ""
        self.Desc = ""
        self.Path = ""
        self.Action = ""
        self.Fbzx = ""
        self.SectionCount = 0
        self.AskEmail = False
        self.Fields = Fields()


def to_int(i):
    if isinstance(i, int):
        return i

    if isinstance(i, (int, float)):
        try:
            return int(i)
        except ValueError:
            pass

    return 0


def to_string(i):
    if isinstance(i, (int, float)):
        return str(i)

    if isinstance(i, str):
        return i

    return ""


def to_bool(i):
    if isinstance(i, bool):
        return i

    if isinstance(i, (int, float)):
        try:
            return int(i) != 0
        except ValueError:
            pass

    return False


def to_slice(i):
    if isinstance(i, list):
        return i

    return None


def NewFieldFromData(data):
    f = Field(
        ID=to_int(data[0]),
        Label=to_string(data[1]),
        Desc=to_string(data[2]),
        TypeID=FieldType(to_int(data[3])),
        Widgets=[]
    )

    if f.TypeID == FieldType.FieldShort or f.TypeID == FieldType.FieldParagraph:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        f.Widgets = [Widget(ID=to_string(widget[0]),
                            required=to_bool(widget[2]))]

    elif f.TypeID in [FieldType.FieldChoices, FieldType.FieldCheckboxes, FieldType.FieldDropdown]:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        options = to_slice(widget[1])

        opts = []
        for opt in options:
            o = to_slice(opt)
            option = Option(label=to_string(o[0]))
            if len(o) > 2:
                option["href"] = to_string(o[2])
            if len(o) > 4:
                option["custom"] = to_bool(o[4])
            opts.append(option)

        f.Widgets = [Widget(
            ID=to_string(widget[0]),
            required=to_bool(widget[2]),
            options=opts
        )]

    elif f.TypeID == FieldType.FieldLinear:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        options = to_slice(widget[1])

        opts = []
        for opt in options:
            o = to_slice(opt)
            opts.append(Option(label=to_string(o[0])))

        legend = to_slice(widget[3])
        f.Widgets = [Widget(
            ID=to_string(widget[0]),
            required=to_bool(widget[2]),
            options=opts,
            legend=Option(
                first=to_string(legend[0]),
                last=to_string(legend[1])
            )
        )]

    elif f.TypeID == FieldType.FieldGrid:
        widgets = to_slice(data[4])
        f.Widgets = []
        for widget_data in widgets:
            widget = to_slice(widget_data)
            columns = to_slice(widget[1])

            cols = []
            for col_data in columns:
                col = to_slice(col_data)
                cols.append(Option(label=to_string(col[0])))

            f.Widgets.append(Widget(
                ID=to_string(widget[0]),
                required=to_bool(widget[2]),
                name=to_string(to_slice(widget[3])[0]),
                columns=cols
            ))

    elif f.TypeID == FieldType.FieldDate:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        options = to_slice(widget[7])

        f.Widgets = [Widget(
            ID=to_string(widget[0]),
            required=to_bool(widget[2]),
            options=Option(
                time=to_bool(options[0]),
                year=to_bool(options[1])
            )
        )]

    elif f.TypeID == FieldType.FieldTime:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        options = to_slice(widget[6])

        f.Widgets = [Widget(
            ID=to_string(widget[0]),
            required=to_bool(widget[2]),
            options=Option(
                duration=to_bool(options[0])
            )
        )]

    elif f.TypeID == FieldType.FieldVideo:
        extra = to_slice(data[6])
        opts = to_slice(extra[2])

        f.Widgets = [Widget(
            ID=to_string(extra[0]),
            res=Option(
                w=to_int(opts[0]),
                h=to_int(opts[1]),
                showText=to_bool(opts[2])
            )
        )]

    elif f.TypeID == FieldType.FieldImage:
        extra = to_slice(data[6])
        opts = to_slice(extra[2])

        f.Widgets = [Widget(
            ID=to_string(extra[0]),
            res=Option(
                w=to_int(opts[0]),
                h=to_int(opts[1]),
                showText=f.Desc != ""
            )
        )]

    elif f.TypeID == FieldType.FieldUpload:
        widgets = to_slice(data[4])
        widget = to_slice(widgets[0])
        options = to_slice(widget[10])

        f.Widgets = [Widget(
            ID=to_string(widget[0]),
            required=to_bool(widget[2]),
            options=Option(
                types=to_slice(options[1]),
                maxUploads=to_int(options[2]),
                maxSizeInBytes=to_string(options[3])
            )
        )]

    return f


def NewFieldsFromData(data):
    fields = Fields()
    for d in data:
        field = NewFieldFromData(to_slice(d))
        fields.append(field)
    return fields


class FormEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Form):
            # Convert the Form object to a dictionary that can be serialized
            return {
                "Title": obj.Title,
                "Header": obj.Header,
                "Desc": obj.Desc,
                "Path": obj.Path,
                "Action": obj.Action,
                "Fbzx": obj.Fbzx,
                "SectionCount": obj.SectionCount,
                "AskEmail": obj.AskEmail,
                "Fields": [field.__dict__ for field in obj.Fields],
            }
        elif isinstance(obj, FieldType):
            return obj.value  # Serialize FieldType as its integer value
        return super().default(obj)


def extract_images(response_text, form):
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(response_text.text, 'html.parser')

    for w in form.Fields:
        if w.TypeID == FieldType.FieldImage:
            # Use a regular expression to find the img element
            pattern = f'<div[^>]*data-item-id="{w.ID}"[^>]*>.*?<img[^>]*src="([^"]+)"'
            img_match = re.search(pattern, str(soup))

            if img_match:
                src = img_match.group(1)
                w.Widgets[0]["src"] = src
            else:
                w.Widgets[0]["src"] = ""
        elif w.TypeID == FieldType.FieldVideo:
            # Use a regular expression to find the iframe element
            pattern = f'<div[^>]*data-item-id="{w.ID}"[^>]*>.*?<iframe[^>]*src="([^"]+)"'
            iframe_match = re.search(pattern, str(soup))

            if iframe_match:
                src = iframe_match.group(1)
                w.Widgets[0]["src"] = src
            else:
                w.Widgets[0]["src"] = ""


def form_extract(response_text):
    # Create a BeautifulSoup object from the response content
    soup = BeautifulSoup(response_text.text, "html.parser")

    # Find the script element with the desired content
    script = None
    for s in soup.find_all("script"):
        if "var FB_PUBLIC_LOAD_DATA_" in s.text:
            script = s
            break

    if script is None:
        raise InvalidForm("Invalid Form")

    fbzx_input = soup.find("input", attrs={"name": "fbzx"})
    if fbzx_input is None:
        raise InvalidForm("Invalid Form")

    fbzx = fbzx_input.get("value", "")

    script_text = script.string
    script_text = script_text.replace(
        "var FB_PUBLIC_LOAD_DATA_ =", "").strip(";").strip()
    form_data = json.loads(script_text)

    form = Form()
    form.Title = to_string(form_data[3])
    form.Path = to_string(form_data[2])
    form.Action = to_string(form_data[14])

    extra_data = to_slice(form_data[1])
    form.Fields = NewFieldsFromData(to_slice(extra_data[1]))
    form.SectionCount = 1
    for field in form.Fields:
        if field.TypeID == FieldType.FieldSection:
            form.SectionCount += 1

    form.Desc = to_string(extra_data[0])
    form.Header = to_string(extra_data[8])

    other_extra_data = to_slice(extra_data[10])
    if other_extra_data and len(other_extra_data) > 4:
        form.AskEmail = to_int(other_extra_data[4]) == 1

    form.Fbzx = fbzx

    extract_images(response_text, form)

    return form

# Define the custom exception for InvalidForm


class InvalidForm(Exception):
    pass


def check_url(url):
    parsed_url = urllib.parse.urlparse(url)

    if parsed_url.netloc != "docs.google.com":
        return "Invalid Google Forms address"

    if not parsed_url.path.endswith("/viewform"):
        return "Please use the public URL"

    return None


def fetch_and_exit(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        form_data = form_extract(response)
        # Serialize using the custom encoder
        form_data_nal = json.dumps(form_data, cls=FormEncoder)
        print(form_data_nal)
    except requests.exceptions.RequestException as e:
        logging.error(str(e))
    sys.exit(0)


@ app.route('/', methods=['GET'])
def form_dress_handler():

    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    form_url = request.args.get('url')
    error_message = check_url(form_url)

    if error_message:
        response_data = {'Error': error_message}
        return Response(json.dumps(response_data), status=400, headers=response_headers)

    try:
        response = requests.get(form_url)
        response.raise_for_status()
        form_data = form_extract(response)
        # Serialize using the custom encoder
        form_data_nal = json.dumps(form_data, cls=FormEncoder)

        # Send the response to the client
        response_obj = Response(
            (form_data_nal), status=200, headers=response_headers)

        # Log the timestamp and URL after sending the response
        log_time_and_url(form_url)

        return response_obj

    except requests.exceptions.RequestException as e:
        response_data = {'Error': str(e)}
        return Response(json.dumps(response_data), status=500, headers=response_headers)


def log_time_and_url(url):
    try:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        insert_query = "INSERT INTO log_table (timestamp, url) VALUES (%s, %s)"
        values = (current_time, url)

        g.mysql_cursor.execute(insert_query, values)
        g.mysql_conn.commit()
        print(
            f"Record inserted successfully: Timestamp={current_time}, URL={url}")
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        raise
    finally:
        print("Closing MySQL cursor and connection.")

# Use the with_appcontext decorator


def run_flask_app():
    addr = '0.0.0.0'
    port = 8000

    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        if len(sys.argv) > 2:
            fetch_url = sys.argv[2]
            fetch_and_exit(fetch_url)
        else:
            print("Usage: python script.py -f <URL>")
    else:
        print(f"Serving on {addr}:{port}")

    app.run(host=addr, port=port)

    # The code here won't be executed until the Flask server is stopped.

    # The following lines won't be executed immediately after app.run.
    print("Before log_time_and_url call")
    log_time_and_url("Test URL")
    print("After log_time_and_url call")


def shutdown_server(signum, frame):
    print("Shutting down...")


signal.signal(signal.SIGINT, shutdown_server)
signal.signal(signal.SIGTERM, shutdown_server)


if __name__ == '__main__':
    addr = '0.0.0.0'
    port = 8000

    signal.signal(signal.SIGINT, shutdown_server)
    signal.signal(signal.SIGTERM, shutdown_server)
    run_flask_app()
