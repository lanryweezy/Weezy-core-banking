# Tools for Customer Onboarding Agent
import requests
from . import config
from weezy_cbs.customer_identity_management import services as customer_services
from weezy_cbs.customer_identity_management import schemas as customer_schemas
from weezy_cbs.database import get_db

def ocr_document(image_path: str) -> dict:
    """
    Parses document using an OCR service.
    Input: Path to the image file.
    Output: Parsed data as a dictionary.
    """
    # This is a placeholder. Implementation depends on the OCR service.
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(config.OCR_SERVICE_URL, files=files)
            response.raise_for_status() # Raises an exception for HTTP errors
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OCR service: {e}")
        return {"error": str(e), "details": "OCR request failed"}
    except Exception as e:
        print(f"An unexpected error occurred in ocr_document: {e}")
        return {"error": str(e), "details": "Unexpected OCR error"}


def verify_face_match(image1_path: str, image2_path: str) -> dict:
    """
    Verifies if two faces match using a face match API.
    Input: Paths to two image files.
    Output: Verification result as a dictionary.
    """
    # This is a placeholder. Implementation depends on the face match API.
    # Ensure you handle API keys securely, likely via config or environment variables.
    payload = {
        "image1": "path_or_base64_encoded_image1", # Replace with actual data prep
        "image2": "path_or_base64_encoded_image2", # Replace with actual data prep
    }
    headers = {
        "Authorization": f"Bearer {config.WEEZY_API_KEY}" # Example, adjust as needed
    }
    try:
        # Fictional paths for example, actual implementation would take image data
        # response = requests.post(config.FACE_MATCH_API_URL, json=payload, headers=headers)
        # response.raise_for_status()
        # return response.json()
        print(f"Mock call to Face Match API for {image1_path} and {image2_path}")
        # Simulate a successful response
        return {"match": True, "confidence": 0.9, "message": "Mock successful face match"}
    except requests.exceptions.RequestException as e:
        print(f"Error calling Face Match API: {e}")
        return {"error": str(e), "details": "Face Match API request failed"}
    except Exception as e:
        print(f"An unexpected error occurred in verify_face_match: {e}")
        return {"error": str(e), "details": "Unexpected Face Match error"}


def verify_bvn_nin(customer_id: int, bvn: str = None, nin: str = None) -> dict:
    """
    Verifies BVN or NIN using the respective verification API.
    Input: BVN (Bank Verification Number) or NIN (National Identity Number).
    Output: Verification result as a dictionary.
    """
    db = next(get_db())
    if bvn:
        try:
            response = customer_services.verify_bvn(db, customer_id, customer_schemas.BVNVerificationRequest(bvn=bvn), "onboarding_agent")
            return response.dict()
        except customer_services.NotFoundException as e:
            return {"error": str(e), "details": "Customer not found"}
    if nin:
        try:
            response = customer_services.verify_nin(db, customer_id, customer_schemas.NINVerificationRequest(nin=nin), "onboarding_agent")
            return response.dict()
        except customer_services.NotFoundException as e:
            return {"error": str(e), "details": "Customer not found"}

    return {"valid": False, "message": "BVN or NIN must be provided."}

if __name__ == '__main__':
    # Example usage (for testing tools individually)
    # Create dummy image files for testing if ocr_document and verify_face_match were to be run
    # with open("dummy_doc.png", "w") as f: f.write("dummy image data")
    # with open("dummy_selfie.png", "w") as f: f.write("dummy image data")

    # print("Testing OCR Tool:")
    # ocr_result = ocr_document("dummy_doc.png")
    # print(ocr_result)

    # print("\nTesting Face Match Tool:")
    # face_match_result = verify_face_match("dummy_doc.png", "dummy_selfie.png")
    # print(face_match_result)

    print("\nTesting BVN/NIN Verification Tool:")
    bvn_result = verify_bvn_nin(bvn="12345678901")
    print(bvn_result)
    nin_result = verify_bvn_nin(nin="10987654321")
    print(nin_result)
