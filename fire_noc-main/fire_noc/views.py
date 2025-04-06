from django.shortcuts import render,redirect
import cloudinary.uploader
from .models import FireNOCSubmission
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import A4
from io import BytesIO
from reportlab.pdfgen import canvas
import qrcode
from django.core.mail import EmailMessage
from .image_verification import verify_equipment_type, is_duplicate_image
import json

# Create your views here.
def index(request):
    return render(request,"index.html")

def verify_image(request):
    """API endpoint to verify if uploaded image is valid"""
    if request.method == "POST" and request.FILES.get('image'):
        image_file = request.FILES['image']
        equipment_type = request.POST.get('equipment_type')
        
        if not equipment_type:
            return JsonResponse({'valid': False, 'message': 'Equipment type not specified'}, status=400)
        
        # Check if image is valid for the specified equipment type
        is_valid, confidence, message = verify_equipment_type(image_file, equipment_type)
        
        # If valid, check for duplicates from previously uploaded images
        duplicate_check = {'is_duplicate': False, 'message': ''}
        if is_valid:
            # Get existing images of this type
            existing_submissions = FireNOCSubmission.objects.all()
            existing_images = []
            
            # Use the correct field based on equipment type
            for submission in existing_submissions:
                if equipment_type == 'fire_extinguisher':
                    existing_images.append(submission.fire_extinguisher)
                elif equipment_type == 'fire_exit':
                    existing_images.append(submission.fire_exit)
                elif equipment_type == 'fire_safety_sign':
                    existing_images.append(submission.fire_safety_sign)
                elif equipment_type == 'water_infrastructure':
                    existing_images.append(submission.water_infrastructure)
            
            if existing_images:
                # Reset file pointer for duplicate check
                image_file.seek(0)
                is_duplicate, _, similarity = is_duplicate_image(image_file, existing_images)
                if is_duplicate:
                    duplicate_check = {
                        'is_duplicate': True,
                        'message': f'This appears to be a duplicate image (similarity: {similarity:.2f})'
                    }
        
        # Reset file pointer for further use
        image_file.seek(0)
        
        return JsonResponse({
            'valid': is_valid,
            'confidence': float(confidence),
            'message': message,
            'duplicate_check': duplicate_check
        })
    
    return JsonResponse({'valid': False, 'message': 'Invalid request'}, status=400)

