import itertools
import logging
import os
import re
from datetime import datetime

import requests

from . import Clinic


class Cosentinos(Clinic):
    def get_locations(self):
        clinic_index_url = "https://www.cosentinos.com/covid-vaccine"
        clinic_info_regex = r"<strong>(.{10,50})<\/strong><br \/>[\s\S]{1,50}<br \/>\s*(.{1,30}), (\w{2}) \d{5}<br \/>\s*[\d-]{12}<br(?: \/)?>[\s\S]{1,100}calendarID=(\d{7}).{1,50}Vaccine Availability<\/a>"
        response = requests.get(clinic_index_url)

        clinics_with_vaccine = []
        clinics_without_vaccine = []

        if response.status_code == 200:
            clinics = re.findall(clinic_info_regex, response.text)
            for clinic in clinics:
                clinic_data = format_data(
                    {
                        "clinic_id": clinic[3],
                        "name": clinic[0].replace("'", "'"),
                        "city": clinic[1],
                        "state": clinic[2],
                    }
                )
                if get_availability_for_clinic(clinic[3]):
                    clinics_with_vaccine.append(clinic_data)
                else:
                    clinics_without_vaccine.append(clinic_data)

        else:
            logging.error(
                "Bad response from Cosentinos: Code {}: {}".format(
                    response.status_code, response.text
                )
            )

        return {
            "with_vaccine": clinics_with_vaccine,
            "without_vaccine": clinics_without_vaccine,
        }


def get_availability_for_clinic(clinic_id):
    current_offset = 0
    more_results = True
    offset_regex = r"offset:(\d{2})[\s\S]{1,100}More Times"

    while more_results is True:
        page_data = get_page(clinic_id, current_offset)
        # There are two on each page, except last page has zero
        offset_amount = int((re.findall(offset_regex, page_data) or [0])[0])

        if (
            "No upcoming classes are available" in page_data
            or "There are no appointment types available for scheduling" in page_data
        ):
            return False

        has_availability = page_data.count(
            'no <span id="spots-left-text">spots left'
        ) != page_data.count("spots left")
        if has_availability:
            return True

        more_results = "More Times" in page_data
        current_offset += offset_amount

    return False


def get_page(clinic_id, offset):
    date_url = "https://app.squarespacescheduling.com/schedule.php?action=showCalendar&fulldate=1&owner=21943707&template=class"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    payload = "type=&calendar=&month=&skip=true&options%5Boffset%5D={}&options%5BnumDays%5D=5&ignoreAppointment=&appointmentType=&calendarID={}".format(
        offset, clinic_id
    )
    response = requests.post(date_url, headers=headers, data=payload)

    if response.status_code == 200:
        return response.text
    else:
        logging.error(
            "Bad Response from Cosentino's Squarespace: {} {}".format(
                response.statusCode, response.text
            )
        )
        return ""


def format_data(clinic):
    return {
        "link": "https://app.squarespacescheduling.com/schedule.php?owner=21943707&calendarID={}".format(
            clinic["clinic_id"]
        ),
        "id": "cosentinos-{}".format(clinic["clinic_id"]),
        "name": "{} {}".format(clinic["name"], clinic["city"]),
        "state": clinic["state"],
    }
