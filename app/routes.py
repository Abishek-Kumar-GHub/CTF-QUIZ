from flask import Blueprint, render_template, url_for, flash, redirect, request, session
import time
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User, Challenge

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/home")
def home():
    if current_user.is_authenticated:
        # Reset the user's score when home is visited
        user = User.query.get(current_user.id)
        if user:
            user.score = 0.0
            db.session.commit()
            print(f"[DEBUG] User Score Reset: {user.score}")

    first_challenge = Challenge.query.order_by(Challenge.id.asc()).first()
    return render_template("index.html", first_challenge=first_challenge)


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken. Choose a different one.", "danger")
            return redirect(url_for("main.register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully!", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and bcrypt.check_password_hash(user.password, request.form["password"]):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(
                url_for(
                    "main.challenges",
                    challenge_id=Challenge.query.order_by(Challenge.id.asc())
                    .first()
                    .id,
                )
            )
        else:
            flash("Login failed. Check email and password.", "danger")
    return render_template("login.html")


@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@main.route("/challenges/<int:challenge_id>", methods=["GET", "POST"])
@login_required
def challenges(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    if request.method == "POST":
        selected_option = request.form["answer"]
        remaining_time = float(
            request.form.get("remaining_time", 10.0)
        )  # Default to 10s

        # Map "option_4" to actual value (e.g., "HTTPS")
        option_map = {
            "option_1": challenge.option_1,
            "option_2": challenge.option_2,
            "option_3": challenge.option_3,
            "option_4": challenge.option_4,
        }
        user_answer = option_map.get(selected_option, "")

        print(f"[DEBUG] Correct Answer: {challenge.correct_option}")
        print(f"[DEBUG] User Selected: {user_answer}")

        user = User.query.get(current_user.id)

        if not user:
            print("[ERROR] User not found!")
            flash("User not found! Please log in again.", "danger")
            return redirect(url_for("main.login"))

        if user_answer == challenge.correct_option:
            # Calculate time-based score
            time_based_points = challenge.base_points * (remaining_time / 10.0)
            user.score += time_based_points
            db.session.commit()

            print(f"[DEBUG] Earned Points: {time_based_points:.2f}")
            print(f"[DEBUG] Updated Score: {user.score}")
            flash(f"Correct! You earned {time_based_points:.2f} points.", "success")
        else:
            flash(
                f"Incorrect! The correct answer was: {challenge.correct_option}",
                "danger",
            )

        # Move to next challenge or leaderboard
        next_challenge = Challenge.query.filter(Challenge.id > challenge_id).first()
        if next_challenge:
            return redirect(url_for("main.challenges", challenge_id=next_challenge.id))
        else:
            return redirect(url_for("main.leaderboard"))

    return render_template("challenges.html", challenge=challenge)


@main.route("/leaderboard")
def leaderboard():
    users = User.query.order_by(User.score.desc()).limit(10).all()
    return render_template("leaderboard.html", users=users)


@main.route("/start_challenge/<int:challenge_id>")
@login_required
def start_challenge(challenge_id):
    session[f"start_time_{challenge_id}"] = time.time()
    return redirect(url_for("main.challenges", challenge_id=challenge_id))


@main.route("/apply_penalty/<int:challenge_id>", methods=["POST"])
@login_required
def apply_penalty(challenge_id):
    user = User.query.get(current_user.id)
    if user:
        user.score = max(
            0, user.score - 5.0
        )  # Deduct 5 points, ensuring it doesn't go negative
        db.session.commit()
        print(f"[DEBUG] Penalty applied! New Score: {user.score}")

    return {"success": True}