def generate_fire_noc_pdf(request):
    if request.method == "POST":
        # Get form data
        name = request.POST["name"]
        email = request.POST["email"]
        phone = request.POST["phone"]
        date = request.POST["date"]
        org_name = request.POST["org_name"]
        org_address = request.POST["org_address"]
        fire_extinguisher = request.FILES["fire_extinguisher"]
        fire_exit = request.FILES["fire_exit"]
        fire_safety_sign = request.FILES["fire_safety_sign"]
        water_infrastructure = request.FILES["water_infrastructure"]
        
        # Verify each image type
        image_verification_results = {}
        equipment_files = {
            'fire_extinguisher': fire_extinguisher,
            'fire_exit': fire_exit,
            'fire_safety_sign': fire_safety_sign,
            'water_infrastructure': water_infrastructure
        }
        
        all_valid = True
        duplicate_found = False
        error_messages = []
        
        for equipment_type, file_obj in equipment_files.items():
            is_valid, confidence, message = verify_equipment_type(file_obj, equipment_type)
            image_verification_results[equipment_type] = {
                'valid': is_valid,
                'confidence': confidence,
                'message': message
            }
            
            if not is_valid:
                all_valid = False
                error_messages.append(f"{equipment_type}: {message}")
            
            # Reset file pointer after verification
            file_obj.seek(0)
            
            # Check for duplicates
            existing_submissions = FireNOCSubmission.objects.all()
            existing_images = []
            
            # Use the correct field based on equipment type
            for submission in existing_submissions:
                if equipment_type == 'fire_extinguisher':
                    existing_images.append(submission.fire_extinguisher)
                elif equipment_type == 'fire_exit':
                    existing_images.append(submission.fire_exit)
                elif equipment_type == 'fire_safety_sign':
                    existing_images.append(submission.fire_safety_sign)
                elif equipment_type == 'water_infrastructure':
                    existing_images.append(submission.water_infrastructure)
            
            if existing_images:
                is_duplicate, _, similarity = is_duplicate_image(file_obj, existing_images)
                if is_duplicate:
                    duplicate_found = True
                    error_messages.append(f"{equipment_type}: Duplicate image detected (similarity: {similarity:.2f})")
                
                # Reset file pointer after duplicate check
                file_obj.seek(0)
        
        if not all_valid or duplicate_found:
            return HttpResponse(f"<script>alert('Image verification failed. {' '.join(error_messages)}'); window.history.back();</script>")
    
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Title
        p.setFont("Times-Bold", 16)
        p.drawString(180, height - 50, "Bhavnagar Municipal Corporation")
        p.setFont("Times-Bold", 14)
        p.drawString(180, height - 70, "Fire & Emergency Services Department")
        p.drawString(190, height - 100, "No Objection Certificate (Fire NOC)")

        # Certificate Details
        p.setFont("Times-Roman", 14)
        p.drawString(50, height - 140, "Certificate No: NOC-12345678")
        p.drawString(50, height - 160, f"Date of Issue: {date}")
        p.drawString(50, height - 180, "Validity: One year from the date of issuance")

        # Address Section
        p.drawString(50, height - 220, f"To: {name}")
        p.drawString(50,height-240,f"Email Id:- {email}")
        p.drawString(50,height-260,f"Phone No:- {phone}")
        p.drawString(50, height - 280, f"Organization Name: {org_name}")
        p.drawString(50, height - 300, f"Address: {org_address}")
    

       # Certification Text
        p.setFont("Times-Bold", 14)
        p.drawString(50, height - 330, "Subject:")
        p.setFont("Times-Roman",14)
        p.drawString(110, height - 330, f"Fire No Objection Certificate for {org_name}")
        p.setFont("Times-Bold", 14)
        p.drawString(50, height - 350, "Reference: ")
        p.setFont("Times-Roman",14)
        p.drawString(120, height - 350, f"Your application dated {date} regarding Fire NOC.")

        #Text 
        p.setFont("Times-Roman",14)
        p.drawString(50, height-380,f"This is to certify that the premises located at {org_address}")
        p.drawString(50, height-400,"has been inspected by the Fire & Emergency Services Department of Bhavnagar ")
        p.drawString(50, height-420,"Municipal Corporation as per the applicable fire safety norms and regulations. ")
        p.drawString(50, height-440,"Based on the inspection and compliance with the prescribed fire prevention and ")
        p.drawString(50, height-460,"safety measures, the Fire NOC is granted with the following conditions:")
        
        #General Conditions
        p.setFont("Times-Bold",16)
        p.drawString(50, height-490,"General Conditions:")
        p.setFont("Times-Roman",14)
        p.drawString(50, height-510,"1.The applicant shall ensure regular maintenance of all fire safety equipment installed")
        p.drawString(50, height-530,"in the premises.")
        p.drawString(50, height-550,"2.Adequate fire prevention measures including fire extinguishers, hydrants, and alarms")
        p.drawString(50, height-570," shall be maintained at all times.")
        p.drawString(50, height-590,"3.Fire exits, escape routes, and emergency evacuation plans must be clearly marked and")
        p.drawString(50, height-610,"kept unobstructed.")
        p.drawString(50, height-630,"4.Regular fire safety drills should be conducted to train the staff/residents on emergency")
        p.drawString(50, height-650,"response.")
        p.drawString(50, height-670,"5.Any modifications or structural changes must be reported to the Fire Department for")
        p.drawString(50, height-690,"re-evaluation.")
        p.drawString(50, height-710,"6.This NOC does not exempt the applicant from obtaining any other required approvals")
        p.drawString(50, height-730,"from relevant authorities.")
        p.drawString(50, height-750,"7.The NOC is subject to renewal as per the applicable regulations and should be ")
        p.drawString(50, height-770,"renewed before the expiry date mentioned above.")

        p.showPage()

        #New Page
        p.setFont("Times-Roman",14) 
        p.drawString(50, height-50,"In case of any violation of the above-mentioned conditions, the Fire NOC is liable to be ")
        p.drawString(50,height-70,"revoked by the Bhavnagar Municipal Corporation.")
        p.drawString(50,height-100,"This Fire NOC is valid for one year from the date of issuance, after which a renewal must")
        p.drawString(50,height-120,"obtained following a fresh inspection.")
        p.drawString(50,height-150,"For further details or renewal procedures, please visit the Online Fire NOC Issuance")
        p.drawString(50,height-170,"System or contact us at: Email: cfo.bmcfire@gmail.com")

        # Signature
        p.setFont("Times-Bold",16)
        p.drawString(50,height-210,"Authorized Signatory,")
        p.setFont("Times-Roman",14)
        p.drawString(50,height-230,"Chief Fire Officer")
        p.drawString(50,height-250,"Bhavnagar Municipal Corporation")
        p.drawString(50,height-270,"Fire & Emergency Services Department")

        p.setFont("Times-Italic",14)
        p.drawString(50,height-300,"Note: This document is electronically generated and does not require a physical ")
        p.drawString(50,height-320,"signature.")

        # Save the PDF
        p.showPage()
        p.save()    

        buffer.seek(0)
        cloudinary_response = cloudinary.uploader.upload(
            buffer, 
            resource_type="auto", 
            format="pdf", 
            type="upload",
            access_mode="public",
            public_id=f"fire_noc_{name.replace(' ', '_')}"
        )
        noc_pdf_url=cloudinary_response.get("url")
        qr = qrcode.make(noc_pdf_url)
        qr_bytes = BytesIO()
        qr.save(qr_bytes, format="PNG")
        qr_bytes.seek(0)

        subject = "Your Fire NOC QR Code"
        message = f"Dear {name},\n\nYour Fire NOC has been generated successfully. Scan the QR code to access your NOC PDF.\n\nBest Regards,\nBhavnagar Municipal Corporation"

        email_msg = EmailMessage(subject, message, "your-email@gmail.com", [email])
        email_msg.attach("fire_noc_qr.png", qr_bytes.getvalue(), "image/png")  # Attach QR
        email_msg.send()
        # Save data in database
        noc = FireNOCSubmission.objects.create(
            name=name,
            email=email,
            phone=phone,
            date=date,
            org_name=org_name,
            org_address=org_address,
            fire_extinguisher=fire_extinguisher,
            fire_exit=fire_exit,
            fire_safety_sign=fire_safety_sign,
            water_infrastructure=water_infrastructure,
            noc_pdf_url=noc_pdf_url
        )
        return HttpResponse("<script>alert('Fire NOC submitted successfully! Check your email for the QR code.'); window.location.href='/';</script>")