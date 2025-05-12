import os
import json
import base64
import boto3
import numpy as np
from facenet_pytorch import MTCNN
from PIL import Image
import io

print("started")
q_service = boto3.client('sqs')
req_queue_url = ""

#Face detection code taken from the github repo in provided project document
class FaceDetection:
    def __init__(self):
        print("starting model")
        self.mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20, device='cpu')
        temp_image = Image.fromarray(np.uint8(np.random.rand(240, 240, 3) * 255))
        temp_ans = self.mtcnn(temp_image)
        print("model done")

    def face_detection_func(self, img: Image.Image, image_name, output_path="/tmp"):
        try:
            
            # Step-1: Read the image
            if not isinstance(img, Image.Image):
                img     = Image.open(img).convert("RGB")
                img     = np.array(img)
                img     = Image.fromarray(img)

            face, prob = self.mtcnn(img, return_prob=True, save_path=None)

            if face != None:
                
                os.makedirs(output_path, exist_ok=True)
                
                face_img = face - face.min() # Shift min value to 0
                face_img = face_img / face_img.max() # Normalize to range [0,1]
                face_img = (face_img * 255).byte().permute(1, 2, 0).numpy() # Convert to uint8

                # Convert numpy array to PIL Image
                face_pil = Image.fromarray(face_img, mode="RGB")
                face_img_path = os.path.join(output_path, f"{image_name}_face.jpg")
                
                # Save face image
                face_pil.save(face_img_path)
                print(f"detected face path {face_img_path}")
                return face_img_path
            
            else:
                print("No face detected")
                return None

        except Exception as e:
            print(f"error in detection: {e}")
            return None

detector = FaceDetection()

print("starting lambda")
def detection_lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        content = base64.b64decode(body['content'])
        request_id = body['request_id']
        filename = body['filename']
        
        img = Image.open(io.BytesIO(content)).convert("RGB")
        only_filename = os.path.splitext(os.path.basename(filename))[0]

        print("detection started")
        detected_img_path = detector.face_detection_func(img, image_name=only_filename)
        print("detection complete")

        if detected_img_path:
            print("enter if after detection")
            with open(detected_img_path, "rb") as f:
                img_encoded = base64.b64encode(f.read()).decode('utf-8')
                print("conversion done")

            os.remove(detected_img_path)  
            
            msg = {
                'request_id': request_id,
                'filename': filename,
                'face_detected': True,
                'content': img_encoded
            }

            q_service.send_message(
                QueueUrl=req_queue_url,
                MessageBody=json.dumps(msg)
            )

            return {
                'statusCode': 200,
                'body': json.dumps('sent to req q')
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps('ntg detected')
            }

    except Exception as e:
        print(f"error in lambda: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
