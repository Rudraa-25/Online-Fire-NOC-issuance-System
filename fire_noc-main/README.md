# Fire NOC Issuance System

A modern web application for issuing Fire No Objection Certificates (NOCs) with AI-powered image verification.

## Features

- **AI Image Verification**: Automatically validates uploaded fire safety equipment images
- **Duplicate Detection**: Prevents reuse of previously submitted images
- **PDF Certificate Generation**: Creates professional NOC documents with all required details
- **QR Code Integration**: Generated QR codes link to digital certificates
- **Email Notifications**: Automatic email delivery of NOC documents

## Technology Stack

- Django web framework
- OpenCV and scikit-learn for image processing and verification
- Cloudinary for cloud storage
- Responsive UI design with modern CSS
- PDF generation with ReportLab

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fire_noc.git
cd fire_noc

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

## Usage

1. Fill in the application form with personal and organization details
2. Upload images of fire safety equipment (extinguishers, exits, warning signs, water infrastructure)
3. The AI system will verify the authenticity of the images
4. Upon successful verification, a NOC certificate is generated and emailed to the user

## Future Enhancements

- Admin dashboard for managing applications
- Advanced machine learning for more accurate image recognition
- Integration with government databases
- Mobile application 