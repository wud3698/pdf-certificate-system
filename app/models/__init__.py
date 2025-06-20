from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .admin import Admin
from .activity import Activity
from .certificate import Certificate
from .carousel_image import CarouselImage

__all__ = ['db', 'Admin', 'Activity', 'Certificate', 'CarouselImage'] 