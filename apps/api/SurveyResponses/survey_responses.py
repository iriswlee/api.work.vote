from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from jurisdiction.models import State, Jurisdiction
from .check_authorization import checkAuth
from django.conf import settings
from django.core.mail import send_mail

import json

def send_error_email(jurisdiction_no):
    # Send an email to admin
    msg = msg + 'Message: \n\n'
    send_mail(
        'Error on survey response import',
        'Error trying to import survey for Jurisdiction {}'.format(jurisdiction_no),
        'info@workelections.com',
        [settings.CONTACT_US],
        fail_silently=False
    )

@csrf_exempt
def GetSurveyResponse(request):
    # check authorization
    try:
        assert checkAuth(request)
    except:
        response = HttpResponse()
        response.status_code = 401
        return response

    decoded = request.body.decode('utf-8')
    try:
        json_dict = json.loads(decoded)
    except json.decoder.JSONDecodeError:
        return HttpResponse(status=400)
    
    # Find jurisdiction to update
    jurisdiction_id = json_dict["Custom Variable__JurisdictionNo"]
    j = Jurisdiction.objects.get(pk=jurisdiction_id)

    for q, a in json_dict.items():
        try:
            q_list = q.split(')')
            q_no = int(q_list[0])
            # Sanitize input
            a = str(a)
        except ValueError: # not a question
            if q_list[0][13:20] == "further":
                # manually set "further notes"
                q_no = 13
            else:
                # If the key doesn't start with a number, then it's not a question
                print("ValueError on '{}'".format(q_list[0]))
                continue
        
        compensation_text = [False, '', '']
        if a != "Not Answered" and a != "N/A":
            j.display = 'Y'
            if q_no == 1:
                j.hours_start = a
            elif q_no == 2:
                j.hours_end = a
            elif q_no == 3:
                j.full_day_req = a[0]
            elif q_no == 4:
                compensation_text[0] == True
                if (q_list[2][3:6]) == "Low":
                    compensation_text[1] = a
                elif (q_list[2][3:8]) == "Upper":
                    compensation_text[2] = a
            elif q_no == 5:
                j.minimum_age = a
            elif q_no == 6:
                j.pre_registration = a[0]
            elif q_no == 7:
                # Should change this question
                if a == "Yes":
                    j.registration_status = "J"
                elif a == "No":
                    j.registration_status = "S"
            elif q_no == 8:
                j.must_have_email = a[0]
            elif q_no == 9:
                j.interview = a[0]
            elif q_no == 10:
                j.training = a[0]
            elif q_no == 11:
                j.complete_training = a[0]
            elif q_no == 12:
                j.post_training_exam = a[0]
            elif q_no == 13:
                j.further_notes = a
        else:
            continue
    
    if compensation_text[0] == True:
        if compensation_text[1] != '' and compensation_text[2] != '':
            j.compensation = compensation_text[0] + " to " + compensation_text[1]
        elif compensation_text[1] != '':
            j.compensation = compensation_text[1]
        else:
            j.compensation = compensation_text[2]
        j.display = 'Y'

    if (j.display == 'Y'):
        j.save()
        return HttpResponse(status=200)
    else: # There was nothing to update
        # should eventually send name and state of jurisdiction
        send_error_email(jurisdiction_id)
        return HttpResponse(status=400)