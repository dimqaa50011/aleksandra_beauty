from ninja import NinjaAPI
from django.conf import settings



from cert_app.schemas import CreateCertSchema
from .controllers import CertController
from .auth import AuthBearer



api = NinjaAPI(auth=AuthBearer())
cert_controller = CertController(settings.CERT_SECRET)

@api.get("/cert/get/{phone}")
def get_cert_by_phone(request, phone: str):
    ...

@api.post("/cert/use/{phone}")
def use_cert(request, phone: str):
    ...

@api.post("/cert/create")
def create_cert(requset, data: CreateCertSchema):
    new_crt = cert_controller.create_new_cert(data.phone, data.email, data.price)
    new_crt.send_email()
    
