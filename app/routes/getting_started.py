from flask import Blueprint, render_template
from flask_login import login_required

gs_bp = Blueprint("getting_started", __name__)


@gs_bp.route("/getting-started")
@login_required
def getting_started():
    return render_template("getting_started.html")
