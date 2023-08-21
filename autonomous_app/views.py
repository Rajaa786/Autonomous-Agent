from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import HttpResponse, JsonResponse , FileResponse
import random
from .ai import Chat
from .config import default_config
import os
from .models import *
import re
import hashlib

from .utils import *
from .ingest import ingest_and_log_data
import json

email = "example@example.com"

from dotenv import load_dotenv

load_dotenv(".env")

from autonomous_app.chat import conversation_initiate, conversation_continue , summary_request

conversation_stack = conversation_initiate()


# open_api_key = 
# print("Openai key " , os.getenv("OPENAI_API_KEY"))


# Create your views here.

@xframe_options_exempt
def base(request):
    return render(request , "base.html")

def bard(request):
    return render(request , "bard_chat.html")

@xframe_options_exempt
def gpt_chat(request):
    return render(request , "chat.html")




def email_data_post(request):

    if request.method == "POST":

        email = request.POST.get('email' , '')

        unique_key = hashlib.sha256(email.encode()).hexdigest()

        if(Business.objects.filter(email = email).exists()):
            print("\n\n\nEmail already exists\n\n\n")
            return JsonResponse({'message': "Email already exists" , 'user_id' : Business.objects.get(email = email).id})

        business = Business.objects.create(email = email , key = unique_key)


        print("\n\n\nEmail: " , email)

        # generate key ans save in models 



        return JsonResponse({'message': "Email successfully generated." , 'user_id' : business.id})
    



def generate_business_data(request):
    return render(request , "generate_business_data.html")


responses = [
    "Thank you for your message. Our team will get back to you soon.",
    "Your message has been received. We'll respond shortly.",
    "We appreciate your feedback. Our team will review it.",
    "Your input has been noted. Expect a reply from us soon.",
]


chat = Chat(config=default_config)

def bot_response(request):
    if request.method == 'POST':
        query = request.POST.get('message', '')

        prev_chat_history = request.session.get('chat_history', [])


        list_of_tuples = [tuple(item) for item in prev_chat_history]
        print("\n\nPrev chat history: " , list_of_tuples)
        print("\n\n")

        # bot_response = "Thank you for your message. Our team will get back to you soon."
        bot_response_ , updated_chat_history = chat(question = query , history = list_of_tuples)

        request.session['chat_history'] = updated_chat_history

        print("\n\n\nBot history: " , updated_chat_history)
        print("\n\n")

        # bot_response = random.choice(responses)

        return JsonResponse({'message': bot_response_})

    return JsonResponse({'message': 'Invalid request'}, status=400)


def business_data_post(request):

    end = False
    if request.method == 'POST':
        query = request.POST.get('user_id', '')
        question = request.POST.get('message', '')
        end_of_talk = request.POST.get('end_of_talk', '')
        start_of_talk = request.POST.get('start_of_talk', '')


        if start_of_talk:
            busi_chat_hist = BusinessChatHistory(business_id = query)
            if busi_chat_hist and busi_chat_hist.chat_history:
                request.session['business_chat_history'] = json.loads(busi_chat_hist.chat_history)
            else:
                request.session['business_chat_history'] = conversation_stack

            
        prev_chat_history = request.session.get('business_chat_history', [])

        # list_of_dicts = [tuple(item) for item in prev_chat_history]
        # print("\n\nPrev chat history: " , list_of_tuples)
        # print("\n\n")

        # bot_response = "Thank you for your message. Our team will get back to you soon."
        bot_response_ , updated_chat_history = conversation_continue(conversation=prev_chat_history , user_input=question)

        request.session['business_chat_history'] = updated_chat_history



        match = re.search(r'Prompt:\s*', bot_response_)

        # Search for the pattern in the example text
        print("\n\n\nBot response: " , bot_response_)
        print("\n\n\n")

        if match:
            end = True
            busi_chat_hist = BusinessChatHistory(business_id = query)
            busi_chat_hist.chat_history = json.dumps(updated_chat_history)
            busi_chat_hist.save()


            busi_summary = BusinessSummary(business_id = query)
            busi_summary.summary = bot_response_
            busi_summary.save()

            request.session['business_chat_history'] = conversation_stack

            request.session.modified = True


            # say ression to update 




        print("\n\n\nBot history: " , updated_chat_history)
        print("\n\n")

        # bot_response = random.choice(responses)

        return JsonResponse({'message': bot_response_ , 'end_of_talk' : end})

    return JsonResponse({'message': 'Invalid request'}, status=400)



def file_upload(request):

    if request.method == "POST":

        file = request.FILES['file']
        print("\n\n\nFile: " , file)

        file_name = file.name
        print("\n\n\nFile name: " , file_name)

        file_content = file.read()
        print("\n\n\nFile content: " , file_content)

        file_type = file.content_type
        print("\n\n\nFile type: " , file_type)

        file_size = file.size
        print("\n\n\nFile size: " , file_size)

        file_path = "autonomous_app/static/autonomous_app/files/" + file_name

        with open(file_path , "wb") as f:
            f.write(file_content)

        # Return the uploaded file as a response
        response = FileResponse(open(file_path, 'rb'), content_type=file_type)
        response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(file_path)
        return response
        # return JsonResponse({'message': "File uploaded successfully." , 'file_path' : file_path})



def create_chatbot(request):
    businessId = request.POST.get('businessId', '')
    unique_cb_key = generate_unique_key()

    BusinessChatbot(business_id = businessId , chatbot_key = unique_cb_key , chatbot_name = f"Test{unique_cb_key[:4]}").save()

    try:
        ingest_and_log_data(unique_user_key = unique_cb_key)
        return JsonResponse({'message': "Chatbot created successfully." , 'chatbot_key' : unique_cb_key})
    except:
        return JsonResponse({'message': "Error in creating chatbot." , 'chatbot_key' : unique_cb_key} , status=400)

