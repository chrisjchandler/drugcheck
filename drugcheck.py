import requests
import json

from gunicorn.app.base import BaseApplication
from flask import Flask, request

class GunicornApp(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

app = Flask(__name__)

@app.route('/')
def index():
    # Define a list of common medical conditions
    conditions = ['Arthritis', 'Asthma', 'Diabetes', 'High Blood Pressure', 'Migranes','Acid reflux','Anxiety','Depression','Insomnia','Allergies','Osteoporosis','Hypothyroidism','Hyperthyroidism','Chronic pain','Fibromyalgia', 'High Cholesterol']
    return '''
    <form method="post" action="/get_medications">
        <label for="conditions">Select medical conditions:</label>
        <select name="conditions[]" id="conditions" multiple>
            {}
        </select>
        <button type="submit">Submit</button>
    </form>
    '''.format(''.join(['<option value="{}">{}</option>'.format(c, c) for c in conditions]))

@app.route('/get_medications', methods=['POST'])
def get_medications():
    # Retrieve the selected medical conditions from the form
    selected_conditions = request.form.getlist('conditions[]')

    # Initialize an empty list to store the medications for each selected condition
    all_medications = []

    # Loop through each selected condition and retrieve the corresponding medications
    for condition in selected_conditions:
        # Make an API call to the FDA to retrieve a list of medications for the selected condition
        fda_url = 'https://api.fda.gov/drug/label.json?search=indications_and_usage:"{}"&limit=10'.format(condition)
        response = requests.get(fda_url)
        data = json.loads(response.text)

        # Extract the medication names from the FDA API response
        medications = [item['openfda']['brand_name'][0] for item in data['results'] if 'openfda' in item and 'brand_name' in item['openfda']]
        all_medications.extend(medications)

    # Make an API call to retrieve information about potential harmful drug interactions between the selected medications
    openfda_url = 'https://api.fda.gov/drug/label.json?search=({})+AND+patient.drug.druginteractions'.format('+'.join(all_medications))
    response = requests.get(openfda_url)
    data = json.loads(response.text)

    # Extract the drug interaction information from the OpenFDA API response
    if 'results' in data:
        interactions = [interaction['description'] for item in data['results'] if 'patient' in item for interaction in item['patient']['drug']['druginteractions']]
    else:
        interactions = []

    # Make another API call to retrieve information about potential side effects of the selected medications
    openfda_url = 'https://api.fda.gov/drug/event.json?search=patient.drug.openfda.brand_name:({})&count=patient.reaction.reactionmeddrapt.exact&limit=10'.format('+'.join(all_medications))
    response = requests.get(openfda_url)
    data = json.loads(response.text)

    # Extract the side effect information from the OpenFDA API response
    if 'results' in data:
        side_effects = [item['term'] for item in data['results']]
    else:
        side_effects = []

    # Return the list of medications, potential drug interactions, and potential side effects to the user
    if side_effects:
        return '''
        <h3>Medications for {}:</h3>
        <ul>
            {}
        </ul>
        <h3>Potential drug interactions:</h3>
        <ul>
            {}
        </ul>
        <h3>Potential side effects:</h3>
        <ul>
            {}
        </ul>
        '''.format(', '.join(selected_conditions), ''.join(['<li>{}</li>'.format(m) for m in all_medications]), ''.join(['<li>{}</li>'.format(i) for i in interactions]), ''.join(['<li>{}</li>'.format(se) for se in side_effects]))
    else:
        return '''
        <h3>Medications for {}:</h3>
        <ul>
            {}
        </ul>
        <h3>Potential drug interactions:</h3>
        <ul>
            {}
        </ul>
        <h3>Potential side effects:</h3>
        <p>No potential side effects found.</p>
        '''.format(', '.join(selected_conditions), ''.join(['<li>{}</li>'.format(m) for m in all_medications]), ''.join(['<li>{}</li>'.format(i) for i in interactions]))

if __name__ == '__main__':
    options = {
        'bind': '0.0.0.0:8000',
        'workers': 4,
        'accesslog': '-',
        'errorlog': '-'
    }
    GunicornApp(app, options).run()
