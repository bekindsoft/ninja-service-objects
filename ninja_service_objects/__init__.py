from ninja_service_objects.fields import ModelField, MultipleModelField
from ninja_service_objects.services import Service

__all__ = ["Service", "ModelField", "MultipleModelField"]
__version__ = "0.1.0"

default_app_config = "ninja_service_objects.apps.NinjaServiceObjectsConfig"
