
from flask_admin.contrib.sqla import ModelView
from .extensions import admin, db
from .models import WorkOrder, Customer, Vehicle

def setup_admin(app):
    admin.init_app(app)
    admin.add_view(ModelView(Customer, db.session))
    admin.add_view(ModelView(Vehicle, db.session))
    admin.add_view(ModelView(WorkOrder, db.session))
