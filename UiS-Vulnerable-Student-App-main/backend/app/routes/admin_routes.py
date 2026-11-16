from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import run_query, get_conn
from app.auth import get_user_from_session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

STAFF_ROLES = ["admin", "teacher", "ta"]
ADMIN_ROLES = ["admin"]
VALID_ROLES = ["admin", "teacher", "ta", "student"]


def role_check(request: Request, allowed_roles):
    user = get_user_from_session(request)
    if not user:
        return None, RedirectResponse("/login", status_code=302)
    if user["role"] not in allowed_roles:
        return None, RedirectResponse("/dashboard", status_code=302)
    return user, None


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    user, denied = role_check(request, STAFF_ROLES)
    if denied:
        return denied

    users_count = run_query("SELECT COUNT(*) as c FROM users", fetchone=True)
    submissions_count = run_query("SELECT COUNT(*) as c FROM submissions", fetchone=True)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "users_count": users_count["c"],
            "submissions_count": submissions_count["c"],
        },
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    user, denied = role_check(request, ADMIN_ROLES)
    if denied:
        return denied
    users = run_query("SELECT id, email, full_name, role FROM users ORDER BY id", fetchall=True)
    return templates.TemplateResponse("admin_users.html", {"request": request, "user": user, "users": users})


@router.post("/admin/users/{user_id}/role")
def update_role(request: Request, user_id: int, role: str = Form(...)):
    user, denied = role_check(request, ADMIN_ROLES)
    if denied:
        return denied

    if role in VALID_ROLES:
        run_query("UPDATE users SET role=%s WHERE id=%s", (role, user_id), commit=True)

    return RedirectResponse("/admin/users", status_code=302)


@router.get("/admin/grades", response_class=HTMLResponse)
def admin_grades(request: Request):
    user, denied = role_check(request, STAFF_ROLES)
    if denied:
        return denied

    grades = run_query(
        """
        SELECT g.id, u.full_name as student_name, a.title as assignment_title, g.grade_value, g.feedback
        FROM grades g
        JOIN users u ON u.id = g.student_id
        JOIN assignments a ON a.id = g.assignment_id
        ORDER BY g.id DESC
        """,
        fetchall=True,
    )
    return templates.TemplateResponse("admin_grades.html", {"request": request, "user": user, "grades": grades})


@router.post("/admin/grades/{grade_id}/update")
def update_grade(
    request: Request,
    grade_id: int,
    grade_value: str = Form(...),
    feedback: str = Form(...),
):
    user, denied = role_check(request, STAFF_ROLES)
    if denied:
        return denied

    run_query(
        "UPDATE grades SET grade_value=%s, feedback=%s, status='published' WHERE id=%s",
        (grade_value, feedback, grade_id),
        commit=True,
    )

    return RedirectResponse("/admin/grades", status_code=302)


@router.get("/admin/search-users", response_class=HTMLResponse)
def search_users(request: Request, q: str = ""):
    user, denied = role_check(request, ADMIN_ROLES)
    if denied:
        return denied

    pattern = f"%{q}%"
    users = run_query(
        "SELECT id, email, full_name, role FROM users WHERE email ILIKE %s OR full_name ILIKE %s",
        (pattern, pattern),
        fetchall=True,
    )

    return templates.TemplateResponse("admin_users.html", {"request": request, "user": user, "users": users, "q": q})
