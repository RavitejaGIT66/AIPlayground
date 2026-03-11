from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Mapping of 2-letter state codes to FIPS codes (US Census)
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
    "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
    "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
    "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
    "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    "DC": "11",
}

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    state_code = ""

    if request.method == "POST":
        state_code = request.form.get("state_code", "").strip().upper()
        if not state_code:
            error = "Please enter a state code."
        elif state_code not in STATE_FIPS:
            error = f"'{state_code}' is not a valid US state code."
        else:
            fips = STATE_FIPS[state_code]
            url = f"https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=state:{fips}"
            response = requests.get(url, timeout=10)
            if response.ok:
                data = response.json()
                # data[0] is headers, data[1] is values
                name, population, _ = data[1]
                result = {
                    "state": name,
                    "code": state_code,
                    "population": int(population),
                    "year": 2020,
                }
            else:
                error = "Failed to fetch data from the US Census API. Try again later."

    return render_template("index.html", result=result, error=error, state_code=state_code)

if __name__ == "__main__":
    app.run(debug=True)
