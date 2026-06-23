from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
import json

from .models import ChatSession, Message
from .ai import get_ai_response_stream, get_ai_title

# -------------------------
# AUTH UI
# -------------------------
def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = UserCreationForm()
    return render(request, "chat/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "chat/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("/login/")

# -------------------------
# CHAT UI
# -------------------------
@login_required(login_url="/login/")
def chat_page(request):
    return render(request, "chat/index.html")


# -------------------------
# SEND MESSAGE
# -------------------------
@csrf_exempt
@login_required(login_url="/login/")
def send_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_text = data.get("message")
            session_id = data.get("session_id")
            persona = data.get("persona", "default")
            enable_search = data.get("enable_search", False)

            if not user_text:
                return JsonResponse({"error": "message is required"}, status=400)

            # GET OR CREATE SESSION
            session = None
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id, user=request.user)
                except ObjectDoesNotExist:
                    pass
            
            if session is None:
                session = ChatSession.objects.create(user=request.user, title="New Chat")

            # SAVE USER MESSAGE
            Message.objects.create(session=session, role="user", content=user_text)

            # AUTO TITLE (FIRST MESSAGE ONLY)
            if session.title == "New Chat":
                session.title = get_ai_title(user_text)
                session.save()

            # BUILD HISTORY (LAST 10 MESSAGES)
            recent_msgs = Message.objects.filter(session=session).order_by("-id")[:10]
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(recent_msgs)
            ]

            # GLOBAL MEMORY (Context from other recent chats)
            global_memory = ""
            other_sessions = ChatSession.objects.filter(user=request.user).exclude(id=session.id).order_by("-created_at")[:2]
            if other_sessions.exists():
                global_msgs = Message.objects.filter(session__in=other_sessions).order_by("-id")[:5]
                for msg in reversed(global_msgs):
                    global_memory += f"[{msg.session.title}] {msg.role}: {msg.content}\n"

            # STREAM RESPONSE
            def stream_response():
                full_reply = ""
                for chunk in get_ai_response_stream(user_text, history, persona, enable_search, global_memory):
                    full_reply += chunk
                    yield chunk
                
                # Save the final compiled string to DB
                Message.objects.create(session=session, role="assistant", content=full_reply)
                
                # Yield a special token so the frontend knows the session ID (for new chats)
                yield f"\n[__SESSION_ID__:{session.id}]"

            return StreamingHttpResponse(stream_response(), content_type='text/plain')

        except Exception as e:
            import traceback
            print("FULL ERROR:", str(e))
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Invalid request"}, status=400)


# -------------------------
# LIST SESSIONS (SIDEBAR)
# -------------------------
@login_required(login_url="/login/")
def list_sessions(request):
    sessions = ChatSession.objects.filter(user=request.user).order_by("-id")
    data = [{"id": s.id, "title": s.title} for s in sessions]
    return JsonResponse({"sessions": data})


# -------------------------
# CREATE SESSION (NEW CHAT)
# -------------------------
@csrf_exempt
def create_session(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        session = ChatSession.objects.create(user=request.user, title="New Chat")
        return JsonResponse({"session_id": session.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------
# CHAT HISTORY
# -------------------------
@login_required(login_url="/login/")
def chat_history(request, session_id):
    try:
        messages = Message.objects.filter(session_id=session_id, session__user=request.user).order_by("id")
        data = [{"role": msg.role, "content": msg.content} for msg in messages]
        return JsonResponse({"session_id": session_id, "messages": data})
    except Exception as e:
        import traceback
        print("HISTORY ERROR:", str(e))
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------
# DELETE SESSION
# -------------------------
@csrf_exempt
def delete_session(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    if request.method == "DELETE":
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.delete()
            return JsonResponse({"success": True})
        except ObjectDoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)


# -------------------------
# DELETE ACCOUNT
# -------------------------
@csrf_exempt
@login_required(login_url="/login/")
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Method not allowed"}, status=405)


# -------------------------
# UPLOAD PDF
# -------------------------
@csrf_exempt
@login_required(login_url="/login/")
def upload_pdf(request):
    if request.method == "POST":
        try:
            pdf_file = request.FILES.get('file')
            session_id = request.POST.get('session_id')
            
            if not pdf_file:
                return JsonResponse({"error": "Missing file"}, status=400)
                
            try:
                import PyPDF2
            except ImportError:
                import sys
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
                import PyPDF2
                
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            text = text[:10000] # Truncate to save tokens
            
            # Create session if none
            if not session_id or session_id == "null":
                session = ChatSession.objects.create(user=request.user, title=f"PDF: {pdf_file.name}")
            else:
                session = ChatSession.objects.get(id=session_id, user=request.user)
                
            # Store PDF content
            Message.objects.create(
                session=session,
                role="user",
                content=f"[Attached PDF: {pdf_file.name}]\n\n{text}"
            )
            
            # Add AI acknowledgment
            bot_reply = f"I've analyzed the document `{pdf_file.name}`. What questions do you have about it?"
            Message.objects.create(session=session, role="assistant", content=bot_reply)
            
            return JsonResponse({"success": True, "message": bot_reply, "session_id": session.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)